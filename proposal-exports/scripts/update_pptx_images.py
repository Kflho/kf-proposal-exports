#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""update_pptx_images.py — 把 pptx 内的图片换成新渲染的 PNG，其余部分逐字节不动。

用途：申报书的图通常要求以 PPT 交付，而 PPT 里往往是「一页一张图」。图改完后
只需换图，不要用 python-pptx 重存（它会重新序列化整个包，版式与母版有被改动
的风险）。本脚本直接改写 zip 内的 media 条目，幻灯片 XML、版式、备注、几何
位置全部保持原样。

用法：
    # 1) 先看包里有哪些图片条目
    python update_pptx_images.py 三图.pptx --list

    # 2) 换图（先干跑，确认清单无误再加 --apply）
    python update_pptx_images.py 三图.pptx \
        --map "ppt/media/image1.png=out/图1.png" \
        --map "ppt/media/image2.png=out/图2.png" --apply

    # 3) 也可用映射文件（每行 "条目=新图"，# 开头为注释）
    python update_pptx_images.py 三图.pptx --map-file replace.txt --apply

不依赖第三方库（纯标准库 zipfile）。与 render_svg.py 配合：
    render_svg.py 图1.svg --png out/图1.png --scale 2
    update_pptx_images.py 三图.pptx --map-file replace.txt --apply
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime

IMG_EXT = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff', '.emf', '.wmf')


def read_size(data: bytes):
    """读 PNG/JPG 像素尺寸，读不出返回 None。"""
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        w = int.from_bytes(data[16:20], 'big')
        h = int.from_bytes(data[20:24], 'big')
        return w, h
    if data[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3):
                h = int.from_bytes(data[i + 5:i + 7], 'big')
                w = int.from_bytes(data[i + 7:i + 9], 'big')
                return w, h
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg = int.from_bytes(data[i + 2:i + 4], 'big')
            i += 2 + seg
    return None


def list_media(zf: zipfile.ZipFile) -> list[str]:
    return sorted(n for n in zf.namelist()
                  if n.startswith('ppt/media/') and n.lower().endswith(IMG_EXT))


def parse_map(args) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in args.map or []:
        if '=' not in item:
            raise SystemExit(f'--map 需要「条目=新图」形式: {item}')
        k, v = item.split('=', 1)
        mapping[k.strip()] = v.strip()
    if args.map_file:
        with open(args.map_file, encoding='utf-8') as fh:
            for line in fh:
                line = line.split('#', 1)[0].strip()
                if not line:
                    continue
                if '=' not in line:
                    raise SystemExit(f'{args.map_file}: 需要「条目=新图」形式: {line}')
                k, v = line.split('=', 1)
                mapping[k.strip()] = v.strip()
    return mapping


def main() -> int:
    ap = argparse.ArgumentParser(description='把 pptx 内图片换成新渲染的 PNG（其余部分不动）')
    ap.add_argument('pptx')
    ap.add_argument('--list', action='store_true', help='只列出包内图片条目与尺寸')
    ap.add_argument('--map', action='append', metavar='条目=新图', help='可重复')
    ap.add_argument('--map-file', help='映射文件，每行「条目=新图」')
    ap.add_argument('--apply', action='store_true', help='真正写入（默认只干跑）')
    ap.add_argument('--backup', action='store_true', help='写入前留一份 .bak_时间戳（仓库用 git 时可不开）')
    ap.add_argument('--keep-mtime', action='store_true', default=True,
                    help='保留原条目时间戳与压缩方式（默认开）')
    args = ap.parse_args()

    if not os.path.exists(args.pptx):
        raise SystemExit(f'找不到 pptx: {args.pptx}')

    zf = zipfile.ZipFile(args.pptx)
    media = list_media(zf)
    if not media:
        raise SystemExit('包内没有 ppt/media 图片')

    if args.list or not (args.map or args.map_file):
        print(f'== {os.path.basename(args.pptx)}  图片条目 {len(media)}')
        for name in media:
            data = zf.read(name)
            size = read_size(data)
            tag = f'{size[0]}×{size[1]}' if size else '尺寸未知'
            print(f'  {name:<28} {len(data):>9} B  {tag}')
        if not args.list:
            print('\n（加 --map "条目=新图" 指定替换；--apply 才写入）')
        zf.close()
        return 0

    mapping = parse_map(args)
    missing = [k for k in mapping if k not in zf.namelist()]
    if missing:
        raise SystemExit(f'pptx 里没有这些条目: {missing}')

    repl: dict[str, bytes] = {}
    print(f'== {os.path.basename(args.pptx)}')
    for entry, path in mapping.items():
        if not os.path.exists(path):
            raise SystemExit(f'新图不存在: {path}')
        old = zf.read(entry)
        new = open(path, 'rb').read()
        os_, ns_ = read_size(old), read_size(new)
        warn = ''
        if os_ and ns_ and os_ != ns_:
            warn = f'  ⚠ 尺寸变了 {os_[0]}×{os_[1]} → {ns_[0]}×{ns_[1]}（PPT 里会被拉伸）'
        repl[entry] = new
        print(f'  {entry:<28} {len(old):>9} → {len(new):>9} B   {os.path.basename(path)}{warn}')

    if not args.apply:
        print('\nDRY RUN（加 --apply 写入）')
        zf.close()
        return 0

    if args.backup:
        bak = args.pptx + '.bak_' + datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(args.pptx, bak)
        print(f'  备份 → {os.path.basename(bak)}')

    tmp = args.pptx + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zf.infolist():
            data = repl.get(item.filename, zf.read(item.filename))
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zout.writestr(zi, data)
    zf.close()
    os.replace(tmp, args.pptx)
    print(f'\nAPPLIED：换图 {len(repl)} 张，其余条目原样保留')
    return 0


if __name__ == '__main__':
    sys.exit(main())
