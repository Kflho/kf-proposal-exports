---
name: kf-proposal-exports
description: "中文技术申报书/方案/答辩的**两类交付物规范**：①配图（SVG 优先，可导入 PPT 编辑）——三类图版式（总体框架图、技术路线图、研究计划矩阵）、配色与字体令牌、文字与符号规范、指标表述规范、几何自检与一致性自检；②页片（PPT）与报告文字——页计划与 action title、版式令牌、公式 PNG、页片静态自检、口播备注、文字去 AI 味检查。触发词：画图, 配图, 申报书配图, 技术路线图, 总体框架图, 检查图片, 文字越界, 做PPT, 做个PPT, 幻灯片, 页片, 汇报PPT, 答辩PPT, 讲解PPT, 把讲稿做成PPT, 页稿成片, 报告文字, 标题像话题, 检查PPT文字, 口播稿, draw diagram, proposal figure, technical roadmap, framework figure, check svg text, slide deck, presentation, pptx, speaker notes."
metadata:
  version: "2.0.1"
  last_updated: "2026-10-22"
  status: active
  data_access_level: raw
  task_type: open-ended
  related_skills:
    - kf-personal-development
    - pptx
    - academic-paper
    - academic-paper-reviewer
---

# Proposal Exports v2.0.0 — 中文申报材料：配图 + 页片

把手写的"看着差不多就行"变成**可机器校验**的交付流程：结构与文案先定、画完必自检、交付必目视。

> 跨机协作 / 开发流程：见 `kf-personal-development` 的 `references/skill-dev.md`
> 「跨机协作流程」（canonical）；本 skill 不重复。

本 skill 面向中文技术申报书 / 技术方案 / 项目答辩材料，管**两类交付物**：

| 交付物 | 产物 | 规则与检查 |
| --- | --- | --- |
| **配图** | 自包含 SVG（可导入 PPT/WPS 再编辑），或 PNG | 本文件 + `references/figure-types.md`、5 个 SVG 检查脚本 |
| **页片（PPT）** | 可编辑 `.pptx` + 每页口播备注 + 预览 PNG | `references/ppt-deck.md` + `deck_check.py`、`render_pptx_png.py` |
| **文字**（页片标题/要点/报告段落） | 页计划、标题序列、正文 | `references/text-quality.md` + `text_check.py` |

依赖说明：图流程以纯标准库 Python 为主（出图默认手写 SVG / 模板；TikZ 需 TeX Live，
D2 只做关系草图，Graphviz 只在遗留图里用，Mermaid 只做文档草图）；
页片流程需要 Node（`pptxgenjs`）、`python-pptx`、`Pillow`，预览需要 Windows + PowerPoint（COM），
公式需要 TeX Live（`pdflatex`/`pdftoppm`）。脚本缺依赖时直接报错并给安装命令，不静默降级。

## Quick Start

```bash
# ---- 配图：拷模板 → 改文案 → 自检 → 目视 ----
cp assets/template.svg 图1_总体框架.svg
python scripts/render_svg.py 图1_总体框架.svg --png out/f1.png     # 渲染
python scripts/check_overlap.py 图1_总体框架.svg                    # 几何：越界/压线
python scripts/check_symbols.py 图1_总体框架.svg                    # 记法：禁用符号
python scripts/audit_text.py 图1_总体框架.svg                       # 文字清单

# ---- 页片：公式 → 生成 → 静态自检 → 文字自检 → 预览 ----
python scripts/formula_png.py assets/deck/formulas.example.json --out assets/deck/formulas
node assets/deck/gen_deck.js --out out/deck.pptx
python scripts/deck_check.py out/deck.pptx --strict --require-notes
python scripts/text_check.py out/deck.pptx
python scripts/render_pptx_png.py out/deck.pptx --out out/preview

# ---- 路线图：拷案例 → 改 ROWS → 生成 → 5 项检查 → 渲染 ----
python scripts/layout_flow.py assets/deck/cases_route.py --out out/route.svg --apply
python scripts/render_svg.py out/route.svg --png out/route.png
python scripts/check_overlap.py out/route.svg
python scripts/check_connectors.py out/route.svg
python scripts/check_consistency.py out/route.svg
python scripts/check_spacing.py out/route.svg
python scripts/check_symbols.py out/route.svg
```

两条流程最后都必须**自己看一眼**渲染结果（PNG/预览图）。脚本只做机械检查，
看不出"这段话在图上说不通""这一页到底想说什么"。

## Trigger Conditions

### 触发场景

- 要为申报书/方案/答辩画图或配图（总体框架、技术路线、研究计划、指标体系、进度甘特、组织架构）
- 要检查已有配图：文字压线、重叠、越界、错乱、与实际不符
- 要核对**图 ↔ 正文 ↔ 技术方案**三方是否一致（数字、术语、称谓、限定条件）
- 要把导师/模板给的示例图落到自己的图上
- 要把图导出/嵌入 PPT、Word，或转 PNG 做汇报
- 要做汇报/答辩/组会**页片**：把讲稿落成 PPT、补标题与口播、把图/公式排进去
- 要检查**页片或报告的文字**：标题像话题、要点太多、句子太长、AI 腔、口播超长

### 不触发

- 纯粹的数据可视化（折线/柱状/散点）→ 用 matplotlib / 统计可视化规范
- 照片、渲染图、界面截图
- 仓库 README、用法/API 文档、代码注释、commit/release 文案 →
  `kf-personal-development` 的 `readme.md` / `text-review.md`
- 长篇论文/公文写作（页片与申报材料之外的体裁）→ 用写作/评审类 skill

## 页片与文字工作流（详见 `references/ppt-deck.md`、`text-quality.md`）

| 步 | 做什么 | 产出 | 卡点 |
| --- | --- | --- | --- |
| 1 页计划 | 每页一句**结论**作标题；列证据（图/公式/表）与口播 | `deck-plan.md` | 标题写话题 = 返工（见 `text-quality.md`） |
| 2 定令牌 | 选浅/深色、字号、边距；拷 `assets/deck/gen_deck.js` | `gen_deck.js` 常量段 | 一页一个样 |
| 3 备素材 | 公式走 `formula_png.py`；图走本 skill 的图流程；表用原生表格 | PNG + `sizes.json` | 公式白底、图被拉伸 |
| 4 生成 | `node gen_deck.js` | `.pptx` + 每页 notes | 中文标点孤行、下标写成 `u_r` |
| 5 自检 | `deck_check.py` → `text_check.py` → `render_pptx_png.py` → 逐页目视 | 报告 + 预览 PNG | 三项全过才算交付 |

> **页片交付三件套**：`deck_check.py` 0 error、`text_check.py` 0 error、预览逐页看过。
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

## 硬规则（违反即返工）

1. **文字不许越框、压线**：任何 `<text>` 的四边都要落在所属方框内（内边距 ≥12px），
   且与线段、箭头、相邻文字净距 ≥12px。以 `check_overlap.py` 命中 0 为准。
2. **跨行文字一律拆成独立 `<text>`**，不要用同一 `<text>` 内的多个 `<tspan>` 靠 `dy` 换行——
   部分查看器/转换器不认 `dy`，两行会拼成一串（表现为"文字错乱"）。
   行尾补标点（顿号/逗号），保证拼起来也读得通。
3. **符号与记法**：不得用 `↓↑` 表示升降（写"降低/提高 ≥N%"）；`＋` 只用于专名（如 `5G-A＋毫米波`）；
   并列一律顿号 `、`；箭头 `→` 只用于连线标签与流程带；`@`、"精度@距离"之类自创记法禁用。
4. **术语统一**：同一事物全文一个叫法（含称谓层级：母课题 / 子课题 / 研究内容 / 研究子内容），
   图、正文、技术方案三处必须逐字一致。术语表见 `references/text-norms.md`。
5. **缩写首现给全称**：`交替方向乘子法（ADMM）`，之后才可单用缩写。
6. **示例原样**：导师/模板/上级给的示例图或示例条目，**一字不改**照搬；
   自己的补充放在别处（如"支撑产出"框），并单独说明。差异只登记在对照表里。
7. **图上承诺必须有依据**：图上出现的任何指标、指标值、限定条件，都要能在正文/技术方案里找到出处；
   做不到或依赖未落实的，写清限定（如"（组网模式）""（由项目集成环节考核）""门限待任务书给定"）。
8. **图里只放已完成/已确认的信息**：未定项写"待定/待任务书给定"，不臆造数值。
9. **自包含**：无 `<image>`、无脚本、无外部字体、无 `foreignObject`；每张图自己定义 `marker`。
10. **可编辑性**：坐标取整（10 的倍数优先）、形状类别收敛（`rect`/`text`/`line`/`polyline`/`path`/`circle`），
    便于日后在 PPT 里按同一坐标重画或导入后微调。
11. **改动留痕**：改文案/坐标后必须重跑第 4、5 步；自检脚本的命中数从 N→0 才算完成。
12. **一处改、处处改**：图上改了称谓或指标写法，正文、技术方案、台账同步改，并复算字数。
13. **连线只用正交折线，箭头只表达因果/对应**：禁斜线与扇形发散线；一对多用"母线"（一路出 → 竖母线 →
    N 条水平支线），多对一用汇流；**并列项之间不画箭头**（会被读成流程）；标签锚点与 x 统一、放在线的外侧；
    上下行数量不匹配时（如上行 4 列、下行 3 格）用**通栏 + 分隔线**表达"跨条目"，不要强行对齐。
    详见 `references/figure-types.md` §5。
14. **同类元素必须同一处理（设计系统）**：开工前先定"角色 → 锚点/字号/颜色"表
    （`references/figure-types.md` §6），画完用 `check_consistency.py` 验。
    三条对齐铁律：**单元格里的东西一律居中于列心；通栏里的段落左对齐；通栏里的并列项等分居中**。
    同一角色的锚点/字号/分隔线处理不一致 = 视觉语言混乱（真实事故：一张矩阵图 28 处居中、17 处左对齐，
    几何自检全绿）。
15. **先查证，不要重复造轮子**：① 术语查 [术语在线 termonline.cn](https://www.termonline.cn/about)（全国科技名词委）
    → 单位查 GB 3100~3102 → 图表格式看目标期刊/出版社规范；② 图形语言与检查清单先看已有 skill
    （`artifact-diagramming`、`opum-ai/diagram-skills`、`excalidraw-skill` 等）；
    页片生成/编辑先看官方 `pptx` skill（pptxgenjs、OOXML、validate）；③ 已有标准/工具能覆盖的，
    就**引用它**，不要自建一套并行的规则表。自建的规则只保留"权威来源查不到"的部分，并标注"项目内约定"。
16. **页片标题写结论（action title）**：一句话、带判断、≤30 汉字；不写"背景/方法/结果"这类话题标签；
    全册标题连读要能讲完故事（读不通就改标题，不许靠正文补）。规则见 `references/text-quality.md`。
    **例外（按任务书验收的课程/实验汇报）**：标题改为切「研究目标/实验要求」的条目名，
    结论移到每页底部「结论｜」行（依据用户 `project note`「exports/汇报稿：标题切研究目标」）；
    此时 `text_check.py` 的 `title-*` warning 属预期，在交付说明里登记，不作为返工依据。
17. **文案禁用 AI 腔与套话**：禁用词、套话开头和翻译腔模式见 `assets/text/banned.json`，
    正文不重复列举；报告段落同样适用。`text_check.py` 命中 0 error 为准。
18. **页片自检三件套 + 目视**：`deck_check.py`（几何/图片比例/备注/占位符）、`text_check.py`（标题/句子/禁用词）、
    `render_pptx_png.py`（预览）三项全过，再逐页看图。只看生成代码不算验收。
19. **图引擎选型按场景**：三类申报图默认模板/`layout_flow.py`（16:9 成品、可校验）；
    TeX 用户可用 TikZ 做精确版式，但不进 5 个 SVG 检查链；临时关系图可用 D2；
    Graphviz 只用于存量图；Mermaid 只做文档草图（理由见「出图方式」）。

## 三类图的版式（详见 references/figure-types.md）

| 图 | 回答的问题 | 骨架 |
| --- | --- | --- |
| **总体框架图** | 本部分**如何支撑上级**？与兄弟部分什么关系？ | 顶栏（上级）→ 两侧/左列兄弟（弱化色）→ 中央本部分 → 右侧研究子内容（3~4 条，每条 ~10 字）→ 右下产出框 → 底部承接指标通栏 |
| **技术路线图** | 技术路线**怎么走**？ | 标题条 → 2~3 条横向层次带（带标题 + 带内 3 模块：小示意 + 标题 + 说明）→ 带间居中向下箭头配 2~4 字动作词 → 底部验证带 |
| **研究计划矩阵** | 目标→问题→内容→方法→验证**如何对齐**？ | 左侧竖排标题条 + 自上而下 5 行（目标需求 / 关键问题 / 研究内容 / 子内容与关键方法 / 实验验证），问题↔内容↔方法**竖向成列** |

## 样式令牌（详见 references/style-tokens.md）

```text
主色 #2F6FB0（描边）／#E8F1FA（填充）    层次带标题 #4A7EBB 底 + 白字
强调 #E8A33D ／ #FDF3E3                   弱化（兄弟项）#9AA5B1 ／ #F2F4F7
正文 #1F2937，次要 #4B5563
字体 Microsoft YaHei, PingFang SC, Source Han Sans SC, SimHei, sans-serif
标题 30~34 / 带标题 20~24 / 模块标题 17~18 / 正文 15~17 / 小字注 12~13
圆角 8~12，描边 2（核心框 2.5），画布 16:9 用 viewBox="0 0 1600 900"
```

## 指标表述（详见 references/indicator-wording.md）

- 指标名用**任务书/指南的原文名称**，不自造（如"通感专用定位测距"）；确需规范化的写进台账并注明原文。
- 精度类写**距离限定前置**：`1 km 处定位精度 ≤10 m`（不写 `≤10 m@1 km`）。
- 相对指标**必带基线**：`较固定 50:50 时频划分降低 ≥10%`（不写 `↓≥10%`）。
- 时间类指标**必带层级与计时口径**：`≤100 ms（快变层单次求解；慢变层秒级更新；≤8 站；自感知数据就绪起计）`。
- **成对约束成对写**：`虚警率 ≤5%（与检测概率成对约束，其门限待任务书给定）`。
- 承接的系统级指标要**写明由谁考核**：`支撑的系统级指标（由项目集成与硬件环节考核）：…`。

## 设计语言（学术规范，出图前先读）

> 完整口径见 **`references/design-tokens.md`**；唯一真源是 **`scripts/tokens.py`**——改配色/字号/线宽只改它。

依据 Nature 官方图规范与 Wong 无障碍色板（[出处](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/)）。要点：

| 维度 | 规范 |
| --- | --- |
| **按成品尺寸设计** | SVG 坐标 = 交付 pt（1:1）。`gv_figure.py --fit "11.2x6.3"` 自动迭代缩尺，`tokens.py` 里的字号即最终字号 |
| **色彩** | Wong 色板语义化：结构 `#0072B2`／产出 `#E69F00`／验证 `#009E73`；**文字一律黑或白**，颜色只用于框线、色块、键线 |
| **禁用** | 彩色文字、红绿组合、图案填充、投影、背景网格、装饰性图标 |
| **字号** | 正文 6.5 / 小标题 7 / 面板号 8（粗体）/ 标题 9 pt；**最小 5、最大 7**（标题与面板号除外） |
| **线宽** | 只用三档：框 0.8 / 连线 0.6 / 强调 1.2 pt |
| **交付** | 矢量优先（SVG/EMF，文字可编辑不转曲）；位图 ≥300 dpi；进 PPT 前确认**比例与图片框一致** |
| **版式** | 面板字母序、最小化空白、内容决定面板大小；图注不是可选项 |

```bash
# 出图（成品 1:1 + 300dpi + 自动缩尺）
python scripts/gv_figure.py 图1_gv.py --out 图1.svg --fit "11.2x6.3" \
       --png 图1.png --dpi 300
```

## 出图方式：模板优先，TikZ 可选，D2 备选，Graphviz 退役

> **2026-10 实测后的调整。** 自动布局引擎优化的是"图读得懂"，不是"版面像设计过的"：
> 同一份三层流程，Graphviz 出成 611×1607 的竖条、D2 默认方向出成 2893×468 的横幅，
> Mermaid 出成 1004×1600 的竖版，都不符合 16:9 页片；中文字距、留白、分组关系全由引擎决定。
> 而 `assets/template.svg` 在 1600×900 上**直接就是成品**，还能被 5 个检查脚本逐项验。
> 所以：**默认用模板 / 网格引擎；TikZ 给需要精确版式的 TeX 用户；D2 只做临时关系图；
> Graphviz 只改存量图；Mermaid 只做文档草图。**

| 场景 | 用什么 | 为什么 |
| --- | --- | --- |
| 三类申报图（总体框架、技术路线、研究计划矩阵） | `assets/template.svg` 手改，或 `layout_flow.py` 从内容生成 | 版式即坐标，检查脚本能验；天然 16:9 |
| 精确版面、TeX 工程 | TikZ（`xelatex` + `ctex`） | 1600×900 可精确控制；但坐标手写、5 个 SVG 检查不适用 |
| 临时关系图 / 结构示意（≤15 节点，不要求像素级） | **D2**（`winget install Terrastruct.D2`） | ELK 布局 + 现代主题，出图快；导出后仍需 `render_svg.py` 与检查 |
| 存量 `.dot` 图改造 | Graphviz（保留，不推荐新图） | 旧图迁移用；新图不要从这里开始 |
| README / 文档里的流程草图 | Mermaid（`@mermaid-js/mermaid-cli`） | 文本即图，改起来快；竖版、断行密，不进页片 |

**D2 的用法**（装一次）：

```bash
winget install Terrastruct.D2
d2 --theme 0 --layout elk 关系图.d2 关系图.svg
python scripts/render_svg.py 关系图.svg --png out/关系图.png --size 1600x900
python scripts/check_overlap.py 关系图.svg        # 文字压线仍可查
```

> D2 输出是"关系图"，不是"申报版式图"。放进页片时按示意图用（`render_svg.py --size 1600x900`
> 缩放到画布），不要把 D2 图当总体框架图交。

**TikZ 的用法**（TeX 用户，需 TeX Live）：

```bash
xelatex -interaction=nonstopmode 路线图.tex
pdftoppm -png -r 200 -scale-to-x 1600 -scale-to-y 900 路线图.pdf 路线图
```

起手模板见 `references/design-notes/bench/route_tikz.tex`。坐标手写，改文案要同步改节点宽度；
交付前目视，不进 5 个 SVG 检查链。

**Mermaid 的用法**（只做文档草图）：

```bash
npm install @mermaid-js/mermaid-cli
mmdc -i 流程.mmd -o 流程.png --size 1600x900
```

样例见 `references/design-notes/bench/route_mermaid.mmd`。竖版输出、长句断行密，不要直接进页片。

**Graphviz 的写法**（只给存量图参考）：`rankdir` / `rank=same` 分层，`subgraph cluster_x` 表并列，
边上 `label=` 自动避让；中文断行仍用 `scripts/gv_figure.py`（内部 `_wrap_dp.py` 做 DP 断行）。
装了 Graphviz 才能用这条路：`winget install Graphviz.Graphviz`。

## 脚本

| 脚本 | 用途 | 关键参数 |
| --- | --- | --- |
| `scripts/tokens.py` | **设计令牌唯一真源**：Wong 色板、成品 pt 字号档、线宽、间距（见 `references/design-tokens.md`） | 被各 spec `import` |
| `scripts/layout_flow.py` | **首选（图）**：从内容生成"行 × 栏"式图，自带生成前断言与生成后回读 | `cases.py --out 图.svg [--apply] [--report]` |
| `scripts/gv_figure.py` | 遗留/备选：声明式 Graphviz 出图 + 中文 DP 断行（需装 `dot`） | `spec.py --out 图.svg --fit 11.2x6.3 [--png]` |
| `scripts/_wrap_dp.py` | 中文断行器（DP：标点不入行首 / 行宽均衡 / 末行不过短） | 被 `gv_figure.py`、`layout_flow.py` 调用 |
| `scripts/render_svg.py` | 无头浏览器渲染 SVG → PNG，支持裁切放大与指定画布 | `--png out.png` `--crop "x y w h"` `--scale 2` `--size 1600x900` |
| `scripts/svg_to_pdf.py` | SVG → PDF（Edge 打印；供外部碰撞/字号审计读取真实几何） | `svg --out out.pdf [--engine cairo]` |
| `scripts/check_overlap.py` | 文字包围盒 vs 线段/折线/矩形边框，报越界与压线 | `paths...` `--pad 12` `--json` |
| `scripts/check_consistency.py` | **视觉语言一致性**：同尺寸单元格逐格比对锚点/字号/分隔线 | `paths...` `--min-cells 2` `--json` |
| `scripts/check_spacing.py` | **框间距审计**：相邻框净距分布 | `paths...` `--scale 12,24,32` `--tol 2` |
| `scripts/check_connectors.py` | **连线端点贴合**：端点距方框边界，悬空即报并给吸附坐标 | `paths...` `--tol 1.5` `--min-len 60` |
| `scripts/check_symbols.py` | 禁用符号/记法扫描（可自定义规则表） | `paths...` `--rules file.json` |
| `scripts/audit_text.py` | 导出每个 text 的坐标/字号/锚点/字数 | `path` `--md out.md` |
| `scripts/update_pptx_images.py` | **换图**：把 pptx 内嵌图片换成新图，版式逐字节不动 | `pptx --list`｜`--map "条目=新图" --apply` |
| `scripts/fit_pptx_frames.py` | 按图片真实比例重排图片框（消除拉伸） | `pptx --list`｜`--apply [--margin 0.4]` |
| `scripts/formula_png.py` | **公式**：LaTeX → 裁白边 PNG（默认透明）+ `sizes.json` | `formulas.json --out dir [--dpi 400] [--no-alpha]` |
| `scripts/deck_check.py` | **页片静态自检**：16:9、安全边距、图片拉伸、文字溢出、备注、占位符 | `deck.pptx [--strict] [--require-notes] [--json]` |
| `scripts/text_check.py` | **文字自检**：标题像话题、长句、要点过多、口播过长、禁用词 | `deck.pptx｜report.md [--json]` |
| `scripts/render_pptx_png.py` | **页片预览**：PowerPoint COM 逐页导出 PNG（替代 LibreOffice） | `deck.pptx --out preview [--width 1600]` |

脚本只做机械判定，**结论一律以"命中 0 + 目视通过"共同成立为准**。

> **从内容生成图（`layout_flow.py`）**：手改坐标改不动的图用它。把文案写进一份
> `cases.py`（`ROWS` 列表 + 版面常量），脚本负责：按字数断行 → 由行数反推框高 →
> 按基线网格放文字 → 四行间距 → 三列对齐 → 连线（x=列心，y 贯通行间空隙）→ 白底。
> 三道关：**生成前断言**（超宽 / 行首标点 / 框越界 / 竖排标签超条）、
> **生成后回读**（连线竖直、x=列心、y 贴合上下框、白底覆盖、无 `foreignObject`）。
> 改文案只改 `cases.py` 重跑，不要再手改 SVG 坐标。规则要点：
> - 行型三选：`full` 通栏整段｜`cols` 三列（带栏标题）｜`seg` 通栏分三段、各居中于列心
> - 段落写成**一整段**（不要在句号处拆成多个字符串，否则会各自断行、长短不齐）
> - 格内要"一条一行"时在文案里写 `\n`（硬换行优先于 DP 断行）
> - 左侧**大标题**用 `MAIN_TITLE`（漏了整幅会显得缺一块）
> - 断行器 `_wrap_dp.py` 是动态规划：代价 = 标点孤行 1000 + 行宽不满平方×0.002 + 末行过短 400

> **交付物是 PPT 时的收尾**：本 skill 出 SVG，而申报书常要交 PPT。流程是
> `render_svg.py` 出 PNG → `update_pptx_images.py` 换图。换图前先 `--list` 看清包内
> 条目与尺寸，再干跑一次确认清单（脚本会**报出尺寸变化**：若新图与包内旧图尺寸不一致，
> PPT 里会被拉伸，须先把渲染尺寸对齐——`render_svg.py` 的窗口按 `viewBox × scale` 取整，
> 与旧图差几个像素是常见的，例如 `viewBox 878` 出 1756 而旧图是 1760）。

> **评审要改图时，转"原生对象"而不是换图**：调用 `~/.dsh/tools/svg-native-pptx/powerpoint_native.py`
> 把 SVG 转成原生形状 + 原生文本框的 PPTX（PowerPoint 出实际预览对照）；装了 Illustrator 才可走 `.ai`。
> 命令见 `references/external-calls.md`；坑：文本别放全角空格 U+3000（会拆成逐字框）、输出目录必须不存在。

## 外部 skill：只调用，不自研

| 需求 | 调用 |
| --- | --- |
| 数据图（曲线/柱状/分布/多面板） | `scipilot-figure-skill`（选型 + 出图）或 `nature-figure` |
| 交付前碰撞 / 字号 / 画布审计 | `nature-figure` 的 `audit_figure_collisions.py`、`audit_pdf_text.py`、`audit_svg_schematic.py` |
| 评审要改字：SVG → 原生 PPT / AI | `~/.dsh/tools/svg-native-pptx/powerpoint_native.py`（需桌面 PowerPoint；AI 需装 Illustrator） |

命令与判读见 **`references/external-calls.md`**。本 skill 只保留外部没有的：连线端点、视觉语言一致性、
禁用符号、框间距、指标表述、图↔文一致、PPT 换图。`check_overlap.py` 降级为源码级预检。

## 输出格式（交付物）

1. **SVG 文件**（每图一个，自包含）；
2. **结构说明**（版式、每格文案、连线语义、图↔文对照表；可合并为 `图_xx_结构.md`）；
3. **自检记录**（脚本命中数 + 目视结论 + 已知偏差）；
4. 若涉及他人给的示例：**差异/待定清单**（哪些按示例原样、哪些待对方确认）。

## Anti-Patterns（都是真实踩过的）

| 反模式 | 后果 | 正确做法 |
| --- | --- | --- |
| 用 `tspan dy` 换行 | 某些查看器把两行拼成一串，看着像"文字错乱" | 拆成两个 `<text>` |
| 把说明塞进标题行内（小字 tspan） | 行变长撑出右边框（实测溢出 47px） | 说明下沉为第二行小字注，框高相应加大 |
| 只跑一次自检就交付 | 改一次文案就 reintroduce 越界 | 每次改动后重跑；命中数必须为 0 |
| 只看整图缩略图 | 7~13px 净距/溢出看不出来 | 对可疑区域 `--crop` 放大 4 倍再看 |
| 图上写 `↓≥10%` | 与正文"降低 ≥10%"不一致，且非规范 | 用文字，且与正文逐字一致 |
| 图上自己给指标加"最优/保证" | 验收时被追问依据 | 只写可达成的措辞，限定条件写全 |
| 直接改导师示例的措辞 | 与上级口径脱节，返工 | 示例原样，差异进对照表 |
| 称谓各写各的（课题/子课题/研究内容） | 评审看不懂层级，甚至自相矛盾 | 全文一套称谓，先定后用 |
| 同类元素锚点混用（表头居中、条目左对齐） | 一眼看出"乱"，但几何自检全绿 | 先定设计系统表（§6），画完跑 `check_consistency.py` |
| 连线直角与斜线混用 / 并列项画箭头 | 视觉语言不统一；把并列讲成流程 | 见硬规则 13 与 `figure-types.md` §5 |

## Quality Standards（交付前逐条打勾）

- [ ] `check_overlap.py` 命中 **0**（含出框与压线）
- [ ] **外部门禁**：`nature-figure` 的碰撞审计 verdict 为 `PASS`（`REVIEW REQUIRED` 时每条 WARN 有目视结论），字号审计 ≥ 6 pt
- [ ] `check_connectors.py` 命中 **0**（连线两端都贴在方框/层带边界上）
- [ ] `check_consistency.py` 命中 **0**（同类元素锚点/字号/分隔线一致）
- [ ] `check_spacing.py` 命中 **0**（或例外已写入结构说明）
- [ ] `check_symbols.py` 命中 **0**（或每条都有明确豁免理由）
- [ ] 每张图 `xml.etree.ElementTree.parse` 通过
- [ ] 无 `<image>`／`<script>`／`foreignObject`／外部字体
- [ ] 文字与正文/技术方案的术语、称谓、指标写法**逐字一致**
- [ ] 图上每个数值都能在正文/方案里找到出处
- [ ] 已渲染并**目视**（含可疑区域放大）
- [ ] 结构说明与图↔文对照表已更新
- [ ] 若改了称谓/指标：正文、方案、台账同步，并复算字数

**页片（PPT）交付前**：

- [ ] `deck_check.py` 命中 **0 error**（16:9、0.5in 边距、图片无拉伸、备注齐全、无占位符）
- [ ] `text_check.py` 命中 **0 error**（无禁用词；标题是结论）
- [ ] 每页标题连读能成故事（"ghost deck" 自测）
- [ ] 公式图透明、图片按真实比例入槽
- [ ] `render_pptx_png.py` 出图成功，**逐页目视**（溢出/重叠/对比度/图注错位）
- [ ] 每页有口播备注（≤120 字），与页面内容一致

## Integration

### 与 `paper-experiment` 的分工（按图种切，不按工序切）

| 维度 | `paper-experiment`（数据图） | 本 skill（结构图） |
| --- | --- | --- |
| 图种 | 实验/数据图：曲线、分布、柱状、箱线、对比图 | 结构示意图：总体框架、技术路线、研究计划矩阵、指标体系、组织/进度 |
| 生成方式 | **代码出图**（MATLAB/Python + `run_visualization`），版式由脚本统一 | **手写 SVG**，版式即坐标，逐图设计 |
| 载体与语言 | PNG，中英双语，进论文与实验 Note | SVG（可转 PPT/PNG），中文申报材料，单语 |
| 规范核心 | 图表清单在设计阶段定、参数入图例标题留目标、标题单行不超宽、路径与引用三处同步 | 版式类别、配色字体令牌、文字与符号规范、指标表述规范、几何自检、图↔文↔方案一致 |

**共享三条原则**（两边同源，勿各写一套）：**先设计后出图**、**术语与符号有出处**、**出图后必须看图**。
数据图侧的"看图"可直接套用本 skill `references/verification.md` 的做法：可疑区域**裁切放大**再核、
**换一个查看器**再看一遍（不同查看器对字体与换行处理不同）。

**本 skill 不管**：数据图（曲线/分布/柱状）、绘图脚本与 `run_visualization`、中英双语出图、
论文/Note 的图片路径与引用同步——这些归 `paper-experiment`。

**上游**：写作/评审类 skill 给出正文与术语口径 → 本 skill 出图并核对一致性。
**下游**：图交付后，正文里的"如图 N 所示"、图号、图注由文档侧统一编号；
若图随文提交，图的指标表述要与正文考核指标逐字对齐。

与其他 skill 的分工：**数据图**→ `paper-experiment`（实验出图管线）或统计可视化规范；
**论文投稿插图**→ 期刊图表规范（caption/字号/分辨率/矢量图要求）；
**页片的生成/编辑**→ 本 skill 的 `ppt-deck.md`（新生成）+ 官方 `pptx` skill（改已有 `.pptx`、OOXML、
`add_slide`/`clean`/`validate`）；**文字规范**→ `references/text-quality.md`（标题 action title、禁用词、
句式），去 AI 味的完整规则仍以 `kf-personal-development` 的 `text-review.md` 为准；
本 skill 专治**工程类申报书/技术方案的结构图、路线图、计划矩阵与页片交付**。

### 与 `kf-personal-development` 的分工

| 事情 | `kf-personal-development` | 本 skill |
| --- | --- | --- |
| 仓库 README、用法/API 文档、开发文档 | 负责 | — |
| 代码注释、commit/release 文案、发布说明 | 负责 | — |
| humanizer-zh 通用去 AI 味 | 规则正文 + `text_review.py` | 引用，不重写 |
| 申报书/方案/答辩材料：结构图、页片、指标表述、报告段落 | — | 负责 |

判断：跟着仓库走、给跑项目的人看 → development；交出去给评审、客户、导师看 → 本 skill。
README 即使随申报材料一起提交，结构仍按 development 的 `readme.md`，交付文字再按本 skill 的
`text-quality.md` 检查。

### 与官方 `pptx` skill 的分工

| 事情 | 谁做 |
| --- | --- |
| 从零生成页片 | 本 skill（`gen_deck.js` + `formula_png.py` + `deck_check.py`） |
| 编辑已有 `.pptx`、套模板、复制/清理页、schema 校验 | 官方 `pptx` skill（`add_slide.py`、`clean.py`、`validate.py`） |
| 读别人给的 deck（提文字、页序、缩略图网格） | 官方 `pptx` skill（`markitdown`、`thumbnail.py`） |
| 换图不改版式 / 按比例重排图片框 | 本 skill（`update_pptx_images.py`、`fit_pptx_frames.py`） |

## Version Info

- **v2.0.1（2026-10-22）**：页片实战反馈（线性系统实验一二合册，13 页）。
  ① `banned.json` 补控制类固定搭配（传递矩阵、特征多项式等前缀词），避免控制术语被误报 error；
  配套两条测试；
  ② 硬规则 16 加例外：按任务书验收的课程/实验汇报，标题切研究目标，结论放下方「结论｜」行；
  ③ `ppt-deck.md` 补三条实测：`render_pptx_png.py` 需 `pywin32`、`text_check.py` 会把 10–22pt
  图注/数字标签算成要点（`too-many-bullets` 虚高）、宽矩阵拆成 A/B/C 三张图更好排。
- **v2.0.0（2026-10-16）**：从"配图 skill"扩成**配图 + 页片 + 文字**三类交付物。
  ① 更名 `proposal-exports`；② 新增页片流程（`references/ppt-deck.md`、`assets/deck/gen_deck.js`、
  `formula_png.py`、`deck_check.py`、`render_pptx_png.py`）；③ 新增文字规范（`references/text-quality.md`、
  `text_check.py`）；④ 出图引擎改版：**模板优先、D2 备选、Graphviz 退役**（实测 Graphviz/D2 的 16:9
  适配差、中文排版不可控，见 `references/design-notes/diagram-engine-decision.md`）；
  ⑤ 新增 pytest（`tests/`）与设计记录（`references/design-notes/`）。
- **v1.1.5（2026-10-15）**：硬规则新增第 15 条「先查证，不要重复造轮子」（术语→术语在线/GB 3100~3102，
  图形→已有 skill）；`text-norms.md` §7 改为"先查权威再谈通俗化"（删掉自建术语表，改指向
  [术语在线](https://www.termonline.cn/about)、ISO 704/GB/T 15237，只留"项目内约定"小节）；
  新增 §9 竖排文字横向居中（`rotate(-90)` 的 0.30em 偏移与两种做法）。
- **v1.1.4（2026-10-15）**：`text-norms.md` 增 §7 术语通俗化（"不可公度"→"量纲不可比"等）与
  §8 编号与标签：**优先用词，不用裸编号**（研究内容行表头写"组网建模"而非"4-1"）。
- **v1.1.3（2026-10-15）**：新增 `scripts/check_connectors.py`——把"连线端点有没有贴在方框上"
  变成可算的数字（实测一图抓出 10 处 4~6px 悬空）。
- **v1.1.0（2026-10-15）**：补「视觉语言一致性」这一环——新增 `scripts/check_consistency.py`、
  设计系统表与三条对齐铁律（`figure-types.md` §6）、硬规则 13/14、案例复盘（`references/case-notes.md`，
  含外部同类 skill 调研结论）。
- v1.0.0（2026-10-15）：从实际申报书项目中提炼。含三类图版式、样式令牌、文字与符号规范、
  指标表述规范、4 个自检脚本、起手模板。

## Changelog

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 2.0.1 | 2026-10-22 | 补控制类固定搭配，避免术语被误报（含两条测试）；硬规则 16 加课程汇报例外（标题切研究目标）；ppt-deck 补 pywin32 依赖、text_check 图注计数、宽矩阵拆图 |
| 2.0.0 | 2026-10-16 | 更名 proposal-exports；加页片（公式/生成/自检/预览）与文字规范（action title/禁用词检查）；出图默认改模板优先、D2 备选、Graphviz 退役；新增 tests 与设计记录 |
| 1.1.6 | 2026-10-15 | `fit_pptx_frames.py`（按图片真实比例重排图片框）+ 硬规则 12（改动留痕） |
| 1.1.3 | 2026-10-15 | 新增 `check_connectors.py`（连线端点贴合检查，含"端点接母线"合规判定与背景框排除）+ 验收清单第 2 条 |
| 1.1.0 | 2026-10-15 | 新增 `check_consistency.py`（同类元素一致性检查）+ 设计系统表 + 硬规则 13（连线语言）、14（设计系统）+ `case-notes.md` 复盘与外部 skill 调研 |
| 1.0.0 | 2026-10-15 | 首版：五步工作流、12 条硬规则、三类图版式、4 个脚本、模板 |
