"""svg_to_pdf.py 的测试：画布换算与失败路径不依赖外部程序，成功路径需要 Edge/Chrome。

期望值来自 SVG 规范（96dpi 换算）与脚本契约（文件不存在返回 2、--out 必填），不抄实现。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import svg_to_pdf  # noqa: E402


def test_canvas_px_converts_units():
    svg = '<svg width="160mm" height="90mm"></svg>'
    w, h = svg_to_pdf.canvas_px(svg)
    assert w == pytest.approx(160 * 96 / 25.4)
    assert h == pytest.approx(90 * 96 / 25.4)


def test_canvas_px_falls_back_to_viewbox():
    svg = '<svg viewBox="0 0 1600 900"></svg>'
    assert svg_to_pdf.canvas_px(svg) == (1600.0, 900.0)


def test_canvas_px_raises_without_size():
    with pytest.raises(ValueError):
        svg_to_pdf.canvas_px("<svg></svg>")


def test_main_returns_2_for_missing_file(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out.pdf"
    monkeypatch.setattr(sys, "argv", ["svg_to_pdf.py", str(tmp_path / "nope.svg"),
                                      "--out", str(out)])
    assert svg_to_pdf.main() == 2
    assert "文件不存在" in capsys.readouterr().out
    assert not out.exists()


@pytest.mark.skipif(svg_to_pdf.find_browser() is None, reason="没有 Edge/Chrome")
def test_main_prints_pdf_with_browser(tmp_path, monkeypatch):
    svg = tmp_path / "fig.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="160" height="90">'
        '<rect width="160" height="90" fill="#2F6FB0"/>'
        '<text x="12" y="48" font-size="16" fill="#fff">中文</text></svg>',
        encoding="utf-8",
    )
    out = tmp_path / "out.pdf"
    monkeypatch.setattr(sys, "argv", ["svg_to_pdf.py", str(svg), "--out", str(out)])
    assert svg_to_pdf.main() == 0
    assert out.stat().st_size > 0
    assert out.read_bytes()[:4] == b"%PDF"
