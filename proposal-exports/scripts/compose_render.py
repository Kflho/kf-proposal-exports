#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose_render.py — 把 nested_box 的盒模型 + lines 的连线拼成一整幅 SVG。

用法
  python compose_render.py 图.py --out out/图1.svg          # 干跑：只算不写
  python compose_render.py 图.py --out out/图1.svg --apply  # 真的写盘

spec（图.py）里要有
  ROOT      nested_box.Node —— 结构树（坐标由 measure/place 算，不用手写）
  CANVAS_W  画布宽（pt，默认 1600）
  PAD       页边距（默认 40）
  FS_DEF    默认字号（默认 15）
  CANVAS_H  可选；不给就按 root 高度 + 上下 PAD 推
  WIRES     可选；连线列表，每项 dict，kind 指明线型：

    dict(kind='straight', a='A', b='B', sa=None, sb=None, label='…')
    dict(kind='elbow',    a='A', b='D', trunk='auto', label='…')
    dict(kind='branch',   src='A', dsts=['B', 'C'], sside=None, dside=None, gap=40, label='…')
    dict(kind='merge',    srcs=['B', 'C'], dst='D', sside=None, dside=None, gap=40, label='…')

  节点用 spec 里的**变量名**（字符串）指，也可以直接塞 Node 对象；
  其余键（color/width/arrow/label_pos）透传给 lines.to_svg。

输出顺序：defs（箭头 marker）→ 白底 → 连线 → 叶子框（圆角矩形 + 文字垂直居中）。
"""
import argparse
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nested_box import BLUE, FACE, INK, LH, PAD_X, PAD_Y, TAG_GAP  # noqa: E402
import lines  # noqa: E402

LEAF_FILL = '#E8F1FA'      # 叶子默认底色（浅主色）
LEAF_STROKE_W = 2          # 叶子描边宽，与 lines.to_svg 的默认线宽一致
LEAF_RX = 8                # 圆角半径
LINE_H_FACTOR = 0.35       # 基线相对行盒中线的下沉系数（近似视觉居中）


def _esc(s):
    """文字进 SVG 前的最小转义。"""
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _text(x, y, s, fill, fs, bold=False):
    """一行文字；tag 行用 bold。"""
    weight = ' font-weight="bold"' if bold else ''
    return (f'  <text x="{x:.1f}" y="{y:.1f}" font-family="{FACE}" font-size="{fs:g}"'
            f'{weight} fill="{fill}">{_esc(s)}</text>')


def leaf_svg(lf):
    """一个叶子：圆角矩形 + 垂直居中的文字块（tag 行粗体在最前）。"""
    fill = getattr(lf, 'fill_color', LEAF_FILL)
    stroke = getattr(lf, 'stroke_color', BLUE)
    ink = getattr(lf, 'ink', INK)
    fs = getattr(lf, 'fs_v', 15)
    tfs = getattr(lf, 'tfs_v', fs)
    tag = getattr(lf, 'tag', None)
    rows = list(getattr(lf, 'lines', None) or [])
    if not rows:                       # 没 measure 过就退回原始 text
        rows = str(getattr(lf, 'text', '')).split('\n')
    blk = (tfs * LH + TAG_GAP if tag else 0) + len(rows) * fs * LH
    cy = lf.y + max(PAD_Y, (lf.h - blk) / 2)
    out = [f'  <rect x="{lf.x:g}" y="{lf.y:g}" width="{lf.w:g}" height="{lf.h:g}"'
           f' rx="{LEAF_RX}" fill="{fill}" stroke="{stroke}"'
           f' stroke-width="{LEAF_STROKE_W}"/>']
    if tag:
        out.append(_text(lf.x + PAD_X, cy + tfs * (LH / 2 + LINE_H_FACTOR), tag, ink, tfs, True))
        cy += tfs * LH + TAG_GAP
    for t in rows:
        out.append(_text(lf.x + PAD_X, cy + fs * (LH / 2 + LINE_H_FACTOR), t, ink, fs))
        cy += fs * LH
    return out


def render(root, canvas_w, canvas_h, pad, wire_svg):
    """整幅 SVG：箭头 marker → 白底 → 连线片段 → 叶子框。"""
    if not canvas_h:                   # 不给高度就按 root 高度 + 上下边距推
        canvas_h = 2 * pad + root.h
    if isinstance(wire_svg, (list, tuple)):
        wire_svg = '\n'.join(wire_svg)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:g}" height="{canvas_h:g}"'
           f' viewBox="0 0 {canvas_w:g} {canvas_h:g}" font-family="{FACE}">',
           '  <defs>',
           '    <marker id="nb-arrow" viewBox="0 0 7 7" refX="7" refY="3.5" markerWidth="7"'
           ' markerHeight="7" markerUnits="userSpaceOnUse" orient="auto">',
           f'      <path d="M0,0 L7,3.5 L0,7 Z" fill="{BLUE}"/>',
           '    </marker>',
           '  </defs>',
           f'  <rect x="0" y="0" width="{canvas_w:g}" height="{canvas_h:g}" fill="#FFFFFF"/>']
    if wire_svg.strip():
        out.append('  <g id="wires">')
        out.append(wire_svg)
        out.append('  </g>')
    out.append('  <g id="boxes">')
    for lf in root.leaves():
        out += leaf_svg(lf)
    out.append('  </g>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def _node(m, ref):
    """WIRES 里的节点引用：字符串按 spec 变量名取，其它（Node）直接用。"""
    if isinstance(ref, str):
        if not hasattr(m, ref):
            raise SystemExit(f'!! spec 里没有变量 {ref!r}')
        return getattr(m, ref)
    return ref


def _make_wire(m, w):
    """按 kind 调 lines 的四种线型，返回 (segments, label)。"""
    kind = (w.get('kind') or 'straight').lower()
    label = w.get('label')
    if kind == 'straight':
        return lines.straight(_node(m, w['a']), _node(m, w['b']),
                              w.get('sa'), w.get('sb'), label)
    if kind == 'elbow':
        return lines.elbow(_node(m, w['a']), _node(m, w['b']),
                           w.get('sa'), w.get('sb'), label, w.get('trunk', 'auto'))
    if kind == 'branch':
        return lines.branch(_node(m, w['src']), [_node(m, d) for d in w.get('dsts', [])],
                            w.get('sside'), w.get('dside'), w.get('gap', 40), label)
    if kind == 'merge':
        return lines.merge([_node(m, s) for s in w.get('srcs', [])], _node(m, w['dst']),
                           w.get('sside'), w.get('dside'), w.get('gap', 40), label)
    raise SystemExit(f'!! 未知线型 {kind!r}：只支持 straight / elbow / branch / merge')


def _label_info(label):
    """标注摘要：dict（branch/merge 自动算的槽位）连坐标一起打。"""
    if isinstance(label, dict):
        txt = str(label.get('text', '')).replace('\n', '⏎')
        return (f'标注 {txt!r} @({label.get("x", 0):.0f},{label.get("y", 0):.0f})'
                f' anchor={label.get("anchor", "middle")}')
    if label:
        return f'标注 {str(label)!r}'
    return '无标注'


def main() -> int:
    ap = argparse.ArgumentParser(description='盒模型 + 连线 → 整幅 SVG')
    ap.add_argument('spec', help='图定义脚本（要有 ROOT / CANVAS_W / PAD / FS_DEF）')
    ap.add_argument('--out', required=True, help='输出的 .svg 路径')
    ap.add_argument('--apply', action='store_true', help='真的写盘（默认只干跑）')
    a = ap.parse_args()

    sp = importlib.util.spec_from_file_location('spec', a.spec)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)

    root = m.ROOT
    fs_def = getattr(m, 'FS_DEF', 15)
    canvas_w = getattr(m, 'CANVAS_W', 1600)
    pad = getattr(m, 'PAD', 40)
    inner_w = canvas_w - 2 * pad
    root.measure(fs_def)
    root.place(pad, pad, inner_w, None)
    canvas_h = getattr(m, 'CANVAS_H', None) or (2 * pad + root.h)

    print(f'=== {a.spec} ===')
    print(f'  画布 {canvas_w:.0f}×{canvas_h:.0f}  边距 {pad:.0f}  内宽 {inner_w:.0f}'
          f'  根盒 {root.w:.0f}×{root.h:.0f}  叶 {len(list(root.leaves()))} 个')

    wires = getattr(m, 'WIRES', None) or []
    if not wires:
        print('  （spec 没给 WIRES，只画盒子）')
    wire_svg = []
    for k, w in enumerate(wires, 1):
        segments, label = _make_wire(m, w)
        wire_svg += lines.to_svg(segments, color=w.get('color', BLUE),
                                 width=w.get('width', 2), arrow=w.get('arrow', True),
                                 label=label, label_pos=w.get('label_pos'))
        print(f'  线{k} {str(w.get("kind", "straight")):8} {len(segments)} 段   {_label_info(label)}')

    errs = root.verify()
    if errs:
        print(f'  校验：失败（{len(errs)} 条）')
        for e in errs:
            print(f'    ★ {e}')
    else:
        print('  校验：通过 ✓')

    svg = render(root, canvas_w, canvas_h, pad, wire_svg)
    if not a.apply:
        print(f'（干跑）SVG {len(svg)} 字符，未写盘；加 --apply 才写到 {a.out}')
        return 0
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding='utf-8')
    print(f'✅ {out}  ({out.stat().st_size / 1024:.1f} KB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
