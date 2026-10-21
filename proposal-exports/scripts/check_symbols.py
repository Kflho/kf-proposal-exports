#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_symbols.py — 图内文字的非规范符号与记法扫描。

默认规则覆盖中文技术材料里最常见的自创记法（箭头表示升降、全角加号作连词、
间隔号作并列、精度@距离、数字与单位间缺空格、三箭头分隔符等）。
可用 --rules 传入 JSON 覆盖或扩展：{"规则名": {"pattern": "正则", "hint": "建议改法"}}

用法:
  python check_symbols.py 图1.svg [图2.svg ...] [--rules my_rules.json] [--json out.json]
退出码: 有命中 1，无命中 0，参数/文件错误 2。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from xml.etree import ElementTree as ET

try:  # Windows 控制台默认 GBK，打印 ⚠ 等字符会 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SVG = "{http://www.w3.org/2000/svg}"

DEFAULT_RULES = {
    "箭头表示升降": {"pattern": r"[↓↑]", "hint": "改为文字：降低/提高 ≥N%（与正文逐字一致）"},
    "全角加号作连词": {"pattern": r"[\u4e00-\u9fff]＋[\u4e00-\u9fff]", "hint": "改为「与」；＋ 只用于专名（如 5G-A＋毫米波）"},
    "间隔号作并列": {"pattern": r"[\u4e00-\u9fff]·[\u4e00-\u9fff]", "hint": "改为顿号「、」"},
    "ASCII 箭头": {"pattern": r"(->|=>|>>>|<--)", "hint": "连线用 →；正式图里 >>> 改为「说明：」或另起小字行"},
    "精度@距离": {"pattern": r"@\s*\d", "hint": "改为「1 km 处定位精度 ≤10 m」"},
    "数字与单位缺空格": {"pattern": r"\d(?:km|m|ms|GHz|MHz|s|kg|个|套|份)(?![\w])", "hint": "数字与单位间加半角空格：10 km / 100 ms"},
    "中文紧邻半角数字": {"pattern": r"[\u4e00-\u9fff]\d", "hint": "中英数字间加半角空格（除“第3”“3号”等固定搭配）"},
    "半角数字紧邻中文": {"pattern": r"\d[\u4e00-\u9fff]", "hint": "同上；如“1套”应为“1 套”"},
    "省略号代替字": {"pattern": r"……|\.\.\.", "hint": "检查是否为未填的占位"},
}


def load_rules(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    rules = dict(DEFAULT_RULES)
    for k, v in raw.items():
        if v is None:
            rules.pop(k, None)
        else:
            rules[k] = v
    return rules


def scan(path, rules):
    root = ET.parse(path).getroot()
    hits = []
    for el in root.iter(SVG + "text"):
        text = "".join(el.itertext()).strip()
        if not text:
            continue
        x, y = el.get("x", "?"), el.get("y", "?")
        for name, spec in rules.items():
            for m in re.finditer(spec["pattern"], text):
                hits.append({"rule": name, "x": x, "y": y,
                             "match": m.group(0), "hint": spec.get("hint", ""),
                             "text": text})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="图内文字符号/记法扫描")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--rules", default=None, help="JSON 规则文件（覆盖或禁用默认规则；值设 null 表示禁用）")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    rules = load_rules(a.rules) if a.rules else DEFAULT_RULES
    rc, out = 0, {}
    for p in a.paths:
        try:
            hits = scan(p, rules)
        except Exception as exc:  # noqa: BLE001
            print(f"!! {p}: {type(exc).__name__}: {exc}")
            rc = 2
            continue
        print(f"== {p}  命中 {len(hits)}")
        for h in hits:
            print(f"   ⚠ [{h['rule']}] 『{h['match']}』 @({h['x']},{h['y']}) → {h['hint']}")
            print(f"      原文：{h['text'][:70]}")
        out[p] = hits
        if hits:
            rc = 1
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
        print("json →", a.json)
    if rc == 0:
        print("✅ 无命中（仍须人工确认术语与指标写法）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
