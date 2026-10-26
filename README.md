# kf-proposal-exports

中文技术申报书 / 技术方案 / 答辩材料的**配图 + 页片 + 文字**交付规范（skill：`kf-proposal-exports`，目录 `proposal-exports/`）。

> 当前状态：v2.0.2。图流程可用（模板优先，D2 备选，Graphviz 退役）；页片流程可用（Python + Node + PowerPoint）；
> 文字检查可用。`pytest` 82 项（13 个模块）全绿。

## 快速开始

```bash
# ---- 配图：拷模板 → 改文案 → 自检 → 目视 ----
cp proposal-exports/assets/template.svg 图1.svg
python proposal-exports/scripts/render_svg.py 图1.svg --png out/图1.png
python proposal-exports/scripts/check_overlap.py 图1.svg
python proposal-exports/scripts/check_symbols.py 图1.svg

# ---- 页片：公式 → 生成 → 闸门（字体→静态→文字→外部审计）→ 预览 ----
cd proposal-exports
npm i pptxgenjs          # 一次
python scripts/formula_png.py assets/deck/formulas.example.json --out assets/deck/formulas
node assets/deck/gen_deck.js --out out/deck.pptx
python scripts/deck_gate.py out/deck.pptx --strict --require-notes --scale 54,33,18,12
python scripts/render_pptx_png.py out/deck.pptx --out out/preview
```

## 安装与依赖

| 能力 | 依赖 | 说明 |
| --- | --- | --- |
| 配图 | Python 3.10+（标准库） + Edge/Chrome（渲染 PNG） | 模板与检查脚本无第三方依赖 |
| 关系图（可选） | D2：`winget install Terrastruct.D2` | 仅用于临时关系图，不作为申报版式图 |
| 存量图（可选） | Graphviz：`winget install Graphviz.Graphviz` | 只用于改造旧 `.dot` 图 |
| 公式 | TeX Live（`pdflatex`、`pdftoppm`）+ `pip install pillow` | 输出透明 PNG + `sizes.json` |
| 页片生成 | Node 18+ + `npm i pptxgenjs` | 模板 `assets/deck/gen_deck.js` |
| 页片检查 | `pip install python-pptx pillow` | `deck_check.py`、`text_check.py` |
| 页片预览 | Windows + PowerPoint + `pip install pywin32` | 无 Office 时用官方 `pptx` skill 的 soffice 路线 |

## 用法（四个场景）

**1. 画申报结构图**：三类版式（总体框架 / 技术路线 / 研究计划矩阵）见 `references/figure-types.md`。
起手拷 `assets/template.svg`，只改文案与坐标；画完跑 5 个检查脚本，再渲染看图。
版式与文字规则在 `SKILL.md` 的硬规则 1–15。

**2. 把讲稿做成 PPT**：先写页计划（每页一句结论 + 证据 + 口播），再套 `assets/deck/gen_deck.js` 的
版式函数；公式走 `formula_png.py`；生成后跑 `deck_check.py` + `text_check.py` + 预览。
细节见 `references/ppt-deck.md`，文案规则见 `references/text-quality.md`。
按任务书验收的课程/实验汇报（标题切研究目标、结论放下方结论行）见硬规则 16 的例外。

**3. 改已有页片**：换图用 `scripts/update_pptx_images.py`（版式逐字节不动）；
图片被拉伸用 `scripts/fit_pptx_frames.py`；结构性编辑（加页/删页/改 XML）走官方 `pptx` skill。

**4. 交付前转换与审计**：`scripts/svg_to_pdf.py` 把 SVG 转 PDF（Edge 打印，供外部碰撞/字号审计读真实几何）；
评审要能改字时，用 `%USERPROFILE%\.dsh\tools\svg-native-pptx\` 把 SVG 转原生 PPT（形状 + 文本框，独立安装）。

## 输出

- 图：`*.svg`（自包含，可进 PPT/WPS）+ `out/*.png`（目视/汇报用）；
- 公式：`out/<名字>.png`（默认透明）+ `out/sizes.json`；
- 页片：`*.pptx`（可编辑，含每页 speaker notes）+ `preview/slide-XX.png`；
- 检查报告：`deck_check.py` / `text_check.py` 的终端输出或 `--json`。

脚本不覆盖输入文件；`update_pptx_images.py` 只有加 `--apply` 才写盘。

## 验证

```bash
cd proposal-exports
python -m pytest -q          # 82 项（13 个模块）：公式/页片检查/文字检查/字体/闸门/回灌/结构回归
```

成功判据：`pytest` 全绿；`deck_gate.py` 0 error（字体 → 静态 → 文字 → 外部审计）；预览逐页目视通过。

## 已知限制

- 页片预览依赖 Windows + PowerPoint；其他平台需改用官方 `pptx` skill 的 LibreOffice 路线；
- `deck_check.py` 的文字溢出是**估算**（Pillow 量字宽），不是 PowerPoint 的真实排版，`--strict` 下可能误报；
- 文字检查只抓高置信度问题（禁用词、标题像话题、句子过长），**不能判断标题有没有洞察**；
- D2 的样式语法随版本变化（本轮遇到过 `font-family`/`stroke-width` 报错），升级后需重测模板；
- 图流程的"手写 SVG"仍要用坐标改版，复杂关系图（>15 节点）建议拆图而不是硬塞。

## 文档

| 文档 | 内容 |
| --- | --- |
| [`proposal-exports/SKILL.md`](proposal-exports/SKILL.md) | 入口：触发、两条工作流、硬规则、脚本表 |
| [`references/figure-types.md`](proposal-exports/references/figure-types.md) | 三类图版式、连线规范、设计系统 |
| [`references/ppt-deck.md`](proposal-exports/references/ppt-deck.md) | 页片五步流程、令牌、五条本地纪律、质检 |
| [`references/external-deck.md`](proposal-exports/references/external-deck.md) | 页片外部能力：何时调 `nature-paper2ppt` / `academic-ppt`、调用契约、回退 |
| [`references/deck-generator.md`](proposal-exports/references/deck-generator.md) | 页片生成器契约与回灌五步：pptx 改动同步回代码 |
| [`references/text-quality.md`](proposal-exports/references/text-quality.md) | action title、禁用词、句式与口播规范 |
| [`references/design-notes/`](proposal-exports/references/design-notes/) | 设计记录：PPT 接入、出图引擎选型（含视觉调研协议） |
| [`references/case-notes.md`](proposal-exports/references/case-notes.md) | 真实返工复盘与外部 skill 调研 |

## 外部 skill 协作（能调用就不自研）

| 需求 | 调用 |
| --- | --- |
| 数据图（曲线/柱状/分布/多面板） | `scipilot-figure-skill`（选图顾问 + 出图）或 `nature-figure` |
| 交付前碰撞审计 / 最终字号审计 | `nature-figure` 的 `audit_figure_collisions.py`、`audit_pdf_text.py` |
| SVG 画布与有效字号 | `nature-figure` 的 `audit_svg_schematic.py`（16:9 传 `--max-width-mm 339`） |
| 评审要改字：SVG → 原生 PPT / AI | `%USERPROFILE%\.dsh\tools\svg-native-pptx\`（独立安装，不在本仓库） |
| 「看着好看、不像模型默认审美」的视觉决策 | `taste-skill`（**完整安装**，入口 `~/.dsh/skills/taste-skill/SKILL.md`；要 node + 浏览器） |

本 skill 只保留外部没有的部分：连线端点贴合、视觉语言一致性、禁用符号、框间距、
中文指标表述、图↔文一致、PPT 换图。命令与判读见 `proposal-exports/references/external-calls.md`。

## 许可

见 [`LICENSE.txt`](LICENSE.txt)。
