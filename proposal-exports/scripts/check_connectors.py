#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_connectors.py — 连线端点贴合检查：每条连线的两端是否落在方框/层带边界上。

背景：箭头端点悬空（`x2=466` 而方框左边在 `470`）这类问题，几何自检（查文字）
与一致性自检（查同类元素）都发现不了，只能靠人眼——实测被用户连抓两次。
本脚本把"端点距最近方框边界多远"算成数字，> 容差即 FLAG。

判定
- 取每条 `line`/`polyline` 的首尾端点（带 `marker-end`/`marker-start` 者视为连线）；
- 计算端点到所有矩形四条边的**最短距离**；
- 距离 > `--tol`（默认 1.5px）即报「悬空」，并给出最近的方框边与建议坐标；
- 长度 < `--min-len` 的短线（示意图标内部）默认跳过。

用法:
  python check_connectors.py 图1.svg [图2.svg ...] [--tol 1.5] [--min-len 60] [--json out.json]
退出码: 有悬空 1，全贴合 0，参数/文件错 2。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
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


def rects_of(root):
    """取出所有方框；排除画布背景框（否则端点会被判为"在内部"，距离恒为 0）。"""
    cw = num(root.get("width"), 0)
    ch = num(root.get("height"), 0)
    if not cw or not ch:
        vb = (root.get("viewBox") or "").split()
        if len(vb) == 4:
            cw, ch = float(vb[2]), float(vb[3])
    out = []
    for el in root.iter(SVG + "rect"):
        w, h = num(el.get("width")), num(el.get("height"))
        if w <= 20 or h <= 20:
            continue
        if cw and ch and w >= 0.8 * cw and h >= 0.8 * ch:
            continue  # 背景框
        out.append((num(el.get("x")), num(el.get("y")), w, h))
    return out


def connectors_of(root):
    out = []
    for idx, el in enumerate(root.iter()):
        tag = el.tag.replace(SVG, "")
        if tag == "line":
            pts = [(num(el.get("x1")), num(el.get("y1"))), (num(el.get("x2")), num(el.get("y2")))]
            arrow = bool(el.get("marker-end") or el.get("marker-start"))
        elif tag == "polyline":
            raw = [q.split(",") for q in (el.get("points") or "").split()]
            pts = [(float(q[0]), float(q[1])) for q in raw if len(q) == 2]
            arrow = bool(el.get("marker-end") or el.get("marker-start"))
        else:
            continue
        if len(pts) < 2 or not arrow:
            continue
        length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        out.append({"pts": pts, "len": length, "tag": tag, "key": idx})
    return out


def dist_to_rect(p, r):
    """点到矩形四条边的最短距离（点在矩形内部时返回 0）。"""
    x, y = p
    x0, y0, w, h = r
    x1, y1 = x0 + w, y0 + h
    if x0 <= x <= x1 and y0 <= y <= y1:
        return 0.0, "内部"
    dx = max(x0 - x, 0, x - x1)
    dy = max(y0 - y, 0, y - y1)
    return math.hypot(dx, dy), "外部"


def snap(p, r, tol):
    """把点吸附到最近的矩形边上，返回 (新坐标, 该边描述)。"""
    x, y = p
    x0, y0, w, h = r
    x1, y1 = x0 + w, y0 + h
    cands = [(abs(y - y0), (x, y0), f"上边 y={y0:g}"), (abs(y - y1), (x, y1), f"下边 y={y1:g}"),
             (abs(x - x0), (x0, y), f"左边 x={x0:g}"), (abs(x - x1), (x1, y), f"右边 x={x1:g}")]
    cands.sort(key=lambda t: t[0])
    return cands[0][1], cands[0][2]


def segments_of(root):
    """所有 line/polyline 的线段（用于判定"端点接在另一条线上"，如母线）。"""
    segs = []
    for idx, el in enumerate(root.iter()):
        tag = el.tag.replace(SVG, "")
        pts = []
        if tag == "line":
            pts = [(num(el.get("x1")), num(el.get("y1"))), (num(el.get("x2")), num(el.get("y2")))]
        elif tag in ("polyline", "polygon"):
            raw = [q.split(",") for q in (el.get("points") or "").split()]
            pts = [(float(q[0]), float(q[1])) for q in raw if len(q) == 2]
        else:
            continue
        key = idx
        segs += [(pts[i], pts[i + 1], key) for i in range(len(pts) - 1)]
    return segs


def point_seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.dist(p, (ax + t * vx, ay + t * vy))


def check(path, tol, min_len):
    root = ET.parse(path).getroot()
    rects = rects_of(root)
    segs = segments_of(root)
    conns = connectors_of(root)
    flags = []
    for c in conns:
        if c["len"] < min_len:
            continue
        for which, p in (("起点", c["pts"][0]), ("终点", c["pts"][-1])):
            best = None
            for r in rects:
                d, where = dist_to_rect(p, r)
                if best is None or d < best[0]:
                    best = (d, r, where)
            if best is None:
                continue
            d, r, where = best
            if where == "内部" or d <= tol:
                continue
            # 端点可能接在另一条线上（母线/干线）：距离 ≤ tol 视为已接
            if any(point_seg_dist(p, a, b) <= tol for a, b, k in segs if k != c["key"]):
                continue
            newp, edge = snap(p, r, tol)
            flags.append({"端点": which, "坐标": [round(v, 1) for v in p],
                          "最近方框": [round(v) for v in r], "距离px": round(d, 1),
                          "建议吸附到": edge, "建议坐标": [round(v, 1) for v in newp],
                          "长度": round(c["len"])})
    return flags, len(rects), len(conns)


def main() -> int:
    ap = argparse.ArgumentParser(description="SVG 连线端点贴合检查")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--tol", type=float, default=0.5, help="端点到边框最大距离（px）；1~2px 的缝肉眼可见，故默认 0.5")
    ap.add_argument("--min-len", type=float, default=16, help="只检查长度 ≥ 该值的连线；默认 16，避免漏掉行间短箭头")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    rc, out = 0, {}
    for p in a.paths:
        try:
            flags, nr, nc = check(p, a.tol, a.min_len)
        except Exception as exc:  # noqa: BLE001
            print(f"!! {p}: {type(exc).__name__}: {exc}")
            rc = 2
            continue
        print(f"== {p}  方框 {nr}  连线 {nc}  悬空端点 {len(flags)}")
        for f in flags:
            print(f"   ⚠ {f['端点']} {tuple(f['坐标'])} 距最近方框 {f['距离px']}px"
                  f" → 建议 {f['建议吸附到']}（{tuple(f['建议坐标'])}）")
        out[p] = flags
        if flags:
            rc = 1
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print("json →", a.json)
    if rc == 0:
        print("✅ 所有连线端点贴合（仍须目视确认箭头指向）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
