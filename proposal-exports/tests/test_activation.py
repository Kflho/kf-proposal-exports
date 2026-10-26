"""功能激活测试：能力能被激活，而不是"文档里写了"。

按 project note「实验/测试」的要求：
- 激活条件：每个能力有可执行入口（脚本 `--help` 能跑）、文档指向存在、阶段闸门覆盖；
- 功能完整性：同一阶段的检查要封装进闸门（`deck_gate` 的 step）；taste-skill 的两个接入点
  （定令牌前决策、交付前评估）必须有可执行产物；
- 对测试的测试：能力清单与测试映射的缺口必须显式登记（`EXPECTED_GAPS`），不假装覆盖。
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import capabilities  # noqa: E402
import deck_gate  # noqa: E402

SCRIPTS = [item for item in capabilities.CAPABILITIES if item.script.endswith(".py")]


def test_capability_scripts_are_runnable():
    for item in SCRIPTS:
        path = ROOT / item.script
        assert path.is_file(), f"{item.name}：脚本不存在 {item.script}"
        proc = subprocess.run([sys.executable, str(path), "--help"],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
        assert proc.returncode == 0, f"{item.name}：--help 失败 {proc.stderr[:120]}"


def test_docs_exist():
    for item in capabilities.CAPABILITIES:
        assert (ROOT / item.doc).is_file(), f"{item.name}：文档不存在 {item.doc}"


def test_gate_covers_stage_capabilities():
    steps = set(deck_gate.DEFAULT_STEPS)
    assert {"fonts", "deck_check", "text_check", "critique", "external"} <= steps
    for item in capabilities.CAPABILITIES:
        if item.gate:
            assert item.gate in steps, f"{item.name}：闸门里没有 {item.gate} 步"


def test_taste_skill_wiring_has_artifacts():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    deck = (ROOT / "references" / "ppt-deck.md").read_text(encoding="utf-8")
    assert "deck_critique" in skill, "SKILL.md 没接审美评估脚本"
    assert "deck-critique.md" in skill, "SKILL.md 没指向审美评估规则"
    assert "critique" in deck, "页片流程没写审美评估"
    assert (ROOT / "references" / "deck-critique.md").is_file()
    assert (ROOT / "references" / "design-notes" / "deck-aesthetics.md").is_file()


def test_test_coverage_gaps_are_explicit():
    data = capabilities.report()
    assert data["coverage"] >= 0.55, f"覆盖率过低：{data['coverage']:.0%}"
    assert set(data["gaps"]) == capabilities.EXPECTED_GAPS, (
        "能力清单与登记的缺口不一致：新增能力要么补测试，要么写进 EXPECTED_GAPS")
