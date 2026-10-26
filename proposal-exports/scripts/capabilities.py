#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""capabilities.py — 能力清单与完整性报告（对测试的测试）。

每个能力一行：脚本、文档、测试、是否进闸门。`--report` 打印缺口与覆盖率，
`tests/test_activation.py` 用同一份清单断言"新增能力必须带测试或被显式登记为缺口"。

用法:
  python scripts/capabilities.py --report
  python scripts/capabilities.py --report --json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Capability:
    name: str
    script: str            # 相对 skill 根的路径
    doc: str               # 相对 skill 根的文档（说明它在哪一步）
    test: str | None       # tests/ 下的模块名（不含 .py），None = 缺口
    gate: str | None = None  # 在 deck_gate 的哪个 step 里
    external: bool = False   # 外部 skill / 工具，不算本仓脚本


CAPABILITIES: list[Capability] = [
    Capability("配图-几何自检", "scripts/check_overlap.py", "SKILL.md", "test_capabilities"),
    Capability("配图-禁用符号", "scripts/check_symbols.py", "SKILL.md", "test_capabilities"),
    Capability("配图-框间距", "scripts/check_spacing.py", "SKILL.md", "test_capabilities"),
    Capability("配图-连线端点", "scripts/check_connectors.py", "SKILL.md", "test_figure_checks"),
    Capability("配图-视觉一致性", "scripts/check_consistency.py", "SKILL.md", "test_figure_checks"),
    Capability("配图-SVG 渲染", "scripts/render_svg.py", "SKILL.md", None),
    Capability("配图-文字清单", "scripts/audit_text.py", "SKILL.md", None),
    Capability("配图-SVG→PDF", "scripts/svg_to_pdf.py", "references/external-calls.md", "test_svg_to_pdf"),
    Capability("配图-从内容生成", "scripts/layout_flow.py", "SKILL.md", None),
    Capability("页片-公式 PNG", "scripts/formula_png.py", "references/ppt-deck.md", "test_formula_png"),
    Capability("页片-静态自检+令牌", "scripts/deck_check.py", "references/ppt-deck.md",
               "test_deck_check", gate="deck_check"),
    Capability("页片-文字检查", "scripts/text_check.py", "references/text-quality.md",
               "test_text_check", gate="text_check"),
    Capability("页片-字体落实", "scripts/deck_fonts.py", "references/ppt-deck.md", "test_fonts", gate="fonts"),
    Capability("页片-交付闸门", "scripts/deck_gate.py", "references/ppt-deck.md", "test_deck_gate"),
    Capability("页片-回灌", "scripts/deck_spec.py", "references/deck-generator.md", "test_deck_spec"),
    Capability("页片-按模板出片", "scripts/deck_template.py", "references/deck-template.md", "test_deck_template"),
    Capability("页片-审美评估", "scripts/deck_critique.py", "references/deck-critique.md",
               "test_deck_critique", gate="critique"),
    Capability("页片-预览 PNG", "scripts/render_pptx_png.py", "references/ppt-deck.md", "test_render"),
    Capability("页片-换图", "scripts/update_pptx_images.py", "SKILL.md", "test_pptx_edit"),
    Capability("页片-重排图片框", "scripts/fit_pptx_frames.py", "SKILL.md", "test_pptx_edit"),
    Capability("文本-一致性", "scripts/text_consistency.py", "references/text-quality.md",
               "test_text_consistency"),
    Capability("MATLAB 出图封装", "assets/matlab/export_figure.m", "references/matlab-figures.md", None),
]

# 显式登记的缺口：没有自动测试、靠人工或外部能力覆盖。新增缺口要写在这里。
EXPECTED_GAPS = {
    "配图-SVG 渲染",
    "配图-文字清单",
    "配图-从内容生成",
    "MATLAB 出图封装",
}


def status(item: Capability) -> str:
    if item.test is None:
        return "GAP"
    if item.external:
        return "EXT"
    return "OK"


def report() -> dict:
    rows = []
    for item in CAPABILITIES:
        script_exists = (ROOT / item.script).is_file()
        doc_exists = (ROOT / item.doc).is_file()
        test_exists = item.test is not None and (ROOT / "tests" / f"{item.test}.py").is_file()
        rows.append({**asdict(item), "status": status(item),
                     "script_exists": script_exists, "doc_exists": doc_exists,
                     "test_exists": test_exists})
    covered = sum(1 for row in rows if row["test"])
    return {"total": len(rows), "covered": covered,
            "coverage": round(covered / len(rows), 3),
            "rows": rows, "gaps": sorted(row["name"] for row in rows if not row["test"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="能力清单与完整性报告")
    parser.add_argument("--report", action="store_true", help="打印能力矩阵")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = report()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return 0
    print(f"能力 {data['total']} 项，有用例 {data['covered']} 项，覆盖率 {data['coverage']:.0%}")
    print(f"{'能力':<18}{'脚本':<34}{'文档':<10}{'用例':<10}{'闸门':<10}状态")
    for row in data["rows"]:
        print(f"{row['name']:<18}{row['script']:<34}{Path(row['doc']).name:<10}"
              f"{(row['test'] or '—'):<10}{(row['gate'] or '—'):<10}{row['status']}")
    if data["gaps"]:
        print("缺口（人工/外部覆盖）：" + "、".join(data["gaps"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
