#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_text.py — 导出 SVG 里每个 text 的坐标/字号/锚点/字数/文字，供人工核对。

用途：
  1. 逐条读文字，核对术语、称谓、指标写法（图内文字是要读的，不是看的）；
  2. 检查字号是否跳档（同类元素应同字号）；
  3. 检查同类元素是否对齐（同列 x 应一致、同排 y 应一致）。

用法:
  python audit_text.py 图1.svg
  python audit_text.py 图1.svg --md out/f1_text.md
  python audit_text.py 图1.svg --align        # 顺带按 x/y 聚类，报对齐异常
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from xml.etree import ElementTree as ET

try:  # Windows 控制台默认 GBK，打印 ⚠ 等字符会 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SVG = "{http://www.w3.org/2000/svg}"
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
LAT = re.compile(r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*")


def count_zh(t: str) -> int:
    return len(CJK.findall(t)) + len(LAT.findall(t))


def rows(path: str):
    root = ET.parse(path).getroot()
    for el in root.iter(SVG + "text"):
        text = "".join(el.itertext()).strip()
        if not text:
            continue
        yield {
            "x": float(el.get("x", 0) or 0),
            "y": float(el.get("y", 0) or 0),
            "fs": float(el.get("font-size", 16) or 16),
            "anchor": el.get("text-anchor", "start"),
            "rot": "ROT" if (el.get("transform") or "").startswith("rotate") else "",
            "n": count_zh(text),
            "text": text,
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="SVG 文字清单")
    ap.add_argument("path")
    ap.add_argument("--md", default=None, help="同时写出 Markdown 表")
    ap.add_argument("--align", action="store_true", help="报字号/对齐异常")
    a = ap.parse_args()

    rs = list(rows(a.path))
    print(f"== {a.path}  文字元素 {len(rs)}")
    for r in rs:
        print(f"  x={r['x']:>7.0f} y={r['y']:>6.0f} fs={r['fs']:>4.0f} {r['anchor']:>6} {r['rot']:>3} "
              f"n={r['n']:>3} | {r['text']}")

    if a.align:
        fs = Counter(r["fs"] for r in rs)
        print("\n-- 字号分布 --")
        for k, v in sorted(fs.items()):
            print(f"   {k:>4.0f}px × {v}")
        xs = Counter(round(r["x"]) for r in rs)
        print("-- 出现 ≥3 次的 x（同列应对齐）--")
        for k, v in sorted(xs.items()):
            if v >= 3:
                print(f"   x={k:>6} × {v}")

    if a.md:
        with open(a.md, "w", encoding="utf-8") as fh:
            fh.write(f"# 图内文字清单 · {a.path}\n\n| # | x | y | 字号 | 锚点 | 旋转 | 字数 | 文字 |\n")
            fh.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
            for i, r in enumerate(rs, 1):
                fh.write(f"| {i} | {r['x']:.0f} | {r['y']:.0f} | {r['fs']:.0f} | {r['anchor']} | "
                         f"{r['rot'] or '-'} | {r['n']} | {r['text']} |\n")
        print("md →", a.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
