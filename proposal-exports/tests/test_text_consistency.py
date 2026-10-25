# -*- coding: utf-8 -*-
"""文本一致性：仓库内文档的用词、标题层级、相对链接、非备忘录检查。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = sorted([ROOT / "SKILL.md", *ROOT.glob("references/*.md"), *ROOT.glob("templates/*.md")])

# 同一对象只允许一种拼法；忽略代码片段与带连字符的仓库名（obsidian-locally-save）
CANONICAL = {
    "kf-personal-development": ["kf_personal_development", "kf personal development"],
    "kf-personal-service": ["kf_personal_service", "kf personal service"],
    "kf-personal-data": ["kf_personal_data", "kf personal data"],
    "kf-development-project": ["kf_development_project", "kf development project"],
}

MEMO = re.compile(r"20\d\d-\d\d-\d\d")
FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`]*`")


def body(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def prose(path: Path) -> str:
    """去掉代码块与行内代码：命令、路径、示例不参与用词检查。"""
    return INLINE_CODE.sub("", FENCE.sub("", body(path)))


def lines_without_fence(path: Path):
    in_fence = False
    for number, line in enumerate(body(path).splitlines(), 1):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def test_headings_do_not_skip_levels() -> None:
    bad, previous = [], 0
    for path in DOCS:
        for number, line in lines_without_fence(path):
            match = re.match(r"^(#{1,6})\s", line)
            if not match:
                continue
            level = len(match.group(1))
            if previous and level > previous + 1:
                bad.append(f"{path.name}:{number} 从 {'#' * previous} 跳到 {'#' * level}")
            previous = level
    assert not bad, "标题层级跳级：\n" + "\n".join(bad)


def test_single_top_level_heading() -> None:
    TABLE_SKIP = True
    bad = [p.name for p in DOCS
           if sum(1 for _, line in lines_without_fence(p) if re.match(r"^#\s", line)) > 1]
    assert not bad, f"一份文档只能有一个一级标题：{bad}"


def test_canonical_nouns() -> None:
    TABLE_SKIP = True
    bad = []
    for path in DOCS:
        text = prose(path)
        for canonical, wrong in CANONICAL.items():
            for variant in wrong:
                if variant in text:
                    bad.append(f"{path.name}: 用「{variant}」，应统一为「{canonical}」")
        # 单独出现的 obsidian（不带连字符、不在代码里）统一写 Obsidian
        for match in re.finditer(r"(?<![-`\w])obsidian(?![-`\w])", text):
            bad.append(f"{path.name}: 用「obsidian」，应统一为「Obsidian」")
    assert not bad, "用词不一致：\n" + "\n".join(sorted(set(bad)))



def test_relative_links_resolve() -> None:
    TABLE_SKIP = True
    bad = []
    pattern = re.compile(r"\[[^\]]*\]\((?!https?://|#|mailto:)([^)#]+)")
    for path in DOCS:
        for target in pattern.findall(prose(path)):
            if not (path.parent / target).resolve().exists():
                bad.append(f"{path.name} -> {target}")
    assert not bad, "相对链接指向不存在的文件：\n" + "\n".join(bad)


def test_no_trailing_whitespace_and_final_newline() -> None:
    TABLE_SKIP = True
    bad = []
    for path in DOCS:
        text = body(path)
        if not text.endswith("\n"):
            bad.append(f"{path.name}: 末尾缺换行")
        for number, line in enumerate(text.splitlines(), 1):
            if line != line.rstrip():
                bad.append(f"{path.name}:{number} 行尾有空白")
    assert not bad, "\n".join(bad)