#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deck_check.py — .pptx 静态自检：16:9、安全边距、图片拉伸、文字溢出、备注、占位符，加令牌检查。

为什么要有它：中文页片最常见的四类返工——贴边、图被拉扁、文字挤出框、
改完留了 TODO——靠眼睛看容易漏；这里全部变成可数的 entry。
令牌检查（design-notes/deck-aesthetics.md）：一页最多五档字号、强调色每页 ≤2 处、
不用渐变与阴影。这三条是外部 skill 不管、又最容易"看着像 AI 做的"的地方。

用法:
  python deck_check.py deck.pptx
  python deck_check.py deck.pptx --strict --require-notes
  python deck_check.py deck.pptx --scale 54,33,18,12,10 --accent E8A33D
  python deck_check.py deck.pptx --json > report.json

判据（与 references/ppt-deck.md 一致）:
  - 画布比例 16:9，容差 2%；
  - 安全边距 0.5in（背景级元素除外，面积 ≥85% 视为背景）；
  - 图片原生比例与摆放比例差 >2% = 拉伸（error）；
  - 文字估算高度超过文本框 5% = 溢出（默认 warning，--strict 变 error）；
  - 每页备注 <10 字 = warning（--require-notes 变 error）；
  - TODO/XXX/lorem/待补 等占位符 = error；
  - 字号 <8pt = error（投影不可读）；一页 >5 种字号 = warning；给了 --scale 时不在档位 = warning；
  - 强调色每页超过 --accent-budget（默认 2）= warning（--strict 变 error）；
  - 渐变/阴影 = error（用平色与色阶分层）。

退出码: 0 无 error；1 有 error；2 环境/参数错误（如没装 python-pptx）。
依赖: python-pptx（读几何/图片），Pillow（量字，缺了则只跳过溢出估算并提示）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PLACEHOLDER_RE = re.compile(r"\bTODO\b|\bXXX+\b|lorem|ipsum|待补|待填|\[insert", re.I)
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)
ASPECT_16X9 = 16 / 9
ACCENT_DEFAULT = "E8A33D"
GRADIENT_RE = re.compile(r"<a:gradFill\b")
SHADOW_RE = re.compile(r"<a:(?:outerShdw|innerShdw)\b")
# 字体规范（project note → 论文撰写 → 字体）：标题黑体、正文宋体、英文 Times New Roman
ALLOWED_FONTS = {
    "SimHei", "黑体", "SimSun", "宋体", "Times New Roman",
    "Arial", "Consolas", "Cambria Math", "Microsoft YaHei", "微软雅黑",
}
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _run_typefaces(run) -> tuple[str | None, str | None]:
    """读 run 的 (latin, ea) 字体名；python-pptx 只暴露 latin，中文要读 `a:ea`。"""
    from pptx.oxml.ns import qn

    latin = ea = None
    rpr = run._r.find(qn("a:rPr"))
    if rpr is not None:
        latin_node = rpr.find(qn("a:latin"))
        ea_node = rpr.find(qn("a:ea"))
        latin = latin_node.get("typeface") if latin_node is not None else None
        ea = ea_node.get("typeface") if ea_node is not None else None
    if latin is None and run.font.name:
        latin = run.font.name
    return latin, ea


def _slide_xml(slide) -> str:
    """把一页的形状 XML 拼起来：查颜色/渐变/阴影比逐属性读 python-pptx 稳。"""
    parts = []
    for shape in slide.shapes:
        element = getattr(shape, "_element", None)
        if element is not None:
            parts.append(element.xml)
    return "".join(parts)


def _slide_font_sizes(slide) -> list[float]:
    sizes: list[float] = []
    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False):
            continue
        for para in shape.text_frame.paragraphs:
            if para.font.size is not None:
                sizes.append(round(float(para.font.size.pt), 2))
            for run in para.runs:
                if run.font.size is not None:
                    sizes.append(round(float(run.font.size.pt), 2))
    return sizes


@dataclass
class Issue:
    level: str          # "error" | "warning"
    code: str
    slide: int
    message: str


@dataclass
class Report:
    path: str
    slides: int = 0
    size: tuple[float, float] = (0.0, 0.0)
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    checked: dict[str, bool] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def _inches(value) -> float:
    return float(value or 0) / 914400.0


def _font(size_pt: int):
    from PIL import ImageFont
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size_pt)
            except Exception:
                continue
    return None


def _wrap_count(text: str, font, max_width_pt: float) -> int:
    """按字符贪心折行（中文逐字、西文也逐字，偏保守）。"""
    if not text:
        return 1
    lines, cur = 1, 0.0
    for ch in text:
        width = font.getlength(ch)
        if cur + width > max_width_pt and cur > 0:
            lines += 1
            cur = width
        else:
            cur += width
    return lines


def estimate_text_height_in(text_frame, width_in: float) -> float | None:
    """粗估文字高度（英寸）。字体缺失返回 None（不假装能查）。"""
    usable_pt = max(width_in - 0.2, 0.1) * 72.0     # 文本框左右内边距各 0.1in
    total_pt = 0.0
    for para in text_frame.paragraphs:
        text = "".join(run.text for run in para.runs) or para.text
        if not text.strip():
            total_pt += 6.0                            # 空行
            continue
        size = next((r.font.size.pt for r in para.runs if r.font.size), 18.0)
        font = _font(int(round(size)))
        if font is None:
            return None
        lines = _wrap_count(text, font, usable_pt)
        total_pt += lines * size * 1.2
        if para.space_after is not None:
            total_pt += para.space_after.pt
        if para.space_before is not None:
            total_pt += para.space_before.pt
    return total_pt / 72.0


def check_deck(path, margin: float = 0.5, aspect_tol: float = 0.02,
               min_notes: int = 10, require_notes: bool = False,
               strict: bool = False, overflow_tol: float = 0.05,
               accent: str = ACCENT_DEFAULT, accent_budget: int = 2,
               type_scale: list[float] | None = None,
               min_type_pt: float = 8.0,
               title_ea: str | None = None, body_ea: str | None = None,
               title_min_pt: float = 30.0) -> Report:
    from pptx import Presentation

    path = Path(path)
    prs = Presentation(str(path))
    report = Report(path=str(path), slides=len(prs.slides))
    width, height = _inches(prs.slide_width), _inches(prs.slide_height)
    report.size = (width, height)

    def add(level: str, code: str, slide: int, message: str):
        (report.errors if level == "error" else report.warnings).append(
            Issue(level=level, code=code, slide=slide, message=message))

    if height <= 0 or abs(width / height - ASPECT_16X9) > 0.02:
        add("error", "aspect-ratio", 0,
            f"画布 {width:.3f}x{height:.3f} in，不是 16:9（13.333x7.5）")

    report.checked["text-overflow"] = True
    for index, slide in enumerate(prs.slides, start=1):
        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
        if len(notes) < min_notes:
            level = "error" if require_notes else "warning"
            add(level, "notes", index, f"备注只有 {len(notes)} 字（要求 ≥{min_notes}）")

        for shape in slide.shapes:
            left, top = _inches(shape.left), _inches(shape.top)
            w, h = _inches(shape.width), _inches(shape.height)
            if w <= 0 or h <= 0:
                continue
            is_background = (w * h) >= 0.85 * width * height

            # 1) 安全边距（只查内容元素：有字的文本框/图片/表格；装饰形状允许出血）
            is_content = (shape.shape_type in (13, 19)
                          or (shape.has_text_frame and shape.text_frame.text.strip()))
            if not is_background and is_content:
                out = []
                if left < margin - 1e-6:
                    out.append(f"左边距 {left:.2f}in")
                if top < margin - 1e-6:
                    out.append(f"上边距 {top:.2f}in")
                if width - (left + w) < margin - 1e-6:
                    out.append(f"右边距 {width - (left + w):.2f}in")
                if height - (top + h) < margin - 1e-6:
                    out.append(f"下边距 {height - (top + h):.2f}in")
                if out:
                    add("error", "margin", index, "超出安全区：" + "，".join(out))

            # 2) 图片拉伸
            if shape.shape_type == 13:                     # PICTURE
                try:
                    native_w, native_h = shape.image.size
                    if native_w and native_h:
                        ratio = (w / h) / (native_w / native_h)
                        if abs(ratio - 1) > aspect_tol:
                            add("error", "image-stretch", index,
                                f"图片比例 {ratio:.3f}（1 表示未拉伸）："
                                f"框 {w:.2f}x{h:.2f}in，原图 {native_w}x{native_h}px")
                except Exception:
                    pass

            # 3) 文字溢出 / 占位符
            if shape.has_text_frame:
                text = shape.text_frame.text
                if PLACEHOLDER_RE.search(text):
                    add("error", "placeholder", index,
                        f"疑似占位符：{text.strip()[:24]!r}")
                est = estimate_text_height_in(shape.text_frame, w)
                if est is None:
                    report.checked["text-overflow"] = False
                elif est > h * (1 + overflow_tol):
                    level = "error" if strict else "warning"
                    add(level, "text-overflow", index,
                        f"文字估算 {est:.2f}in > 框高 {h:.2f}in（{text.strip()[:16]!r}）")

        # 4) 令牌：渐变与阴影（用平色和色阶分层，别用装饰）
        xml = _slide_xml(slide)
        if GRADIENT_RE.search(xml):
            add("error", "gradient-fill", index, "出现渐变填充/底色：改用平色或同色系色阶")
        if SHADOW_RE.search(xml):
            add("error", "shadow-effect", index, "出现阴影：用底色深浅分层代替")

        # 5) 令牌：强调色预算（一页最多两处：结论数字 + 一处框线/引线）
        accent_hits = len(re.findall(r'<a:srgbClr val="%s"' % accent, xml, re.I))
        if accent_hits > accent_budget:
            level = "error" if strict else "warning"
            add(level, "accent-budget", index,
                f"强调色 #{accent} 出现 {accent_hits} 处（上限 {accent_budget}）")

        # 6) 令牌：字号档位（投影最小 8pt；一页最多五档；可给 --scale 白名单）
        sizes = _slide_font_sizes(slide)
        report.checked["type-scale"] = True
        too_small = [s for s in sizes if s < min_type_pt]
        if too_small:
            add("error", "type-too-small", index,
                f"字号 {min(too_small):g}pt < {min_type_pt:g}pt，投影不可读")
        distinct = sorted(set(sizes))
        if len(distinct) > 5:
            add("warning", "type-scale", index,
                f"一页 {len(distinct)} 种字号 {distinct}，上限 5 档")
        if type_scale:
            off_scale = [s for s in distinct
                         if all(abs(s - allowed) > 0.6 for allowed in type_scale)]
            if off_scale:
                add("warning", "type-scale", index,
                    f"字号 {off_scale} 不在档位 {type_scale} 内")

        # 7) 字体：字体族、中英分工、角色一致
        bad_faces: set[str] = set()
        missing_ea = 0
        role_mismatch = 0
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    latin, ea = _run_typefaces(run)
                    for face in (latin, ea):
                        if face and face not in ALLOWED_FONTS:
                            bad_faces.add(face)
                    if CJK_RE.search(run.text or "") and not ea:
                        missing_ea += 1
                    if title_ea and body_ea and ea:
                        size = run.font.size
                        is_title = size is not None and size.pt >= title_min_pt
                        want = title_ea if is_title else body_ea
                        if ea != want:
                            role_mismatch += 1
        report.checked["font-spec"] = True
        if bad_faces:
            add("warning", "font-face", index,
                f"字体不在规范表：{sorted(bad_faces)}（标题 SimHei / 正文 SimSun / 西文 Times New Roman）")
        if missing_ea:
            add("warning", "font-ea-missing", index,
                f"{missing_ea} 个中文 run 没写 a:ea：换机器会回退、字宽会变")
        if role_mismatch:
            add("warning", "font-role", index,
                f"{role_mismatch} 个 run 的中文字体与角色不符（标题 {title_ea} / 正文 {body_ea}）")
    return report


def report_to_dict(report: Report) -> dict:
    payload = asdict(report)
    payload["size"] = list(report.size)
    payload["ok"] = report.ok
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=".pptx 静态自检")
    parser.add_argument("deck", help="待检查的 .pptx")
    parser.add_argument("--margin", type=float, default=0.5, help="安全边距（英寸，默认 0.5）")
    parser.add_argument("--aspect-tol", type=float, default=0.02, help="图片比例容差（默认 2%%）")
    parser.add_argument("--min-notes", type=int, default=10, help="备注最少字数（默认 10）")
    parser.add_argument("--require-notes", action="store_true", help="备注不足算 error")
    parser.add_argument("--strict", action="store_true", help="文字溢出与强调色超预算算 error")
    parser.add_argument("--accent", default=ACCENT_DEFAULT, help="强调色 RRGGBB（默认 %(default)s）")
    parser.add_argument("--accent-budget", type=int, default=2, help="每页强调色出现上限（默认 2）")
    parser.add_argument("--scale", default="", help="允许的字号档位，逗号分隔（如 54,33,18,12,10）")
    parser.add_argument("--min-type-pt", type=float, default=8.0, help="最小字号（默认 8pt）")
    parser.add_argument("--title-ea", default="", help="标题中文字体（给值才查角色一致，如 SimHei）")
    parser.add_argument("--body-ea", default="", help="正文中文字体（如 SimSun）")
    parser.add_argument("--title-min-pt", type=float, default=30.0,
                        help="≥ 该字号算标题（默认 %(default)s）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    scale = ([float(part) for part in args.scale.replace("，", ",").split(",") if part.strip()]
             if args.scale else None)

    try:
        report = check_deck(args.deck, margin=args.margin, aspect_tol=args.aspect_tol,
                            min_notes=args.min_notes, require_notes=args.require_notes,
                            strict=args.strict, accent=args.accent,
                            accent_budget=args.accent_budget, type_scale=scale,
                            min_type_pt=args.min_type_pt,
                            title_ea=args.title_ea or None,
                            body_ea=args.body_ea or None,
                            title_min_pt=args.title_min_pt)
    except ModuleNotFoundError as exc:
        print(f"错误：缺少依赖（{exc.name}）：pip install python-pptx pillow", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI 边界
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report_to_dict(report), indent=1, ensure_ascii=False))
    else:
        print(f"{report.path}：{report.slides} 页，{report.size[0]:.3f}x{report.size[1]:.3f} in")
        for issue in report.errors + report.warnings:
            mark = "E" if issue.level == "error" else "W"
            print(f"  [{mark}] slide {issue.slide} [{issue.code}] {issue.message}")
        print(f"summary: {len(report.errors)} error / {len(report.warnings)} warning")
        if not report.checked.get("text-overflow", True):
            print("提示：没找到可用中文字体，跳过文字溢出估算（装微软雅黑或改 FONT_CANDIDATES）")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
