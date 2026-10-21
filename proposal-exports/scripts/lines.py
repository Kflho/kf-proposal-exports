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


def connect(a, b, sa=None, sb=None, label=None, tol=0.5):
    """**首选**连线方式：能直连就直连，否则退化为直角折线。

    直连的判据（横向为例）：把源框那条边的中点，沿边滑动到目标框边点的 y，
    若该 y 落在源框的纵向范围内（即"源框那条边上确实存在这个高度"），
    则一根水平直线即可连接，不需要拐弯。
    """
    sa2, sb2 = (sa, sb) if (sa and sb) else _auto_sides(a, b)
    p1 = _pt(b, sb2)
    if sa2 in 'lr':
        if a.y - tol <= p1[1] <= a.y + a.h + tol:          # 目标高度落在源框范围内
            return [((a.x + a.w if sa2 == 'r' else a.x, p1[1]), p1)], label
    elif sa2 in 'tb':
        if a.x - tol <= p1[0] <= a.x + a.w + tol:
            return [((p1[0], a.y + a.h if sa2 == 'b' else a.y), p1)], label
    return elbow(a, b, sa2, sb2, label)


def elbow(a, b, sa=None, sb=None, label=None, trunk='auto'):
    """直角折线：自动选拐点。

    先判断能否**直连**：两侧边点已经对齐（横向同 y / 纵向同 x）时，
    直接给一根直线——这是最常见的观感问题（能直却硬折一个弯）。
    """
    sa, sb = (sa, sb) if (sa and sb) else _auto_sides(a, b)
    p0, p1 = _pt(a, sa), _pt(b, sb)
    if sa in 'lr' and sb in 'lr' and abs(p0[1] - p1[1]) < 1.0:
        return [(p0, p1)], label
    if sa in 'tb' and sb in 'tb' and abs(p0[0] - p1[0]) < 1.0:
        return [(p0, p1)], label
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
        # 引出点取**支线跨度的中点**（干线上下对称），并夹在源框该边的纵向范围内
        y_mid = (ys[0] + ys[-1]) / 2
        y_feed = min(max(y_mid, src.y + 1.0), src.y + src.h - 1.0)
        lines.append([(p0[0], y_feed), (mx, y_feed)])         # 引出段
        lines.append([(mx, min(y_feed, ys[0])), (mx, max(y_feed, ys[-1]))])   # 干线

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
        x_lo, x_hi = min([p0[0]] + xs), max([p0[0]] + xs)
        lines.append([(p0[0], p0[1]), (p0[0], my)])
        lines.append([(x_lo, my), (x_hi, my)])

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
        y_lo, y_hi = min([p1[1]] + ys), max([p1[1]] + ys)
        lines.append([(mx, y_lo), (mx, y_hi)])
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


def route(pa, pb, trunk=None, tol=1.0):
    """给定两个端点，**能直就直**（同高走水平直线、同列走竖直直线），否则走直角折线。

    trunk 为干线坐标（水平连接给 x，垂直连接给 横线 y）；缺省取两端点中点。
    供 ports() 取好均匀分布点之后调用。
    """
    (x0, y0), (x1, y1) = pa, pb
    if abs(y0 - y1) < tol or abs(x0 - x1) < tol:
        return [(pa, pb)]
    if abs(y0 - y1) <= abs(x0 - x1):          # 以水平为主：竖干线
        tx = trunk if trunk is not None else (x0 + x1) / 2
        return [(pa, (tx, y0), (tx, y1), pb)]
    ty = trunk if trunk is not None else (y0 + y1) / 2
    return [(pa, (x0, ty), (x1, ty), pb)]


def ports(node, side, n, inset=1.0):
    """R1：在 node 的某条边上取 **n 个均匀分布**的引出/引入点。

    位置为 k/(n+1) 分位（k=1..n）：n=2 → 三等分点；n=3 → 四等分点。
    inset 用于把点从边端点向内收一点，避免压到圆角。
    """
    if n <= 0:
        return []
    if side in 'lr':
        x = node.x + node.w if side == 'r' else node.x
        lo, hi = node.y + inset, node.y + node.h - inset
        return [(x, lo + (hi - lo) * (k + 1) / (n + 1)) for k in range(n)]
    y = node.y + node.h if side == 'b' else node.y
    lo, hi = node.x + inset, node.x + node.w - inset
    return [(lo + (hi - lo) * (k + 1) / (n + 1), y) for k in range(n)]


def connect_many(srcs, dsts, sside=None, dside=None, label=None):
    """多源→多目标：源侧与目标侧都按 R1 均匀分布，每条按 R2 能直就直。

    返回 (segments, label)；适用于"若干框并到一框"或"一框分到若干框"的场合。
    """
    segs = []
    sside = sside or 'r'
    dside = dside or 'l'
    if len(srcs) == 1:                       # 一源多目标：源侧走 branch（干线+支线）
        return branch(srcs[0], dsts, sside=sside, dside=dside, label=label)
    if len(dsts) == 1:                       # 多源一目标：目标侧走 merge
        return merge(srcs, dsts[0], sside=sside, dside=dside, label=label)
    # 多对多：两侧均匀取点，逐条连（能直就直）
    ps = ports(srcs[0], sside, len(srcs)) if len(srcs) > 1 else [None]
    pd = ports(dsts[0], dside, len(dsts)) if len(dsts) > 1 else [None]
    for i, a in enumerate(srcs):
        for j, b in enumerate(dsts):
            if i != j and len(srcs) == len(dsts):
                continue
            sp = ps[i] if ps[i] else _pt(a, sside)
            dp = pd[j] if pd[j] else _pt(b, dside)
            if abs(sp[1] - dp[1]) < 1.0 or (sside in 'lr' and a.y <= dp[1] <= a.y + a.h):
                segs.append([sp, dp])
            else:
                segs += elbow(a, b, sside, dside)[0]
    return segs, label


def place_label(segment, text, fs=12, gap=6, side='above', avail=None, wrap=None):
    """**标注贴自己那一段**：返回 (x, y, anchor, lines)。

    · 水平段：**x 取段中点、anchor=middle**，整块置于线上方 gap 像素（并让出 0.25em 下行部）
    · 竖直段：置于线右侧 gap 像素（anchor=start）
    · wrap = 折行函数（如 _wrap_dp.wrap_dp 的偏函数），avail 为可用宽度
    """
    (x0, y0), (x1, y1) = segment[0], segment[-1]
    lines = [text]
    if wrap and avail:
        lines = wrap(text, fs, avail) or [text]
    horiz = abs(y1 - y0) <= abs(x1 - x0)
    if horiz:
        x = (x0 + x1) / 2
        # 让出下行部（0.25em）：否则文字盒底会压线
        # 保守让出近一行高度：保证文字盒整体（含下行部）都落在线上方
        y = min(y0, y1) - gap - fs * 0.9
        anchor = 'middle'
    else:
        x = max(x0, x1) + gap
        y = (y0 + y1) / 2
        anchor = 'start'
    if side == 'below' and horiz:
        y = max(y0, y1) + gap + fs
    if side == 'left' and not horiz:
        x = min(x0, x1) - gap
        anchor = 'end'
    return x, y, anchor, lines


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
