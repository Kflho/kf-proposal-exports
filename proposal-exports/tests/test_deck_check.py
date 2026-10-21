"""deck_check.py 的行为测试：判据来自设计记录（16:9、0.5in 安全边距、图片不拉伸、备注、占位符）。

期望值写死为规范值，不从实现里抄：
- 画布比例 16:9，容差 2%；
- 安全边距 0.5 in；
- 图片原生比例与摆放比例差 > 2% 视为拉伸；
- 每页备注 ≥ 10 字（可选强校验）；
- `TODO/XXX/lorem` 之类占位符一律报错。
"""
import sys
from pathlib import Path

import pytest
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import deck_check  # noqa: E402

W, H = 13.333, 7.5


def new_deck(ratio=16 / 9):
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(W / ratio)
    return prs


def add_text(slide, text, x, y, w, h, size=20):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    box.text_frame.text = text
    for run in box.text_frame.paragraphs[0].runs:
        run.font.size = Pt(size)
    return box


def test_clean_deck_passes(tmp_path):
    prs = new_deck()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, "卫星运动的状态反馈极点配置", 0.8, 0.6, 8, 1.0, size=32)
    slide.notes_slide.notes_text_frame.text = "开场先讲模型，再讲能控性。"
    path = tmp_path / "ok.pptx"
    prs.save(path)

    report = deck_check.check_deck(path)
    assert report.errors == []
    assert report.ok


def test_non_widescreen_is_error(tmp_path):
    prs = new_deck(ratio=4 / 3)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, "标题", 0.8, 0.6, 6, 0.8)
    slide.notes_slide.notes_text_frame.text = "备注内容足够长。"
    path = tmp_path / "p43.pptx"
    prs.save(path)

    report = deck_check.check_deck(path)
    assert any(i.code == "aspect-ratio" for i in report.errors)
    assert not report.ok


def test_shape_outside_safe_margin_is_error(tmp_path):
    prs = new_deck()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, "贴边的文字", 0.1, 1.0, 4, 0.6)
    slide.notes_slide.notes_text_frame.text = "备注内容足够长。"
    path = tmp_path / "margin.pptx"
    prs.save(path)

    report = deck_check.check_deck(path)
    assert any(i.code == "margin" for i in report.errors)


def test_stretched_picture_is_error(tmp_path):
    img = Image.new("RGB", (200, 100), "white")   # 原生 2:1
    img_path = tmp_path / "fig.png"
    img.save(img_path)

    prs = new_deck()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_picture(str(img_path), Inches(1), Inches(1.5), Inches(3), Inches(3))  # 1:1
    slide.notes_slide.notes_text_frame.text = "备注内容足够长。"
    path = tmp_path / "stretch.pptx"
    prs.save(path)

    report = deck_check.check_deck(path)
    assert any(i.code == "image-stretch" for i in report.errors)


def test_picture_with_matching_aspect_passes(tmp_path):
    img = Image.new("RGB", (200, 100), "white")
    img_path = tmp_path / "fig.png"
    img.save(img_path)

    prs = new_deck()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_picture(str(img_path), Inches(1), Inches(1.5), Inches(3), Inches(1.5))
    slide.notes_slide.notes_text_frame.text = "备注内容足够长。"
    path = tmp_path / "okpic.pptx"
    prs.save(path)

    report = deck_check.check_deck(path)
    assert not [i for i in report.errors if i.code == "image-stretch"]


def test_placeholder_text_is_error(tmp_path):
    prs = new_deck()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, "TODO 这里补结论", 0.8, 2.0, 8, 0.8)
    slide.notes_slide.notes_text_frame.text = "备注内容足够长。"
    path = tmp_path / "todo.pptx"
    prs.save(path)

    report = deck_check.check_deck(path)
    assert any(i.code == "placeholder" for i in report.errors)


def test_notes_are_warning_by_default_and_error_when_required(tmp_path):
    prs = new_deck()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_text(slide, "没有口播的一页", 0.8, 2.0, 8, 0.8)
    path = tmp_path / "nonotes.pptx"
    prs.save(path)

    soft = deck_check.check_deck(path)
    assert any(i.code == "notes" for i in soft.warnings)
    assert not any(i.code == "notes" for i in soft.errors)

    hard = deck_check.check_deck(path, require_notes=True)
    assert any(i.code == "notes" for i in hard.errors)


def test_text_overflow_is_warning_and_strict_makes_it_error(tmp_path):
    prs = new_deck()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    long_text = "这是一段明显放不下的中文说明" * 6            # 96 字
    add_text(slide, long_text, 1.0, 2.0, 2.0, 0.5, size=20)   # 2in 宽、0.5in 高
    slide.notes_slide.notes_text_frame.text = "备注内容足够长。"
    path = tmp_path / "overflow.pptx"
    prs.save(path)

    soft = deck_check.check_deck(path)
    assert any(i.code == "text-overflow" for i in soft.warnings)
    assert not any(i.code == "text-overflow" for i in soft.errors)

    hard = deck_check.check_deck(path, strict=True)
    assert any(i.code == "text-overflow" for i in hard.errors)


@pytest.mark.parametrize("code", ["aspect-ratio", "margin", "image-stretch", "placeholder"])
def test_json_report_contains_issue_codes(tmp_path, code):
    """CLI 的 --json 输出必须带 code 字段（供 CI/agent 解析）。"""
    prs = new_deck(ratio=4 / 3 if code == "aspect-ratio" else 16 / 9)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    if code == "margin":
        add_text(slide, "贴边", 0.1, 1.0, 4, 0.6)
    elif code == "placeholder":
        add_text(slide, "TODO 补内容", 1.0, 1.0, 4, 0.6)
    else:
        add_text(slide, "标题", 0.8, 0.6, 6, 0.8)
    if code == "image-stretch":
        img = Image.new("RGB", (200, 100), "white")
        p = tmp_path / "f.png"
        img.save(p)
        slide.shapes.add_picture(str(p), Inches(1), Inches(1.5), Inches(3), Inches(3))
    slide.notes_slide.notes_text_frame.text = "备注内容足够长。"
    path = tmp_path / f"{code}.pptx"
    prs.save(path)

    report = deck_check.check_deck(path)
    payload = deck_check.report_to_dict(report)
    assert any(i["code"] == code for i in payload["errors"])
