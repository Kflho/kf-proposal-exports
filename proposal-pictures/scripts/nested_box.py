#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""嵌套盒排版引擎：用"并列"（横排/纵排）递归描述结构，坐标全由脚本算。

核心思想
  一张图 = 一棵树。节点两类：
    box(text=...)                     叶子：文字块，尺寸由文字定
    stack(dir='v'|'h', children=[...]) 并列：把子节点按方向排开
  每个 stack 的尺寸 = 子节点尺寸 + 间距（递归求得）
  然后自顶向下分配位置：
    · 若父容器给的尺寸 > 子节点所需，按 align 对齐（默认居中）
    · 若某子节点是 stack 且空间有富余，**等比撑高/撑宽其内部**（fill 策略），
      于是"垂直三个并列 + 下面一个"能撑到与左列等高，实现纵向对齐

嵌套示例（本图的右列）
  stack(dir='v', children=[
      stack(dir='v', children=[box('4-1'), box('4-2'), box('4-3')]),   # 三个并列
      box('支撑产出'),                                                # 与上面并列
  ])

输出：每个叶子框的 (x, y, w, h) + 每行文字的基线位置
"""
import argparse
import importlib.util
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wrap_dp import wrap_dp, char_w

FACE = 'Microsoft YaHei, PingFang SC, Source Han Sans SC, SimHei, sans-serif'
BLUE, ORANGE, INK, MUTED = '#2F6FB0', '#E8A33D', '#1F2937', '#4B5563'
LH, PAD_X, PAD_Y, TAG_GAP = 1.45, 22, 18, 6
INK_H, ROT_OFF = 1.02, 0.375
NO_START = set('，。；、：！？）》」』%')


def tw(s, fs):
    return sum(char_w(c, fs) for c in s)


class Node:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.children = kw.get('children') or []
        self.dir = kw.get('dir', 'v')
        self.gap = kw.get('gap')
        self.align = kw.get('align', 'center')
        self.fill = kw.get('fill_children', True)
        for c in self.children:
            c.parent = self
        self.w = self.h = 0.0
        self.x = self.y = 0.0


    def measure(self, fs_def):
        # 车道节点：只占一条 lane_w 宽的列，高度不计（由相邻 stack 自行排布）
        if getattr(self, 'lane', False):
            self.w = float(getattr(self, 'lane_w', 60))
            self.h = 0.0
            self.lines = []
            self.fs_v = self.tfs_v = fs_def
            return self.w, self.h
        if not self.children:
            fs = getattr(self, 'fs', fs_def)
            tfs = getattr(self, 'tag_fs', fs)
            avail = getattr(self, 'width', None)
            if avail is None:
                head = getattr(self, 'tag', None)
                self.w = max([tw(p, fs) for p in self.text.split('\n')]
                             + ([tw(head, tfs)] if head else [])) + 2 * PAD_X
            else:
                self.w = avail
            inner = self.w - 2 * PAD_X
            self.lines = []
            for part in self.text.split('\n'):
                self.lines += wrap_dp(part, fs, inner) or [part]
            self.h = len(self.lines) * fs * LH + (tfs * LH + TAG_GAP if getattr(self, 'tag', None) else 0) + 2 * PAD_Y
            self.fs_v, self.tfs_v = fs, tfs
            return self.w, self.h
        gap = self.gap if self.gap is not None else 30
        ws, hs = [], []
        for c in self.children:
            w, h = c.measure(fs_def)
            ws.append(w)
            hs.append(h)
        if self.dir == 'v':
            self.w = max(ws)
            self.h = sum(hs) + gap * (len(hs) - 1)
        else:
            self.w = sum(ws) + gap * (len(ws) - 1)
            self.h = max(hs)
        self._ws, self._hs, self._gap = ws, hs, gap
        return self.w, self.h


    def place(self, x, y, w=None, h=None):
        self.x, self.y = x, y
        if getattr(self, 'lane', False):
            self.w = w or self.w
            self.h = h or self.h
            return
        if not self.children:
            self.w, self.h = w or self.w, h or self.h
            return
        gap = self._gap
        if self.dir == 'v':
            need = sum(self._hs) + gap * (len(self._hs) - 1)
            extra = max(0.0, (h or self.h) - need)
            # 富余高度只分给"可撑"的子节点：自身还有子节点，或显式 stretch
            growable = [i for i, c in enumerate(self.children)
                        if c.children or getattr(c, 'stretch', False)]
            if self.fill and extra > 0 and growable:
                per = extra / len(growable)
                for i in growable:
                    self._hs[i] += per
            total = sum(self._hs) + gap * (len(self._hs) - 1)
            cy = y + (0 if self.align == 'top' else max(0.0, (h or self.h) - total) / 2)
            for i, c in enumerate(self.children):
                c.place(x, cy, w or self.w, self._hs[i])
                cy += self._hs[i] + gap
        else:
            need = sum(self._ws) + gap * (len(self._ws) - 1)
            extra = max(0.0, (w or self.w) - need)
            growable = [i for i, c in enumerate(self.children) if c.children]
            if self.fill and extra > 0 and growable:
                per = extra / len(growable)
                for i in growable:
                    self._ws[i] += per
            total = sum(self._ws) + gap * (len(self._ws) - 1)
            cx = x + max(0.0, (w or self.w) - total) / 2
            for i, c in enumerate(self.children):
                c.place(cx, y, self._ws[i], h or self.h)
                cx += self._ws[i] + gap


    def leaves(self):
        if getattr(self, 'lane', False):
            return
        if not self.children:
            yield self
        else:
            for c in self.children:
                yield from c.leaves()

    def verify(self):
        errs = []
        for lf in self.leaves():
            if lf.x < 0 or lf.y < 0:
                errs.append(f'负坐标 {lf.text[:12]}')
            inner = lf.w - 2 * PAD_X
            for t in lf.lines:
                if tw(t, lf.fs_v) > inner + 0.5:
                    errs.append(f'超宽 {tw(t, lf.fs_v):.0f}>{inner:.0f} 「{t[:22]}」')
                if t and t[0] in NO_START:
                    errs.append(f'行首标点 「{t[:18]}」')
            blk = len(lf.lines) * lf.fs_v * LH + (lf.tfs_v * LH + TAG_GAP if getattr(lf, 'tag', None) else 0)
            if blk > lf.h - 2 * PAD_Y + 0.5:
                errs.append(f'文字块 {blk:.0f} 超框内高 {lf.h - 2 * PAD_Y:.0f} @{lf.text[:12]}')
        return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    spec = importlib.util.spec_from_file_location('spec', a.spec)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    root = m.ROOT
    root.measure(getattr(m, 'FS_DEF', 15))
    canvas_w = getattr(m, 'CANVAS_W', 1600) - 2 * getattr(m, 'PAD', 40)
    root.place(getattr(m, 'PAD', 40), getattr(m, 'PAD', 40), canvas_w, None)

    print('=== 递归盒模型算出的版式 ===')
    print(f'  根节点 需要 {root.w:.0f}×{root.h:.0f}   给宽 {canvas_w}')
    for lf in root.leaves():
        print(f'  叶 x={lf.x:6.1f}..{lf.x + lf.w:6.1f}  y={lf.y:6.1f}..{lf.y + lf.h:6.1f}'
              f'  ({lf.w:5.1f}×{lf.h:5.1f})  {getattr(lf, "tag", None) or lf.text[:20]}')
    errs = root.verify()
    print(f'  校验：{"通过 ✓" if not errs else "失败"}')
    for e in errs:
        print('   ★ ' + e)


if __name__ == '__main__':
    main()
