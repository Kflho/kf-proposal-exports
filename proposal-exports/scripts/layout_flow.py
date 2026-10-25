#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按内容排版"行 × 栏"式流程/路线图 SVG（内容优先：先量文字，再定框大小）。

与其它脚本的分工
  render_svg.py         SVG → PNG（本脚本产出 SVG 后用）
  check_overlap.py      越界/压线检测
  update_pptx_images.py 把 PNG 换进 pptx
  本脚本                由内容生成 SVG，自带两道验收

用法
  python layout_flow.py <cases.py> --out 图.svg [--apply] [--report]

cases.py 需定义：CANVAS_W / STRIP_X / STRIP_W / STRIP_FS / COL_W / GUTTER /
MARGIN_L / PAD_X / PAD_V / FS_LABEL / FS_BODY / FS_TITLE / FS_FULL / LH /
GAP_LABEL / TOP / ROW_GAP / TITLE / ROWS，可选 STRIP_PAD_V / STRIP_PAD_H /
MAIN_TITLE / MAIN_TITLE_X / MAIN_TITLE_W / MAIN_TITLE_FS / PARA_GAP。

版面口径
  内容区左右边界＝三列框的左右边界；**通栏框与三列框共用同一条边界**（并列与否都对齐）
  行高＝max(内容块 + 上下留白, 竖排标签所需高)
  竖排标签字号：四向留白都不小于 STRIP_PAD_H / STRIP_PAD_V
"""
import argparse
import importlib.util
import math
import re
import sys
from pathlib import Path

try:  # Windows 控制台默认 GBK，打印 ✓ 会崩
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _wrap_dp import wrap_dp, char_w          # noqa: E402

FACE = 'Microsoft YaHei, PingFang SC, Source Han Sans SC, SimHei, sans-serif'
NO_START = set('，。；、：！？）》」』%')
COLOR_BLUE, COLOR_RED, COLOR_INK = '#2F6FB0', '#E8A33D', '#1F2937'

# 竖排汉字：每字占的水平宽度（相对字号）。实测 13px 时 4 字标签墨长约 39.5px
INK_H_FACTOR = 1.02
# 实测（13px 与 20px 两档同规律）：偏移 0.0/0.25/0.375/0.5em 时，
# 墨迹中心距条中心 -5.5/-2.5/≈0/+1.5 px（13px 档）→ 居中偏移 = 0.375em
ROT_OFFSET = 0.375           # rotate(-90) 后基线的水平偏移（相对字号）——实测反解值，见下


def fit_strip_fs(text, strip_h, strip_w, fs_max, pad_v=12, pad_h=14):
    """竖排标签字号：使四向留白都不小于 pad。

    竖排后  长度方向 = 字数 × 字号 × INK_H_FACTOR
            水平方向 = 字号 × INK_H_FACTOR
    """
    by_len = (strip_h - 2 * pad_v) / max(1, len(text)) / INK_H_FACTOR
    by_wid = (strip_w - 2 * pad_h) / INK_H_FACTOR
    return max(5.0, min(fs_max, by_len, by_wid))


def tw(s, fs):
    return sum(char_w(c, fs) for c in s)


def build(cfg):
    rows = cfg['ROWS']
    col_w, gutter = cfg['COL_W'], cfg['GUTTER']
    col_x = [cfg['STRIP_X'] + cfg['STRIP_W'] + cfg['MARGIN_L']]
    col_x += [col_x[0] + col_w + gutter, col_x[0] + 2 * (col_w + gutter)]
    col_cx = [x + col_w / 2 for x in col_x]
    band_l, band_r = col_x[0], col_x[2] + col_w
    pad_x, pad_v = cfg['PAD_X'], cfg['PAD_V']
    avail = col_w - 2 * pad_x
    spv, sph = cfg.get('STRIP_PAD_V', 12), cfg.get('STRIP_PAD_H', 14)

    for r in rows:
        if r['kind'] == 'full':
            r['avail'] = band_r - band_l - 2 * pad_x
            r['wrapped'] = [wrap_dp(t, r['fs'], r['avail']) for t in r['text']]
            n = sum(len(w) for w in r['wrapped'])
            need = n * r['fs'] * cfg['LH'] + 2 * pad_v
        elif r['kind'] == 'seg':
            r['avail'] = avail
            r['wrapped'] = [wrap_dp(t, r['fs'], avail) for t in r['segs']]
            n = max(len(w) for w in r['wrapped'])
            need = n * cfg['FS_BODY'] * cfg['LH'] + 2 * pad_v
        else:
            r['avail'] = avail
            r['wrapped'] = [wrap_dp(t, cfg['FS_BODY'], avail) for t in r['text']]
            n = max(len(w) for w in r['wrapped'])
            need = (cfg['FS_LABEL'] * cfg['LH'] + cfg['GAP_LABEL']
                    + n * cfg['FS_BODY'] * cfg['LH'] + 2 * pad_v)
        sfs = fit_strip_fs(r['name'], 10 ** 6, cfg['STRIP_W'], cfg['STRIP_FS'], spv, sph)
        r['strip_fs'] = sfs
        strip_need = len(r['name']) * sfs * INK_H_FACTOR + 2 * spv
        r['h'] = math.ceil(max(need, strip_need))
    y = cfg['TOP']
    for r in rows:
        r['y'] = y
        y += r['h'] + cfg['ROW_GAP']
    canvas_h = y - cfg['ROW_GAP'] + cfg['TOP']

    links = []
    for i in range(len(rows) - 1):
        r0, r1 = rows[i], rows[i + 1]
        for cx in col_cx:
            links.append(dict(x=cx, y1=r0['y'] + r0['h'], y2=r1['y']))
    return dict(rows=rows, links=links, canvas_h=canvas_h, band_l=band_l, band_r=band_r,
                col_x=col_x, col_cx=col_cx, avail=avail)


def verify(cfg, L):
    errs = []
    rows, canvas_h = L['rows'], L['canvas_h']
    spv, sph = cfg.get('STRIP_PAD_V', 12), cfg.get('STRIP_PAD_H', 14)
    for r in rows:
        for lines in r['wrapped']:
            fs = r['fs'] if r['kind'] in ('full', 'seg') else cfg['FS_BODY']
            for t in lines:
                if tw(t, fs) > r['avail'] + 0.5:
                    errs.append(f"D 超宽 {tw(t,fs):.0f}>{r['avail']} 「{t}」")
                if t and t[0] in NO_START:
                    errs.append(f'D 行首标点 「{t}」')
        if r['kind'] == 'cols':
            for lab in r['labels']:
                if tw(lab, r['label_fs']) > r['avail']:
                    errs.append(f'D 标签超宽 「{lab}」')
        if r['y'] + r['h'] > canvas_h - 20:
            errs.append(f'C 框底越界 @{r["name"]}')
        sfs = fit_strip_fs(r['name'], r['h'], cfg['STRIP_W'], cfg['STRIP_FS'], spv, sph)
        if len(r['name']) * sfs * INK_H_FACTOR > r['h'] - 2 * spv + 0.5:
            errs.append(f'E 竖排标签上下留白不足 @{r["name"]}')
        if sfs * INK_H_FACTOR > cfg['STRIP_W'] - 2 * sph + 0.5:
            errs.append(f'H 竖排标签左右留白不足 @{r["name"]}')
    mt = cfg.get('MAIN_TITLE')
    if mt:
        mfs = fit_strip_fs(mt, canvas_h, cfg.get('MAIN_TITLE_W', 68),
                           cfg.get('MAIN_TITLE_FS', 20),
                           cfg.get('MAIN_TITLE_PAD_V', 24), cfg.get('MAIN_TITLE_PAD_H', 18))
        if len(mt) * mfs * INK_H_FACTOR > canvas_h - 2 * cfg.get('MAIN_TITLE_PAD_V', 24) + 0.5:
            errs.append('F 大标题竖排长度超画布高')
        if mfs * INK_H_FACTOR > cfg.get('MAIN_TITLE_W', 68) - 2 * cfg.get('MAIN_TITLE_PAD_H', 18) + 0.5:
            errs.append('F 大标题左右留白不足')
    if L['band_l'] != L['col_x'][0] or L['band_r'] != L['col_x'][2] + cfg['COL_W']:
        errs.append('G 通栏框与三列框左右边界不一致')
    if L['col_x'][0] - (cfg['STRIP_X'] + cfg['STRIP_W']) < cfg['GUTTER'] * 0.8:
        errs.append('G 竖条与内容区外边距过窄')
    return errs


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def generate(cfg, L):
    rows, canvas_w, canvas_h = L['rows'], cfg['CANVAS_W'], L['canvas_h']
    band_l, band_r, col_w = L['band_l'], L['band_r'], cfg['COL_W']
    pad_x, pad_v, lh = cfg['PAD_X'], cfg['PAD_V'], cfg['LH']
    spv, sph = cfg.get('STRIP_PAD_V', 12), cfg.get('STRIP_PAD_H', 14)

    def txt(x, y, s, fs, anchor='middle', color=COLOR_INK, bold=False):
        bw = ' font-weight="bold"' if bold else ''
        return (f'  <text x="{x:.0f}" y="{y:.0f}" font-family="{FACE}" font-size="{fs:.1f}"{bw} '
                f'fill="{color}" text-anchor="{anchor}">{esc(s)}</text>')

    o = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
         f'viewBox="0 0 {canvas_w} {canvas_h}">',
         f'  <title>{esc(cfg["TITLE"])}</title>', '  <defs>',
         '    <marker id="fl-arrow" viewBox="0 0 10 8" refX="10" refY="4" markerWidth="9" '
         'markerHeight="7" markerUnits="userSpaceOnUse" orient="auto">',
         f'      <path d="M0,0 L10,4 L0,8 Z" fill="{COLOR_BLUE}"/>', '    </marker>', '  </defs>',
         f'  <rect x="0" y="0" width="{canvas_w}" height="{canvas_h}" fill="#FFFFFF"/>']

    mt = cfg.get('MAIN_TITLE')
    if mt:
        tx = cfg.get('MAIN_TITLE_X', 24)
        mw, mfs_max = cfg.get('MAIN_TITLE_W', 68), cfg.get('MAIN_TITLE_FS', 20)
        mfs = fit_strip_fs(mt, canvas_h, mw, mfs_max,
                           cfg.get('MAIN_TITLE_PAD_V', 24), cfg.get('MAIN_TITLE_PAD_H', 18))
        o.append(f'  <rect x="{tx}" y="0" width="{mw}" height="{canvas_h}" fill="{COLOR_BLUE}"/>')
        mcx, mcy = tx + mw / 2 + mfs * ROT_OFFSET, canvas_h / 2
        o.append(f'  <text transform="rotate(-90 {mcx:.1f} {mcy:.1f})" x="{mcx:.1f}" y="{mcy:.1f}" '
                 f'font-family="{FACE}" font-size="{mfs:.1f}" font-weight="bold" fill="#FFFFFF" '
                 f'text-anchor="middle">{esc(mt)}</text>')

    for lk in L['links']:
        o.append(f'  <line x1="{lk["x"]:.0f}" y1="{lk["y1"]}" x2="{lk["x"]:.0f}" y2="{lk["y2"]}" '
                 f'stroke="{COLOR_BLUE}" stroke-width="1.5" marker-end="url(#fl-arrow)"/>')

    for r in rows:
        y0, h = r['y'], r['h']
        if r['kind'] == 'full':
            fill, stroke = r.get('fill', '#E8F1FA'), r.get('stroke', COLOR_BLUE)
            o.append(f'  <rect x="{band_l}" y="{y0}" width="{band_r-band_l}" height="{h}" rx="10" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
            cy = y0 + pad_v + r['fs']
            for lines in r['wrapped']:
                for t in lines:
                    o.append(txt(band_l + pad_x, cy, t, r['fs'], anchor='start'))
                    cy += r['fs'] * lh
                cy += cfg.get('PARA_GAP', 4)
        elif r['kind'] == 'seg':
            fill, stroke = r.get('fill', '#FDF3E3'), r.get('stroke', COLOR_RED)
            o.append(f'  <rect x="{band_l}" y="{y0}" width="{band_r-band_l}" height="{h}" rx="10" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
            for i, cx in enumerate(L['col_cx']):
                lines = r['wrapped'][i]
                cy = y0 + (h - len(lines) * r['fs'] * lh) / 2 + r['fs']
                for t in lines:
                    o.append(txt(cx, cy, t, r['fs']))
                    cy += r['fs'] * lh
        else:
            fill, stroke = r.get('fill', '#E8F1FA'), r.get('stroke', COLOR_BLUE)
            for i, (bx, cx) in enumerate(zip(L['col_x'], L['col_cx'])):
                o.append(f'  <rect x="{bx}" y="{y0}" width="{col_w}" height="{h}" rx="10" '
                         f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
                cy = y0 + pad_v + r['label_fs']
                o.append(txt(cx, cy, r['labels'][i], r['label_fs'], color=COLOR_BLUE, bold=True))
                cy += cfg['GAP_LABEL'] + cfg['FS_BODY'] * lh * 0.6
                for t in r['wrapped'][i]:
                    o.append(txt(cx, cy, t, cfg['FS_BODY']))
                    cy += cfg['FS_BODY'] * lh
        sfs = fit_strip_fs(r['name'], h, cfg['STRIP_W'], cfg['STRIP_FS'], spv, sph)
        cyc = y0 + h / 2
        sx = cfg['STRIP_X'] + cfg['STRIP_W'] / 2 + sfs * ROT_OFFSET
        o.append(f'  <rect x="{cfg["STRIP_X"]}" y="{y0}" width="{cfg["STRIP_W"]}" height="{h}" '
                 f'rx="8" fill="#4A7EBB" stroke="none"/>')
        o.append(f'  <text transform="rotate(-90 {sx:.1f} {cyc:.1f})" x="{sx:.1f}" y="{cyc:.1f}" '
                 f'font-family="{FACE}" font-size="{sfs:.1f}" font-weight="bold" fill="#FFFFFF" '
                 f'text-anchor="middle">{esc(r["name"])}</text>')
    o.append('</svg>')
    return '\n'.join(o) + '\n'


def post_check(svg, canvas_w, canvas_h, col_cx, col_w, band_w):
    rects = [tuple(map(int, m.groups())) for m in
             re.finditer(r'<rect x="(\d+)" y="(\d+)" width="(\d+)" height="(\d+)"', svg)]
    lines = [tuple(map(int, m.groups())) for m in
             re.finditer(r'<line x1="(\d+)" y1="(\d+)" x2="(\d+)" y2="(\d+)"', svg)]
    fail = []
    for x1, y1, x2, y2 in lines:
        if x1 != x2:
            fail.append(f'连线不竖直 x {x1}..{x2}')
        if x1 not in [int(c) for c in col_cx]:
            fail.append(f'连线 x={x1} 不是列心')
        if not any(abs(y1 - (ry + rh)) <= 1 for _, ry, rw, rh in rects if rw in (col_w, band_w)):
            fail.append(f'连线 y1={y1} 未贴上一行框底')
        if not any(abs(y2 - ry) <= 1 for _, ry, rw, rh in rects if rw in (col_w, band_w)):
            fail.append(f'连线 y2={y2} 未贴下一行框顶')
    if not any(x == 0 and y == 0 and w == canvas_w and h == canvas_h for x, y, w, h in rects):
        fail.append('缺白底矩形')
    if 'foreignObject' in svg:
        fail.append('出现 foreignObject（多数 SVG 查看器不渲染）')
    return fail, len(rects), len(lines)


def load_cfg(path):
    spec = importlib.util.spec_from_file_location('layout_case', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {k: getattr(mod, k) for k in dir(mod) if k.isupper()}


def row_lines(L):
    for r in L['rows']:
        yield (f"  {r['name']:<12} 框 y={r['y']:3d}..{r['y']+r['h']:3d} (h={r['h']:3d})  "
               f"行数 {[len(w) for w in r['wrapped']]}  竖排字号 {r['strip_fs']:.1f}")


def main():
    ap = argparse.ArgumentParser(description='按内容排版行×栏式流程/路线图 SVG')
    ap.add_argument('case')
    ap.add_argument('--out', required=True)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()

    cfg = load_cfg(a.case)
    L = build(cfg)

    print('=== 版面核算 ===')
    for line in row_lines(L):
        print(line)
    print(f"  画布 {cfg['CANVAS_W']}×{L['canvas_h']}")
    print(f"  三列 x {L['col_x']}  列心 {L['col_cx']}  宽 {cfg['COL_W']}  栏距 {cfg['GUTTER']}")
    print(f"  通栏框 x {L['band_l']}..{L['band_r']}（与三列框同左右边界）")
    print(f"  竖条 x {cfg['STRIP_X']}..{cfg['STRIP_X']+cfg['STRIP_W']}  外距 {cfg['MARGIN_L']}"
          f"  留白 左右≥{cfg.get('STRIP_PAD_H',14)} 上下≥{cfg.get('STRIP_PAD_V',12)}")
    print(f"  连线 {len(L['links'])} 条：x=列心，y 贯通行间空隙")

    if a.report:
        print('\n=== 断行结果 ===')
        for r in L['rows']:
            for i, lines in enumerate(r['wrapped']):
                tag = r['labels'][i] if r['kind'] == 'cols' else r['name']
                print(f'  [{tag}]')
                for t in lines:
                    fs = r['fs'] if r['kind'] in ('full', 'seg') else cfg['FS_BODY']
                    print(f'      {tw(t, fs):>5.0f}px  {t}')

    errs = verify(cfg, L)
    if errs:
        print('\n★ 生成前验收失败：')
        for e in errs:
            print('   ' + e)
        return 1
    print('  生成前验收通过 ✓')
    if not a.apply:
        print('\nDRY RUN（加 --apply 写入）')
        return 0

    svg = generate(cfg, L)
    Path(a.out).write_text(svg, encoding='utf-8', newline='\n')
    print(f'\nAPPLIED → {a.out}')

    fail, nr, nl = post_check(svg, cfg['CANVAS_W'], L['canvas_h'], L['col_cx'],
                              cfg['COL_W'], L['band_r'] - L['band_l'])
    print('=== 回读校验 ===')
    print(f'  rect {nr}  line {nl}')
    if fail:
        for f in fail:
            print('   ★ ' + f)
        return 1
    print('  连线竖直、x=列心、y 贴合上下框；白底覆盖整幅 ✓')
    return 0


if __name__ == '__main__':
    sys.exit(main())
