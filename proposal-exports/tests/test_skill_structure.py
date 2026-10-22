"""skill 结构回归：命名、触发词、脚本清单、旧名残留。

这些是"改完就坏、坏了不报错"的部分，用测试钉住：
- frontmatter 的 name 必须等于目录名，或目录名的 kf- 前缀形式（agent 按名字路由）；
- description 必须同时覆盖"配图"和"PPT"两类触发；
- SKILL.md 脚本表里列出的脚本必须存在；
- 仓库里不能再出现旧名字 `proposal-pictures`（重命名回归）。
"""
import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"
TEXT_SUFFIXES = {".md", ".py", ".js", ".json", ".txt", ".yml", ".yaml"}
SKIP_DIRS = {".git", "node_modules", "dev", "__pycache__", ".pytest_cache", "tests"}
# 设计记录要写清"为什么改名"，会提到旧名字；测试文件本身含旧字符串作为检索词。都允许。
ALLOW_OLD_NAME = ("references/design-notes/", "tests/")


def frontmatter(text: str) -> dict:
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    assert match, "SKILL.md 缺 frontmatter"
    meta = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        if key.strip():
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def iter_tracked_texts():
    for path in SKILL_DIR.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def test_frontmatter_name_matches_directory():
    meta = frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    name = meta["name"]
    assert name in {SKILL_DIR.name, f"kf-{SKILL_DIR.name}"}


def test_description_covers_figures_and_ppt():
    meta = frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    desc = meta["description"]
    assert "配图" in desc or "图" in desc
    assert "PPT" in desc and "幻灯片" in desc


def test_no_stale_old_name_anywhere():
    offenders = []
    for path in iter_tracked_texts():
        rel = str(path.relative_to(SKILL_DIR)).replace("\\", "/")
        if rel.startswith(ALLOW_OLD_NAME):
            continue
        if "proposal-pictures" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(rel)
    assert offenders == []


def test_skill_md_script_table_points_to_existing_files():
    text = SKILL_MD.read_text(encoding="utf-8")
    listed = set(re.findall(r"`(scripts/[A-Za-z0-9_./-]+\.py)`", text))
    assert listed, "SKILL.md 里没有脚本清单"
    missing = sorted(p for p in listed if not (SKILL_DIR / p).is_file())
    assert missing == []


def test_ppt_capability_files_exist():
    for rel in ("references/ppt-deck.md",
                "references/text-quality.md",
                "references/design-notes/ppt-integration.md",
                "references/design-notes/diagram-engine-decision.md",
                "assets/deck/gen_deck.js",
                "assets/deck/formulas.example.json",
                "scripts/formula_png.py",
                "scripts/deck_check.py",
                "scripts/render_pptx_png.py",
                "scripts/text_check.py"):
        assert (SKILL_DIR / rel).is_file(), f"缺 {rel}"


def test_new_scripts_have_docstring_and_main_guard():
    for name in ("formula_png.py", "deck_check.py", "render_pptx_png.py", "text_check.py"):
        src = (SKILL_DIR / "scripts" / name).read_text(encoding="utf-8")
        assert src.lstrip().startswith(('"""', "#!/usr/bin/env python3")), name
        assert "__main__" in src, name


def test_text_rigor_points_to_development_research():
    text = SKILL_MD.read_text(encoding="utf-8")
    for phrase in ("严谨性", "kf-personal-development", "专有名词", "reference_docs"):
        assert phrase in text, f"SKILL.md 缺文字严谨性契约：{phrase}"


def test_figure_layout_adjustment_is_documented():
    text = SKILL_MD.read_text(encoding="utf-8")
    for phrase in ("图片排版调整", "先调版式", "check_overlap"):
        assert phrase in text, f"SKILL.md 缺图片排版调整：{phrase}"


def test_skill_has_readme_and_gitignore():
    assert (SKILL_DIR / "README.md").is_file()
    assert (SKILL_DIR / ".gitignore").is_file()
