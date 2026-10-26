# 按 PPT 模板出片：取令牌 + 套版式

> 两类来源要分清：**模板**（`.pptx`，含主题、母版、版式）决定"长什么样"；**素材**（图、公式、表格）
> 决定"填什么"。本文件管模板这条路；素材只做"按真实比例入槽 + 换图"。

## 两条路线

| 路线 | 做法 | 适用 |
| --- | --- | --- |
| **套版式**（默认） | `slide_layouts` 里挑一个版式 → 新页 → 按占位符填标题/正文/图片 | 模板版式规范、占位符齐全 |
| **复制页** | 复制模板某页的形状 → 替换文字/图片 | 模板页是手工排的、没有可用占位符 |

## 第 1 层：抽令牌

```bash
python scripts/deck_template.py 模板.pptx --list            # 有什么版式、每页什么形状
python scripts/deck_template.py 模板.pptx --tokens tokens.json
```

`tokens.json` 给出：画布尺寸、主题色（dk1/lt1/dk2/lt2/accent1–6）、主题字体（major/minor 的
latin 与 ea）、每个版式的占位符（类型 + idx + 坐标）、每页观察到的字号/字体/颜色。

用法：把主题色映射成生成器的强调色/主色，把 major/minor 字体写进 `deck_fonts.py` 的参数，
把观察到的字号收成 3–5 档。**别逐像素复刻版式**——坐标系和占位符由模板负责。

## 第 2 层：套版式生成

```bash
python scripts/deck_template.py 模板.pptx --plan plan.json --out out/deck.pptx
```

```jsonc
{"pages": [
  {"layout": "Title Slide", "title": "结论式标题", "subtitle": "场景 · 指标 · 口径",
   "notes": "口播"},
  {"layout": 1, "title": "页标题", "body": ["要点一", "要点二"], "notes": "口播"},
  {"copy": 2, "text": {"模板里的原句": "新句"}, "images": {"0": "figs/a.png"}}
]}
```

- `layout`：版式名或序号；`title` 走 `slide.shapes.title`，`body` 接受 body/object/text 类占位符；
- `copy`：复制第 N 页（1 起）的形状，再按**原文匹配**替换文字、按图片序号换图；
- 模板里的样例页会被清空，最终页序完全由 plan 决定；
- 返回 0 表示全部解析；有未命中的占位符/文字/图片时返回 1 并逐条列出。

生成后固定走：

```bash
python scripts/deck_fonts.py out/deck.pptx --apply        # 标题黑体 / 正文宋体 / 西文 TNR
python scripts/deck_gate.py out/deck.pptx --strict --require-notes --margin 0.3
python scripts/render_pptx_png.py out/deck.pptx --out out/preview
```

## 三条硬经验（都是实测）

1. **中文字体用中文族名**：`a:ea` 写 `SimHei`/`SimSun` 在部分 Office 里不解析，会静默回退成宋体
   （标题黑体直接丢）。写 `黑体` / `宋体`。`deck_fonts.py` 默认已改。
2. **外部模板的边距不要套 0.5in**：模板标题常在 0.3in；`deck_check --margin 0.3` 按模板来。
3. **复制页要先深拷再清空**：清掉样例页后源页就没了；`deck_template.py` 在清空前把源形状复制到内存。

## 限制

- 模板的 SmartArt、原生图表、动画只能保留形状级别，文字替换不保证；
- 图片占位符用 `insert_picture` 会裁切填满，比例与占位符不一致时先看预览；
- 抽令牌不做主题色"语义映射"，哪一个是强调色要人判断（一般 `accent1`）；
- 版式空位由模板决定，本工具不自动排版；素材多时先定"每页一个主张"再填。
