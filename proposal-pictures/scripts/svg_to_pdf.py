#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""svg_to_pdf.py — 把 SVG 打成 PDF，喂给 nature-figure 的审计脚本。

为什么需要这一步：
  `nature-figure` 的碰撞/字号审计吃的是 **PDF 几何**（audit_figure_collisions.py、
  audit_pdf_text.py），而我们出的是 SVG。这个脚本只做格式搬运，不做任何判定。

为什么默认 Edge 而不是 cairosvg：
  实测同一份 SVG，cairosvg 对全角空格 / 混排段落的定位有偏差，会在模板图上
  制造 3 处**假重叠**（'层次一' 与 '阶段名' 重叠 75%）；Edge 无头打印与浏览器
  观感一致，审计结果与目视对得上。cairosvg 只作无浏览器环境的退路。

用法：
  python svg_to_pdf.py 图1.svg --out out/图1.pdf
  python svg_to_pdf.py 图1.svg --out out/图1.pdf --engine cairo   # 退路
  python svg_to_pdf.py 图1.svg --out out/图1.pdf --keep-html      # 留 HTML 便于排查

依赖：Edge/Chrome（默认）；或 cairosvg（--engine cairo）。
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "msedge", "google-chrome", "chromium", "chromium-browser",
]
UNIT_PX = {"px": 1.0, "": 1.0, "pt": 96 / 72, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96.0}


def find_browser() -> str | None:
    for c in BROWSERS:
        if Path(c).exists():
            return c
        w = shutil.which(c)
        if w:
            return w
    return None


def canvas_px(svg: str) -> tuple[float, float]:
    """SVG 画布换算成 96dpi 像素（打印页面尺寸用）。"""
    m = re.search(r'<svg[^>]*?width="([\d.]+)\s*(px|pt|mm|cm|in)?"[^>]*?'
                  r'height="([\d.]+)\s*(px|pt|mm|cm|in)?"', svg)
    if m:
        return (float(m.group(1)) * UNIT_PX[m.group(2) or "px"],
                float(m.group(3)) * UNIT_PX[m.group(4) or "px"])
    vb = re.search(r'viewBox="[\d.-]+[ ,]+[\d.-]+[ ,]+([\d.]+)[ ,]+([\d.]+)"', svg)
    if vb:
        return float(vb.group(1)), float(vb.group(2))
    raise ValueError("无法确定画布尺寸：既没有 width/height，也没有 viewBox")


def print_with_browser(svg_path: Path, pdf: Path, work: Path) -> None:
    browser = find_browser()
    if not browser:
        raise RuntimeError("未找到 Edge/Chrome；可用 --engine cairo 退路")
    svg = svg_path.read_text(encoding="utf-8")
    w, h = canvas_px(svg)
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        f"@page {{ size: {w:.4f}px {h:.4f}px; margin: 0 }}"
        "html,body{margin:0;padding:0}"
        f"svg{{display:block;width:{w:.4f}px;height:{h:.4f}px}}"
        f"</style></head><body>{svg}</body></html>"
    )
    html_path = work / "figure.html"
    html_path.write_text(html, encoding="utf-8")
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           "--no-margins", "--disable-extensions",
           f"--user-data-dir={work / 'profile'}", f"--print-to-pdf={pdf}",
           "file:///" + str(html_path).replace("\\", "/")]
    subprocess.run(cmd, capture_output=True, timeout=180)
    if not pdf.exists() or pdf.stat().st_size == 0:
        raise RuntimeError("浏览器打印 PDF 失败（检查 SVG 是否可正常打开）")


def print_with_cairo(svg_path: Path, pdf: Path) -> None:
    import cairosvg  # 第三方库，缺失时明确报错

    cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf))
    if not pdf.exists():
        raise RuntimeError("cairosvg 未产出 PDF")


def main() -> int:
    ap = argparse.ArgumentParser(description="SVG → PDF（供 nature-figure 审计）")
    ap.add_argument("svg", type=Path)
    ap.add_argument("--out", type=Path, required=True, help="输出 PDF 路径")
    ap.add_argument("--engine", choices=["auto", "edge", "cairo"], default="auto",
                    help="auto：优先 Edge，失败回落 cairosvg；cairo：直接用 cairosvg")
    ap.add_argument("--keep-html", action="store_true", help="保留中间 HTML（排查用）")
    a = ap.parse_args()

    if not a.svg.exists():
        print(f"!! 文件不存在：{a.svg}")
        return 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="svg2pdf_"))
    try:
        if a.engine == "cairo":
            print_with_cairo(a.svg, a.out)
            engine = "cairosvg"
        else:
            try:
                print_with_browser(a.svg, a.out, tmp)
                engine = "edge"
            except Exception as exc:  # noqa: BLE001
                if a.engine == "edge":
                    raise
                print(f"   浏览器打印失败（{exc}），回落 cairosvg")
                print_with_cairo(a.svg, a.out)
                engine = "cairosvg"
        size_kb = a.out.stat().st_size / 1024
        print(f"✅ {a.out}  ({size_kb:.1f} KB, engine={engine})")
        if engine == "cairosvg":
            print("   注意：cairosvg 对全角空格/混排定位可能有偏差，审计结果请与目视对照")
        if a.keep_html and (tmp / "figure.html").exists():
            keep = a.out.with_suffix(".html")
            shutil.copy(tmp / "figure.html", keep)
            print(f"   中间 HTML → {keep}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"!! {type(exc).__name__}: {exc}")
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
