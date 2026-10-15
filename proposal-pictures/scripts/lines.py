#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""声明式画线模块：直线 / 折线 / 分支（一出多）/ 汇合（多入一）。

与 nested_box 的配合：线用**节点引用**声明，端点自动吸附到框边，不用写坐标。

四种线型
  straight(a, b)            直连（同一水平/垂直带上时用）
  elbow(a, b, via='auto')   折线：自动选拐点，走直角
  branch(src, dsts)         分支：一条干线 + 各支线（一出多，带竖/横干线）
  merge(srcs, dst)          汇合：多入一（各源汇到干线再到目标）

方向与吸附
  每个端点可指定边 'l'|'r'|'t'|'b'，默认按两框相对位置自动选（左→右用 'r'→'l'）。
  折线拐点：水平对水平时取两侧中点 x 作竖干线；垂直对垂直时取中点 y 作横干线。

标注
  label='文字' —— 画在干线中点旁；label_at='start|mid|end' 控制位置。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

BLUE, MUTED = '#2F6FB0', '#4B5563'
FACE = 'Microsoft YaHei, PingFang SC, Source Han Sans SC, SimHei, sans-serif'


def _edges(n):
    return dict(l=(n.x, n.y + n.h / 2), r=(n.x + n.w, n.y + n.h / 2),
                t=(n.x + n.w / 2, n.y), b=(n.x + n.w / 2, n.y + n.h))


def _auto_sides(a, b):
    """按两框相对位置自动选边。"""
    if b.x >= a.x + a.w - 1:
        return 'r', 'l'
    if a.x >= b.x + b.w - 1:
        return 'l', 'r'
    if b.y >= a.y + a.h - 1:
        return 'b', 't'
    return 't', 'b'


def _fit_label(text, slot_w, fs=13):
    """标注按槽位宽度折行：优先在空格/顿号处断，避免超出槽位。"""
    out = []
    for raw in str(text).split('\n'):
        cur = ''
        for ch in raw:
            if tw13(cur + ch) <= slot_w or not cur:
                cur += ch
            else:
                out.append(cur)
                cur = ch
        if cur:
            out.append(cur)
    return '\n'.join(out)


def tw13(s, fs=13):
    return sum(fs * (0.55 if ord(c) < 0x2E80 else 1.0) for c in s)


def _pt(n, side):
    return _edges(n)[side]


def straight(a, b, sa=None, sb=None, label=None):
    sa, sb = (sa, sb) if (sa and sb) else _auto_sides(a, b)
    return [(_pt(a, sa), _pt(b, sb))], label


def elbow(a, b, sa=None, sb=None, label=None, trunk='auto'):
    """直角折线：自动选拐点。"""
    sa, sb = (sa, sb) if (sa and sb) else _auto_sides(a, b)
    p0, p1 = _pt(a, sa), _pt(b, sb)
    horiz = sa in 'lr' and sb in 'lr'
    if horiz:
        if trunk == 'auto':
            # 竖干线 x：优先落在两框 x 重叠区中点，无重叠则退到两端中点
            lo = max(a.x, b.x)
            hi = min(a.x + a.w, b.x + b.w)
            mx = (lo + hi) / 2 if lo < hi else (p0[0] + p1[0]) / 2
        else:
            mx = trunk
        pts = [p0, (mx, p0[1]), (mx, p1[1]), p1]
    else:
        if trunk == 'auto':
            lo = max(a.y, b.y)
            hi = min(a.y + a.h, b.y + b.h)
            my = (lo + hi) / 2 if lo < hi else (p0[1] + p1[1]) / 2
        else:
            my = trunk
        pts = [p0, (p0[0], my), (p1[0], my), p1]
    return [tuple(pts)], label


def branch(src, dsts, sside=None, dside=None, gap=40, label=None):
    """分支：源出来先走一段，再沿干线分出各支线。

    返回 (segments, label)；label 以 dict 形式给出**自动算好的放置点**，
    放在干线与目标之间的空档里，避免压线压框。
    """
    lines = []
    if not dsts:
        return lines, label
    sside = sside or ('r' if dsts[0].x >= src.x + src.w - 1 else 'b')
    dside = dside or ('l' if sside == 'r' else 't')
    p0 = _pt(src, sside)
    lab = dict(text=label) if label else None
    if sside in 'lr':
        # 竖干线：取“源该边”与“最近目标该边”之间的中点
        nearest = min(_pt(d, dside)[0] for d in dsts)
        mx = (p0[0] + nearest) / 2
        ys = sorted(_pt(d, dside)[1] for d in dsts)
        lines.append([(p0[0], p0[1]), (mx, p0[1]), (mx, ys[-1])])
        for d in dsts:
            pt = _pt(d, dside)
            lines.append([(mx, pt[1]), pt])
        if lab:
            slot = nearest - p0[0]
            lab['text'] = _fit_label(lab['text'], slot)
            lab.update(x=mx, y=min(p0[1], ys[0]) - 6, anchor='middle')
    else:
        nearest = min(d.y if sside == 'b' else d.y + d.h for d in dsts)
        my = (p0[1] + nearest) / 2
        xs = sorted(_pt(d, dside)[0] for d in dsts)
        lines.append([(p0[0], p0[1]), (p0[0], my), (xs[-1], my)])
        for d in dsts:
            pt = _pt(d, dside)
            lines.append([(pt[0], my), pt])
        if lab:
            lab.update(x=xs[0] - 10, y=my - 8, anchor='end')
    return lines, lab


def merge(srcs, dst, sside=None, dside=None, gap=40, label=None):
    """汇合：多入一（与 branch 对称），标注同样自动找空位。"""
    lines = []
    if not srcs:
        return lines, label
    dside = dside or ('l' if srcs[0].x < dst.x else 't')
    p1 = _pt(dst, dside)
    lab = dict(text=label) if label else None
    if dside in 'lr':
        farthest = max(s.x + s.w if dside == 'l' else s.x for s in srcs)
        mx = (farthest + p1[0]) / 2
        ys = sorted(_pt(s, 'r' if dside == 'l' else 'l')[1] for s in srcs)
        for s in srcs:
            pt = _pt(s, 'r' if dside == 'l' else 'l')
            lines.append([pt, (mx, pt[1])])
        lines.append([(mx, ys[0]), (mx, ys[-1])])
        lines.append([(mx, p1[1]), p1])
        if lab:
            slot = p1[0] - farthest
            lab['text'] = _fit_label(lab['text'], slot - 16)
            # 贴干线右侧起排，避免压住干线
            lab.update(x=mx + 12, y=ys[0] + 4, anchor='start')
    else:
        farthest = max(s.y + s.h if dside == 't' else s.y for s in srcs)
        my = (farthest + p1[1]) / 2
        for s in srcs:
            pt = _pt(s, 'b' if dside == 't' else 't')
            lines.append([pt, (pt[0], my)])
        lines.append([(p1[0], my), p1])
        if lab:
            lab.update(x=p1[0] + 10, y=my - 8, anchor='start')
    return lines, lab


def to_svg(segments, color=BLUE, width=2, arrow=True, label=None, label_pos=None):
    """把线段集合渲染成 SVG 片段（最后一段带箭头）。

    label 三种写法
      '文字'                            自动放到最长一段旁，按段方向偏移
      '第一行\\n第二行'                  多行标注
      dict(text=…, x=…, y=…, anchor=…)  由 branch/merge 自动算好的槽位坐标
    """
    o = []
    n = len(segments)
    for i, seg in enumerate(segments):
        d = ' '.join('%g,%g' % p for p in seg)
        head = ' marker-end="url(#nb-arrow)"' if (arrow and i == n - 1) else ''
        o.append(f'  <polyline points="{d}" fill="none" stroke="{color}"'
                f' stroke-width="{width}"{head}/>')
    if label:
        if isinstance(label, dict):
            txt = label.get('text', '')
            tx, ty = label.get('x', 0), label.get('y', 0)
            anchor = label.get('anchor', 'middle')
        else:
            txt = label
            def seglen(s):
                return sum(abs(s[j + 1][0] - s[j][0]) + abs(s[j + 1][1] - s[j][1])
                           for j in range(len(s) - 1))
            seg = max(segments, key=seglen)
            mid = seg[len(seg) // 2]
            nxt = seg[min(len(seg) // 2 + 1, len(seg) - 1)]
            if abs(nxt[0] - mid[0]) >= abs(nxt[1] - mid[1]):
                tx, ty, anchor = mid[0], mid[1] - 8, 'middle'
            else:
                tx, ty, anchor = mid[0] + 10, mid[1] + 4, 'start'
            if label_pos == 'start':
                tx, ty, anchor = seg[0][0] + 8, seg[0][1] - 8, 'start'
            elif label_pos == 'end':
                tx, ty, anchor = seg[-1][0] + 8, seg[-1][1] - 8, 'start'
        for k, line in enumerate(str(txt).split('\n')):
            o.append(f'  <text x="{tx:.0f}" y="{ty + k * 16:.0f}" font-family="{FACE}"'
                    f' font-size="13" fill="{MUTED}" text-anchor="{anchor}">{line}</text>')
    return o
