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


def _tokens(text):
    """把文本切成**不可拆分的最小单元**，返回 [(起始下标, 结束下标, 宽度权重字符数)]。

    为什么需要：逐字断行会把拉丁词/数字串拆开（`5G-A` 被断成 `5` 与 `G-A`，
    `4.9 GHz` 被断成 `4.` 与 `9`），出现行首拉丁残片。
    规则：连续的「拉丁字母 / 数字 / 半角点 / 连字符 / 加号 / 斜杠」视为一个原子 token，
    整体不许拆；CJK 与全角标点各自成 token。
    """
    import re
    pat = re.compile(r'[0-9A-Za-z][0-9A-Za-z.\-+/]*')
    toks, i, n = [], 0, len(text)
    while i < n:
        m = pat.match(text, i)
        if m:
            toks.append((i, m.end()))
            i = m.end()
        else:
            toks.append((i, i + 1))
            i += 1
    return toks


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
    toks = _tokens(text)
    tn = len(toks)
    # 前缀宽度（按字符），以及"第 k 个 token 起点/终点"的字符下标
    pre = [0.0] * (n + 1)
    for i, ch in enumerate(text):
        pre[i + 1] = pre[i] + char_w(ch, fs)
    starts = [t[0] for t in toks] + [n]
    ends = [t[1] for t in toks]

    INF = float('inf')
    # 状态按 token 边界推进：第 k 个 token 之前已排好
    best = [INF] * (tn + 1)
    best[0] = 0.0
    prev = [-1] * (tn + 1)
    lines_at = [0] * (tn + 1)

    for j in range(1, tn + 1):
        for i in range(j):
            a, b = starts[i], ends[j - 1]          # 候选行的字符区间 [a, b)
            w = pre[b] - pre[a]
            if w > avail + 0.5:
                continue
            if best[i] == INF:
                continue
            if max_lines and lines_at[i] >= max_lines:
                continue
            cost = best[i]
            frag = text[a:b]
            # 标点不得入行首
            if frag[0] in NO_START:
                cost += 1000
            # 开括号不得留行尾
            if frag[-1] in NO_END:
                cost += 1000
            # 行满度：越不满越贵（鼓励排满，宽度均衡）
            cost += (avail - w) ** 2 * 0.002
            # 末行（排到文末）过短惩罚
            if j == tn and w < avail * 0.55:
                cost += 400
            if cost < best[j]:
                best[j] = cost
                prev[j] = i
                lines_at[j] = lines_at[i] + 1

    if best[tn] == INF:
        return None
    out, j = [], tn
    while j > 0:
        i = prev[j]
        out.append(text[starts[i]:ends[j - 1]].strip())
        j = i
    return out[::-1]


if __name__ == '__main__':
    FACE_FS = float(sys.argv[2]) if len(sys.argv) > 2 else 13.5
    AV = float(sys.argv[3]) if len(sys.argv) > 3 else 268.0
    for t in [sys.argv[1]]:
        for ln in wrap_dp(t, FACE_FS, AV) or ['★放不下']:
            print(f'  {sum(char_w(c, FACE_FS) for c in ln):>5.0f}px  {ln}')
