#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_overlap.py — SVG 文字包围盒 vs 线段/折线/矩形边框：越界与压线检测。

原理：按「中文 1 字宽 = 字号，其余 0.55 × 字号」估算每个 <text> 的包围盒
（支持 text-anchor: start/middle/end 与 ±90° 旋转文字），再与所有 line、polyline 各段、
rect 的四条边做相交判定。命中 = 文字压线或文字撑出所属方框。

局限：估算宽度 ≠ 真实字形宽度；path 自绘图形不参与判定；结论以「命中 0 + 目视通过」为准。

用法:
  python check_overlap.py 图1.svg [图2.svg ...] [--pad 12] [--json out.json]
退出码: 有命中 1，无命中 0，参数/文件错误 2。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from xml.etree import ElementTree as ET

try:  # Windows 控制台默认 GBK，打印 ⚠ 等字符会 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SVG = "{http://www.w3.org/2000/svg}"
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")


def char_width(ch: str, fs: float) -> float:
    """中日韩字符与全角标点按 1em，其余按 0.55em 估宽。"""
    return fs if CJK.match(ch) else 0.55 * fs


def text_width(text: str, fs: float) -> float:
    return sum(char_width(ch, fs) for ch in text)


def text_box(el: ET.Element):
    """返回 (x0, y0, x1, y1, text, fs) 或 None。"""
    text = "".join(el.itertext()).strip()
    if not text:
        return None
    try:
        fs = float(el.get("font-size", 16))
        x = float(el.get("x", 0))
        y = float(el.get("y", 0))
    except ValueError:
        return None
    anchor = el.get("text-anchor", "start")
    wm = el.get("writing-mode", "") or ""
    if "vertical" in wm:  # eaVert/vertical-rl：字正立、自上而下，列宽约 1em
        x, y = float(el.get("x", 0)), float(el.get("y", 0))
        h = text_width(text, fs)
        anc = el.get(text-anchor, start)
        if anc == middle:          # 竖排多以 y 为居中锚点
            return [x - 0.5 * fs, y - h / 2, x + 0.5 * fs, y + h / 2, text]
        if anc == end:
            return [x - 0.5 * fs, y - h, x + 0.5 * fs, y, text]
        return [x - 0.5 * fs, y, x + 0.5 * fs, y + h, text]
    w = text_width(text, fs)
    rot = el.get("transform") or ""
    m = re.search(r"rotate\(\s*(-?[\d.]+)", rot)
    if m:
        ang = float(m.group(1)) % 360
        if abs(ang - 90) < 1 or abs(ang - 270) < 1:  # 竖排
            x0, x1 = x - 0.85 * fs, x + 0.25 * fs
            if anchor == "middle":
                y0, y1 = y - w / 2, y + w / 2
            elif anchor == "end":
                y0, y1 = y, y + w
            else:
                y0, y1 = y - w, y
            if abs(ang - 270) < 1:
                x0, x1 = x - 0.25 * fs, x + 0.85 * fs
            return (x0, y0, x1, y1, text, fs)
        return None  # 其他角度不判
    if anchor == "middle":
        x0 = x - w / 2
    elif anchor == "end":
        x0 = x - w
    else:
        x0 = x
    return (x0, y - 0.85 * fs, x0 + w, y + 0.25 * fs, text, fs)


def segments(el: ET.Element):
    tag = el.tag.replace(SVG, "")
    out = []
    if tag == "line":
        try:
            out.append(tuple(float(el.get(k)) for k in ("x1", "y1", "x2", "y2")))
        except (TypeError, ValueError):
            pass
    elif tag == "polyline" or tag == "polygon":
        raw = [p.split(",") for p in (el.get("points") or "").replace("  ", " ").split()]
        pts = [(float(a), float(b)) for a, b in (q for q in raw if len(q) == 2)]
        out += [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1)]
        if tag == "polygon" and len(pts) > 2:
            out.append((pts[-1][0], pts[-1][1], pts[0][0], pts[0][1]))
    elif tag == "rect":
        try:
            x, y = float(el.get("x", 0)), float(el.get("y", 0))
            w, h = float(el.get("width", 0)), float(el.get("height", 0))
        except ValueError:
            return out
        out += [(x, y, x + w, y), (x + w, y, x + w, y + h), (x + w, y + h, x, y + h), (x, y + h, x, y)]
    return out


def seg_hits_box(seg, box, pad: float = 0.0) -> bool:
    x1, y1, x2, y2 = seg
    bx0, by0, bx1, by1 = (box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad)
    if max(x1, x2) < bx0 or min(x1, x2) > bx1 or max(y1, y2) < by0 or min(y1, y2) > by1:
        return False
    if abs(y1 - y2) < 0.5:  # 水平
        return not (max(x1, x2) < bx0 or min(x1, x2) > bx1)
    if abs(x1 - x2) < 0.5:  # 垂直
        return not (max(y1, y2) < by0 or min(y1, y2) > by1)
    steps = max(8, int(math.hypot(x2 - x1, y2 - y1) / 4))
    for k in range(steps + 1):
        t = k / steps
        px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        if bx0 <= px <= bx1 and by0 <= py <= by1:
            return True
    return False


def check(path: str, pad: float):
    root = ET.parse(path).getroot()
    boxes = [b for b in (text_box(e) for e in root.iter(SVG + "text")) if b]
    segs = [s for e in root.iter() if e.tag.replace(SVG, "") in ("line", "polyline", "polygon", "rect")
            for s in segments(e)]
    hits = []
    for box in boxes:
        for seg in segs:
            if seg_hits_box(seg, box, pad):
                hits.append({"text": box[4], "box": [round(v, 1) for v in box[:4]],
                             "segment": [round(v, 1) for v in seg]})
    return len(boxes), len(segs), hits


def main() -> int:
    ap = argparse.ArgumentParser(description="SVG 文字越界/压线检测")
    ap.add_argument("paths", nargs="+", help="SVG 文件")
    ap.add_argument("--pad", type=float, default=0.0, help="容差像素（默认 0，严格判定）")
    ap.add_argument("--json", default=None, help="把结果写入 JSON")
    a = ap.parse_args()

    all_hits, rc = {}, 0
    for p in a.paths:
        try:
            nb, ns, hits = check(p, a.pad)
        except Exception as exc:  # noqa: BLE001
            print(f"!! {p}: {type(exc).__name__}: {exc}")
            rc = 2
            continue
        print(f"== {p}  文字 {nb}  线段/边框 {ns}  命中 {len(hits)}")
        for h in hits:
            print(f"   ⚠ 『{h['text'][:40]}』 盒={tuple(h['box'])} 相交={tuple(h['segment'])}")
        all_hits[p] = hits
        if hits:
            rc = 1
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(all_hits, fh, ensure_ascii=False, indent=2)
        print("json →", a.json)
    if rc == 0:
        print("✅ 无命中（仍须目视验收）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
