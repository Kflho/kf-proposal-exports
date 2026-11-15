#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可读性检查：假设读者没参与开发、也不知道脚本是什么，这句话能不能单独读懂。

为什么单列一套：`text_consistency.py` 查的是"AI 腔"（空泛、套话、假对比），
查不出"记录顶部写着「我现在」的编号"这类**依赖上下文才能懂**的写法——
读者不知道窗口长什么样、不知道「我现在」是哪来的，句子在主谓上就断了。

检查对象（都是要给没开发背景的人读的）：
- 用户可见字符串：Notice / 状态栏 / 设置项 / 弹窗 / 命令名 / 菜单项；
- 测试用例名：`check('…')` / `checkTrue('…')` / `test('…')` 的第一个参数
  （下一个人看测试名就知道这条在守什么）；
- Markdown 标题：文档目录里只有一行，指代和方位词在这里最伤。

判据见 `references/text-quality.md`「可读性」。

用法:
    python scripts/readability_check.py --root <项目>
    python scripts/readability_check.py --root <项目> --tests <测试仓>
    python scripts/readability_check.py --root <项目> --json

项目可以在根上放 `readability.json`：
    {"allow": ["留包", "完整副本"], "glossary": "bin/reference_docs/术语表.md"}
`allow` 里的词不再报；`glossary` 里登记过的术语不再报"未解释"。

退出码：0 没有 error；1 有 error；2 参数 / 目录问题。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {'.git', 'node_modules', 'dist', 'build', '__pycache__', '.pytest_cache',
             'dev', 'temp', 'exports'}
UI_CALL = re.compile(
    r'(new Notice|Notice\(|setText\(|setName\(|setDesc\(|setButtonText\(|setPlaceholder\(|'
    r'setTitle\(|setTooltip\(|addCommand|createEl\(|createDiv\(|\.name:|desc:|label:|text:)'
)
TEST_CALL = re.compile(r'(?:check|checkTrue|test|it|describe)\(\s*[\'"]([^\'"\n]{0,200})[\'"]')
STRING = re.compile(r'([\'"`])([^\'"`\n]{0,300}[\u4e00-\u9fff][^\'"`\n]{0,300})\1')

# 逐条报的规则：(id, 标题, 正则, 级别, 建议)
RULES = [
    ('R1', '指代开头，脱离上下文读不懂',
     r'^\s*(这个|那个|它|它们|其(?!他)|该|此|上面|下面|上一条|下一条|这一条|那一条|这条|那条|'
     r'此处|这里|这边|那边|刚才|之前的|上次的|前述)',
     'error', '写出具体对象：哪台电脑、哪个窗口、哪份包'),
    ('R2', '用方位词指界面位置',
     r'(顶部|上方|下方|左边|右边|这一行|那一行|这一栏|那一栏|这个窗口|那个窗口|'
     r'列表上方|列表顶部|记录顶部|记录里|界面里)',
     'error', '直接说窗口 / 字段的名字，别让读者去找位置'),
    ('R3', '引号里的口语标签当名字用',
     r'["「\'](我现在|这边|那边|这条|那条|刚才|之前的|这个|那个|上次|这次)["」\']',
     'error', '换成具体名称，例如「本机当前的状态编号」'),
    ('R4', '名词化堆叠（…的编号 / …的状态）',
     r'(写着|显示|列着|记着)[^。；\n]{0,24}的(编号|名字|名称|状态|位置|内容|原因)(?=[。；，、]|$)',
     'error', '拆成完整句子：谁、在哪儿、写了什么'),
]

# 说明句：不用没有名词的指代，不用「原图不留」这种压缩句
PROSE_RULES = [
    ('R12', '没有名词的指示代词',
     r'(这|那)(一)?(段|条|份|次|个|些|种|边|里|时)(?![\u4e00-\u9fff])',
     '写出指代的对象：只排版这一次粘贴的内容'),
    ('R13', '压缩句（只有对象和否定，没有谁做）',
     r'(原图|正文|文件名|链接|内容|数据|设置|选项|图片|消息|签名|计数|控件|仓库文件)'
     r'((与|和|、)[^。；，]{0,6})?\s*(不留|不删|不动|不改|不写|不拆|不覆盖|不保留)',
     '补上主语与动作：原图会被删除 / 文件不会被改动'),
]

# 用户文档里的开发记录（README 专用）：实现细节、测试路径、日期、踩坑史
README_DEV_RULES = [
    ('R15', '把开发记录写进用户文档',
     r'(\bInternal:|\btest/[\w./-]+|\b20\d{2}-\d{1,2}\b|用户(报|要求|实测|反馈)|实测|踩坑|回归|规则登记表|rule registry)',
     '移到 AGENTS.md / CLAUDE.md 或 dev 日志；README 只留用户要做的操作与结果'),
]

# 开发文字（注释 / 用例名）专有的规则；注释里只报 warning
DEV_RULES = [
    ('R8', '压缩成对仗短语',
     r'(在测什么|守在哪|测什么[，、,]|是什么[，、,].{0,12}为什么|怎么用[，、,].{0,12}怎么办)',
     '拆成完整句子：验证什么行为、哪一处出错会让它失败'),
    ('R9', '用前文指代开头',
     r'^\s*(这里|上面|下面|这条|那条|这句|那句|该|此)',
     '写出具体对象，让这一条单独也能读'),
    ('R7', '比喻动词（守 / 兜底 / 挂在 / 吃进 / 塞进 / 落进…）',
     r'(守(着|在|的是|住|了一|得住)|兜底|挂在|长在|吃进|吃掉|塞进|塞到|落进|落到|拽|不炸|崩了|炸了)',
     '换成动作本身：验证 / 放回 / 标记为 / 写进 / 失败'),
]

# 术语表：不逐条报，按词统计（项目可以登记进 allow / glossary）
ABBREV = ['重导', '留包', '推拉', '收包', '回礼', '落点', '收口', '接链', '白跑',
          '货架', '指纹', '兜底', '接不上', '对不上', '捞回来', '拷', '弄坏', '弄丢']
JARGON = ['状态编号', '基准', '世代', '完整副本', '更新包', '差量包', '同步包']

TEXT_EXT = {'.ts', '.tsx', '.md'}


def load_config(root: Path) -> dict:
    file = root / 'readability.json'
    if not file.is_file():
        return {'allow': [], 'glossary': '', 'skip': []}
    try:
        data = json.loads(file.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'allow': [], 'glossary': '', 'skip': []}
    return {
        'allow': list(data.get('allow') or []),
        'glossary': str(data.get('glossary') or ''),
        'skip': list(data.get('skip') or []),
    }


def glossary_text(root: Path, config: dict) -> str:
    rel = config.get('glossary') or 'bin/reference_docs/术语表.md'
    for path in (root / rel, root / 'bin' / 'reference_docs' / '术语表.md'):
        if path.is_file():
            return path.read_text(encoding='utf-8', errors='replace')
    return ''


def walk(root: Path):
    """剪枝遍历：node_modules / dist 这些不进（rglob 会先走进去再过滤，大仓库会卡死）。"""
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in sorted(files):
            path = Path(current) / name
            if path.suffix in TEXT_EXT and path.stat().st_size <= 400_000:
                yield path


def ui_strings(path: Path) -> list[tuple[int, str]]:
    out = []
    for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if not UI_CALL.search(line):
            continue
        for match in STRING.finditer(line):
            out.append((number, match.group(2)))
    return out


def test_names(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding='utf-8', errors='replace')
    out = []
    for match in TEST_CALL.finditer(text):
        line = text[:match.start()].count('\n') + 1
        out.append((line, match.group(1)))
    return out


def headings(path: Path) -> list[tuple[int, str]]:
    out = []
    fenced = False
    for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if line.strip().startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if match:
            out.append((number, match.group(2).strip()))
    return out


def _clean_text(text: str) -> str:
    text = re.sub(r'[`*_>#\-|]', '', text)
    return re.sub(r'[\s\W_]+', '', text, flags=re.UNICODE)


def _bigrams(text: str) -> set[str]:
    return {text[index:index + 2] for index in range(len(text) - 1)}


def markdown_sections(path: Path) -> list[tuple[int, str, str]]:
    """(标题行号, 标题, 标题下第一段)；代码块里的 `#` 不算标题。"""
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    out = []
    fenced = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r'^(#{2,6})\s+(.+)$', line)
        if not match:
            continue
        cursor = index + 1
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        paragraph = []
        while cursor < len(lines):
            body = lines[cursor].strip()
            if not body or body.startswith('#') or body.startswith('```'):
                break
            paragraph.append(body)
            cursor += 1
        if paragraph:
            out.append((index + 1, match.group(2).strip(), ' '.join(paragraph)))
    return out


def _in_code_span(text: str, index: int) -> bool:
    """这个位置是否落在行内代码里（示例日期、命令不算开发记录）。"""
    return text[:index].count('`') % 2 == 1


def markdown_prose(path: Path) -> list[tuple[int, str]]:
    """正文段落（跳过标题、代码块、表格、HTML 注释与空行）。"""
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    out: list[tuple[int, str]] = []
    fenced = False
    in_comment = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        if stripped.startswith('<!--'):
            in_comment = True
        if in_comment:
            if '-->' in stripped:
                in_comment = False
            continue
        if not stripped or stripped.startswith('#') or stripped.startswith('|'):
            continue
        text = re.sub(r'^(?:[-*+>]|\d+\.)\s+', '', stripped)
        if len(text) < 4:
            continue
        out.append((number, text))
    return out


def duplicate_sections(path: Path) -> list[tuple[int, str, str]]:
    """标题与它下面第一段在说同一件事。

    判据只看第一句：第一句里原样包含标题（去掉标点后），或者几乎就是标题的改写。
    正文后面再解释机制、给条件，不算重复。
    """
    out = []
    for line, title, paragraph in markdown_sections(path):
        cjk = len(re.findall(r'[\u4e00-\u9fff]', title))
        if cjk < 3 or cjk / max(1, len(title)) < 0.3:
            continue
        head = _clean_text(title)
        if len(head) < 4:
            continue
        first = re.split(r'[。！？!?；;\n]', paragraph.strip())[0]
        sentence = _clean_text(first)
        if not sentence:
            continue
        if head in sentence:
            out.append((line, title, paragraph))
            continue
        head_grams = _bigrams(head)
        sentence_grams = _bigrams(sentence)
        if not head_grams:
            continue
        shared = len(head_grams & sentence_grams) / len(head_grams)
        if shared >= 0.9 and len(sentence) <= len(head) * 2.5:
            out.append((line, title, paragraph))
    return out


SETTING = re.compile(r"name:\s*'([^'\n]{2,40})'[\s\S]{0,240}?desc:\s*'([^'\n]{2,200})'")


ECHO_FILLER = set('的时一并由本在了是会可把被与和也就都要用到从及或称开时候之间是否')

def _chars(text: str) -> set[str]:
    text = re.sub(r'[A-Za-z0-9]+', '', text)
    return {char for char in text if char not in ECHO_FILLER}


def setting_echoes(path: Path) -> list[tuple[int, str, str]]:
    """设置项：说明只是把名字换了个说法（包含，或字面重合度高且没多出信息）。"""
    text = path.read_text(encoding='utf-8', errors='replace')
    out = []
    for match in SETTING.finditer(text):
        name, desc = match.group(1), match.group(2)
        clean_name = _clean_text(name)
        clean_desc = _clean_text(desc)
        if len(clean_name) < 3:
            continue
        echo = clean_name in clean_desc or clean_desc in clean_name
        if not echo:
            name_grams = _bigrams(clean_name)
            desc_grams = _bigrams(clean_desc)
            if name_grams and len(clean_desc) <= len(clean_name) * 1.8:
                shared = len(name_grams & desc_grams) / len(name_grams)
                echo = shared >= 0.55
        if not echo:
            name_chars = _chars(name)
            desc_chars = _chars(desc)
            if name_chars and desc_chars and len(clean_desc) <= len(clean_name) * 2.2:
                shared = len(name_chars & desc_chars) / len(name_chars | desc_chars)
                echo = shared >= 0.55
        if echo:
            line = text[:match.start()].count('\n') + 1
            out.append((line, name, desc))
    return out


def comment_lines(path: Path) -> list[tuple[int, str]]:
    """`//` 与块注释续行（`* …`）里的中文；去掉注释记号，只用来查开发文字。"""
    out = []
    for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        stripped = line.strip()
        if not (stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*')):
            continue
        text = re.sub(r'^(//+|/\*+|\*+)\s*', '', stripped)
        if re.search(r'[\u4e00-\u9fff]', text):
            out.append((number, text))
    return out


def glossary_aliases(root: Path, config: dict) -> dict[str, str]:
    """从项目术语表读出「禁用别名 → 唯一叫法」。"""
    rel = str(config.get('glossary') or '')
    if not rel:
        return {}
    path = root / rel
    if not path.is_file():
        return {}
    aliases: dict[str, str] = {}
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        cells = [cell.strip() for cell in stripped.strip('|').split('|')]
        if len(cells) < 3:
            continue
        canonical = cells[1].strip('*` ')
        banned = cells[2]
        if not canonical or canonical.startswith('---') or canonical.startswith(':') or '保留' in banned:
            continue
        for alias in re.split(r'[、,，]', banned):
            alias = alias.strip('*` ')
            if (len(alias) >= 2 and re.search(r'[\u4e00-\u9fff]', alias)
                    and not alias.startswith('—')):
                aliases[alias] = canonical
    return aliases


def scan(root: Path, tests: Path | None, config: dict,
         comments: bool = False, docs: bool = False) -> tuple[list[dict], dict[str, dict]]:
    findings: list[dict] = []
    terms: dict[str, dict] = {}
    allow = config['allow']
    gloss = glossary_text(root, config)
    aliases = glossary_aliases(root, config)
    glossary_rel = str(config.get('glossary') or '')

    def check(text: str, file: str, line: int, where: str) -> None:
        # 注释是开发文字：R1–R4（界面读法）不适用，只查 R7–R9
        if where != '注释':
            for rule_id, title, pattern, severity, advice in RULES:
                match = re.search(pattern, text)
                if not match or any(word in text for word in allow):
                    continue
                findings.append({
                    'file': file, 'line': line, 'where': where, 'rule': rule_id,
                    'title': title,
                    'severity': 'warning' if where in {'注释', '文档'} else severity,
                    'text': text[:100],
                    'matched': match.group(0), 'advice': advice,
                })
                break
            for rule_id, title, pattern, advice in PROSE_RULES:
                match = re.search(pattern, text)
                if not match or any(word in text for word in allow):
                    continue
                findings.append({
                    'file': file, 'line': line, 'where': where, 'rule': rule_id,
                    'title': title,
                    'severity': 'warning' if where == '文档' else 'error',
                    'text': text[:100], 'matched': match.group(0), 'advice': advice,
                })
                break
        # 开发文字：注释只查 R7 / R8（R9 的「这里」在注释里是正常指路）
        for rule_id, title, pattern, advice in DEV_RULES:
            if where == '注释' and rule_id == 'R9':
                continue
            match = re.search(pattern, text)
            if not match or any(word in text for word in allow):
                continue
            findings.append({
                'file': file, 'line': line, 'where': where, 'rule': rule_id,
                'title': title,
                'severity': 'warning' if where in {'注释', '文档'} else 'error',
                'text': text[:100], 'matched': match.group(0), 'advice': advice,
            })
            break
        for word in ABBREV + JARGON:
            if word not in text or word in allow or (gloss and word in gloss):
                continue
            item = terms.setdefault(word, {'word': word, 'count': 0, 'examples': []})
            item['count'] += 1
            if len(item['examples']) < 3:
                item['examples'].append({'file': file, 'line': line, 'text': text[:80]})

    for path in walk(root):
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(prefix) for prefix in config.get('skip') or []):
            continue
        if path.suffix == '.md':
            for line, text in headings(path):
                check(text, rel, line, '标题')
            for line, title, paragraph in duplicate_sections(path):
                findings.append({
                    'file': rel, 'line': line, 'where': '标题与首段', 'rule': 'R10',
                    'title': '标题与下面第一段在说同一件事',
                    'severity': 'warning',
                    'text': f'{title} / {paragraph[:70]}',
                    'matched': title,
                    'advice': '删掉复述的段落，或把段落改成证据、条件、例外',
                })
            if docs:
                for line, text in markdown_prose(path):
                    check(text, rel, line, '文档')
                    if path.name.lower() == 'readme.md':
                        for rule_id, title, pattern, advice in README_DEV_RULES:
                            match = re.search(pattern, text)
                            if not match or _in_code_span(text, match.start()):
                                continue
                            findings.append({
                                'file': rel, 'line': line, 'where': 'README', 'rule': rule_id,
                                'title': title, 'severity': 'warning', 'text': text[:100],
                                'matched': match.group(0), 'advice': advice,
                            })
                            break
        else:
            for line, text in ui_strings(path):
                check(text, rel, line, '界面')
            if comments:
                for line, text in comment_lines(path):
                    check(text, rel, line, '注释')
            for line, name, desc in setting_echoes(path):
                if any(word in desc for word in config['allow']):
                    continue
                findings.append({
                    'file': rel, 'line': line, 'where': '设置项', 'rule': 'R11',
                    'title': '设置项的说明只是把名字又说了一遍',
                    'severity': 'error',
                    'text': f'{name} / {desc[:70]}',
                    'matched': name,
                    'advice': '名字已讲清楚就删掉说明；要写就写默认值、影响范围、副作用',
                })
            for match in SETTING.finditer(path.read_text(encoding='utf-8', errors='replace')):
                desc = match.group(2)
                if not desc:
                    continue
                line = path.read_text(encoding='utf-8', errors='replace')[:match.start()].count('\n') + 1
                check(desc, rel, line, '设置说明')
        if aliases and rel != glossary_rel:
            text = path.read_text(encoding='utf-8', errors='replace')
            seen_alias: set[tuple[str, int]] = set()
            for alias, canonical in aliases.items():
                if alias in allow:
                    continue
                for match in re.finditer(re.escape(alias), text):
                    line = text[:match.start()].count('\n') + 1
                    key = (alias, line)
                    if key in seen_alias:
                        continue
                    seen_alias.add(key)
                    findings.append({
                        'file': rel, 'line': line, 'where': '文字', 'rule': 'R14',
                        'title': '用了术语表里的禁用别名', 'severity': 'error',
                        'text': alias, 'matched': alias,
                        'advice': f'改成「{canonical}」',
                    })

    if tests and tests.is_dir():
        for current, dirs, files in os.walk(tests):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
            for name in sorted(files):
                if not name.endswith('.ts'):
                    continue
                path = Path(current) / name
                for line, text in test_names(path):
                    check(text, path.as_posix(), line, '测试名')
    return findings, terms


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', required=True, help='项目根')
    parser.add_argument('--tests', default='', help='测试仓目录（可选，扫测试用例名）')
    parser.add_argument('--comments', action='store_true', help='同时扫 .ts 注释（R7–R9，只报 warning）')
    parser.add_argument('--docs', action='store_true', help='同时扫 Markdown 正文（README / 文档，只报 warning）')
    parser.add_argument('--dump', action='store_true', help='按 文件:行 导出全部界面文字与设置说明（人工抽查用）')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f'目录不存在：{root}', file=sys.stderr)
        return 2
    tests = Path(args.tests) if args.tests else None
    if tests and not tests.is_dir():
        print(f'测试目录不存在：{tests}', file=sys.stderr)
        return 2

    config = load_config(root)
    if args.dump:
        for path in walk(root):
            if path.suffix != '.ts':
                continue
            rel = path.relative_to(root).as_posix()
            for line, text in ui_strings(path):
                print(f'{rel}:{line}\t{text}')
            for match in SETTING.finditer(path.read_text(encoding='utf-8', errors='replace')):
                if match.group(2):
                    line = path.read_text(encoding='utf-8', errors='replace')[:match.start()].count('\n') + 1
                    print(f'{rel}:{line}\t[{match.group(1)}] {match.group(2)}')
        return 0
    findings, terms = scan(root, tests, config, args.comments, args.docs)
    errors = [item for item in findings if item['severity'] == 'error']
    ranked = sorted(terms.values(), key=lambda item: -item['count'])

    if args.json:
        print(json.dumps({'findings': findings, 'terms': ranked,
                          'errors': len(errors)}, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            mark = 'E' if item['severity'] == 'error' else 'W'
            print(f"{item['file']}:{item['line']} [{mark}] {item['rule']} "
                  f"{item['title']}（{item['where']}）：{item['text']}")
            print(f"    → {item['advice']}")
        if ranked:
            print('\n术语 / 自造词（按出现次数；登记到 readability.json 或术语表后不再报）：')
            for item in ranked[:15]:
                print(f"  {item['word']}：{item['count']} 处，例：{item['examples'][0]['text']}")
        print(f'\n{len(errors)} error / {len(findings) - len(errors)} warning'
              '（判据：references/text-quality.md「可读性」）')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
