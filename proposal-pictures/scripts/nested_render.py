#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nested_render.py — 把 nested_box 的盒模型画成整幅 SVG（白底 + 折线 + 叶子框）。

用法
  python nested_render.py 图.py --out out/图1.svg          # 干跑：只算不写
  python nested_render.py 图.py --out out/图1.svg --apply  # 真的写盘

spec（图.py）里要有
  ROOT      nested_box.Node —— 结构树（坐标由 measure/place 算，不用手写）
  CANVAS_W  画布宽（pt，默认 1600）
  PAD       页边距（默认 40）
  FS_DEF    默认字号（默认 15）
  CANVAS_H  可选；不给就按 root 高度 + 上下 PAD 推
  LINKS     可选；折线列表，每项两种写法：
              [(x, y), (x, y), …]                        直角折线，自动带箭头
              dict(pts=[…], color=…, width=…, arrow=True, label='…')

叶子颜色取节点属性，取不到用默认值：
  fill_color / stroke_color / ink
  ★ 注意：Node.fill 是"是否撑满子节点"的布尔开关，不是颜色，别拿它填色。

输出顺序：defs（箭头 marker id=nb-arrow）→ 白底 → links 折线 → 叶子框
（每个叶子：圆角矩形 + 框内文字垂直居中，tag 行在最前且粗体）。
"""
import argparse
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nested_box import BLUE, FACE, INK, LH, PAD_X, PAD_Y, TAG_GAP  # noqa: E402

LEAF_FILL = '#E8F1FA'      # 叶子默认底色（浅主色）
LEAF_STROKE_W = 2          # 叶子描边宽，与 lines.to_svg 的默认线宽一致
LEAF_RX = 8                # 圆角半径
LINE_H_FACTOR = 0.35       # 基线相对行盒中线的下沉系数（近似视觉居中）
LINK_W = 2                 # 折线默认线宽
LABEL_FS = 12.5            # 折线标注字号
LABEL_DY = 6               # 标注相对折点的上浮量


def _esc(s):
    """文字进 SVG 前的最小转义。"""
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _text(x, y, s, fill, fs, bold=False, anchor=None):
    """一行文字；tag 行用 bold。"""
    weight = ' font-weight="bold"' if bold else ''
    anc = f' text-anchor="{anchor}"' if anchor else ''
    return (f'  <text x="{x:.1f}" y="{y:.1f}" font-family="{FACE}" font-size="{fs:g}"'
            f'{weight}{anc} fill="{fill}">{_esc(s)}</text>')


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


def _link_parts(link):
    """折线的两种写法归一成 (点列表, 颜色, 线宽, 要不要箭头, 标注)。"""
    if isinstance(link, dict):
        pts = link.get('pts') or link.get('points') or []
        return ([(float(x), float(y)) for x, y in pts],
                link.get('color', BLUE), float(link.get('width', LINK_W)),
                bool(link.get('arrow', True)), link.get('label'))
    return ([(float(x), float(y)) for x, y in link], BLUE, float(LINK_W), True, None)


def link_svg(link):
    """一条折线：<polyline> + 可选标注（箭头指向最后一点）。"""
    pts, color, width, arrow, label = _link_parts(link)
    if len(pts) < 2:
        return []
    d = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    head = ' marker-end="url(#nb-arrow)"' if arrow else ''
    out = [f'  <polyline points="{d}" fill="none" stroke="{color}"'
           f' stroke-width="{width:g}" stroke-linejoin="round"{head}/>']
    if label:
        mx, my = pts[len(pts) // 2]
        out.append(_text(mx, my - LABEL_DY, label, color, LABEL_FS, False, 'middle'))
    return out


def render(root, canvas_w, canvas_h, pad, links=()):
    """整幅 SVG：箭头 marker → 白底 → links 折线 → 叶子框。"""
    if not canvas_h:                   # 不给高度就按 root 高度 + 上下边距推
        canvas_h = 2 * pad + root.h
    links = list(links or [])
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:g}" height="{canvas_h:g}"'
           f' viewBox="0 0 {canvas_w:g} {canvas_h:g}" font-family="{FACE}">',
           '  <defs>',
           '    <marker id="nb-arrow" viewBox="0 0 7 7" refX="7" refY="3.5" markerWidth="7"'
           ' markerHeight="7" markerUnits="userSpaceOnUse" orient="auto">',
           f'      <path d="M0,0 L7,3.5 L0,7 Z" fill="{BLUE}"/>',
           '    </marker>',
           '  </defs>',
           f'  <rect x="0" y="0" width="{canvas_w:g}" height="{canvas_h:g}" fill="#FFFFFF"/>']
    if links:
        out.append('  <g id="links">')
        for lk in links:
            out += link_svg(lk)
        out.append('  </g>')
    out.append('  <g id="boxes">')
    for lf in root.leaves():
        out += leaf_svg(lf)
    out.append('  </g>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def main() -> int:
    ap = argparse.ArgumentParser(description='盒模型 → SVG')
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
          f'  根盒 {root.w:.0f}×{root.h:.0f}')
    for lf in root.leaves():
        print(f'  叶 x={lf.x:6.1f}..{lf.x + lf.w:6.1f}  y={lf.y:6.1f}..{lf.y + lf.h:6.1f}'
              f'  ({lf.w:5.1f}×{lf.h:5.1f})  {getattr(lf, "tag", None) or lf.text[:20]}')
    errs = root.verify()
    print(f'  校验：{"通过 ✓" if not errs else "失败"}')
    for e in errs:
        print(f'    ★ {e}')

    links = getattr(m, 'LINKS', None) or []
    if not links:
        print('  （spec 没给 LINKS，只画盒子）')
    svg = render(root, canvas_w, canvas_h, pad, links)
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
