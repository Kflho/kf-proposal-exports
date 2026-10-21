# 设计记录：出图引擎选型（模板 / D2 / Graphviz / TikZ / Mermaid）

> 日期：2026-10　｜　触发：用户反馈"Graphviz 产出的图没法用、很难看"，且本机 `dot` 未安装导致
> 原有首选路径跑不通（v2.0.0 前）。本文件是重做选型的证据与决策，含"视觉方案调研"的对照协议。

## 问题

申报材料三类图（总体框架 / 技术路线 / 研究计划矩阵）要求：

1. 成品是 **16:9**，能直接进页片或申报书；
2. 中文断行、字号、留白可控，**改文案不掉版**；
3. 能被现有 5 个 SVG 检查脚本（越界/压线/贴合/一致性/间距）校验；
4. 本机开箱可用（不因缺 `dot` 直接跑不通）。

原 skill 把 Graphviz 当首选，但：本机未装 `dot`（流程直接失败）；即使装上，输出比例与留白也不受控。

## 证据

| # | 来源 | 主张 | 条件/本机验证 | 结论 |
|---|---|---|---|---|
| E1 | [Diagrams as Code in 2026（dev.to）](https://dev.to/levi_liu/diagrams-as-code-in-2026-mermaid-plantuml-d2-excalidraw-when-to-use-what-4mo9) | Graphviz "ergonomics haven't kept pace"，不作为 2026 首选；D2 布局质量最佳（ELK）；Mermaid 默认输出拥挤；Excalidraw 只适合草图 | 二手（对比文章），与 E2 实测一致 | 采信方向 |
| E2 | 本机实测（同一份三层流程文案，2026-10） | Graphviz：`dot -Tpng` 出 **611×1607**（竖条）；D2 `direction: down`：1964×3552（大量留白）；D2 `direction: right`：**2893×468**（横幅）；`assets/template.svg`：**1600×900 成品** | 一手（本机渲染，图表在 `.tmp/diag-bench/`） | 自动布局不适合申报版式 |
| E3 | 本 skill 现有脚本 | 5 个检查脚本基于 SVG 坐标（越界/压线/端点/一致性/间距），模板与 D2 的 SVG 都能查 | 一手（代码） | 模板与 D2 可共用检查 |
| E4 | 官方 `pptx` skill / 本文档 | 页片只要 16:9 图；图片按真实比例入槽 | — | 比例是硬约束 |

## 对照协议（补 kf research 的空白）

> `kf-personal-development/references/research.md` 的证据卡模板适合"有没有成熟方案/能不能用"，
> 但对**视觉质量**不够用：来源写得再对，也无法证明"这张图好看/能进页片"。这里加一段可复用的协议。

1. **同一份文案**分别用候选引擎出图（不许换文案，否则比较无效）；
2. **固定画布**：目标 1600×900（16:9）；超出的按 `render_svg.py --size` 缩放，记录缩放后最小字号；
3. **四个可观察维度**打分（1–5）：
   - 比例与留白：是否接近 16:9、空白是否可控；
   - 中文排版：断行、字距、行首标点；
   - 信息层级：分组/层级是否一眼看出；
   - 可检查性：能否跑 5 个脚本、改文案是否只改文本；
4. **看渲染图**（不是看源码）；评分表与截图一起留档；
5. **决策 + 失败判据**：写下"什么情况下换方案"。

本轮的评分（同一内容，见 `.tmp/diag-bench/`）：

| 候选 | 比例/留白 | 中文排版 | 层级 | 可检查/改版 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 模板（`assets/template.svg`） | 5（1600×900） | 5（手控） | 5（版式固定） | 5（坐标可改、5 脚本全过） | **默认** |
| D2 | 2（竖条/横幅） | 3（字体回退不可控） | 4（ELK 分组好） | 4（SVG 可查，改版重跑） | 备选（关系图） |
| Graphviz | 2（611×1607） | 3（中文靠 fontname） | 3（cluster 尚可） | 4 | 退役（仅存量图） |

## 方案

- **三类申报图**：`assets/template.svg` 起手手改，或 `layout_flow.py` 从内容生成（16:9、可检查）；
- **TeX 用户需要精确版式**：可用 TikZ（见文末补测），不作为默认，也不进 5 个 SVG 检查链；
- **临时关系图**（≤15 节点、不要求像素级）：D2 `--layout elk --theme 0`，导出 SVG 后
  `render_svg.py --size 1600x900` 缩放并跑检查；
- **Graphviz**：保留脚本与文档，只用于改造存量 `.dot` 图，不再作为新图起点；
- **Mermaid**：只用于 README/文档里的流程草图，不进页片；
- `SKILL.md` 的"出图方式"、脚本表、硬规则 19 同步改。

## 假设

1. H1：模板路线能覆盖三类申报图 90% 的版面（证据：`template.svg` 已是成品，`layout_flow.py` 可生成同类版式）；
2. H2：D2 只用于关系图，用户接受"缩放后最小字号可能偏小"的代价（证据：E1 与 E2 的比例问题）；
3. H3：检查脚本对 D2 输出同样有效（证据：两者都输出标准 SVG，坐标可用）。

## 指标

| 指标 | 方法 | 目标 |
| --- | --- | --- |
| 16:9 达标 | 渲染后像素比例 | 模板 1.778±0.01；D2 缩放后同 |
| 可检查性 | 对输出跑 5 个检查脚本 | 模板 0 命中；D2 允许文字类 warning，无 error |
| 改版成本 | 改一句文案后重渲染 | 模板只改 `<text>`；D2 只改 `.d2` 文本 |

## 失败判据

- 若模板表达不了某类图（如 >15 节点的复杂关系网），且 D2 缩放后最小字号 < 9pt 或留白 > 50%，
  则该图改用人工 SVG + 检查脚本，不再依赖自动布局；
- 若用户仍认为模板图"难看"，回到设计令牌（`style-tokens.md`）重评，不盲目换引擎；
- 若 D2 输出无法被 `check_overlap.py` 解析（XML 结构异常），D2 降为"草图工具"，不进交付。

## 风险与回退

| 风险 | 影响 | 回退 |
| --- | --- | --- |
| D2 版本升级改样式语法（本轮已遇到 `font-family`/`stroke-width` 报错） | 图重建失败 | 固定 D2 版本或改回模板手绘 |
| Graphviz 已装但无人维护 | 概念混淆 | 文档标注"退役"，脚本保留 |
| 模板改动坐标出错 | 版式崩 | 检查脚本 + 目视，模板坐标取整 |

## 附：kf-personal-development 调研建议的适用性

| 环节 | 是否够用 | 说明 |
| --- | --- | --- |
| 问题卡（现状/约束/完成判据） | 够 | 本文件"问题"一节直接沿用 |
| 来源优先级（一手/二手/三手） | 够 | E1 二手仅作方向，E2 一手定结论 |
| 证据卡模板 | 够 | 但需加"本机渲染结果"一栏，见 E2 |
| 停止条件（四问） | 够 | 已能回答"有没有/为什么不用/前提是否成立/最坏情况" |
| **视觉/版式类调研** | **不够** | 缺"同内容对照渲染 + 评分维度 + 判据"，本文件"对照协议"即为补丁；建议下次给 kf 的 research.md 加一节"视觉方案调研" |

## 2026-10-21 补测：TikZ / Mermaid / PlantUML / Excalidraw / draw.io

上一轮只比了模板、D2、Graphviz；本轮补 TikZ 和 Mermaid，并确认另外两条路线为什么没进对照。

### 候选与可用性

| 引擎 | 本机状态 | 版本/来源 | 安装成本 | 进对照 |
| --- | --- | --- | --- | --- |
| 模板 + layout_flow | 可用 | 本 skill 自带 | 0 | 是（基线） |
| TikZ | 可用 | TeX Live 2026，xelatex + ctex + tikz | 需 TeX Live | 是 |
| D2 | 可用 | 0.9.0，`C:\Program Files\D2\d2.exe` | 一次安装 | 是 |
| Graphviz | 可用 | 16.1.0，不在 PATH | 一次安装 | 是 |
| Mermaid CLI | 可用 | 12.0.0，npm + 本机 Chrome | 195 包，node_modules 约 385 MB | 是 |
| PlantUML | 不可用 | 无 Java、无 jar | 需先装 JDK | 否 |
| Excalidraw / draw.io | 不可用（无 CLI） | 网页/GUI | 手工 | 否 |

### 同内容对照

- 文案：`bench/content.md`；
- 画布目标 1600×900；文件都在 `bench/`；
- 截图：`route_template.png`（1600×861）、`route_tikz.png`（1600×900）、
  `route_d2.png`（1600×900）、`route_graphviz.png`（1600×900）、
  `route_mermaid.png`（1004×1600）。

| 引擎 | 观察 |
| --- | --- |
| 模板 | 5 行 × 3 栏完整，竖排标签与箭头对齐，画布基本填满；宽 1600、高 861，接近 16:9 |
| TikZ | 1600×900 精确 16:9；字号、行距、坐标全手控；中文用 YaHei；没有自动布局抖动 |
| D2 | 内容集中在左侧约 60%，右侧大片空白；三栏顺序变成 4-3、4-1、4-2；标题偏左中 |
| Graphviz | 竖排，左右空白大；三栏用 HTML 表能对齐；结论行贴底，正文被裁 |
| Mermaid | 1004×1600 竖版；节点窄，长句断成多行；层级清楚，但不适合页片 |

### 评分（1–5，目视 + 可检查性）

| 引擎 | 比例/留白 | 中文排版 | 信息层级 | 可检查/改版 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 模板 + layout_flow | 5 | 5 | 5 | 5（5 个 SVG 脚本全过） | **默认** |
| TikZ | 5 | 4（可设字体，行距要手调） | 5 | 2（PDF；dvisvgm 文本转路径，5 脚本不适用） | TeX 用户可选 |
| D2 | 2 | 3 | 4 | 3（SVG 可查，改文案会重排） | 关系草图 |
| Graphviz | 2 | 3 | 3 | 2（版式不可控，结论行贴底） | 退役 |
| Mermaid | 1 | 2 | 3 | 1（PNG，依赖 Chrome） | 文档草图 |

评分只看这张图的可交付性，不代表引擎的通用能力；D2 做关系图、Mermaid 做文档流程图仍然合适。

### 决策

1. **默认仍是模板 / `layout_flow.py`**：16:9 可控、5 个检查能跑、改文案只改文本。
2. **TikZ 作为 TeX 用户的备选**：需要精确字号/坐标时用；不进默认流程，也不进 5 个 SVG 检查链。
3. **D2 只做临时关系图**：不进申报版式图；缩放后要目视，别把自动布局当成品。
4. **Graphviz 维持退役**：只改存量 `.dot`。
5. **Mermaid 只做文档草图**：README/说明里的流程可以用；不进页片。
6. **PlantUML、Excalidraw、draw.io 不引入**：前者缺 Java，后两者只有 GUI，无法进批量流程。

### 复现命令

```bash
# TikZ
xelatex -interaction=nonstopmode route_tikz.tex
pdftoppm -png -r 200 -scale-to-x 1600 -scale-to-y 900 route_tikz.pdf route_tikz

# D2
d2 --layout elk --theme 0 route.d2 route_d2.svg
python scripts/render_svg.py route_d2.svg --png route_d2.png --size 1600x900

# Graphviz
dot -Tsvg route.dot -o route_graphviz.svg
python scripts/render_svg.py route_graphviz.svg --png route_graphviz.png --size 1600x900

# Mermaid（装一次；node_modules 不进仓库）
npm install @mermaid-js/mermaid-cli
mmdc -i route_mermaid.mmd -o route_mermaid.png --size 1600x900 -p puppeteer.json
```

### 失败判据（更新）

- 模板图如果节点超过 15 个、连线交叉明显，改用 TikZ 或拆图，不硬塞进模板；
- TikZ 如果改一次文案要动 10 处以上坐标，退回模板；
- D2/Mermaid 输出如果进页片，先看缩放后最小字号；小于 9pt 就不进交付；
- 任何引擎出图后都要目视；脚本只做机械检查。
