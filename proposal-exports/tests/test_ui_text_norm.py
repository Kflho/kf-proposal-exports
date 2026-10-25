# -*- coding: utf-8 -*-
"""用户交互文字规范：只在提示状态 / 要求操作时才说话，其余静默。

这条规范是用户拍板的（"防止频繁文字显示，仅显示提示用户状态或要求用户操作的文字"），
在 `references/text-review.md` 里写详细判断，`SKILL.md` 里给一句触发条件 + 指路。
机械检查能守住的只有"规范还在、两处没走散"；产品行为由各项目自己的测试守
（该静默时弹了提示就是 bug）。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTION = "## 用户交互文字（弹窗 / 界面 / 状态栏）"


def test_section_exists_in_text_review() -> None:
    text = (ROOT / "references" / "text-quality.md").read_text(encoding="utf-8")
    assert SECTION in text, "text-review.md 缺少「用户交互文字」一节"


def test_section_states_both_categories_and_silence_rule() -> None:
    text = (ROOT / "references" / "text-quality.md").read_text(encoding="utf-8")
    section = text.split(SECTION, 1)[1].split("\n## ", 1)[0]
    for keyword in ["当前状态", "要求用户操作", "不播报", "该静默"]:
        assert keyword in section, f"「用户交互文字」一节缺关键判据：{keyword}"


def test_skill_md_points_to_the_section() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "面向用户的界面文字" in text, "SKILL.md 没写界面文字规范"
    assert "text-quality.md" in text, "SKILL.md 的指路链接变了"
