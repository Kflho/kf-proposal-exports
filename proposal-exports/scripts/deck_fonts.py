#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deck_fonts.py — 按字体规范给每个 run 写死中英分工（默认干跑，不写盘）。

规范（`project note` → 论文撰写 → 字体）：**标题黑体、正文宋体、英文 Times New Roman**。
pptxgenjs 的 `fontFace` 只写一个 `a:latin`，中文靠 PowerPoint 系统回退，换机器就变字宽、
页面会溢出；这里把角色写进 run 属性：

  - `a:ea`    = 中文：标题用 SimHei（黑体），正文用 SimSun（宋体）；
  - `a:latin` = 西文、数字、单位：Times New Roman；
  - `a:cs`    = 复杂文种，跟 latin 一致。

角色按字号判定（默认 ≥30pt 算标题，对应令牌里的 54/33 两档；其余算正文），
所以字号阶梯一变，这里要同步改 `--title-min-pt`。

用法:
  python deck_fonts.py out/deck.pptx                       # 干跑：报标题/正文各改多少
  python deck_fonts.py out/deck.pptx --apply               # 写盘
  python deck_fonts.py out/deck.pptx --title-ea "SimHei" --body-ea "SimSun" \\
      --latin "Times New Roman" --title-min-pt 30 --apply

退出码: 0 正常；1 文件不存在或没有可改的 run；2 参数或依赖错误。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LATIN_DEFAULT = "Times New Roman"
TITLE_EA_DEFAULT = "黑体"       # 用中文族名：英文名 SimHei 在部分 Office 会被静默替换
BODY_EA_DEFAULT = "宋体"        # 同理，SimSun 会回退成宋体，但黑体标题会丢
TITLE_MIN_PT_DEFAULT = 30.0


def _rpr(run):
    """取 run 的 rPr；没有就建（rPr 必须是 a:r 的第一个子元素）。"""
    from pptx.oxml.ns import qn

    element = run._r
    rpr = element.find(qn("a:rPr"))
    if rpr is None:
        rpr = element.makeelement(qn("a:rPr"), {})
        element.insert(0, rpr)
    return rpr


def _ensure_typeface(rpr, tag: str, face: str) -> bool:
    from pptx.oxml.ns import qn

    node = rpr.find(qn(tag))
    if node is None:
        node = rpr.makeelement(qn(tag), {})
        rpr.append(node)
    changed = node.get("typeface") != face
    node.set("typeface", face)
    return changed


def role_of(run, title_min_pt: float = TITLE_MIN_PT_DEFAULT, shape=None) -> str:
    """分角色：先看字号；没写字号的看占位符类型（版式里的标题不写字号）。"""
    size = run.font.size
    if size is not None:
        return "title" if size.pt >= title_min_pt else "body"
    if shape is not None:
        try:
            if int(shape.placeholder_format.type) in (1, 3):   # TITLE / CENTER_TITLE
                return "title"
        except Exception:
            pass
    return "body"


def deal_fonts(path: Path, latin: str = LATIN_DEFAULT, title_ea: str = TITLE_EA_DEFAULT,
               body_ea: str = BODY_EA_DEFAULT, title_min_pt: float = TITLE_MIN_PT_DEFAULT,
               apply: bool = False) -> dict:
    from pptx import Presentation

    prs = Presentation(str(path))
    counts = {"title": 0, "body": 0}
    changed = 0
    for slide in prs.slides:
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if not run.text:
                        continue
                    role = role_of(run, title_min_pt, shape)
                    counts[role] += 1
                    rpr = _rpr(run)
                    ea = title_ea if role == "title" else body_ea
                    dirty = _ensure_typeface(rpr, "a:latin", latin)
                    dirty |= _ensure_typeface(rpr, "a:ea", ea)
                    dirty |= _ensure_typeface(rpr, "a:cs", latin)
                    if dirty:
                        changed += 1
    if apply and changed:
        prs.save(str(path))
    return {"path": str(path), "title": counts["title"], "body": counts["body"],
            "changed": changed, "applied": bool(apply), "latin": latin,
            "title_ea": title_ea, "body_ea": body_ea}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按字体规范写中英分工（默认干跑）")
    parser.add_argument("deck", help=".pptx")
    parser.add_argument("--latin", default=LATIN_DEFAULT, help="西文/数字字体（默认 %(default)s）")
    parser.add_argument("--title-ea", default=TITLE_EA_DEFAULT, help="标题中文字体（默认 %(default)s）")
    parser.add_argument("--body-ea", default=BODY_EA_DEFAULT, help="正文中文字体（默认 %(default)s）")
    parser.add_argument("--title-min-pt", type=float, default=TITLE_MIN_PT_DEFAULT,
                        help="≥ 该字号算标题（默认 %(default)s）")
    parser.add_argument("--apply", action="store_true", help="写盘（默认只报数）")
    args = parser.parse_args(argv)

    path = Path(args.deck)
    if not path.is_file():
        print(f"错误：找不到 {path}", file=sys.stderr)
        return 1
    try:
        result = deal_fonts(path, latin=args.latin, title_ea=args.title_ea,
                            body_ea=args.body_ea, title_min_pt=args.title_min_pt,
                            apply=args.apply)
    except ModuleNotFoundError as exc:
        print(f"错误：缺少依赖（{exc.name}）：pip install python-pptx", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI 边界
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    mark = "已写盘" if result["applied"] else "干跑（加 --apply 写盘）"
    total = result["title"] + result["body"]
    print(f"{result['path']}：{total} 个 run（标题 {result['title']} / 正文 {result['body']}），"
          f"{result['changed']} 个要改 —— {mark}")
    if result["changed"]:
        print(f"  中文：标题 {result['title_ea']}、正文 {result['body_ea']}；"
              f"西文/数字 {result['latin']}")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
