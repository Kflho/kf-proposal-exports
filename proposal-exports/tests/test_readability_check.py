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


def test_metaphor_verb_in_comment_is_warning(tmp_path: Path) -> None:
    write(tmp_path, "src/a.ts", "// 测试守着这条规则。\n")
    findings, _ = rc.scan(tmp_path, None, {"allow": [], "glossary": ""}, comments=True)
    hit = next(item for item in findings if item["rule"] == "R7")
    assert hit["where"] == "注释"
    assert hit["severity"] == "warning"


def test_metaphor_verb_in_test_name_is_error(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    write(tests, "a.test.ts", "check('它守着这条规则', 1);\n")
    findings, _ = rc.scan(tmp_path, tests, {"allow": [], "glossary": ""})
    hit = next(item for item in findings if item["rule"] == "R7")
    assert hit["severity"] == "error"


def test_compressed_pair_phrase_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "src/a.ts", "// 只写在测什么、守在哪。\n")
    findings, _ = rc.scan(tmp_path, None, {"allow": [], "glossary": ""}, comments=True)
    assert any(item["rule"] == "R8" for item in findings)


def test_leading_reference_in_comment_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "src/a.ts", "new Notice('这里说明原因。');\n")
    findings, _ = scan(tmp_path)
    assert any(item["rule"] == "R9" for item in findings)


def test_heading_repeated_by_first_paragraph(tmp_path: Path) -> None:
    write(tmp_path, "README.md", "## 完整备份是基准\n\n完整备份是基准，更新包不改变它。\n")
    findings, _ = scan(tmp_path)
    assert any(item["rule"] == "R10" for item in findings)


def test_setting_description_echo_is_error(tmp_path: Path) -> None:
    write(tmp_path, "src/settings.ts", "name: '显示用户名',\n\t\t\t\t\tdesc: '聊天记录显示用户名。',\n")
    findings, _ = scan(tmp_path)
    hit = next(item for item in findings if item["rule"] == "R11")
    assert hit["severity"] == "error"


def test_clean_setting_is_not_reported(tmp_path: Path) -> None:
    write(tmp_path, "src/settings.ts", "name: '保留签名',\n\t\t\t\t\tdesc: '默认关闭；开启后保留楼中楼的签名。',\n")
    findings, _ = scan(tmp_path)
    assert not any(item["rule"] == "R11" for item in findings)


def test_setting_without_description_is_allowed(tmp_path: Path) -> None:
    write(tmp_path, "src/settings.ts", "name: '显示用户名',\n\t\t\t\t\tcontrol: { type: 'toggle' },\n")
    findings, _ = scan(tmp_path)
    assert not any(item["rule"] == "R11" for item in findings)


def test_bare_demonstrative_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "src/a.ts", "new Notice('只排版刚粘贴的那一段。');\n")
    findings, _ = scan(tmp_path)
    assert any(item["rule"] == "R12" for item in findings)


def test_elliptical_predicate_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "src/a.ts", "new Notice('原图不留。');\n")
    findings, _ = scan(tmp_path)
    assert any(item["rule"] == "R13" for item in findings)


def test_glossary_alias_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "readability.json", '{"glossary": "术语表.md", "allow": []}')
    write(
        tmp_path,
        "术语表.md",
        "| 概念 | 唯一叫法 | 禁用别名 | 定义 |\n| --- | --- | --- | --- |\n"
        "| 搬运文件 | **同步包** | 留包、包 | 一个文件 |\n"
        "| 镜像 | **镜像** | —（技术词，保留） | 覆盖 |\n",
    )
    write(tmp_path, "src/a.ts", "new Notice('留包失败。');\n")
    findings, _ = rc.scan(tmp_path, None, rc.load_config(tmp_path))
    hit = next(item for item in findings if item["rule"] == "R14")
    assert hit["matched"] == "留包"
    assert "同步包" in hit["advice"]


def test_glossary_file_itself_is_not_flagged(tmp_path: Path) -> None:
    write(tmp_path, "readability.json", '{"glossary": "术语表.md", "allow": []}')
    write(
        tmp_path,
        "术语表.md",
        "| 概念 | 唯一叫法 | 禁用别名 | 定义 |\n| --- | --- | --- | --- |\n"
        "| 搬运文件 | **同步包** | 留包、包 | 一个文件 |\n"
        "| 镜像 | **镜像** | —（技术词，保留） | 覆盖 |\n",
    )
    findings, _ = rc.scan(tmp_path, None, rc.load_config(tmp_path))
    assert not any(item["rule"] == "R14" for item in findings)


def test_reworded_setting_echo_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "src/settings.ts", "name: '整理时转换图片格式',\n\t\t\t\t\tdesc: '整理图片时转换格式。',\n")
    findings, _ = scan(tmp_path)
    assert any(item["rule"] == "R11" for item in findings)
