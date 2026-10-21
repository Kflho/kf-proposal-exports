#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""formula_png.py — LaTeX 公式 → 裁白边的 PNG（默认透明），顺带写 sizes.json。

页片里的公式不做 PPT 原生公式（中文/矩阵容易走样），统一走这条流水线：
    formulas.json（{名字: LaTeX}）→ pdflatex → pdftoppm(400dpi) → 裁白边 → 透明 PNG
    输出目录里同时写 sizes.json（像素宽高），gen_deck.js 用它算图片框。

用法:
  python formula_png.py formulas.json --out out/
  python formula_png.py formulas.json --out out/ --dpi 400 --no-alpha
  python formula_png.py --tex-string "a^2+b^2" --name eq --out out/

依赖:
  - pdflatex / pdftoppm：TeX Live（Windows 装机自带）或 Poppler；
  - Pillow：裁白边与透明化（pip install pillow）。
  缺依赖直接报错并给安装命令，不静默降级。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # Windows 控制台默认 GBK
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEFAULT_FONTPACK = "newtxtext,newtxmath"

TEX_TEMPLATE = r"""\documentclass[border=%dpt]{standalone}
\usepackage{amsmath}
%s\pagestyle{empty}
\begin{document}
$%s$
\end{document}
"""


def toolchain_available() -> tuple[bool, str]:
    """返回 (是否齐备, 缺失说明)。"""
    missing = [name for name in ("pdflatex", "pdftoppm") if shutil.which(name) is None]
    if missing:
        return False, "缺少 " + "、".join(missing) + "（装 TeX Live 或 Poppler）"
    try:
        import PIL  # noqa: F401
    except ImportError:
        return False, "缺少 pillow（pip install pillow）"
    return True, ""


def latex_source(body: str, border: int = 2, fontpack: str = DEFAULT_FONTPACK) -> str:
    """拼出 standalone 文档；body 是 `$...$` 里面的内容。"""
    use = f"\\usepackage{{{fontpack}}}\n" if fontpack else ""
    return TEX_TEMPLATE % (border, use, body)


def content_bbox(img, threshold: int = 245):
    """非白内容的最小外接矩形（left, upper, right, lower，右下开区间）；全白返回 None。"""
    gray = img.convert("L")
    mask = gray.point(lambda v: 0 if v > threshold else 255)
    return mask.getbbox()


def with_alpha(img, threshold: int = 245):
    """近白像素变透明；深色像素保持不透明（RGB 不动，只改 alpha）。"""
    rgba = img.convert("RGBA")
    px = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, _ = px[x, y]
            if r > threshold and g > threshold and b > threshold:
                px[x, y] = (r, g, b, 0)
    return rgba


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace")


def render_one(name: str, body: str, out_dir: Path, dpi: int = 400,
               alpha: bool = True, keep_tex: bool = False) -> tuple[int, int]:
    """渲染一条公式，返回 PNG 的像素宽高。"""
    from PIL import Image

    with tempfile.TemporaryDirectory(prefix="formula_") as tmp:
        work = Path(tmp)
        (work / f"{name}.tex").write_text(latex_source(body), encoding="utf-8")
        proc = _run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"], work)
        if proc.returncode != 0:
            tail = "\n".join((proc.stdout or "").splitlines()[-15:])
            raise RuntimeError(f"pdflatex 失败（{name}）：\n{tail}")
        proc = _run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile",
                     f"{name}.pdf", name], work)
        if proc.returncode != 0:
            raise RuntimeError(f"pdftoppm 失败（{name}）：{proc.stderr.strip()}")

        src = work / f"{name}.png"
        img = Image.open(src).convert("RGB")
        box = content_bbox(img)
        if box is None:
            raise RuntimeError(f"公式渲染结果全白（{name}）：检查 LaTeX 是否写错")
        img = img.crop(box)
        img = with_alpha(img) if alpha else img
        out_dir.mkdir(parents=True, exist_ok=True)
        img.save(out_dir / f"{name}.png")

        if keep_tex:
            (out_dir / f"{name}.tex").write_text(latex_source(body), encoding="utf-8")
        return img.size


def render_spec(spec_path: Path, out_dir: Path, dpi: int = 400, alpha: bool = True,
                keep_tex: bool = False) -> dict[str, list[int]]:
    """读 {name: latex} 的 JSON，逐条渲染，写 sizes.json，返回尺寸表。"""
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or not spec:
        raise ValueError("formulas.json 应是非空对象：{名字: LaTeX}")
    sizes: dict[str, list[int]] = {}
    for name, body in spec.items():
        w, h = render_one(name, body, out_dir, dpi=dpi, alpha=alpha, keep_tex=keep_tex)
        sizes[name] = [w, h]
        print(f"  {name}.png  {w}x{h}")
    (out_dir / "sizes.json").write_text(
        json.dumps(sizes, indent=1, ensure_ascii=False), encoding="utf-8")
    return sizes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LaTeX 公式 → 裁白边的透明 PNG")
    parser.add_argument("spec", nargs="?", help="{名字: LaTeX} 的 JSON 文件")
    parser.add_argument("--tex-string", help="单条公式（与 --name 配合，替代 spec）")
    parser.add_argument("--name", default="formula", help="单条公式的名字")
    parser.add_argument("--out", default="out", help="输出目录（默认 out/）")
    parser.add_argument("--dpi", type=int, default=400, help="渲染 dpi（默认 400）")
    parser.add_argument("--no-alpha", action="store_true", help="保留白底，不做透明")
    parser.add_argument("--keep-tex", action="store_true", help="把 .tex 一并留在输出目录")
    args = parser.parse_args(argv)

    ok, why = toolchain_available()
    if not ok:
        print(f"错误：{why}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    try:
        if args.tex_string:
            w, h = render_one(args.name, args.tex_string, out_dir, dpi=args.dpi,
                              alpha=not args.no_alpha, keep_tex=args.keep_tex)
            sizes = {args.name: [w, h]}
            (out_dir / "sizes.json").write_text(
                json.dumps(sizes, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"  {args.name}.png  {w}x{h}")
            return 0
        if not args.spec:
            parser.error("需要 spec 文件，或 --tex-string")
        sizes = render_spec(Path(args.spec), out_dir, dpi=args.dpi,
                            alpha=not args.no_alpha, keep_tex=args.keep_tex)
        print(f"共 {len(sizes)} 条 → {out_dir}/（含 sizes.json）")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI 边界统一报错
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
