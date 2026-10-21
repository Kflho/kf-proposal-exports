#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_pptx_png.py — 用 PowerPoint COM 把每页导出成 PNG（本机替代 LibreOffice）。

官方 pptx skill 的预览路径是 soffice → PDF → pdftoppm；Windows 上装了 Office 时，
直接调 PowerPoint 导出更快、也更接近用户最终看到的渲染（没有字体替换）。

用法:
  python render_pptx_png.py deck.pptx
  python render_pptx_png.py deck.pptx --out previews --width 1920
  python render_pptx_png.py deck.pptx --height 1080

依赖:
  - Windows + 已安装 PowerPoint（POWERPNT.EXE）；
  - pywin32（pip install pywin32）。
  条件不满足时直接报错并给出替代方案，不静默跳过。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:  # Windows 控制台默认 GBK
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PowerPoint COM 逐页导出 PNG")
    parser.add_argument("deck", help=".pptx 文件")
    parser.add_argument("--out", default="preview", help="输出目录（默认 preview/）")
    parser.add_argument("--width", type=int, default=1600, help="导出宽度像素（默认 1600）")
    parser.add_argument("--height", type=int, default=0, help="导出高度像素（默认按 16:9 推）")
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        print("错误：本脚本依赖 PowerPoint COM，只能在 Windows + Office 环境运行。\n"
              "替代：用官方 pptx skill 的 scripts/office/soffice.py 转 PDF 再 pdftoppm。",
              file=sys.stderr)
        return 2
    try:
        import win32com.client
    except ImportError:
        print("错误：缺少 pywin32：pip install pywin32", file=sys.stderr)
        return 2

    deck = Path(args.deck).resolve()
    if not deck.is_file():
        print(f"错误：找不到 {deck}", file=sys.stderr)
        return 2
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    width = args.width
    height = args.height or round(width * 9 / 16)

    app = win32com.client.Dispatch("PowerPoint.Application")
    pres = None
    try:
        pres = app.Presentations.Open(str(deck), WithWindow=False)
        total = pres.Slides.Count
        for index in range(1, total + 1):
            png = out_dir / f"slide-{index:02d}.png"
            pres.Slides(index).Export(str(png), "PNG", width, height)
            print(f"  {png.name}")
        print(f"共 {total} 页 → {out_dir}")
        return 0
    except Exception as exc:  # noqa: BLE001 - COM 异常类型杂，CLI 边界统一报错
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    finally:
        if pres is not None:
            pres.Close()
        app.Quit()


if __name__ == "__main__":
    raise SystemExit(main())
