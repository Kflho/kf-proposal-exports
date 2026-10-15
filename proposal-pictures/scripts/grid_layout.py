#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网格排版引擎 v3：声明"行 × 列 + 对齐关系"，坐标全由脚本算。

与"死表格"的区别
  · 每格尺寸按自身文字定，**不等宽不等高**
  · 对齐由策略决定：默认**水平居中于所在列带、垂直居中于所在行带**
  · 支持行/列跨格（cols span）；支持竖排标题条（mode='vstrip'）
  · 支持"元素组"（stack）：一组元素按垂直间距堆叠，**整组在行带内居中**
  · 连线由声明生成，端点自动吸附框边 + 自动直角

对齐口径（核心）
  列带 column band：由各列宽累加得到；格若跨列则占多列带之和
  行带 row band：行高 = 该行所有格所需高的最大值；每格在自己行带内**垂直居中**
  于是"横向 1-3-1"表现为三条列带居中；"纵向高度对齐"表现为同一行带的格上下居中对齐
"""
import argparse
import importlib.util
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wrap_dp import wrap_dp, char_w

FACE = 'Microsoft YaHei, PingFang SC, Source Han Sans SC, SimHei, sans-serif'
BLUE, ORANGE, INK, MUTED, LIGHT = '#2F6FB0', '#E8A33D', '#1F2937', '#4B5563', '#E8F1FA'
LH, PAD_X, PAD_Y, TAG_GAP = 1.45, 22, 18, 6
INK_H = 1.02
ROT_OFF = 0.375
NO_START = set('，。；、：！？）》」』%')


def tw(s, fs):
    return sum(char_w(c, fs) for c in s)


def fit_vfs(text, h, w, fs_max, pad_v=12, pad_h=14):
    return max(5.0, min(fs_max, (h - 2 * pad_v) / max(1, len(text)) / INK_H,
                        (w - 2 * pad_h) / INK_H))


class Grid:
    """按声明算出版式。ROWS 里每项 = 一条"行带"，cells = 该行带内的格。"""

    def __init__(self, g):
        self.g = g
        self.rows = g.ROWS
        self.pad, self.gap = g.CANVAS_PAD, g.GAP
        self.fs = self.rows[0].get('fs', 15)
        self.left = getattr(g, 'LEFT_W', 0)
        self._cols()
        self._rows()


    def _cols(self):
        ncol = max(c['cols'][1] for r in self.rows for c in r['cells']) + 1
        need = [0.0] * ncol
        used = [False] * ncol
        for r in self.rows:
            fs, tfs = r.get('fs', self.fs), r.get('tag_fs', r.get('fs', self.fs))
            for c in r['cells']:
                a, b = c['cols']
                for k in range(a, b + 1):
                    used[k] = True
                if a != b:
                    continue
                for part in c['text'].split('\n'):
                    need[a] = max(need[a], tw(part, fs) + 2 * PAD_X)
                if c.get('tag'):
                    need[a] = max(need[a], tw(c['tag'], tfs) + 2 * PAD_X)
        self.live = [k for k in range(ncol) if used[k]]
        base = [max(getattr(self.g, 'COL_MIN', 200), need[k]) for k in self.live]
        pad, gap = self.pad, self.gap
        x0 = pad
        if self.left:
            x0 = pad + self.left + gap
        total = sum(base) + gap * (len(base) - 1)
        target = getattr(self.g, 'CANVAS_W', 1600) - x0 - pad
        if total < target:
            extra = (target - total) / len(base)
            base = [b + extra for b in base]
        self.col_w = base
        self.col_x, x = [], x0
        for v in base:
            self.col_x.append(x)
            x += v + gap
        self.canvas_w = (self.col_x[-1] + self.col_w[-1]) + pad

    def span(self, c):
        a, b = c['cols']
        i0, i1 = self.live.index(a), self.live.index(b)
        return self.col_x[i0], sum(self.col_w[i0:i1 + 1]) + self.gap * (i1 - i0)


    def _rows(self):
        self.row_h, self.packs = [], []
        for r in self.rows:
            fs, tfs = r.get('fs', self.fs), r.get('tag_fs', r.get('fs', self.fs))
            h, packs = 0, []
            if r.get('stack'):
                # 元素组：每个元素先断行定高，整组再在行带内居中
                hs = []
                for item in r['stack']:
                    _, w = self.span(item)
                    ls = [x for part in item['text'].split('\n')
                          for x in (wrap_dp(part, fs, w - 2 * PAD_X) or [part])]
                    bh = len(ls) * fs * LH + (tfs * LH + TAG_GAP if item.get('tag') else 0) + 2 * PAD_Y
                    hs.append(bh)
                    packs.append((item, ls, w))
                sg = r.get('stack_gap', self.gap)
                h = sum(hs) + sg * (len(hs) - 1)
                r['_hs'] = hs
            else:
                for c in r['cells']:
                    _, w = self.span(c)
                    ls = [x for part in c['text'].split('\n')
                          for x in (wrap_dp(part, fs, w - 2 * PAD_X) or [part])]
                    bh = len(ls) * fs * LH + (tfs * LH + TAG_GAP if c.get('tag') else 0) + 2 * PAD_Y
                    h = max(h, bh)
                    packs.append((c, ls, w))
            self.row_h.append(h)
            self.packs.append(packs)
        # 行带 y：自上而下累加，整块在画布内（上下各留 pad）
        self.row_y, y = [], self.pad
        for h in self.row_h:
            self.row_y.append(y)
            y += h + self.gap
        self.canvas_h = y - self.gap + self.pad

    def box(self, ri, ci):
        """普通行的第 ci 个格的框（垂直居中于行带）。"""
        r = self.rows[ri]
        c, ls, w = self.packs[ri][ci]
        fs, tfs = r.get('fs', self.fs), r.get('tag_fs', r.get('fs', self.fs))
        bh = len(ls) * fs * LH + (tfs * LH + TAG_GAP if c.get('tag') else 0) + 2 * PAD_Y
        x0, _ = self.span(c)
        y0 = self.row_y[ri] + (self.row_h[ri] - bh) / 2
        return x0, y0, w, bh

    def stack_boxes(self, ri):
        """元素组的各框（整组垂直居中于行带）。"""
        r = self.rows[ri]
        hs, sg = r['_hs'], r.get('stack_gap', self.gap)
        total = sum(hs) + sg * (len(hs) - 1)
        y0 = self.row_y[ri] + (self.row_h[ri] - total) / 2
        out = []
        for i, item in enumerate(r['stack']):
            x0, w = self.span(item)
            out.append((x0, y0, w, hs[i], item))
            y0 += hs[i] + sg
        return out

    # 验收：超宽 / 行首标点（生成前的 gate，失败则不写图）
    def verify(self):
        errs = []
        for ri, r in enumerate(self.rows):
            fs = r.get('fs', self.fs)
            for c, ls, w in self.packs[ri]:
                avail = w - 2 * PAD_X
                for t in ls:
                    if tw(t, fs) > avail + 0.5:
                        errs.append(f'超宽 {tw(t,fs):.0f}>{avail:.0f} 「{t[:26]}」')
                    if t and t[0] in NO_START:
                        errs.append(f'行首标点 「{t[:20]}」')
            if r.get('stack'):
                for item in r['stack']:
                    if item.get('vstrip'):
                        continue
        return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('grid')
    ap.add_argument('--out', required=True)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()

    spec = importlib.util.spec_from_file_location('grid_spec', a.grid)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    G = Grid(g)

    print('=== 由声明算出的版式（行带 / 列带，格在带内居中）===')
    print(f'  画布 {G.canvas_w:.0f}×{G.canvas_h:.0f}   外边距 {G.pad}  间距 {G.gap}')
    print(f'  列宽 {[round(w) for w in G.col_w]}   列 x {[round(v) for v in G.col_x]}')
    for i, r in enumerate(G.rows):
        n = len(r.get('stack') or r['cells'])
        print(f'  行带{i} {r.get("name",""):<12} y={G.row_y[i]:.0f}..{G.row_y[i]+G.row_h[i]:.0f} (h='
                 f'{G.row_h[i]:.0f})  元素 {n}')
        if r.get('stack'):
            for x0, y0, w, h, item in G.stack_boxes(i):
                print(f'      条 x={x0:.0f}..{x0+w:.0f}  y={y0:.0f}..{y0+h:.0f}  {item["text"][:18]}')
        else:
            for ci in range(n):
                x0, y0, w, h = G.box(i, ci)
                print(f'      格 x={x0:.0f}..{x0+w:.0f}  y={y0:.0f}..{y0+h:.0f}  '
                      f'{G.packs[i][ci][0].get("tag") or G.packs[i][ci][0]["text"][:16]}')

    errs = G.verify()
    if errs:
        print('\n★ 生成前验收失败：')
        for e in errs:
            print('   ' + e)
        return 1
    print('  生成前验收通过 ✓')
    if not a.apply:
        print('\nDRY RUN')
        return 0
    # ★ 以下渲染分支在 pyc 中不存在（字节码到 DRY RUN 为止），是按模块文档 + FACE/色板/fit_vfs/ROT_OFF
    #   这些「定义却没用上」的常量推断补写的，逐字标出，便于日后与真版对比。
    render(G, a.out)
    print(f'\n已渲染 {a.out}')
    return 0


def esc(s):
    """SVG 文本转义（pyc 里 import 了 re 却没用，推断原版就是在这里用的）。"""
    return re.sub(r'[&<>"]', lambda m: {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[m.group(0)], s)


def _line_svg(cx, top, fs, lines, fill, weight='normal'):
    """一坨居中文字：每行按 fs*LH 的行高排，垂直居中到 top..top+len*fs*LH。"""
    out = []
    for k, t in enumerate(lines):
        y = top + fs * LH * (k + 0.5)
        out.append('<text x="%.1f" y="%.1f" font-size="%.1f" fill="%s" font-weight="%s"'
                   ' text-anchor="middle" dominant-baseline="central">%s</text>'
                   % (cx, y, fs, fill, weight, esc(t)))
    return out


def _box_svg(x0, y0, w, h, item, ls, fs, tfs):
    """一个圆角框 + 框内居中文字；tag 粗体在前，vstrip 走竖排。"""
    out = ['<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="10" fill="%s" stroke="%s"'
           ' stroke-width="1.5"/>' % (x0, y0, w, h, LIGHT, MUTED if item.get('vstrip') else BLUE)]
    cx = x0 + w / 2
    if item.get('vstrip'):
        vfs = fit_vfs(item['text'], h, w, fs)
        out.append('<text x="%.1f" y="%.1f" font-size="%.1f" fill="%s" font-weight="bold"'
                   ' text-anchor="middle" dominant-baseline="central" transform="rotate(-90 %.1f %.1f)">%s</text>'
                   % (cx, y0 + h / 2 + vfs * ROT_OFF, vfs, MUTED, cx, y0 + h / 2, esc(item['text'])))
        return out
    tag = item.get('tag')
    ink_h = len(ls) * fs * LH + (tfs * LH + TAG_GAP if tag else 0)
    top = y0 + (h - ink_h) / 2
    if tag:
        out += _line_svg(cx, top, tfs, [tag], ORANGE, 'bold')
        top += tfs * LH + TAG_GAP
    return out + _line_svg(cx, top, fs, ls, INK)


def _link_svg(a, b, label=''):
    """连线：端点自动吸附到框边（左/右），中途一个直角拐点。"""
    ax, ay, bx, by = a[0] + a[2] / 2, a[1] + a[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
    if bx >= ax:
        sx, ex, s = a[0] + a[2], b[0], 5.0
    else:
        sx, ex, s = a[0], b[0] + b[2], -5.0
    mx = (sx + ex) / 2
    out = ['<path d="M %.1f %.1f H %.1f V %.1f H %.1f" fill="none" stroke="%s" stroke-width="1.4"/>'
           % (sx, ay, mx, by, ex, ORANGE),
           '<path d="M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" fill="%s"/>'
           % (ex, by, ex - s, by - 3.5, ex - s, by + 3.5, ORANGE)]
    if label:
        out.append('<text x="%.1f" y="%.1f" font-size="11" fill="%s" text-anchor="middle">%s</text>'
                   % (mx, (ay + by) / 2 - 4, MUTED, esc(label)))
    return out


def render(G, out):
    """把算好的框写成 SVG（★ 推断补写：无字节码可依，按模块文档口径实现）。

    LINKS 支持 (a, b) / [a, b] / dict(a=, b=, label=)，a/b 取行带 name 或格/元素的 name。
    """
    W, H = G.canvas_w, G.canvas_h
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" viewBox="0 0 %.0f %.0f">'
             % (W, H, W, H),
             '<rect x="0" y="0" width="%.0f" height="%.0f" fill="#FFFFFF"/>' % (W, H),
             '<g font-family="%s">' % FACE]
    anchors = {}
    for ri, r in enumerate(G.rows):
        fs, tfs = r.get('fs', G.fs), r.get('tag_fs', r.get('fs', G.fs))
        boxes = []
        if r.get('stack'):
            for i, (x0, y0, w, h, item) in enumerate(G.stack_boxes(ri)):
                boxes.append((x0, y0, w, h, item, G.packs[ri][i][1]))
        else:
            for ci in range(len(G.packs[ri])):
                x0, y0, w, h = G.box(ri, ci)
                boxes.append((x0, y0, w, h, G.packs[ri][ci][0], G.packs[ri][ci][1]))
        for x0, y0, w, h, item, ls in boxes:
            parts += _box_svg(x0, y0, w, h, item, ls, fs, tfs)
            if item.get('name'):
                anchors[item['name']] = (x0, y0, w, h)
        if boxes and r.get('name'):
            anchors[r['name']] = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                                  max(b[0] + b[2] for b in boxes) - min(b[0] for b in boxes),
                                  max(b[1] + b[3] for b in boxes) - min(b[1] for b in boxes))
    for spec in getattr(G.g, 'LINKS', []) or []:
        if isinstance(spec, dict):
            ka = spec.get('a') or spec.get('from') or spec.get('src')
            kb = spec.get('b') or spec.get('to') or spec.get('dst')
            label = spec.get('label') or spec.get('text') or ''
        else:
            ka, kb = (list(spec) + ['', ''])[:2]
            label = ''
        if ka in anchors and kb in anchors:
            parts += _link_svg(anchors[ka], anchors[kb], label)
    parts.append('</g></svg>')
    Path(out).write_text('\n'.join(parts) + '\n', encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
