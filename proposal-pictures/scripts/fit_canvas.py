#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 SVG 归一化到目标画布：**自动**缩放居中 + 自动校验迭代，不需要手调系数。

做法（全自动，无人工试数）
  1. 读入 SVG，取当前内容所在的 <g transform="translate(dx,dy) scale(k)">（没有就补一层）；
  2. 从 k=1 起，按步长逐步缩小内容并重新居中，**每次跑 check_overlap.py 当判据**；
  3. 命中为 0 即停（并再留一档余量），写回 1600×900 的画布；
  4. 打印每一轮的命中数，留下可复核的记录。

用法
  python fit_canvas.py 图.svg [图2.svg ...] [--w 1600] [--h 900] [--step 0.995] [--apply]
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def overlap_hits(path):
    r = subprocess.run([sys.executable, str(HERE / 'check_overlap.py'), str(path)],
                       capture_output=True)
    out = (r.stdout or b'').decode('utf-8', 'replace')
    return out.count('⚠')


def parse(svg):
    m = re.search(r'<svg[^>]*?width="([\d.]+)(?:pt|px)?"[^>]*?height="([\d.]+)(?:pt|px)?"', svg)
    if not m:
        m2 = re.search(r'<svg[^>]*>', svg).group(0)
        raise SystemExit('  ★ 解析不到 width/height：' + m2[:120])
    W, H = float(m.group(1)), float(m.group(2))
    he = svg.index('>', svg.index('<svg'))
    return W, H, svg[:he + 1], svg[he + 1:]


def rebuild(head, body, W, H, k, dx, dy):
    head = re.sub(r'width="[\d.]+(pt|px)?"', f'width="{W:.0f}"', head, count=1)
    head = re.sub(r'height="[\d.]+(pt|px)?"', f'height="{H:.0f}"', head, count=1)
    head = re.sub(r'viewBox="[^"]*"', f'viewBox="0 0 {W:.0f} {H:.0f}"', head, count=1) \
        if 'viewBox=' in head else head[:-1] + f' viewBox="0 0 {W:.0f} {H:.0f}">'
    # 去掉旧的包装层（若有），只保留内容
    inner = re.search(r'<g transform="translate\([-\d.]+,([-\d.]+)\) scale\([\d.]+\)">(.*)</g>\s*$',
                      body, re.S)
    content = inner.group(2) if inner else body.replace('</svg>', '')
    out = (head + f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="#FFFFFF"/>'
           + f'<g transform="translate({dx:.2f},{dy:.2f}) scale({k:.5f})">'
           + content + '</g></svg>')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('svgs', nargs='+')
    ap.add_argument('--w', type=float, default=1600)
    ap.add_argument('--h', type=float, default=900)
    ap.add_argument('--step', type=float, default=0.995)
    ap.add_argument('--min', type=float, default=0.80)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    for f in a.svgs:
        p = Path(f)
        svg = p.read_text(encoding='utf-8')
        W0, H0, head, body = parse(svg)
        # 内容原始尺寸 = 画布 / 已有包装比例
        m = re.search(r'<g transform="translate\(([-\d.]+),([-\d.]+)\) scale\(([\d.]+)\)">',
                      body)
        if m:
            dx0, dy0, k0 = float(m.group(1)), float(m.group(2)), float(m.group(3))
            cw, ch = (W0 - 2 * dx0) / k0, (H0 - 2 * dy0) / k0
        else:
            dx0 = dy0 = 0.0
            k0 = 1.0
            cw, ch = W0, H0
        base_fit = min(a.w / cw, a.h / ch)

        print(f'\n  == {p.name} ==  内容 {cw:.0f}×{ch:.0f} → 画布 {a.w:.0f}×{a.h:.0f}')
        best = None
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / p.name
            k = base_fit
            rounds = 0
            while k >= a.min:
                dx, dy = (a.w - cw * k) / 2, (a.h - ch * k) / 2
                tmp.write_text(rebuild(head, body, a.w, a.h, k, dx, dy),
                               encoding='utf-8', newline='\n')
                hits = overlap_hits(tmp)
                print(f'     k={k:.4f}  留白({dx:.1f},{dy:.1f})  压线命中 {hits}')
                rounds += 1
                if hits == 0:
                    best = (k, dx, dy)
                    # 再留一档余量，避免刚好贴边
                    k2 = k * a.step
                    dx2, dy2 = (a.w - cw * k2) / 2, (a.h - ch * k2) / 2
                    tmp.write_text(rebuild(head, body, a.w, a.h, k2, dx2, dy2),
                                   encoding='utf-8', newline='\n')
                    if overlap_hits(tmp) == 0:
                        best = (k2, dx2, dy2)
                    break
                k *= a.step
        if not best:
            print('     ★ 到下限仍压线，未写回')
            continue
        k, dx, dy = best
        out = rebuild(head, body, a.w, a.h, k, dx, dy)
        print(f'     ✅ 采用 k={k:.4f}（{rounds} 轮自动收敛）')
        if a.apply:
            p.write_text(out, encoding='utf-8', newline='\n')
    if not a.apply:
        print('\n  （未加 --apply，不写文件）')


if __name__ == '__main__':
    main()
