#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""断行器：动态规划，最小化「标点孤行 + 行宽不均 + 末行过短」的代价。

用于图3 的段落折行。输出行数最少、每行宽度尽量接近，且不把标点甩到行首。
"""
import sys

NO_START = set('，。；、：！？）》」』%')
NO_END = set('（《「『')


def char_w(ch, fs):
    return fs * (0.55 if ord(ch) < 0x2E80 else 1.0)


def wrap_dp(text, fs, avail, max_lines=None):
    # 硬换行优先：文本含换行符时按段分别断行（供「一条方法一行」场景）
    if chr(10) in text:
        out = []
        for seg in text.split(chr(10)):
            if seg.strip():
                out += wrap_dp(seg, fs, avail, max_lines)
        return out
    n = len(text)
    if n == 0:
        return []
    # 前缀宽度
    pre = [0.0] * (n + 1)
    for i, ch in enumerate(text):
        pre[i + 1] = pre[i] + char_w(ch, fs)

    INF = float('inf')
    best = [INF] * (n + 1)
    best[0] = 0.0
    prev = [-1] * (n + 1)
    lines_at = [0] * (n + 1)

    for j in range(1, n + 1):
        for i in range(j):
            w = pre[j] - pre[i]
            if w > avail + 0.5:
                continue
            if best[i] == INF:
                continue
            if max_lines and lines_at[i] >= max_lines:
                continue
            cost = best[i]
            frag = text[i:j]
            # 标点不得入行首
            if frag[0] in NO_START:
                cost += 1000
            # 开括号不得留行尾
            if frag[-1] in NO_END:
                cost += 1000
            # 行满度：越不满越贵（鼓励排满，宽度均衡）
            cost += (avail - w) ** 2 * 0.002
            # 末行（j == n）过短惩罚
            if j == n and w < avail * 0.55:
                cost += 400
            if cost < best[j]:
                best[j] = cost
                prev[j] = i
                lines_at[j] = lines_at[i] + 1

    if best[n] == INF:
        return None
    out, j = [], n
    while j > 0:
        i = prev[j]
        out.append(text[i:j].strip())
        j = i
    return out[::-1]


if __name__ == '__main__':
    FACE_FS = float(sys.argv[2]) if len(sys.argv) > 2 else 13.5
    AV = float(sys.argv[3]) if len(sys.argv) > 3 else 268.0
    for t in [sys.argv[1]]:
        for ln in wrap_dp(t, FACE_FS, AV) or ['★放不下']:
            print(f'  {sum(char_w(c, FACE_FS) for c in ln):>5.0f}px  {ln}')
