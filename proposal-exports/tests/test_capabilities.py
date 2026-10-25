"""能力级 smoke：配图模板过自检、页片从公式到 pptx 再到两项检查。

与单元测试的分工：这里只验证“交付流程真的能跑通”，不重复测每个函数分支。
- 配图：仓库自带的 `assets/template.svg` 必须过 `check_overlap` / `check_symbols` / `check_spacing`；
- 页片：公式 PNG → `gen_deck.js` → `deck_check --strict --require-notes` → `text_check`。
  Node 依赖（`pptxgenjs`）没装时跳过页片这一项，不让测试环境失败。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PPTXGEN = ROOT / "node_modules" / "pptxgenjs"


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_shipped_svg_template_passes_checks() -> None:
    template = ROOT / "assets" / "template.svg"
    overlap = run([sys.executable, str(ROOT / "scripts" / "check_overlap.py"), str(template)])
    symbols = run([sys.executable, str(ROOT / "scripts" / "check_symbols.py"), str(template)])
    spacing = run([sys.executable, str(ROOT / "scripts" / "check_spacing.py"), str(template)])
    assert overlap.returncode == 0, overlap.stdout + overlap.stderr
    assert symbols.returncode == 0, symbols.stdout + symbols.stderr
    assert spacing.returncode == 0, spacing.stdout + spacing.stderr


@pytest.mark.skipif(not PPTXGEN.is_dir(), reason="未安装 pptxgenjs（npm install）")
def test_deck_end_to_end(tmp_path: Path) -> None:
    deck = tmp_path / "deck"
    shutil.copytree(ROOT / "assets" / "deck", deck)

    formula = run([
        sys.executable,
        str(ROOT / "scripts" / "formula_png.py"),
        str(deck / "formulas.example.json"),
        "--out",
        str(deck / "formulas"),
    ])
    assert formula.returncode == 0, formula.stdout + formula.stderr

    pptx = tmp_path / "deck.pptx"
    env = dict(os.environ, NODE_PATH=str(ROOT / "node_modules"))
    gen = subprocess.run(
        ["node", str(deck / "gen_deck.js"), "--out", str(pptx)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert gen.returncode == 0, gen.stdout + gen.stderr
    assert pptx.is_file()

    deck_check = run([
        sys.executable,
        str(ROOT / "scripts" / "deck_check.py"),
        str(pptx),
        "--strict",
        "--require-notes",
    ])
    text_check = run([sys.executable, str(ROOT / "scripts" / "text_check.py"), str(pptx)])
    assert deck_check.returncode == 0, deck_check.stdout + deck_check.stderr
    assert text_check.returncode == 0, text_check.stdout + text_check.stderr
