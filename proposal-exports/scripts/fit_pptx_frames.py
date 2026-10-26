#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按图片自身比例重排 pptx 里的图片框（消除拉伸）。

原理：读每张图片的实际像素尺寸得到真实比例，再在"安全区"（页面去掉边距）内取
**最大内接矩形**，居中放置；只改 `<a:off>/<a:ext>`，媒体与其余条目逐字节保留。

用法
  python fit_pptx_frames.py 三图.pptx --list                 # 只看现状
  python fit_pptx_frames.py 三图.pptx --apply [--margin 0.4]  # 按图片比例重排
  python fit_pptx_frames.py 三图.pptx --apply --slot 1:11.2x6.3  # 指定某页目标比例(可选)
"""
import argparse
import re
import shutil
import struct
import zipfile
from pathlib import Path

EMU = 914400.0


def png_size(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    return struct.unpack('>II', data[16:24])


def collect(z):
    """返回 [(slide_name, rel_id, media_name, 宽px, 高px, off, ext)]"""
    rels = {}
    for n in z.namelist():
        m = re.match(r'ppt/slides/_rels/(slide\d+)\.xml\.rels$', n)
        if m:
            s = z.read(n).decode('utf-8')
            for r in re.finditer(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', s):
                rels[(m.group(1), r.group(1))] = r.group(2)
    out = []
    for n in sorted(x for x in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', x)):
        slide = Path(n).stem
        s = z.read(n).decode('utf-8')
        for pic in re.finditer(r'<p:pic>.*?</p:pic>', s, re.S):
            blk = pic.group(0)
            off = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/><a:ext cx="(\d+)" cy="(\d+)"', blk)
            rid = re.search(r'r:embed="(rId\d+)"', blk)
            if not (off and rid):
                continue
            tgt = rels.get((slide, rid.group(1)), '')
            media = 'ppt/' + tgt.replace('../', '')
            if media not in z.namelist():
                continue
            wh = png_size(z.read(media))
            out.append(dict(slide=slide, rid=rid.group(1), media=media,
                            px=wh, off=tuple(int(off.group(i)) for i in (1, 2)),
                            ext=tuple(int(off.group(i)) for i in (3, 4))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pptx')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--margin', type=float, default=0.4, help='安全区边距（英寸）')
    ap.add_argument('--slot', action='append', default=[],
                    help='可选：第N页强制比例，如 --slot 3:3.179')
    a = ap.parse_args()

    src = Path(a.pptx)
    z = zipfile.ZipFile(src)
    pres = z.read('ppt/presentation.xml').decode('utf-8')
    m = re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', pres)
    SW, SH = int(m.group(1)), int(m.group(2))
    slide_w, slide_h = SW / EMU, SH / EMU
    print(f'  幻灯片 {slide_w:.2f} × {slide_h:.2f} in   安全区边距 {a.margin} in')

    force = {}
    for sp in a.slot:
        idx, ratio = sp.split(':')
        force[int(idx)] = float(ratio)

    items = collect(z)
    for it in items:
        if not it['px']:
            continue
        pw, ph = it['px']
        ratio = pw / ph
        idx = int(re.sub(r'\D', '', it['slide']))
        ratio = force.get(idx, ratio)
        avail_w = slide_w - 2 * a.margin
        avail_h = slide_h - 2 * a.margin
        # 安全区内最大内接矩形
        w = min(avail_w, avail_h * ratio)
        h = w / ratio
        cx, cy = int(w * EMU), int(h * EMU)
        ox = int((slide_w - w) / 2 * EMU)
        oy = int((slide_h - h) / 2 * EMU)
        old = '%.2f×%.2f in (比例 %.3f)' % (it['ext'][0] / EMU, it['ext'][1] / EMU,
                                          it['ext'][0] / it['ext'][1])
        new = '%.2f×%.2f in (比例 %.3f)' % (w, h, ratio)
        flag = '' if abs(it['ext'][0] / it['ext'][1] - ratio) < 0.005 else '  ← 需改'
        print(f"  {it['slide']:<7} {it['media'].split('/')[-1]:<14} 图 {pw}×{ph}  "
              f"{old} → {new}{flag}")

    if a.list or not a.apply:
        print('  （--list 或未加 --apply，不写文件）')
        return 0

    # 重写各 slide XML：按 slide 顺序替换 off/ext
    per_slide = {}
    for it in items:
        if it['px']:
            per_slide.setdefault(it['slide'], []).append(it)

    bak = src.with_suffix(src.suffix + '.bak_frames')
    shutil.copy2(src, bak)
    tmp = src.with_suffix('.tmp.pptx')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zo:
        for n in z.namelist():
            data = z.read(n)
            stem = Path(n).stem
            if n.startswith('ppt/slides/slide') and n.endswith('.xml') and stem in per_slide:
                s = data.decode('utf-8')
                for it in per_slide[stem]:
                    pw, ph = it['px']
                    idx = int(re.sub(r'\D', '', stem))
                    ratio = force.get(idx, pw / ph)
                    avail_w, avail_h = slide_w - 2 * a.margin, slide_h - 2 * a.margin
                    w = min(avail_w, avail_h * ratio)
                    h = w / ratio
                    cx, cy = int(w * EMU), int(h * EMU)
                    ox, oy = int((slide_w - w) / 2 * EMU), int((slide_h - h) / 2 * EMU)
                    old_off = f'<a:off x="{it["off"][0]}" y="{it["off"][1]}"/>'
                    old_ext = f'<a:ext cx="{it["ext"][0]}" cy="{it["ext"][1]}"/>'
                    new_off = f'<a:off x="{ox}" y="{oy}"/>'
                    new_ext = f'<a:ext cx="{cx}" cy="{cy}"/>'
                    assert old_off in s and old_ext in s, (stem, 'off/ext 未找到')
                    s = s.replace(old_off, new_off, 1).replace(old_ext, new_ext, 1)
                data = s.encode('utf-8')
            zo.writestr(n, data)
    # Windows 上目标文件偶尔仍被占用（PowerPoint/杀软/同步盘），短暂重试后再回退为复制
    import time
    for attempt in range(5):
        try:
            tmp.replace(src)
            break
        except PermissionError:
            time.sleep(0.2)
    else:
        src.write_bytes(tmp.read_bytes())
        tmp.unlink(missing_ok=True)
    print(f'  APPLIED：图片框已按图片比例重排（备份 {bak.name}）')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
