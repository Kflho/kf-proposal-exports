#!/usr/bin/env python3
"""Release-time text review based on humanizer-zh (2026-09-23).

humanizer-zh is an editorial skill: it edits prose, preserves facts and author
voice, and treats its 31 patterns as clues, not word blacklists.  This tool is
the mechanical half — it catches high-confidence template/boilerplate/AI-tell
patterns in **user-facing** text:

- README.md, SKILL.md and references/*.md;
- Chinese string literals in runtime scripts (CLI help, errors, output).

It cannot judge context like humanizer-zh does.  Findings marked ERROR block the
release; WARNING asks for an editorial pass.  For a real rewrite, load the
humanizer-zh skill and edit the few flagged lines by hand.

Usage:
    python scripts/config/text_review.py --root .
    python scripts/config/text_review.py --root ../kf-personal-service-release --json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

from lib.place import exports_dirs  # noqa: E402

HUMANIZER = 'humanizer-zh 2026-09-23 (31 patterns)'

# (id, title, regex, severity, advice)
RULES = [
    ('A1', '不是 X，而是 Y', r'不是[^。\n]{0,30}而是', 'warning',
     '假对比；两部分都有信息才保留，否则直接陈述'),
    ('A4', '起跑式铺垫', r'(在当今|随着[^。\n]{0,25}(的发展|时代的到来)|众所周知|不难发现|值得一提的是)',
     'error', '删掉铺垫，直接从事实开始'),
    ('A5', '与假想敌辩论', r'(有人会说|很多人认为|也许你会问)', 'warning',
     '没有真实反方时删掉'),
    ('B6', '强凑三段式', r'(首先[^。\n]{0,50}其次[^。\n]{0,50}(最后|第三))', 'warning',
     '顺序不是重点时改成普通叙述'),
    ('B8', '破折号当万能连接', r'——', 'warning',
     '同一篇出现多次时改成句号/逗号/冒号'),
    ('B9', '限定词堆叠', r'(可能|或许|也许|似乎|大概)[^。\n]{0,12}(可能|或许|也许|似乎|大概)',
     'warning', '保留一个真实的不确定程度'),
    ('C12', 'AI 高频词', r'(赋能|闭环|抓手|颗粒度|底层逻辑|顶层设计|生态位|范式|协同|沉淀|链路|心智|势能|护城河)',
     'error', '换成具体动作/对象，或删掉'),
    ('C13', '意义拔高', r'(标志着|里程碑|开启新篇章|具有深远意义|至关重要|意义重大)', 'error',
     '写清楚实际影响，不要替读者下结论'),
    ('C14', '模糊关联', r'(业内人士|专家表示|研究表明|数据显示|有分析称)', 'warning',
     '补来源；补不了就保留不确定性'),
    ('C15', '句尾补充式拔高', r'，\s*(这|它)(不仅仅|更是|正)[^。\n]{0,30}', 'warning',
     '后半句没有新信息就删'),
    ('C16', '宣传语', r'(完美|极致|全新|一站式|无缝|领先|颠覆|颠覆性)', 'error',
     '换成可验证的功能/条件'),
    ('C17', '借权威', r'(正如[^，。\n]{0,12}所说|大师[^，。\n]{0,8}曾)', 'warning',
     '没有出处就删'),
    ('E22', '客服腔', r'(感谢您的|如有疑问|请随时|希望对您有帮助)', 'error',
     '文档不需要客服话术'),
    ('E24', '首句复读标题', r'^#\s+(.+)\n+(?:\1)', 'warning',
     '标题后直接给信息，不要重复标题'),
    ('E25', '谈论上一稿', r'(上一版|这次修改|如前所述|前文提到)', 'warning',
     '交付稿不要留修订痕迹'),
    ('F26', '层叠的“的”', r'[^。\n]{0,12}的[^。\n]{0,12}的[^。\n]{0,12}的', 'warning',
     '拆句或删掉冗余的'),
    ('F27', '进行＋动词', r'进行(了)?[\u4e00-\u9fff]{2}', 'warning',
     '直接用动词'),
    ('F30', '随着……的发展', r'随着[^。\n]{0,20}的发展', 'error',
     '直接从具体变化写起'),
    ('F31', '套话收尾', r'(总而言之|综上所述|希望本文|让我们一起|未来可期|拭目以待)', 'error',
     '删掉，或换成具体下一步'),
]

SKIP_DIRS = {'.git', '__pycache__', 'temp', 'tests', '.pytest_cache', 'dev'}
TECH_ALLOW = {
    '链路': re.compile(r'(下载|网络|远程|数据|全|这条|处理|调用|音频|视频|字幕|端到端)链路|链路(层|不可用|正常|中断)'),
    '闭环': re.compile(r'(三步|流程|业务|反馈|控制|自动)闭环|闭环(系统|流程)'),
    '完美': re.compile(r'完美(正确|匹配|对齐|同步)'),
    '——': re.compile(r'xx——序号|——序号'),
}
EXEMPT_FILES = {'references/text-review.md'}
MARKDOWN = {'.md', '.mdx'}
EXPORT_TEXT = {'.md', '.mdx', '.txt', '.html', '.htm'}
PYTHON = {'.py'}


def _scan_text(text: str, file: str, line: int = 0) -> list[dict]:
    findings = []
    for rule_id, title, pattern, severity, advice in RULES:
        for match in re.finditer(pattern, text, re.MULTILINE):
            line_no = line + text[:match.start()].count('\n')
            line_text = text.splitlines()[line_no - line] if text.splitlines() else ''
            allow = TECH_ALLOW.get(match.group(0))
            if allow and allow.search(line_text):
                continue
            findings.append({
                'file': file,
                'line': line_no,
                'rule': rule_id,
                'title': title,
                'severity': severity,
                'text': match.group(0)[:80],
                'advice': advice,
            })
    return findings


def _text_files(root: Path, suffixes: set[str]) -> list[Path]:
    files = []
    for path in root.rglob('*'):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in suffixes:
            files.append(path)
    return sorted(files)


def _python_strings(root: Path) -> list[tuple[Path, int, str]]:
    strings = []
    for path in sorted(root.rglob('*.py')):
        if (any(part in SKIP_DIRS for part in path.parts)
                or path.name == 'text_review.py'):
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8-sig',
                                       errors='replace'))
        except (OSError, UnicodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if re.search(r'[\u4e00-\u9fff]', node.value):
                    strings.append((path, node.lineno, node.value))
    return strings


def scan(root: Path, include_exports: bool = False) -> list[dict]:
    findings = []
    if include_exports:
        for exports in exports_dirs(root):
            for path in _text_files(exports, EXPORT_TEXT):
                rel = path.relative_to(root).as_posix()
                try:
                    text = path.read_text(encoding='utf-8-sig',
                                          errors='replace')
                except OSError:
                    continue
                findings.extend(_scan_text(text, rel, 0))
        return findings
    for path in _text_files(root, MARKDOWN):
        rel = path.relative_to(root).as_posix()
        if rel in EXEMPT_FILES:
            continue
        try:
            text = path.read_text(encoding='utf-8-sig', errors='replace')
        except OSError:
            continue
        findings.extend(_scan_text(text, rel, 0))
    for path, line, text in _python_strings(root):
        rel = path.relative_to(root).as_posix()
        findings.extend(_scan_text(text, rel, line - 1))
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--exports', action='store_true',
                        help='scan bin/exports (or legacy exports) text instead of the repo')
    args = parser.parse_args(argv)
    findings = scan(Path(args.root), args.exports)
    errors = [item for item in findings if item['severity'] == 'error']
    if args.json:
        print(json.dumps({'humanizer': HUMANIZER, 'findings': findings,
                          'errors': len(errors)}, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"{item['file']}:{item['line']} [{item['severity']}] "
                  f"{item['rule']} {item['title']}: {item['text']!r}")
            print(f"  -> {item['advice']}")
        print(f'{len(errors)} error(s), {len(findings) - len(errors)} '
              f'warning(s) — {HUMANIZER}')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
