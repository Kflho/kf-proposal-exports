---
name: kf-proposal-exports
description: "中文技术申报书/方案/答辩的**交付物规范**：①配图（SVG 优先，可导入 PPT 编辑）——三类图版式（总体框架图、技术路线图、研究计划矩阵）、配色与字体令牌、文字与符号规范、指标表述规范、几何自检与一致性自检；②页片（PPT）与报告文字——页计划与 action title、版式令牌、公式 PNG、页片静态自检、口播备注、文字去 AI 味检查；③MATLAB 数据图产物——统一入口 run_visualization、PNG/600 dpi、中英双语路径、标题单行。触发词：画图, 配图, 申报书配图, 技术路线图, 总体框架图, 检查图片, 文字越界, 做PPT, 做个PPT, 幻灯片, 页片, 汇报PPT, 答辩PPT, 讲解PPT, 把讲稿做成PPT, 页稿成片, 报告文字, 标题像话题, 检查PPT文字, 口播稿, MATLAB 出图, 数据图规范, matlab figure, paper figure, draw diagram, proposal figure, technical roadmap, framework figure, check svg text, slide deck, presentation, pptx, speaker notes, 做或改页片, 套模板, 维护生成器, 评估审美, 写评审理由, 交付前自检."
metadata:
  version: "2.0.7"
  last_updated: "2026-10-23"
  status: active
  data_access_level: raw
  task_type: open-ended
  related_skills:
    - kf-personal-development
    - taste-skill
    - pptx
    - academic-paper
    - academic-paper-reviewer
---

# Proposal Exports v2.0.6 — 中文申报材料：配图 + 页片 + MATLAB 图产物

把手写的"看着差不多就行"变成**可机器校验**的交付流程：结构与文案先定、画完必自检、交付必目视。

> 跨机协作 / 开发流程：见 `kf-personal-development` 的 `references/skill-dev.md`
> 「跨机协作流程」（canonical）；本 skill 不重复。

本 skill 面向中文技术申报书 / 技术方案 / 项目答辩材料，管以下交付物：

| 交付物 | 产物 | 规则与检查 |
| --- | --- | --- |
| **配图** | 自包含 SVG（可导入 PPT/WPS 再编辑），或 PNG | 本文件 + `references/figure-types.md`、5 个 SVG 检查脚本 |
| **页片（PPT）** | 可编辑 `.pptx` + 每页口播备注 + 预览 PNG | `references/ppt-deck.md` + `deck_gate.py`（字体/几何/文字/外部审计）、`deck_fonts.py`、`render_pptx_png.py` |
| **文字**（页片标题/要点/报告段落） | 页计划、标题序列、正文 | `references/text-quality.md` + `text_check.py`、`text_consistency.py` |
| **界面文字**（弹窗/状态栏/提示） | 只写当前状态或要求操作 | `references/text-quality.md`「用户交互文字」一节 |
| **MATLAB 数据图产物** | PNG（论文/报告图），中英双语路径 | `references/matlab-figures.md` + `assets/matlab/export_figure.m` + 共享库 `matlab-project-utils` |

## 能力分层（常驻 / 选择性）

启动只加载**常驻**；选择性文档由触发条件点名，不预读。

| 层 | 内容 | 何时加载 |
| --- | --- | --- |
| **常驻（持续激活）** | 本文件：触发、画布与令牌、两条工作流、硬规则、脚本表 | 每次会话 |
| **选择性（阶段触发）** | `references/`：画图取 [figure-types](references/figure-types.md)；页片取 [ppt-deck](references/ppt-deck.md)；文字取 [text-quality](references/text-quality.md)/[text-norms](references/text-norms.md)；外部能力取 [external-deck](references/external-deck.md)；生成器/回灌取 [deck-generator](references/deck-generator.md)；模板取 [deck-template](references/deck-template.md)；审美取 [deck-critique](references/deck-critique.md)；目视取 [verification](references/verification.md)；MATLAB 取 [matlab-figures](references/matlab-figures.md) | 流程走到那一步才读 |
| **交付前一次** | `deck_gate.py` 一条命令（字体 → 静态 → 文字 → 审美 → 外部审计）+ 预览 PNG | 闸门统一调用 |

判断方法：先看这一步的判据在哪份 reference，只读那一份；读不到再查笔记，不靠猜。

> 图片排版调整：**先调版式，再调文案**；版式定了跑 check_overlap.py / check_symbols.py，最后目视。
> 画布、设计语言、引擎选型见 [references/figure-engine.md](references/figure-engine.md)。

## 审美

taste-skill 只接两步：定令牌前抽三个方向并记录（`design-notes/deck-aesthetics.md`）；交付前跑
`deck_critique.py` 出 `*_critique.md`（闸门含该步）。规则见 [deck-critique.md](references/deck-critique.md)。

> 概论 / 研究内容 / 目标 / 创新点 / 实验 / 产出各写什么，见 [references/project-content.md](references/project-content.md)。

## Trigger Conditions

## 触发场景

- 要为申报书/方案/答辩画图或配图（总体框架、技术路线、研究计划、指标体系、进度甘特、组织架构）
- 要检查已有配图：文字压线、重叠、越界、错乱、与实际不符
- 要核对**图 ↔ 正文 ↔ 技术方案**三方是否一致（数字、术语、称谓、限定条件）
- 要把导师/模板给的示例图落到自己的图上
- 要把图导出/嵌入 PPT、Word，或转 PNG 做汇报
- 要做汇报/答辩/组会**页片**：把讲稿落成 PPT、补标题与口播、把图/公式排进去
- 要检查**页片或报告的文字**：标题像话题、要点太多、句子太长、AI 腔、口播超长
- 写申报书正文 / 技术方案 / 项目笔记，或梳理「研究内容、目标、创新点、技术方案」的边界
- 要出 **MATLAB 数据图**、统一字体/线宽/图例，或核对论文/报告的图片产物（PNG、600 dpi、双语路径、标题单行）

## 面向用户的界面文字

面向用户的界面文字（弹窗/状态栏/提示）只写当前状态或要求操作，规则见 `references/text-quality.md`「用户交互文字」一节。

## 不触发

纯代码/算法实现、纯数据分析、与申报材料无关的网页前端 → 不加载本 skill。

## 页片与文字工作流（详见 `references/ppt-deck.md`、`text-quality.md`）

| 步 | 做什么 | 产出 | 卡点 |
| --- | --- | --- | --- |
| 1 页计划 | 每页一句**结论**作标题；列证据（图/公式/表）与口播 | `deck-plan.md` | 标题写话题 = 返工（见 `text-quality.md`） |
| 2 定令牌 | 选浅/深色、字号、边距；拷 `assets/deck/gen_deck.js` | `gen_deck.js` 常量段 | 一页一个样 |
| 3 备素材 | 公式走 `formula_png.py`；图走本 skill 的图流程；表用原生表格 | PNG + `sizes.json` | 公式白底、图被拉伸 |
| 4 生成 | `node gen_deck.js` | `.pptx` + 每页 notes | 中文标点孤行、下标写成 `u_r` |
| 5 自检 | `deck_gate.py`（字体 → 静态 → 文字 → **审美评估** → 外部审计）→ `render_pptx_png.py` → 逐页目视 | 报告 + `*_critique.md` + 预览 PNG | 闸门 0 error、critique 无 FAIL 才算交付 |

> **页片交付**：`deck_gate.py` 0 error（内含字体落实、`deck_check`、`text_check`、外部审计）+ 预览逐页看过。
> **要长期维护的册子先建生成器**：代码出片、页片里的改动用 `deck_spec.py --compare` 回灌，见 `references/deck-generator.md`。
> **有现成模板**：用 `deck_template.py` 抽令牌、套版式/复制页，见 `references/deck-template.md`（中文字体写中文族名）。
> 缺一项就算没做完。

## 五步工作流（顺序不可颠倒）

| 步 | 做什么 | 产出 | 卡点 |
| --- | --- | --- | --- |
| 1 定结构 | 明确这张图**回答什么问题**（谁支撑谁？先后关系？谁负责什么？），画出格子再想文字 | 结构说明（版式草图 + 每格写什么） | 结构没定就调字号＝返工 |
| 2 定文案 | 每格文字**先写成纯文本**，逐条核对术语、称谓、指标写法 | 文案清单（可计入字数台账） | 文案进 SVG 后再改，坐标要跟着动 |
| 3 画 | 用 `assets/template.svg` 起手；只改文案与坐标，不临时发明图元 | SVG 文件 | 一处改字号，全列跟着改 |
| 4 机器自检 | 渲染 + 越界/压线 + 禁用符号 + 文字清单 | 自检记录 | **不许跳过**；跳过必被抓 |
| 5 目视验收 | 看渲染图；对可疑区域**裁切放大**再看一遍 | 目视结论 | 7px 净距人眼看不出来 |

> 若图是给**他人**（导师/总体组/评审）看的：第 1 步要先把结构发出去确认，再动手画。

## 硬规则

19 条硬规则已下沉：[references/hard-rules.md](references/hard-rules.md)（违反即返工；先读它再画/再做页片）。

> 三类图版式（框架 / 路线 / 计划矩阵）与连线规范见 [references/figure-types.md](references/figure-types.md)。

> 脚本表与命令见 [references/quick-start.md](references/quick-start.md)；交付前一律跑 `deck_gate.py`。

## 外部 skill：只调用

数据图 → `scipilot-figure-skill` / `nature-figure`；审计 → `nature-figure` 的三个 audit 脚本；
原生 PPT/AI → `svg-native-pptx`；页片 → `nature-paper2ppt` / `academic-ppt`。命令与判读见
[references/external-calls.md](references/external-calls.md)、[references/external-deck.md](references/external-deck.md)。

> 反模式、交付标准与集成说明见 [references/quality.md](references/quality.md)。

## 脚本（入口一览）

| 阶段 | 脚本 |
| --- | --- |
| 配图 | `scripts/check_overlap.py`、`scripts/check_symbols.py`、`scripts/check_connectors.py`、`scripts/check_consistency.py`、`scripts/check_spacing.py`、`scripts/render_svg.py`、`scripts/audit_text.py`、`scripts/svg_to_pdf.py` |
| 页片 | `scripts/formula_png.py`、`scripts/deck_check.py`、`scripts/text_check.py`、`scripts/deck_fonts.py`、`scripts/deck_gate.py`、`scripts/deck_spec.py`、`scripts/deck_template.py`、`scripts/deck_critique.py`、`scripts/render_pptx_png.py`、`scripts/update_pptx_images.py`、`scripts/fit_pptx_frames.py` |
| 文本 | `scripts/text_consistency.py` |

命令与参数见 [references/quick-start.md](references/quick-start.md)；交付前跑 `deck_gate.py`。

## 文字严谨性
专有名词、概念、指标口径先按 `kf-personal-development` 的前期调研核对权威来源再落笔；调研发现在
`bin/reference_docs/` 留档，不写进用户 Obsidian 笔记。不自行造术语，也不把网络口语当定义。

## 阶段路由（触发 → 先读哪份）

| 触发 | 先读 | 产物 |
| --- | --- | --- |
| 画申报结构图 / 框架 / 路线 / 计划矩阵 | [figure-types](references/figure-types.md) + [figure-engine](references/figure-engine.md) | SVG + 5 个几何/记法检查 |
| 做或改页片、套模板、维护生成器 | [ppt-deck](references/ppt-deck.md) / [deck-template](references/deck-template.md) / [deck-generator](references/deck-generator.md) | pptx + `deck_gate` |
| 评估审美、写评审理由 | [deck-critique](references/deck-critique.md)（记录在 `design-notes/deck-aesthetics`） | `*_critique.md` |
| 写申报书 / 方案 / 报告文字 | [project-content](references/project-content.md) + [text-quality](references/text-quality.md) + [text-norms](references/text-norms.md) | 段落 |
| 交付前自检 | [verification](references/verification.md) + [quality](references/quality.md) + [quick-start](references/quick-start.md) | 打勾清单 |
| 外部能力（数据图/审计/原生 PPT） | [external-calls](references/external-calls.md) + [external-deck](references/external-deck.md) | 调用 |

## 参考索引
- 图与令牌：[figure-types](references/figure-types.md) [figure-engine](references/figure-engine.md) [design-tokens](references/design-tokens.md) [style-tokens](references/style-tokens.md) [indicator-wording](references/indicator-wording.md) [text-norms](references/text-norms.md) [verification](references/verification.md) [graphviz-usage](references/graphviz-usage.md)
- 页片与文字：[ppt-deck](references/ppt-deck.md) [quick-start](references/quick-start.md) [deck-generator](references/deck-generator.md) [deck-template](references/deck-template.md) [deck-critique](references/deck-critique.md) [text-quality](references/text-quality.md) [project-content](references/project-content.md) [quality](references/quality.md)
- 外部与案例：[external-calls](references/external-calls.md) [external-deck](references/external-deck.md) [case-notes](references/case-notes.md)；设计记录 `design-notes/`（[deck-aesthetics](references/design-notes/deck-aesthetics.md) [deck-template-eval](references/design-notes/deck-template-eval.md) [ppt-integration](references/design-notes/ppt-integration.md) [writing-standards-research](references/design-notes/writing-standards-research.md) [diagram-engine-decision](references/design-notes/diagram-engine-decision.md) [kf-research-gap](references/design-notes/kf-research-gap.md) [bench/content](references/design-notes/bench/content.md)）
