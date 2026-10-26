#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deck_spec.py — 页片"回灌"工具：把 .pptx 拆成 spec，或对比两版找差异。

为什么要有它：页片有两份真相——生成器（代码）和交付物（.pptx）。在 PowerPoint 里改完，
要把改动回灌到生成器，靠肉眼比两个文件必然漏。这里做两件事：

  dump：把 pptx 拆成 JSON（每页的形状/文字 run/字号/颜色/表格/图片/备注），当回灌清单；
  compare：比两个 pptx（或两个 spec），逐页逐项报"新增 / 删除 / 文字变了 / 位置变了"。

用法:
  python deck_spec.py deck.pptx --out spec.json [--assets out/assets]
  python deck_spec.py --compare old.pptx new.pptx      # 生成器出的 vs 手改后的
  python deck_spec.py --compare old.json new.json --json

退出码: dump 成功 0；compare 无差异 0、有差异 1；参数/依赖错误 2。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EMU = 914400.0


def _color(run):
    try:
        rgb = run.font.color.rgb
        return str(rgb) if rgb is not None else None
    except Exception:
        return None


def _baseline(run):
    rpr = run.font._rPr
    return rpr.get("baseline") if rpr is not None else None


def _text_item(shape) -> dict:
    paras = []
    for para in shape.text_frame.paragraphs:
        runs = []
        for run in para.runs:
            if not run.text:
                continue
            runs.append({"t": run.text,
                         "sz": run.font.size.pt if run.font.size else None,
                         "b": bool(run.font.bold) if run.font.bold is not None else None,
                         "c": _color(run), "base": _baseline(run)})
        if runs:
            paras.append(runs)
    return {"kind": "text", "box": _box(shape), "paras": paras,
            "plain": ["".join(r["t"] for r in para) for para in paras]}


def _box(shape) -> dict:
    return {"x": round(shape.left / EMU, 2), "y": round(shape.top / EMU, 2),
            "w": round(shape.width / EMU, 2), "h": round(shape.height / EMU, 2)}


def dump_deck(path: Path, assets: Path | None = None) -> dict:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    prs = Presentation(str(path))
    if assets:
        assets.mkdir(parents=True, exist_ok=True)
    slides = []
    for page, slide in enumerate(prs.slides, start=1):
        items = []
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                part = slide.part.related_part(shape._element.blip_rId)
                name = Path(str(part.partname)).name
                if assets:
                    target = assets / name
                    if not target.exists():
                        target.write_bytes(part.blob)
                items.append({"kind": "image", "box": _box(shape), "asset": name})
                continue
            if getattr(shape, "has_table", False):
                rows = [[cell.text for cell in row.cells] for row in shape.table.rows]
                items.append({"kind": "table", "box": _box(shape), "rows": rows})
                continue
            if shape.has_text_frame and shape.text_frame.text.strip():
                items.append(_text_item(shape))
        notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
        slides.append({"page": page, "items": items, "notes": notes})
    return {"source": str(path), "pages": len(slides),
            "size": [round(prs.slide_width / EMU, 3), round(prs.slide_height / EMU, 3)],
            "slides": slides}


def _shape_key(item: dict) -> str:
    if item["kind"] == "text":
        return "text：" + " / ".join(item.get("plain") or [])
    if item["kind"] == "image":
        return "image：" + item.get("asset", "")
    return "table：" + " | ".join(cell for row in item.get("rows", []) for cell in row)


def compare_specs(a: dict, b: dict) -> dict:
    diffs = []
    if a.get("pages") != b.get("pages"):
        diffs.append({"page": 0, "kind": "page-count",
                      "old": a.get("pages"), "new": b.get("pages")})
    for index in range(max(len(a["slides"]), len(b["slides"]))):
        old_slide = a["slides"][index] if index < len(a["slides"]) else {"items": [], "notes": ""}
        new_slide = b["slides"][index] if index < len(b["slides"]) else {"items": [], "notes": ""}
        page = index + 1
        old_items = {_shape_key(item): item for item in old_slide["items"]}
        new_items = {_shape_key(item): item for item in new_slide["items"]}
        for key in old_items:
            if key not in new_items:
                diffs.append({"page": page, "kind": "removed", "what": key[:80]})
        for key in new_items:
            if key not in old_items:
                diffs.append({"page": page, "kind": "added", "what": key[:80]})
                continue
            old_box, new_box = old_items[key].get("box"), new_items[key].get("box")
            if old_box != new_box:
                diffs.append({"page": page, "kind": "moved", "what": key[:60],
                              "old": old_box, "new": new_box})
        if (old_slide.get("notes") or "") != (new_slide.get("notes") or ""):
            diffs.append({"page": page, "kind": "notes", "what": "口播备注",
                          "old": (old_slide.get("notes") or "")[:60],
                          "new": (new_slide.get("notes") or "")[:60]})
    return {"diffs": diffs, "count": len(diffs)}


def _load(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return dump_deck(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="页片回灌：拆 spec / 比差异")
    parser.add_argument("deck", nargs="?", help=".pptx（dump 模式）")
    parser.add_argument("--out", help="dump 输出 JSON")
    parser.add_argument("--assets", help="图片另存目录（可选）")
    parser.add_argument("--compare", nargs=2, metavar=("OLD", "NEW"),
                        help="比两个 .pptx 或 .json")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    try:
        if args.compare:
            old, new = Path(args.compare[0]), Path(args.compare[1])
            for path in (old, new):
                if not path.is_file():
                    print(f"错误：找不到 {path}", file=sys.stderr)
                    return 2
            result = compare_specs(_load(old), _load(new))
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=1))
            else:
                if not result["count"]:
                    print("无差异：两版结构、文字、位置、备注一致")
                for item in result["diffs"]:
                    page = item["page"] or "-"
                    if item["kind"] in ("added", "removed"):
                        print(f"  P{page} [{item['kind']}] {item['what']}")
                    elif item["kind"] == "moved":
                        print(f"  P{page} [moved] {item['what']} {item['old']} → {item['new']}")
                    elif item["kind"] == "notes":
                        print(f"  P{page} [notes] 口播改动")
                    else:
                        print(f"  P{page} [{item['kind']}] {item.get('old')} → {item.get('new')}")
                print(f"summary: {result['count']} 处差异")
            return 0 if not result["count"] else 1

        if not args.deck:
            parser.error("需要 deck 或 --compare")
        deck = Path(args.deck)
        if not deck.is_file():
            print(f"错误：找不到 {deck}", file=sys.stderr)
            return 2
        spec = dump_deck(deck, Path(args.assets) if args.assets else None)
        payload = json.dumps(spec, ensure_ascii=False, indent=1)
        if args.out:
            Path(args.out).write_text(payload, encoding="utf-8")
            print(f"{deck}：{spec['pages']} 页 → {args.out}")
        else:
            print(payload)
        return 0
    except ModuleNotFoundError as exc:
        print(f"错误：缺少依赖（{exc.name}）：pip install python-pptx", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI 边界
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
