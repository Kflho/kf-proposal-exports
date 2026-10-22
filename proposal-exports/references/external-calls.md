# 外部调用清单

> 只写命令与判读，不放第三方文档。先 `export PYTHONIOENCODING=utf-8`（Windows 控制台默认 GBK）。

## 1 数据图

交给 `scipilot-figure-skill`（选型 + 出图）或 `nature-figure`（投稿级 / 多面板）。
本 skill 只管结构示意图（框架 / 路线 / 计划矩阵），不画曲线柱状。

## 2 交付前审计（权威门禁）

```bash
python scripts/svg_to_pdf.py 图1.svg --out out/图1.pdf

python "$USERPROFILE/.dsh/skills/nature-figure/scripts/audit_figure_collisions.py" \
    out/图1.pdf --json-out out/图1.collision.json

python "$USERPROFILE/.dsh/skills/nature-figure/scripts/audit_pdf_text.py" out/图1.pdf --min-pt 6

python "$USERPROFILE/.dsh/skills/nature-figure/scripts/audit_svg_schematic.py" 图1.svg \
    --max-width-mm 339 --min-pt 6 --max-pt 34      # 16:9 画布用这组参数
```

判读：`FIX BEFORE DELIVERY`（exit 1）必须改；`REVIEW REQUIRED` 逐条目视写理由；
`NOT AUDITABLE`（exit 2）不算通过。

## 3 原生 PPT / AI（评审要改字时才用）

```bash
# SVG → 原生形状 + 原生文本框；需 Windows + 桌面 PowerPoint
python "$USERPROFILE/.dsh/tools/svg-native-pptx/powerpoint_native.py" \
    --svg 图1.svg --output out/图1-ppt

# SVG → 原生 .ai；需本机 Illustrator（未装则不可用）
python "$USERPROFILE/.dsh/tools/svg-native-pptx/illustrator_native.py" \
    --svg 图1.svg --output out/图1-ai
```

产物：`editable.pptx` + `display/powerpoint.png`（PowerPoint 实际渲染）+ `display/index.html`（对照页）。
验收看两处：`report.json` 的 `mode == native_paths` 且 `raster_pictures == 0`；对照页目视。

坑：

- 文本里有**全角空格 U+3000** → 会被拆成逐字文本框（改用普通空格或拆成两个 `<text>`）；
- 输出目录**必须不存在**，否则报 `WinError 183`；
- PowerPoint 换行与浏览器不同，SVG 不压线的段落进 PPT 可能变两行——以实际预览为准。

第三方工具装在 `~/.dsh/tools/svg-native-pptx/`（MIT，未修改，来源见该目录 `SOURCE.md`），
不在本 skill 包内。
