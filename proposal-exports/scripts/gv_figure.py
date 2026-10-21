#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Graphviz 出图（**本 skill 的首选出图方式**），并按成品尺寸 1:1 交付。

为什么用 Graphviz 而不是自己写布局
  · 布局（分层、正交路由、cluster 嵌套、边上标注避让）是 Graphviz 的强项
  · 输出 SVG 干净：无 <style>、无内嵌字体、无 base64，文字可编辑
  · 装一次：`winget install Graphviz.Graphviz`（macOS `brew install graphviz`）

按成品尺寸设计（关键）
  用 `--fit "11.2x6.3"` 把 dot 的输出缩放到交付尺寸并重写 width/height/viewBox，
  于是 SVG 坐标 = 最终 pt，`tokens.py` 里的字号就是最终字号（不再被动缩放）。

用法
  python gv_figure.py <spec.py> --out 图.svg [--fit 11.2x6.3] [--png 图.png] [--dpi 300] [--report]
"""
import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wrap_dp import wrap_dp                    # noqa: E402


def find_dot():
    p = shutil.which('dot')
    if p:
        return p
    for c in (r'C:\Program Files\Graphviz\bin\dot.exe',
              r'C:\Program Files (x86)\Graphviz\bin\dot.exe',
              '/usr/bin/dot', '/usr/local/bin/dot'):
        if Path(c).exists():
            return c
    return None


def cjk_wrap(text, fs, avail, br='<BR/>'):
    out = []
    for part in str(text).split('\n'):
        out += (wrap_dp(part, fs, avail) or [part])
    return br.join(out)


def fit_svg(svg_text, w_in, h_in, px=None):
    """把 dot 的 SVG 缩放到成品尺寸（单位 = pt）。

    只**替换开标签里的 width/height/viewBox 三个属性**（不截断标签，保留 xmlns 等其余属性），
    再在内容外裹一层 <g transform> 做等比缩放 + 居中。
    """
    m = re.search(r'width="([\d.]+)pt"\s+height="([\d.]+)pt"', svg_text)
    if not m:
        return svg_text, None
    w0, h0 = float(m.group(1)), float(m.group(2))
    W, H = w_in * 72.0, h_in * 72.0
    k = min(W / w0, H / h0)
    dx, dy = (W - w0 * k) / 2, (H - h0 * k) / 2

    head_end = svg_text.index('>', svg_text.index('<svg'))
    head = svg_text[:head_end + 1]
    rest = svg_text[head_end + 1:]

    # 宽高写成「无单位像素」（96dpi 下的显示尺寸），viewBox 保持 pt：
    # 这样 render_svg.py 能正确解析窗口尺寸，内部坐标仍是 pt（tokens 字号即最终字号）
    disp_w = px[0] if px else W * 96 / 72
    disp_h = px[1] if px else H * 96 / 72
    head = re.sub(r'width="[\d.]+(pt|px)?"', f'width="{disp_w:.0f}"', head, count=1)
    head = re.sub(r'height="[\d.]+(pt|px)?"', f'height="{disp_h:.0f}"', head, count=1)
    if 'viewBox=' in head:
        head = re.sub(r'viewBox="[^"]*"', f'viewBox="0 0 {W:.0f} {H:.0f}"', head, count=1)
    else:
        head = head[:-1] + f' viewBox="0 0 {W:.0f} {H:.0f}">'

    body = f'<g transform="translate({dx:.2f},{dy:.2f}) scale({k:.5f})">' + rest
    body = body.replace('</svg>', '</g></svg>')
    return head + body, k


def rescale_gv(gv_text, k):
    """把 .gv 里的字号/线宽/边距整体乘以 k —— 这样成品尺寸下 1 单位 ≈ 1pt，
    tokens.py 里的"成品 pt"就能直接写进 gv。"""
    def mul(m):
        key, val = m.group(1), float(m.group(2))
        return f'{key}={val * k:g}'
    # width/height 在 Graphviz 里是**英寸**，是节点的硬下限；必须一并缩放，
    # 否则缩尺时字号一路被压小、而节点不肯变小，迭代不收敛
    out = re.sub(r'\b(fontsize|penwidth|width|height)=([\d.]+)', mul, gv_text)
    out = re.sub(r'\bmargin="([\d.]+),([\d.]+)"',
                 lambda m: 'margin="%g,%g"' % (float(m.group(1)) * k, float(m.group(2)) * k), out)
    # HTML-like label 里的字号是 POINT-SIZE，必须一起缩放，否则节点字与边标注失衡
    out = re.sub(r'POINT-SIZE="([\d.]+)"',
                 lambda m: 'POINT-SIZE="%g"' % (float(m.group(1)) * k), out)
    out = re.sub(r'\b(nodesep|ranksep)=([\d.]+)',
                 lambda m: '%s=%g' % (m.group(1), float(m.group(2)) * k), out)
    out = re.sub(r'\barrowsize=([\d.]+)', lambda m: 'arrowsize=%g' % (float(m.group(1)) * k), out)
    return out


def natural_pt(dot, gv_path):
    """跑一遍 dot，返回自然尺寸（pt）。"""
    r = subprocess.run([dot, '-Tsvg', str(gv_path)], capture_output=True, timeout=180)
    if r.returncode != 0:
        return None
    m = re.search(rb'width="([\d.]+)pt"\s+height="([\d.]+)pt"', r.stdout)
    return (float(m.group(1)), float(m.group(2))) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('--out', required=True)
    ap.add_argument('--fit', default=None, help='成品尺寸 WxH（英寸），如 11.2x6.3')
    ap.add_argument('--png', default=None)
    ap.add_argument('--dpi', type=int, default=300)
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()

    dot = find_dot()
    if not dot:
        print('  ★ 找不到 dot：请先装 Graphviz（winget install Graphviz.Graphviz）')
        return 1
    ver = subprocess.run([dot, '-V'], capture_output=True).stderr.decode('utf-8', 'replace').strip()
    print(f'  dot: {dot}\n  {ver}')

    spec = importlib.util.spec_from_file_location('gv_spec', a.spec)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    gv = Path(m.GV_FILE).read_text(encoding='utf-8') if getattr(m, 'GV_FILE', None) else m.GV

    for key, sp in (getattr(m, 'WRAP', {}) or {}).items():
        text, fs, avail = sp[0], sp[1], sp[2]
        br = sp[3] if len(sp) > 3 else '<BR/>'
        wrapped = cjk_wrap(text, fs, avail, br=br)
        gv = gv.replace('@@%s@@' % key, wrapped)
        if a.report:
            print(f'  折行 {key}（{fs}pt/{avail}pt）: ' + ' | '.join(wrapped.split(br)))

    tmp = Path(a.out).with_suffix('.gv')
    tmp.write_text(gv, encoding='utf-8', newline='\n')

    # ---- 迭代缩尺：量自然尺寸 → 求 k → 把字号/线宽/间距乘累积 k，直到收敛 ----
    # 单次缩放会改变自然尺寸，必须迭代；收敛后 1 单位 ≈ 1pt，tokens 里的字号即最终字号
    if a.fit:
        w_in, h_in = (float(v) for v in a.fit.lower().split('x'))
        W, H = w_in * 72.0, h_in * 72.0
        k_cum, nat, it = 1.0, None, 0
        for it in range(6):
            nat = natural_pt(dot, tmp)
            if not nat:
                break
            k = min(W / nat[0], H / nat[1])
            if abs(k - 1.0) < 0.008:
                break
            k_cum *= k
            tmp.write_text(rescale_gv(gv, k_cum), encoding='utf-8', newline='\n')
        nat = natural_pt(dot, tmp) or nat
        if nat:
            print(f'  缩尺 {it} 轮收敛：累积 k={k_cum:.3f} → 自然 {nat[0]:.0f}×{nat[1]:.0f}pt '
                  f'（成品框 {W:.0f}×{H:.0f}pt）')

    r = subprocess.run([dot, '-Tsvg', str(tmp), '-o', str(a.out)], capture_output=True, timeout=180)
    err = (r.stderr or b'').decode('utf-8', 'replace').strip()
    if r.returncode != 0 or not Path(a.out).exists():
        print('  ★ dot 失败：', err[:300])
        return 1
    svg = Path(a.out).read_text(encoding='utf-8')
    print(f'  SVG → {a.out}（{len(svg)} bytes）')

    if a.png:
        if a.fit:
            # 用成品 SVG（宽高=目标像素、viewBox=pt）经浏览器渲染：尺寸与比例都精确
            w_in2, h_in2 = (float(v) for v in a.fit.lower().split('x'))
            raw = Path(a.out).with_suffix('.raw.svg')
            subprocess.run([dot, '-Tsvg', str(tmp), '-o', str(raw)], capture_output=True, timeout=180)
            pxw, pxh = int(round(w_in2 * a.dpi)), int(round(h_in2 * a.dpi))
            fitted, _ = fit_svg(raw.read_text(encoding='utf-8'), w_in2, h_in2, px=(pxw, pxh))
            fp = Path(a.out).with_suffix('.fit.svg')
            fp.write_text(fitted, encoding='utf-8', newline='\n')
            r2 = subprocess.run([sys.executable, str(Path(__file__).with_name('render_svg.py')),
                                 str(fp), '--png', str(a.png), '--scale', '1'],
                                capture_output=True, timeout=180)
            if r2.returncode == 0 and Path(a.png).exists():
                print(f'  PNG → {a.png}（{Path(a.png).stat().st_size} bytes, {pxw}×{pxh} = {a.dpi}dpi）')
            else:
                print('  ★ PNG 失败：', (r2.stderr or b'').decode('utf-8','replace')[:200])
        else:
            subprocess.run([dot, '-Tpng', f'-Gdpi={a.dpi}', str(tmp), '-o', str(a.png)],
                           capture_output=True, timeout=180)
            print(f'  PNG → {a.png}（{Path(a.png).stat().st_size} bytes, {a.dpi}dpi）')
    if err:
        print('  dot 警告：', err.replace('\n', ' ')[:200])
    return 0


if __name__ == '__main__':
    sys.exit(main())
