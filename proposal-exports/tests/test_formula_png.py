"""formula_png.py 的单元测试：期望值来自设计记录与 PNG 语义，不抄实现。

- LaTeX 模板必须自带 `standalone`（裁到内容）与正文包裹 `$...$`；
- 白边裁切按"最暗像素"的包围盒（PNG 原点左上，right/bottom 为开区间）；
- 透明化只处理近白像素，深色像素保持不透明。
"""
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import formula_png  # noqa: E402


def test_latex_source_is_standalone_and_wraps_math():
    src = formula_png.latex_source(r"a^2+b^2", border=2)
    assert r"\documentclass[border=2pt]{standalone}" in src
    assert "$a^2+b^2$" in src
    assert r"\usepackage{amsmath}" in src


def test_latex_source_can_drop_font_package():
    src = formula_png.latex_source("x", fontpack="")
    assert "newtxtext" not in src


def test_content_bbox_returns_tight_box():
    img = Image.new("RGB", (60, 40), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 10, 29, 14], fill="black")   # 20..29, 10..14 闭区间
    bbox = formula_png.content_bbox(img, threshold=245)
    assert bbox == (20, 10, 30, 15)                   # right/bottom 开区间


def test_content_bbox_none_for_blank():
    assert formula_png.content_bbox(Image.new("RGB", (20, 20), "white")) is None


def test_with_alpha_makes_white_transparent_and_keeps_ink():
    img = Image.new("RGB", (4, 4), "white")
    ImageDraw.Draw(img).point((1, 1), fill="black")
    out = formula_png.with_alpha(img, threshold=245)
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0               # 白 → 透明
    assert out.getpixel((1, 1))[3] == 255             # 黑 → 不透明


@pytest.mark.skipif(not formula_png.toolchain_available()[0], reason="没有 pdflatex/pdftoppm")
def test_render_writes_png_and_sizes(tmp_path):
    spec = tmp_path / "formulas.json"
    spec.write_text('{"eq": "a^2+b^2=c^2"}', encoding="utf-8")
    sizes = formula_png.render_spec(spec, tmp_path / "out", dpi=200, alpha=True)
    png = tmp_path / "out" / "eq.png"
    assert png.is_file()
    assert sizes["eq"][0] > 0 and sizes["eq"][1] > 0
    assert Image.open(png).mode == "RGBA"
