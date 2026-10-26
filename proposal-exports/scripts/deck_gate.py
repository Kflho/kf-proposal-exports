#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deck_gate.py — 页片交付闸门：一条命令跑完本仓检查 + 外部审计（装了才跑）。

为什么要有它：页片原来要跑三四个脚本（deck_check / text_check / 外部审计 / 预览），
漏跑一条就看不出问题；同一个阶段的检查封装成一条命令，才不会靠"记得"。

步骤（可按 --steps 选）:
  deck_check  本仓静态自检（几何/图片/备注/占位符/令牌）
  text_check  本仓文字自检（标题/句长/口播/禁用词）
  external    nature-paper2ppt 的 audit_pptx_quality.py（找不到就标 skipped，不算失败）
  preview     render_pptx_png.py 逐页导 PNG（需 PowerPoint + pywin32）

用法:
  python deck_gate.py out/deck.pptx
  python deck_gate.py out/deck.pptx --strict --require-notes
  python deck_gate.py out/deck.pptx --external-script <audit_pptx_quality.py>
  python deck_gate.py out/deck.pptx --steps deck_check,text_check --json

退出码: 0 全过（含 skipped）；1 有失败；2 参数/环境错误。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
DEFAULT_STEPS = ("fonts", "deck_check", "text_check", "critique", "external")

EXTERNAL_CANDIDATES = (
    Path.home() / ".dsh" / "skills" / "nature-paper2ppt" / "scripts" / "audit_pptx_quality.py",
    Path.home() / ".dsh" / "skills" / "nature-skills" / "skills" / "nature-paper2ppt"
    / "scripts" / "audit_pptx_quality.py",
    HERE.parents[1] / ".research" / "Yuan1z0825__nature-skills-mirror" / "skills"
    / "nature-paper2ppt" / "scripts" / "audit_pptx_quality.py",
)


def find_external_audit(explicit: str | None = None,
                        candidates: tuple[Path, ...] = EXTERNAL_CANDIDATES) -> Path | None:
    """按显式参数 → 环境变量 → 常见安装位置 找外部审计脚本；找不到返回 None。"""
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    env = os.environ.get("KF_DECK_AUDIT")
    if env and Path(env).is_file():
        return Path(env)
    for path in candidates:
        if path.is_file():
            return path
    return None


def _run(name: str, args: list[str], cwd: Path | None = None) -> dict:
    started = time.perf_counter()
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=str(cwd) if cwd else None)
    return {
        "name": name,
        "exit": proc.returncode,
        "seconds": round(time.perf_counter() - started, 2),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _tail(text: str, lines: int = 3) -> str:
    rows = [row for row in (text or "").strip().splitlines() if row.strip()]
    return " / ".join(rows[-lines:])


def build_steps(deck: Path, *, steps: tuple[str, ...], strict: bool, require_notes: bool,
                scale: str, external: Path | None, preview_dir: str | None) -> list[dict]:
    results: list[dict] = []
    if "fonts" in steps:
        # 字体规范（标题黑体 / 正文宋体 / 西文 Times New Roman）落实成 run 属性：
        # 幂等，重跑只会报 0 个要改。
        results.append(_run("fonts", [sys.executable, str(HERE / "deck_fonts.py"), str(deck),
                                      "--apply"]))
    if "deck_check" in steps:
        args = [sys.executable, str(HERE / "deck_check.py"), str(deck),
                "--title-ea", "黑体", "--body-ea", "宋体"]
        if strict:
            args.append("--strict")
        if require_notes:
            args.append("--require-notes")
        if scale:
            args += ["--scale", scale]
        results.append(_run("deck_check", args))
    if "text_check" in steps:
        results.append(_run("text_check",
                            [sys.executable, str(HERE / "text_check.py"), str(deck)]))
    if "critique" in steps:
        # 审美评估：机械法条 + 人工三项清单，报告写到 deck 旁边留痕
        md_path = deck.with_name(deck.stem + "_critique.md")
        results.append(_run("critique", [sys.executable, str(HERE / "deck_critique.py"),
                                          str(deck), "--md", str(md_path)]))
    if "external" in steps:
        if external is None:
            results.append({"name": "external", "exit": 0, "seconds": 0.0,
                            "stdout": "", "stderr": "", "skipped": True})
        else:
            results.append(_run("external", [sys.executable, str(external), str(deck),
                                             "--fail-on", "high"]))
    if "preview" in steps:
        out = preview_dir or str(deck.with_name(deck.stem + "_preview"))
        results.append(_run("preview",
                            [sys.executable, str(HERE / "render_pptx_png.py"), str(deck),
                             "--out", out]))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="页片交付闸门（本仓检查 + 外部审计）")
    parser.add_argument("deck", help="待验收的 .pptx")
    parser.add_argument("--steps", default=",".join(DEFAULT_STEPS),
                        help="要跑的步骤，逗号分隔（默认 %(default)s）")
    parser.add_argument("--strict", action="store_true", help="deck_check 严格模式")
    parser.add_argument("--require-notes", action="store_true", help="备注不足算 error")
    parser.add_argument("--scale", default="", help="字号档位（如 54,33,18,12,10）")
    parser.add_argument("--external-script", default=None,
                        help="外部审计脚本路径（默认自动找 nature-paper2ppt）")
    parser.add_argument("--preview-dir", default=None, help="preview 输出目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    deck = Path(args.deck)
    if not deck.is_file():
        print(f"错误：找不到 {deck}", file=sys.stderr)
        return 2

    steps = tuple(part.strip() for part in args.steps.split(",") if part.strip())
    unknown = [step for step in steps if step not in (*DEFAULT_STEPS, "preview")]
    if unknown:
        print(f"错误：未知步骤 {unknown}", file=sys.stderr)
        return 2

    external = find_external_audit(args.external_script)
    if args.external_script and external is None:
        print(f"错误：--external-script 指向的文件不存在：{args.external_script}", file=sys.stderr)
        return 2

    results = build_steps(deck, steps=steps, strict=args.strict,
                          require_notes=args.require_notes, scale=args.scale,
                          external=external, preview_dir=args.preview_dir)
    failed = [item for item in results if item["exit"] != 0]

    if args.json:
        print(json.dumps({"deck": str(deck), "external": str(external) if external else None,
                          "steps": results, "failed": len(failed)}, ensure_ascii=False, indent=1))
    else:
        print(f"页片闸门：{deck}")
        for item in results:
            if item.get("skipped"):
                print(f"  [skip] {item['name']:<11} 未找到外部审计脚本（装 nature-paper2ppt 后自动接上）")
                continue
            mark = "ok  " if item["exit"] == 0 else "FAIL"
            print(f"  [{mark}] {item['name']:<11} {item['seconds']:.2f}s  {_tail(item['stdout'])}")
            if item["exit"] != 0 and item["stderr"].strip():
                print(f"         {_tail(item['stderr'], 2)}")
        print(f"summary: {len(results) - len(failed)} 步通过 / {len(failed)} 步失败")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
