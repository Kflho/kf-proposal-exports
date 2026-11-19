#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""note_dedup.py — 笔记的「去除重复」检查：引用能不能落地、同一信息有没有写两处。

判据出处：data note 的「去除内容重复」（一个信息只记在一个地方 / 引用要写全 /
引用本身不要重复 / 标题能讲清楚不要另起一段）。readability_check.py 只管单份
文档内部与跨文件的段落重复，这份补上引用链路与跨文件的同题并存。

用法:
    python scripts/note_dedup.py --root <笔记目录> [--vault <解析用的库根>] [--json]

退出码：0 没有 error，1 有 error，2 参数或目录问题。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from readability_check import (  # noqa: E402  复用解析，避免两套口径
    _clean_text, duplicate_sections, walk,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 结构性标题：正文本来就是逐条展开，不是复述标题
SCAFFOLD = {
    '概论', '介绍', '建议', '原则', '规范', '框架', '流程', '组成', '分类',
    '操作', '作用', '目标', '内容', '方法', '实例', '推荐', '约束', '通识',
    '附录', '模板', '规范介绍', '推荐介绍', '框架介绍', '介绍介绍', '通识介绍',
    '记录规范', '记录建议', '数据管理规范', '数据优化', '文字规范', '格式规范',
    '语言风格规范', '项目数据管理规范', '建议与规范', '写作规范', '写作原则',
}
# 跨文件同题并存：只放过笔记骨架标题，其余都要人看一眼
N6_SKIP = {'概论', '通识', '附录', '介绍'}

REF_VERB = re.compile(
    r'(见|引用|参考|参见)[\s：:]*'
    r'((?:[A-Za-z][A-Za-z0-9]*)(?: [A-Za-z0-9]+)*[ ](?:note|template))')
# 引用目标到这些符号就结束（后面是解释，不是目标）
CUT = re.compile(r'[，。；、：:（）()\[\]【】「」“”"\'!?！？,;]')
# 引用目标里的限定词：写「引用 xx 相关部分」时不算节名
QUALIFIER = ('相关部分', '通用部分', '相关内容', '通用内容', '相关的内容',
             '相关', '通用', '部分', '里面', '其中', '内容', '里', '中')
# 复述里允许出现的虚词：拿掉这些还剩不到 4 个实字，说明这条只是把标题重说一遍
FILLER_CHARS = set('即就是说是指指的是包括包含得了的了吧呢啊和与及等')


def rest_after_title(title: str, paragraph: str) -> str:
    """首段去掉标题词与虚词后剩下的实字。"""
    clean_title = _clean_text(title)
    clean_para = _clean_text(paragraph)
    if not clean_title:
        return clean_para
    rest = clean_para.replace(clean_title, '')
    return ''.join(char for char in rest if char not in FILLER_CHARS)


LIST_PREFIX = re.compile(r'^\s*(?:\d+\.|[-*+])\s+')
# 节名后面常跟着解释（`data note-建立流程来建立笔记文件模板`），到连接词就截断
PROSE_TAIL = re.compile(r'(?:来|以|并|再|然后|从而|使得|便于|即可|这样)')
# 行首就是引用动词：目标可以是笔记、模板名或其他标题路径，都算引用而不是内容
REF_LEAD = re.compile(r'^\s*(?:\d+\.|[-*+])?\s*(见|引用|参考|参见)')

SHORT_LINE = 12


def plain(line: str) -> str:
    text = LIST_PREFIX.sub('', line.strip())
    return re.sub(r'[\s`*_|>\-—–]+', '', text)


def headings_with_body(path: Path) -> list[tuple[int, int, str, bool]]:
    """(行号, 级别, 去标点标题, 该节是否有正文)。

    只列一条引用（「参考 note note-去除重复」）的节不算正文，避免把合规引用当成重复。
    """
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    marks: list[tuple[int, int, str]] = []
    fenced = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            marks.append((number, len(match.group(1)), _clean_text(match.group(2))))
    out = []
    for index, (number, level, title) in enumerate(marks):
        end = len(lines) + 1
        for later, later_level, _ in marks[index + 1:]:
            if later_level <= level:
                end = later
                break
        body = []
        for line in lines[number:end - 1]:
            stripped = line.strip().lstrip('-*+ ')
            if not stripped or stripped == '-' or stripped.startswith('|'):
                continue
            if is_reference_line(stripped):
                continue
            body.append(stripped)
        out.append((number, level, title, bool(body)))
    return out


def vault_index(vault: Path) -> dict[str, Path]:
    """文件名（不含 .md，小写）→ 路径。

    跳过以 `.` 开头的目录：`.trash` / `.obsidian` 里的历史副本与同名笔记会让引用解析到
    旧版本，读到的标题自然对不上。
    """
    index: dict[str, Path] = {}
    for path in walk(vault):
        if path.suffix != '.md':
            continue
        if any(part.startswith('.') for part in path.relative_to(vault).parts):
            continue
        index.setdefault(path.stem.lower(), path)
    return index


def ref_targets(line: str) -> list[tuple[str, str]]:
    """抽出引用：返回 (笔记名, 节名路径)。节名到标点为止。"""
    out = []
    for match in REF_VERB.finditer(line):
        name = match.group(2)
        rest = CUT.split(line[match.end():])[0].strip().strip('-—–').strip()
        out.append((name, rest))
    return out


def resolve(name: str, index: dict[str, Path]) -> Path | None:
    return index.get(name.lower())


def _variants(part: str) -> list[str]:
    """节名去掉限定词后的几种写法：`去除重复通用部分` → `去除重复`。"""
    out = [part]
    changed = True
    while changed and out[-1]:
        changed = False
        for word in QUALIFIER:
            if out[-1].endswith(word) and len(out[-1]) > len(word):
                out.append(out[-1][:-len(word)])
                changed = True
                break
    return [item for item in out if item]


def _trim_prose(part: str) -> str:
    """`建立流程来建立笔记文件模板` → `建立流程`；前缀太短时不动（避免截掉「并列内容」）。"""
    match = PROSE_TAIL.search(part)
    if match and match.start() >= 2:
        return part[:match.start()].strip()
    return part


def _parts(rest: str) -> list[str]:
    out = []
    for part in re.split(r'[-—–/／]|\s+', rest):
        part = _trim_prose(part.strip())
        if not part or part in QUALIFIER:
            continue
        out.append(part)
    return out


def heading_index(vault: Path, index: dict[str, Path]) -> dict[str, list[tuple[str, int]]]:
    """标题名 → [(笔记名, 行号)…]：引用指错笔记时，同名标题可能有好几处。"""
    found: dict[str, list[tuple[str, int]]] = {}
    for path in index.values():
        for number, _level, text, _body in headings_with_body(path):
            found.setdefault(text, []).append((path.stem, number))
    return found


def locate(part: str, heads: list[str], body: str) -> tuple[str, str]:
    """(heading / text / none, 说明)。"""
    for variant in _variants(part):
        clean = _clean_text(variant)
        if len(clean) < 2:
            continue
        if any(clean in text for text in heads):
            return 'heading', ''
        if variant in body:
            return 'text', ''
    clean = _clean_text(part)
    grams = {clean[i:i + 2] for i in range(len(clean) - 1)}
    best, score = '', 0.0
    for text in heads:
        other = {text[i:i + 2] for i in range(len(text) - 1)}
        if not grams or not other:
            continue
        shared = len(grams & other) / len(grams)
        if shared > score:
            best, score = text, shared
    return 'none', best if score >= 0.4 else ''


def is_reference_line(line: str) -> bool:
    """引用行本身就是合规的重复，不参与跨文件同内容比较。

    行首写「见 / 引用 / 参考」的行都算引用：目标可以是笔记，也可以是「文件模板-实例建立流程」
    这种标题路径。
    """
    if line.strip().startswith('|'):
        return False
    return bool(REF_LEAD.match(line) or REF_VERB.search(line))


def check(root: Path, vault: Path) -> list[dict]:
    findings: list[dict] = []
    index = vault_index(vault)
    heads_cache: dict[Path, list[tuple[int, int, str, bool]]] = {}
    lines_by_file: dict[str, list[tuple[str, int]]] = {}
    same_heading: dict[str, list[tuple[str, int, bool]]] = {}
    global_heads: dict[str, tuple[str, int]] | None = None

    for path in walk(root):
        if path.suffix != '.md':
            continue
        rel = path.relative_to(root).as_posix()
        body = path.read_text(encoding='utf-8', errors='replace')
        heads = heads_cache.setdefault(path.resolve(), headings_with_body(path))
        head_texts = [text for _, _, text, _ in heads]

        refs: dict[str, list[int]] = {}
        for number, line in enumerate(body.splitlines(), 1):
            for target, rest in ref_targets(line):
                refs.setdefault(target, []).append(number)
                found = resolve(target, index)
                if found is None:
                    findings.append(dict(
                        file=rel, line=number, rule='N3', severity='error',
                        title='引用的目标在库里找不到',
                        text=f'引用 {target}', matched=target,
                        advice='改成库里真实的笔记名，或把目标笔记补进库'))
                    continue
                if not rest:
                    continue
                # 被引用的笔记可能不在被检查的目录里：标题现场补算，不然会误判「找不到」
                target_body = heads_cache.get(found.resolve())
                if target_body is None:
                    target_body = headings_with_body(found)
                    heads_cache[found.resolve()] = target_body
                target_heads = [text for _, _, text, _ in target_body]
                target_text = found.read_text(encoding='utf-8', errors='replace')
                for part in _parts(rest):
                    where, near = locate(part, target_heads, target_text)
                    if where in ('heading', 'text'):
                        # 标题能对上，或正文里能找到（列表条目也算）——都不算问题
                        continue
                    if global_heads is None:
                        global_heads = heading_index(vault, index)
                    elsewhere = global_heads.get(_clean_text(part)) or []
                    if elsewhere:
                        where = '、'.join(f'{stem}-{_clean_text(part)}（第 {line} 行）'
                                          for stem, line in elsewhere)
                        advice = f'{found.stem} 里没有「{part}」；同名标题在 {where}'
                    elif near:
                        advice = f'{found.stem} 里没有「{part}」，相近标题是「{near}」'
                    else:
                        advice = f'{found.stem} 里没有「{part}」，全库也没有同名标题'
                    findings.append(dict(
                        file=rel, line=number, rule='N3', severity='error',
                        title='引用的节名在目标笔记里找不到',
                        text=f'引用 {target}-{part}', matched=f'{found.stem}-{part}',
                        advice=advice))

        # 同一处堆叠引用同一目标（相隔 3 行以内）；隔很远的多处引用是正常写法
        for target, numbers in refs.items():
            stacked = [pair for pair in zip(numbers, numbers[1:])
                       if pair[1] - pair[0] <= 3]
            if not stacked:
                continue
            findings.append(dict(
                file=rel, line=stacked[0][1], rule='N4', severity='warning',
                strict=True,
                title='同一处重复引用同一个目标',
                text=f'{target} 出现在第 {", ".join(map(str, numbers))} 行',
                matched=target,
                advice='同一处只留一处引用，其余合并；离得远的分开引用不算重复'))

        for number, _level, title, has_body in heads:
            if len(title) < 4 or title in N6_SKIP:
                continue
            same_heading.setdefault(title, []).append((rel, number, has_body))

        for number, line in enumerate(body.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith(('#', '|', '```')):
                continue
            if is_reference_line(stripped):
                continue
            key = plain(stripped)
            if len(key) < SHORT_LINE:
                continue
            lines_by_file.setdefault(key, []).append((rel, number))

        for number, title, paragraph in duplicate_sections(path):
            if title in SCAFFOLD or title.endswith(('介绍', '建议', '原则', '规范', '模板')):
                continue
            if is_reference_line(paragraph.strip()):
                continue
            if len(rest_after_title(title, paragraph)) >= 4:
                continue  # 复述里还有条件、例子、定义，读得到新东西，不算问题
            findings.append(dict(
                file=rel, line=number, rule='N1', severity='warning',
                title='这条内容只是把标题重说一遍',
                text=f'{title} / {paragraph[:60]}', matched=title,
                advice='标题已经包含内容，删掉这条；要留就写标题没有的条件、范围或例子'))

    for key, places in lines_by_file.items():
        files = {rel for rel, _ in places}
        if len(files) < 2:
            # 同一份笔记里同一句写了两遍（不同小节各写一次），也是重复
            by_file: dict[str, list[int]] = {}
            for rel, number in places:
                by_file.setdefault(rel, []).append(number)
            for rel, numbers in by_file.items():
                if len(numbers) < 2:
                    continue
                findings.append(dict(
                    file=rel, line=numbers[1], rule='N2', severity='warning',
                    title='同一段文字在这份笔记里写了两遍',
                    text=key[:60],
                    matched='、'.join(f'{rel}:{number}' for number in numbers),
                    advice='只留一处，另一处写成引用'))
            continue
        where = '、'.join(f'{rel}:{number}' for rel, number in places)
        for rel, number in places[1:]:
            findings.append(dict(
                file=rel, line=number, rule='N2', severity='warning',
                title='同一段文字写在了两份文件里',
                text=key[:60], matched=where,
                advice='只留一处，另一处写成引用（引用 xx 相关部分）'))

    for title, places in same_heading.items():
        with_body = [(rel, number) for rel, number, has_body in places if has_body]
        # 同一份笔记里同名标题出现多次：多半是复制段落留下的
        per_file: dict[str, list[int]] = {}
        for rel, number in with_body:
            per_file.setdefault(rel, []).append(number)
        for rel, numbers in per_file.items():
            if len(numbers) < 2:
                continue
            findings.append(dict(
                file=rel, line=numbers[1], rule='N7', severity='warning',
                title=f'同一份笔记里「{title}」出现了 {len(numbers)} 次',
                text='、'.join(f'{rel}:{number}' for number in numbers),
                matched=title,
                advice='保留一处，其余改成子标题；重复的整段删掉或合并'))
        files = {rel for rel, _ in with_body}
        if len(files) < 2:
            continue
        where = '、'.join(f'{rel}:{number}' for rel, number in with_body)
        first_rel = with_body[0][0]
        for rel, number in with_body:
            if rel == first_rel:
                continue
            findings.append(dict(
                file=rel, line=number, rule='N6', severity='warning',
                title=f'「{title}」在两份文件里各有正文',
                text=where, matched=title,
                advice='两份写的是不同阶段就各自留下；相同就合并到一处，另一处引用'))

    findings.sort(key=lambda item: (item['rule'], item['file'], item['line']))
    return findings


def report(findings: list[dict], root: Path, hidden: int = 0) -> str:
    errors = [item for item in findings if item['severity'] == 'error']
    out = [f'去除重复检查：{root}', '']
    if not findings:
        out.append('没有发现问题。')
        if hidden:
            out.append(f'（另有 {hidden} 条引用精度问题，加 --strict 查看）')
        return '\n'.join(out)
    for item in findings:
        tag = 'error' if item['severity'] == 'error' else 'warning'
        out.append(f"[{tag}] {item['rule']} {item['title']}")
        out.append(f"    {item['file']}:{item['line']}  {item['text'][:100]}")
        out.append(f"    → {item['advice']}")
    out.append('')
    out.append(f'{len(errors)} error / {len(findings) - len(errors)} warning')
    if hidden:
        out.append(f'另有 {hidden} 条引用精度问题（引用的节名不是标题 / 同一处重复引用），加 --strict 查看')
    return '\n'.join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='笔记的去除重复检查（引用链路 + 跨文件同题）')
    parser.add_argument('--root', required=True, help='要检查的笔记目录')
    parser.add_argument('--vault', default='', help='解析引用用的库根，默认同 --root')
    parser.add_argument('--strict', action='store_true',
                        help='同时报引用精度问题（节名不是标题、同一处重复引用）')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f'目录不存在：{root}', file=sys.stderr)
        return 2
    vault = Path(args.vault).resolve() if args.vault else root
    if not vault.is_dir():
        print(f'解析用的库根不存在：{vault}', file=sys.stderr)
        return 2

    findings = check(root, vault)
    shown = findings if args.strict else [item for item in findings if not item.get('strict')]
    hidden = len(findings) - len(shown)
    if args.json:
        print(json.dumps(shown, ensure_ascii=False, indent=2))
    else:
        print(report(shown, root, hidden))
    return 1 if any(item['severity'] == 'error' for item in shown) else 0


if __name__ == '__main__':
    raise SystemExit(main())

