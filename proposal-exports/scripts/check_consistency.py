#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_consistency.py — SVG「视觉语言一致性」检查：同类元素是否同一处理。

背景：几何自检（check_overlap）只能发现压线/越界，**发现不了"有的居中有的左对齐"**这类问题——
实测一张矩阵图里 28 处居中、17 处左对齐，肉眼看"乱"，脚本却全绿。本脚本补这一环。

检查项
1. 单元格分组：按 rect 尺寸完全相同分组（≥2 格），组内逐格比对
   - 同一「相对 y」上的文字锚点是否一致 → 不一致即 FLAG（例：同是表头，一格居中一格左对齐）
   - 同一「相对 y」上是否都有文字 → 缺项提示
   - 组内字号集合、分隔线有无是否一致
2. 全局报表：字号档位、线宽档位、marker 清单、锚点分布（供人工核对是否成体系）

用法:
  python check_consistency.py 图1.svg [图2.svg ...] [--min-cells 2] [--json out.json]
退出码: 有 FLAG 1，无 0，参数/文件错 2。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from xml.etree import ElementTree as ET

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SVG = "{http://www.w3.org/2000/svg}"


def num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def collect(root):
    rects, texts, lines, others = [], [], [], Counter()
    for el in root.iter():
        tag = el.tag.replace(SVG, "")
        if tag == "rect":
            w, h = num(el.get("width")), num(el.get("height"))
            if w > 0 and h > 0:
                rects.append({"x": num(el.get("x")), "y": num(el.get("y")), "w": w, "h": h})
        elif tag == "text":
            t = "".join(el.itertext()).strip()
            if t:
                texts.append({"x": num(el.get("x")), "y": num(el.get("y")),
                              "fs": num(el.get("font-size"), 16),
                              "anchor": el.get("text-anchor", "start"),
                              "rot": "rotate" in (el.get("transform") or ""), "t": t})
        elif tag == "line":
            lines.append({"x1": num(el.get("x1")), "y1": num(el.get("y1")),
                          "x2": num(el.get("x2")), "y2": num(el.get("y2")),
                          "sw": num(el.get("stroke-width"), 1)})
        elif tag in ("marker", "polyline", "path", "circle", "polygon"):
            others[tag] += 1
    return rects, texts, lines, others


def inside(t, r, pad=0.0):
    return (r["x"] - pad <= t["x"] <= r["x"] + r["w"] + pad
            and r["y"] - pad <= t["y"] <= r["y"] + r["h"] + pad)


def check(path, min_cells):
    root = ET.parse(path).getroot()
    rects, texts, lines, others = collect(root)
    groups = defaultdict(list)
    for r in rects:
        if r["w"] >= 80 and r["h"] >= 60:  # 只看像"单元格"的方框
            groups[(round(r["w"]), round(r["h"]))].append(r)

    flags, notes = [], []
    for (w, h), cells in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(cells) < min_cells:
            continue
        per = []
        for r in cells:
            ts = [t for t in texts if inside(t, r, pad=2) and not t["rot"]]
            if not ts:
                continue
            rel = {}
            for t in ts:
                rel.setdefault(round(t["y"] - r["y"]), []).append(t)
            seps = [ln for ln in lines
                    if abs(ln["y1"] - ln["y2"]) < 0.5
                    and r["x"] + 4 <= ln["x1"] and ln["x2"] <= r["x"] + r["w"] - 4
                    and 0.30 * r["w"] <= (ln["x2"] - ln["x1"]) <= 0.80 * r["w"]]
            per.append({"rect": r, "rel": rel, "seps": len(seps), "fs": {round(t["fs"]) for t in ts if round(t["fs"]) > 13}})
        if len(per) < min_cells:
            continue
        # 同一相对 y 的锚点一致性
        for ry in sorted({ry for p in per for ry in p["rel"]}):
            seen = [(p["rect"], p["rel"][ry]) for p in per if ry in p["rel"]]
            if len(seen) < 2:
                continue
            anchors = {ts[0]["anchor"] for _, ts in seen}
            if len(anchors) > 1:
                detail = "; ".join(f"x={int(r['x'])}:{ts[0]['anchor']}" for r, ts in seen)
                flags.append(f"单元格({w}×{h}) 相对 y={ry} 处锚点不一致：{detail}")
            if len(seen) != len(per):
                notes.append(f"单元格({w}×{h}) 相对 y={ry} 仅 {len(seen)}/{len(per)} 格有文字")
        # 字号集合一致性
        fss = {frozenset(p["fs"]) for p in per}
        if len(fss) > 1:
            flags.append(f"单元格({w}×{h}) 字号集合不一致：" + " / ".join(
                ",".join(map(str, sorted(s))) for s in fss))
        # 分隔线有无一致性
        sep = {p["seps"] > 0 for p in per}
        if len(sep) > 1:
            flags.append(f"单元格({w}×{h}) 表头分隔线不一致：" +
                         f"{sum(1 for p in per if p['seps'])}/{len(per)} 格有")

    stats = {
        "字号": dict(sorted(Counter(round(t['fs']) for t in texts).items())),
        "锚点": dict(Counter(t["anchor"] for t in texts)),
        "线宽": dict(sorted(Counter(round(ln['sw'], 1) for ln in lines).items())),
        "图元": dict(others),
    }
    return flags, notes, stats, len(texts), len(rects)


def main() -> int:
    ap = argparse.ArgumentParser(description="SVG 视觉语言一致性检查")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--min-cells", type=int, default=2, help="成组比对所需的最少单元格数")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    rc, out = 0, {}
    for p in a.paths:
        try:
            flags, notes, stats, nt, nr = check(p, a.min_cells)
        except Exception as exc:  # noqa: BLE001
            print(f"!! {p}: {type(exc).__name__}: {exc}")
            rc = 2
            continue
        print(f"== {p}  文字 {nt} 方框 {nr}  FLAG {len(flags)}")
        for f in flags:
            print("   ⚠ " + f)
        for n in notes[:5]:
            print("   · " + n)
        print("   统计：" + "；".join(f"{k}={v}" for k, v in stats.items()))
        out[p] = {"flags": flags, "notes": notes, "stats": stats}
        if flags:
            rc = 1
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print("json →", a.json)
    if rc == 0:
        print("✅ 同类元素处理一致（仍须目视确认版式意图）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
