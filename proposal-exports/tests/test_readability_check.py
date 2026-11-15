# -*- coding: utf-8 -*-
"""可读性检查的行为测试：判据来自 references/text-quality.md「可读性」。

守的是这几类「离开上下文就读不懂」的写法：
- R1 指代开头（它 / 这个 / 该 / 上面…）；
- R2 方位词指界面（顶部 / 这一行 / 记录里…）；
- R3 引号里的口语标签当名字（「我现在」）；
- R4 名词化堆叠（写着…的编号）；
- 测试用例名与 Markdown 标题也要扫（读者一样需要读懂）。
"""
from __future__ import annotations

from pathlib import Path

import readability_check as rc


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def scan(root: Path, tests: Path | None = None, allow: list[str] | None = None):
    config = {"allow": allow or [], "glossary": ""}
    return rc.scan(root, tests, config)


def test_deictic_opener_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "src/ui.ts", "new Notice('它还没有上报状态');\n")
    findings, _ = scan(tmp_path)
    assert any(item["rule"] == "R1" for item in findings)


def test_position_word_in_heading_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "README.md", "# 记录顶部写着编号\n\n正文。\n")
    findings, _ = scan(tmp_path)
    assert any(item["rule"] == "R2" and item["where"] == "标题" for item in findings)


def test_quoted_colloquial_label_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "src/ui.ts", "new Notice('记录写着「我现在」的编号');\n")
    findings, _ = scan(tmp_path)
    assert any(item["rule"] == "R3" for item in findings)


def test_nominal_chain_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "src/ui.ts", "new Notice('窗口显示本机的编号。');\n")
    findings, _ = scan(tmp_path)
    assert any(item["rule"] == "R4" for item in findings)


def test_test_case_names_are_scanned(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    write(tests, "a.test.ts", "check('它要送到的那份指纹', 1);\n")
    findings, _ = scan(tmp_path, tests)
    assert any(item["where"] == "测试名" and item["rule"] == "R1" for item in findings)


def test_allow_list_suppresses_term(tmp_path: Path) -> None:
    write(tmp_path, "src/ui.ts", "new Notice('它还没有上报状态');\n")
    findings, _ = scan(tmp_path, allow=["它"])
    assert findings == []


def test_glossary_suppresses_term_count(tmp_path: Path) -> None:
    write(tmp_path, "bin/reference_docs/术语表.md", "完整副本：整个仓库的一份快照。\n")
    write(tmp_path, "src/ui.ts", "new Notice('已导出一份完整副本。');\n")
    _, terms = scan(tmp_path)
    assert "完整副本" not in terms
    assert "留包" not in terms  # 没出现的词也不该被统计


def test_clean_text_has_no_finding(tmp_path: Path) -> None:
    write(tmp_path, "src/ui.ts", "new Notice('已导出一份完整副本，需要手动复制给对方。');\n")
    findings, _ = scan(tmp_path)
    assert findings == []


def test_missing_root_exits_2(tmp_path: Path) -> None:
    assert rc.main(["--root", str(tmp_path / "nope")]) == 2
