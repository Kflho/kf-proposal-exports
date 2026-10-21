#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成示例验证图：三档遮挡率下三种调度路线的定位可用率。

输出 1600x900 PNG，给 gen_deck.js 的 figureSlide 用。数据是演示值，不是实测；
替换成自己的实验数据时，改 GROUPS 和 VALUES 即可。
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 900
LEFT, RIGHT, TOP, BOTTOM = 150, 1520, 150, 740
GROUPS = [30, 40, 50]
ROUTES = ["随机调度", "贪心站簇", "本文"]
COLORS = ["#1E2761", "#6B7A90", "#E8A33D"]
VALUES = {
    30: [78, 88, 96],
    40: [72, 82, 89],
    50: [64, 74, 81],
}


def font(size: int, bold: bool = False):
    names = ["msyhbd.ttc", "msyh.ttc"] if bold else ["msyh.ttc", "simhei.ttf"]
    for name in names:
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def xy(value: float) -> int:
    return int(BOTTOM - (value / 100) * (BOTTOM - TOP))


def main() -> None:
    out = Path(__file__).resolve().parent / "figs" / "availability.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(image)

    f_tick, f_axis, f_legend, f_value = font(24), font(28), font(24, bold=True), font(22)

    # 横向网格与 y 轴刻度
    for value in range(0, 101, 20):
        y = xy(value)
        draw.line([(LEFT, y), (RIGHT, y)], fill="#E5EAF2", width=2)
        draw.text((LEFT - 60, y - 14), str(value), font=f_tick, fill="#6B7A90")
    draw.text((24, 70), "定位可用率（%）", font=f_axis, fill="#1F2937")
    draw.text((W // 2 - 100, 820), "遮挡率（%）", font=f_axis, fill="#1F2937")

    group_width = (RIGHT - LEFT) / len(GROUPS)
    bar_w, gap = 68, 14
    for index, group in enumerate(GROUPS):
        center = LEFT + group_width * (index + 0.5)
        start = center - (bar_w * len(ROUTES) + gap * (len(ROUTES) - 1)) / 2
        for order, value in enumerate(VALUES[group]):
            x = start + order * (bar_w + gap)
            draw.rectangle([x, xy(value), x + bar_w, BOTTOM], fill=COLORS[order])
            draw.text((x + 6, xy(value) - 30), f"{value}", font=f_value, fill="#1F2937")
        draw.text((center - 34, BOTTOM + 16), f"{group}%", font=f_tick, fill="#1F2937")

    # 图例
    legend_x, legend_y = RIGHT - 420, 36
    for order, label in enumerate(ROUTES):
        x = legend_x + order * 140
        draw.rectangle([x, legend_y, x + 26, legend_y + 18], fill=COLORS[order])
        draw.text((x + 34, legend_y - 4), label, font=f_tick, fill="#1F2937")

    image.save(out)
    print(out)


if __name__ == "__main__":
    main()
