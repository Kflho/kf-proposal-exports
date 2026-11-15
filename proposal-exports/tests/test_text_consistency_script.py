# -*- coding: utf-8 -*-
"""text_consistency.py 的报告产物检查：图片链接、alt、图注、图号、孤立图。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "text_consistency", ROOT / "scripts" / "text_consistency.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MOD)


def _project(tmp_path: Path):
    exports = tmp_path / "bin" / "exports"
    figures = exports / "figures"
    figures.mkdir(parents=True)
    (figures / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    return exports, figures


def test_scan_skips_dependencies_and_history(tmp_path: Path) -> None:
    for rel in ("node_modules", "bin/reference_docs/technical_solution_docs"):
        folder = tmp_path / rel
        folder.mkdir(parents=True)
        (folder / "a.md").write_text("随着时代的发展，问题自然会解决。\n", encoding="utf-8")
    assert MOD.scan(tmp_path) == []


def test_default_output_hides_warnings(tmp_path: Path, capsys) -> None:
    (tmp_path / "README.md").write_text("这不是更细，而是更啰嗦。\n", encoding="utf-8")
    assert MOD.main(["--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "A1" not in out
    MOD.main(["--root", str(tmp_path), "--warnings"])
    out = capsys.readouterr().out
    assert "A1" in out


def test_absolute_root_with_data_segment_is_scanned(tmp_path: Path) -> None:
    root = tmp_path / "data" / "proj"
    root.mkdir(parents=True)
    (root / "README.md").write_text("这不是更细，而是更啰嗦。\n", encoding="utf-8")
    assert MOD.scan(root), "绝对路径里的 data 段不该让整个项目被跳过"


def _rules(findings):
    return {item["rule"] for item in findings}


def test_report_artifacts_flagged(tmp_path: Path):
    exports, figures = _project(tmp_path)
    (figures / "b.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (figures / "orphan.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (exports / "report.md").write_text(
        "![状态](figures/a.png)\n"
        "*图 1　状态响应*\n"
        "\n"
        "![控制量](figures/b.png)\n"
        "\n"
        "![](figures/missing.png)\n",
        encoding="utf-8",
    )
    rules = _rules(MOD.scan(tmp_path, include_exports=True))
    assert "ART-IMG-MISSING" in rules
    assert "ART-IMG-ALT" in rules
    assert "ART-IMG-CAPTION" in rules
    assert "ART-IMG-ORPHAN" in rules


def test_report_artifacts_clean(tmp_path: Path):
    exports, _ = _project(tmp_path)
    (exports / "report.md").write_text(
        "![状态](figures/a.png)\n"
        "*图 1　状态响应*\n",
        encoding="utf-8",
    )
    rules = _rules(MOD.scan(tmp_path, include_exports=True))
    assert not {r for r in rules if r.startswith("ART-")}


def test_figure_numbering(tmp_path: Path):
    exports, _ = _project(tmp_path)
    (exports / "figures" / "b.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (exports / "report.md").write_text(
        "![状态](figures/a.png)\n"
        "*图 1　状态响应*\n"
        "\n"
        "![控制量](figures/b.png)\n"
        "*图 3　控制量*\n",
        encoding="utf-8",
    )
    rules = _rules(MOD.scan(tmp_path, include_exports=True))
    assert "ART-FIG-NUM" in rules
