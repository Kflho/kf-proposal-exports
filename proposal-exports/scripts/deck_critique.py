#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deck_critique.py — 审美评估的机械部分（taste-skill 法条的可算版本）。

taste-skill 给的是网页的检查器；页片里能搬的是**法条**，这里把可算的挑出来：

  L1 字号档位：一页 ≤5 档、最小 ≥8pt            （两三档做可见工作）
  L2 强调色预算：每页 ≤2 处                     （一个强调，动作加一处）
  L3 平色：无渐变、无阴影                       （house rules）
  L4 居中克制：全册居中标题 ≤1 页（封面）        （居中最多一次）
  L5 轴线：标题与正文左边缘对齐（或都居中）       （左对齐为默认）
  L6 页满度：内容覆盖率 30%–92%                 （不空、不挤）
  L7 字体族：全册 ≤2 条非等宽族                  （两族为上限）
  L8 主导：最大字号 ≥ 次大字号 × 1.6            （一页一个主导）

L1–L3 是硬判（FAIL 返回 1）；L4–L8 是 REVIEW（要人看后签结论）。人工部分固定三条，
打印在报告末尾：图注贴图、数字有出处、标题连读成故事。

用法:
  python deck_critique.py deck.pptx
  python deck_critique.py deck.pptx --md out/critique.md --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import deck_check  # noqa: E402

EMU = 914400.0
GRADIENT_RE = re.compile(r"<a:gradFill\b")
SHADOW_RE = re.compile(r"<a:(?:outerShdw|innerShdw)\b")
MANUAL_PASSES = ("图注贴在图上、来源可查", "每个数字都能在正文/方案里找到出处", "标题连读能讲完故事")


@dataclass
class Finding:
    rule: str
    level: str          # "FAIL" | "REVIEW" | "PASS"
    page: int
    evidence: str


@dataclass
class Critique:
    path: str
    slides: int = 0
    findings: list[Finding] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return any(item.level == "FAIL" for item in self.findings)


def _content_shapes(slide):
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip():
            yield shape
        elif shape.shape_type == 13 or getattr(shape, "has_table", False):
            yield shape


def _area_fraction(slide, width: float, height: float) -> float:
    total = width * height
    used = 0.0
    for shape in _content_shapes(slide):
        w = shape.width / EMU
        h = shape.height / EMU
        used += max(0.0, w) * max(0.0, h)
    return min(1.0, used / total) if total else 0.0


def _text_metrics(slide):
    """返回 (最大字号, 次大字号, 标题左边缘, 正文左边缘, 是否居中)。"""
    runs = []
    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False) or not shape.text_frame.text.strip():
            continue
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                if run.font.size:
                    runs.append((run.font.size.pt, shape))
        sizes = [r.font.size.pt for p in shape.text_frame.paragraphs
                 for r in p.runs if r.font.size]
        _ = sizes
    if not runs:
        return None
    biggest = max(runs, key=lambda item: item[0])
    others = [size for size, shape in runs if shape is not biggest[1]]
    second = max(others) if others else biggest[0]
    title_shape = biggest[1]
    body = next((shape for size, shape in runs if shape is not title_shape), None)
    def _centered(shape) -> bool:
        try:
            from pptx.enum.text import PP_ALIGN
            return shape.text_frame.paragraphs[0].alignment == PP_ALIGN.CENTER
        except Exception:
            return False

    centered = _centered(title_shape)
    body_centered = _centered(body) if body is not None else False
    return {
        "max": biggest[0],
        "second": second,
        "title_left": round(title_shape.left / EMU, 2),
        "body_left": round(body.left / EMU, 2) if body is not None else None,
        "centered": bool(centered),
        "body_centered": bool(body_centered),
    }


def critique(path: Path, accent: str = deck_check.ACCENT_DEFAULT) -> Critique:
    from pptx import Presentation

    prs = Presentation(str(path))
    width = prs.slide_width / EMU
    height = prs.slide_height / EMU
    report = Critique(path=str(path), slides=len(prs.slides))
    centered_pages: list[int] = []
    fonts_cjk: set[str] = set()
    fonts_latin: set[str] = set()

    for index, slide in enumerate(prs.slides, start=1):
        sizes = sorted(set(round(float(size), 1) for size in deck_check._slide_font_sizes(slide)))
        if len(sizes) > 5:
            report.findings.append(Finding("L1 字号档位", "FAIL", index, f"{len(sizes)} 档：{sizes}"))
        if sizes and min(sizes) < 8:
            report.findings.append(Finding("L1 字号档位", "FAIL", index, f"最小 {min(sizes)}pt"))

        xml = deck_check._slide_xml(slide)
        hits = len(re.findall(r'<a:srgbClr val="%s"' % accent, xml, re.I))
        if hits > 2:
            report.findings.append(Finding("L2 强调色", "FAIL", index, f"{hits} 处"))
        if GRADIENT_RE.search(xml):
            report.findings.append(Finding("L3 平色", "FAIL", index, "出现渐变"))
        if SHADOW_RE.search(xml):
            report.findings.append(Finding("L3 平色", "FAIL", index, "出现阴影"))

        metrics = _text_metrics(slide)
        if metrics:
            if metrics["centered"] and metrics["body_left"] is not None:
                centered_pages.append(index)
            if metrics["body_left"] is not None and metrics["centered"] != metrics["body_centered"]:
                report.findings.append(
                    Finding("L5 轴线", "REVIEW", index,
                            "标题与正文对齐方式不一致（一个居中、一个左对齐）"))
            elif metrics["body_left"] is not None and \
                    abs(metrics["title_left"] - metrics["body_left"]) > 0.1:
                report.findings.append(
                    Finding("L5 轴线", "REVIEW", index,
                            f"标题左缘 {metrics['title_left']}、正文左缘 {metrics['body_left']}"))
            if metrics["second"] and metrics["max"] < metrics["second"] * 1.6:
                report.findings.append(
                    Finding("L8 主导", "REVIEW", index,
                            f"最大 {metrics['max']:g}pt / 次大 {metrics['second']:g}pt"))

        fraction = _area_fraction(slide, width, height)
        if fraction < 0.30:
            report.findings.append(Finding("L6 页满度", "REVIEW", index, f"内容只占 {fraction:.0%}"))
        elif fraction > 0.92:
            report.findings.append(Finding("L6 页满度", "REVIEW", index, f"内容占到 {fraction:.0%}"))

        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    latin, ea = deck_check._run_typefaces(run)
                    if latin:
                        fonts_latin.add(latin)
                    if ea:
                        fonts_cjk.add(ea)

    if len(centered_pages) > 1:
        report.findings.append(
            Finding("L4 居中克制", "REVIEW", 0, f"居中标题出现在 {centered_pages}"))
    if len(fonts_cjk) > 2:
        report.findings.append(Finding("L7 字体族", "REVIEW", 0, f"中文 {sorted(fonts_cjk)}"))
    if len(fonts_latin) > 2:
        report.findings.append(Finding("L7 字体族", "REVIEW", 0, f"西文 {sorted(fonts_latin)}"))
    return report


def to_markdown(report: Critique, notes: list[str] | None = None,
                preserve: str | None = None) -> str:
    fails = [f for f in report.findings if f.level == "FAIL"]
    reviews = [f for f in report.findings if f.level == "REVIEW"]
    lines = [
        "# 页片审美评估（deck_critique）",
        "",
        f"- 文件：`{report.path}`",
        f"- 页数：{report.slides}",
        f"- 硬判 FAIL：{len(fails)}；人工复核 REVIEW：{len(reviews)}",
        "",
        "| 规则 | 级别 | 页 | 证据 |",
        "| --- | --- | --- | --- |",
    ]
    for item in report.findings:
        lines.append(f"| {item.rule} | {item.level} | {item.page or '-'} | {item.evidence} |")
    lines += ["", "## 人工三项（必须逐页看过再签）", ""]
    lines += [f"- [ ] {item}" for item in MANUAL_PASSES]
    lines += ["", "## 复核理由（REVIEW 逐条写）", ""]
    lines += [f"- {note}" for note in (notes or [])] or ["- （尚未填写）"]
    if preserve:
        lines += ["", preserve.rstrip()]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="页片审美评估（taste-skill 法条的机械部分）")
    parser.add_argument("deck", help="待评估的 .pptx")
    parser.add_argument("--accent", default=deck_check.ACCENT_DEFAULT, help="强调色 RRGGBB")
    parser.add_argument("--md", help="把评估报告写到该 Markdown")
    parser.add_argument("--note", action="append", default=[],
                        help="复核理由（可多次传入；重跑时保留）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    deck = Path(args.deck)
    if not deck.is_file():
        print(f"错误：找不到 {deck}", file=sys.stderr)
        return 2
    try:
        report = critique(deck, accent=args.accent)
    except ModuleNotFoundError as exc:
        print(f"错误：缺少依赖（{exc.name}）：pip install python-pptx", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI 边界
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    if args.md:
        md_path = Path(args.md)
        preserve = None
        if md_path.is_file():
            old = md_path.read_text(encoding="utf-8")
            marker = "## 复核理由"
            if marker in old:
                preserve = old[old.index(marker):]
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(to_markdown(report, args.note, preserve), encoding="utf-8")
    if args.json:
        print(json.dumps({"path": report.path, "slides": report.slides,
                          "failed": report.failed,
                          "findings": [asdict(item) for item in report.findings]},
                         ensure_ascii=False, indent=1))
    else:
        fails = [item for item in report.findings if item.level == "FAIL"]
        reviews = [item for item in report.findings if item.level == "REVIEW"]
        print(f"{report.path}：{report.slides} 页，FAIL {len(fails)} / REVIEW {len(reviews)}")
        for item in fails + reviews:
            print(f"  [{item.level}] P{item.page or '-':<2} {item.rule}：{item.evidence}")
        print("人工三项：" + "；".join(MANUAL_PASSES))
        if args.md:
            print(f"报告：{args.md}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
