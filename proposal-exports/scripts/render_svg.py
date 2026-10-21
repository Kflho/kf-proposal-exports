#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_svg.py — 用无头浏览器把 SVG 渲染成 PNG；支持裁切放大（目视验收用）。

用法:
  python render_svg.py 图1.svg --png out/f1.png
  python render_svg.py 图1.svg --png out/f1_2x.png --scale 2
  python render_svg.py 图1.svg --png out/zoom.png --crop "300 540 600 60" --scale 4
  python render_svg.py 图1.svg --png out/f1.png --browser "C:/path/to/msedge.exe"

--crop "x y w h" 会生成一个临时 SVG（只改 viewBox/width/height），其余内容不动。
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

try:  # Windows 控制台默认 GBK，打印 ⚠ 等字符会 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "chromium", "chromium-browser", "microsoft-edge", "msedge",
]


def find_browser(explicit=None):
    if explicit:
        return explicit if os.path.exists(explicit) or shutil.which(explicit) else None
    for c in CANDIDATES:
        if os.path.sep in c or c.endswith(".exe"):
            if os.path.exists(c):
                return c
        elif shutil.which(c):
            return shutil.which(c)
    return None


def make_crop(src: str, crop: str, scale: float, tmpdir: str) -> str:
    x, y, w, h = (float(v) for v in crop.split())
    raw = open(src, encoding="utf-8").read()
    new = (f'width="{int(w * scale)}" height="{int(h * scale)}" '
           f'viewBox="{x:g} {y:g} {w:g} {h:g}"')
    raw2, n = re.subn(r'width="[\d.]+"\s+height="[\d.]+"\s+viewBox="[^"]*"', new, raw, count=1)
    if n == 0:
        raw2, n = re.subn(r'viewBox="[^"]*"', f'viewBox="{x:g} {y:g} {w:g} {h:g}"', raw, count=1)
        if n:
            raw2 = raw2.replace("<svg ", f'<svg width="{int(w * scale)}" height="{int(h * scale)}" ', 1)
    out = os.path.join(tmpdir, "crop.svg")
    open(out, "w", encoding="utf-8").write(raw2)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="SVG → PNG（无头浏览器）")
    ap.add_argument("svg")
    ap.add_argument("--png", required=True)
    ap.add_argument("--crop", default=None, help='"x y w h"，只渲染该区域')
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--size", default=None, help="窗口尺寸 WxH（默认按 SVG 尺寸×scale）")
    ap.add_argument("--browser", default=None)
    a = ap.parse_args()

    if not os.path.exists(a.svg):
        print("!! 文件不存在:", a.svg)
        return 2
    browser = find_browser(a.browser)
    if not browser:
        print("!! 未找到无头浏览器。请用 --browser 指定 msedge/chrome 可执行文件路径，")
        print("   或改用任何浏览器手动截图（本脚本仅为便利，不阻塞流程）。")
        return 2

    src = os.path.abspath(a.svg)
    out = os.path.abspath(a.png)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    tmpdir = tempfile.mkdtemp(prefix="render_svg_")
    try:
        if a.crop:
            src = make_crop(src, a.crop, a.scale, tmpdir)
        else:
            raw = open(src, encoding="utf-8").read()
            # 宽高可能带单位（pt / px / mm …）：pt 按 96dpi 折算成 px（1pt = 96/72 px）
            m = re.search(r'width="([\d.]+)\s*(pt|px|mm|cm|in)?"\s+'
                          r'height="([\d.]+)\s*(pt|px|mm|cm|in)?"', raw)
            if m:
                k = {"pt": 96 / 72, "px": 1.0, "mm": 96 / 25.4, "cm": 96 / 2.54,
                     "in": 96.0, None: 1.0}
                base = (float(m.group(1)) * k[m.group(2) or None],
                        float(m.group(3)) * k[m.group(4) or None])
                if (m.group(2) or "") == "pt" or (m.group(4) or "") == "pt":
                    print(f"   SVG 尺寸 {m.group(1)}{m.group(2) or ''}×{m.group(3)}"
                          f"{m.group(4) or ''} → {base[0]:.0f}×{base[1]:.0f} px @96dpi")
            else:
                # 退路：用 viewBox 尺寸
                vb = re.search(r'viewBox="[\d.-]+ [\d.-]+ ([\d.]+) ([\d.]+)"', raw)
                base = (float(vb.group(1)), float(vb.group(2))) if vb else (1600.0, 900.0)
            size = f"{int(base[0] * a.scale)},{int(base[1] * a.scale)}"
            # --scale 必须同时放大 SVG 自身宽高，否则只是把窗口撑大、内容仍按原尺寸画（缩在角落）
            if a.scale != 1.0:
                scaled = re.sub(r'(<svg[^>]*?)width="[\d.]+\s*(pt|px|mm|cm|in)?"',
                                rf'\g<1>width="{int(base[0] * a.scale)}"', raw, count=1)
                scaled = re.sub(r'(<svg[^>]*?)height="[\d.]+\s*(pt|px|mm|cm|in)?"',
                                rf'\g<1>height="{int(base[1] * a.scale)}"', scaled, count=1)
                src = os.path.join(tmpdir, "scaled.svg")
                open(src, "w", encoding="utf-8").write(scaled)
        if a.crop:
            x, y, w, h = (float(v) for v in a.crop.split())
            size = a.size.replace("x", ",") if a.size else f"{int(w * a.scale)},{int(h * a.scale)}"
        elif a.size:
            size = a.size.replace("x", ",")
        url = "file:///" + src.replace("\\", "/")
        cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
               f"--window-size={size}", f"--screenshot={out}", url]
        r = subprocess.run(cmd, capture_output=True)
        if not os.path.exists(out):
            print("!! 渲染失败，浏览器输出：")
            print(r.stderr.decode("utf-8", "replace")[-600:])
            return 2
        print(f"✅ {out}  ({os.path.getsize(out) / 1024:.1f} KB, 窗口 {size})")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
