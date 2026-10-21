#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deck_check.py — .pptx 静态自检：16:9、安全边距、图片拉伸、文字溢出、备注、占位符。

为什么要有它：中文页片最常见的四类返工——贴边、图被拉扁、文字挤出框、
改完留了 TODO——靠眼睛看容易漏；这里全部变成可数的 entry。

用法:
  python deck_check.py deck.pptx
  python deck_check.py deck.pptx --strict --require-notes
  python deck_check.py deck.pptx --json > report.json

判据（与 references/ppt-deck.md 一致）:
  - 画布比例 16:9，容差 2%；
  - 安全边距 0.5in（背景级元素除外，面积 ≥85% 视为背景）；
  - 图片原生比例与摆放比例差 >2% = 拉伸（error）；
  - 文字估算高度超过文本框 5% = 溢出（默认 warning，--strict 变 error）；
  - 每页备注 <10 字 = warning（--require-notes 变 error）；
  - TODO/XXX/lorem/待补 等占位符 = error。

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
               strict: bool = False, overflow_tol: float = 0.05) -> Report:
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
    parser.add_argument("--strict", action="store_true", help="文字溢出算 error")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    try:
        report = check_deck(args.deck, margin=args.margin, aspect_tol=args.aspect_tol,
                            min_notes=args.min_notes, require_notes=args.require_notes,
                            strict=args.strict)
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
