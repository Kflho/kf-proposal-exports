# Changelog（kf-proposal-exports）

> 只记版本与变更；判据与流程在 SKILL.md 与 references/。

## 版本

- **v2.0.6（2026-10-27）**：审美接入落地——`deck_critique.py`（8 条法条的机械版 + 人工三项，报告 `*_critique.md`）、`deck_gate` 增 `critique` 步、`references/deck-critique.md`；新增 `capabilities.py` 与功能激活测试（脚本可 `--help`、文档链接、闸门覆盖、taste 接入产物、缺口显式登记）。

- **v2.0.5（2026-10-27）**：按模板出片两层能力——`deck_template.py`（`--tokens` 抽主题色/字体/版式占位符；`--plan` 套版式、复制页替换文字与图片）+ `references/deck-template.md`、审美评估 `design-notes/deck-template-eval.md`；修中文字体族名（`SimHei`/`SimSun` 被 Office 静默回退成宋体，改 `黑体`/`宋体`）。

- **v2.0.4（2026-10-27）**：新增页片回灌流程 `references/deck-generator.md` 与 `scripts/deck_spec.py`（dump spec / `--compare` 比两版），把「在 PowerPoint 里改完 → 同步回生成器」固化成五步流程与差异判读。

- **v2.0.3（2026-10-26）**：页片流程改「接线 + 补充」。① 新增 `references/external-deck.md`（论文→页片调 `nature-paper2ppt` / `academic-ppt`，含调用契约与回退）；② 新增 `deck_gate.py`（字体→静态→文字→外部审计，一条命令）与 `deck_fonts.py`（标题黑体/正文宋体/西文 Times New Roman，写进 run 的 `a:ea`/`a:latin`）；③ 审美按 taste-skill 实跑定档（`design-notes/deck-aesthetics.md`），字号收敛为 54/33/18/12 四档；④ `deck_check` 增令牌与字体检查，`text_check` 标题上限 30→16 汉字、增口语语体检查；⑤ 修掉 sk_05 断链与「官方 pptx skill」死引用。

- **v2.0.2（2026-10-23）**：把 MATLAB 出图产物规范从 `kf-personal-development` 的 MATLAB 附录
  移入本 skill：新增 `references/matlab-figures.md`（统一入口 `run_visualization`、600 dpi PNG、
  双语路径、标题单行、目视自检）；MATLAB 代码风格与环境仍留在开发 skill，仅保留一条指向本 skill
  的引用。
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

## 变更记录

| 版本 | 日期 | 变更 |
| --- | --- | --- |
| 2.0.6 | 2026-10-27 | 审美评估进流程（deck_critique + critique 步 + 报告留痕）；能力清单与激活测试 |
| 2.0.5 | 2026-10-27 | 按模板出片：`deck_template.py`（抽令牌 + 套版式/复制页）+ 文档与审美评估；中文字体族名修正 |
| 2.0.4 | 2026-10-27 | 生成器回灌：`deck_spec.py`（dump/compare）+ `deck-generator.md`（契约、五步回灌、差异判读、限制） |
| 2.0.3 | 2026-10-26 | 页片改接线+补充：`external-deck.md`（调 paper2ppt/academic-ppt）、`deck_gate.py`、`deck_fonts.py`；四档字号；字体与令牌检查；标题 ≤16 汉字；修死链 |
| 2.0.2 | 2026-10-22 | 新增「章节定义」（`references/project-content.md`）：概论 / 研究内容 / 目标与子课题 / 创新点 / 技术方案优势 / 实验 / 产出各写什么；项目笔记功能只写"做什么"，不写实现手段 |
| 2.0.2 | 2026-10-23 | MATLAB 出图产物规范从 kf-personal-development 移入（`references/matlab-figures.md`）：统一入口/600 dpi/双语路径/标题单行/目视；开发 skill 只留引用 |
| 2.0.1 | 2026-10-22 | 补控制类固定搭配，避免术语被误报（含两条测试）；硬规则 16 加课程汇报例外（标题切研究目标）；ppt-deck 补 pywin32 依赖、text_check 图注计数、宽矩阵拆图 |
| 2.0.0 | 2026-10-16 | 更名 proposal-exports；加页片（公式/生成/自检/预览）与文字规范（action title/禁用词检查）；出图默认改模板优先、D2 备选、Graphviz 退役；新增 tests 与设计记录 |
| 1.1.6 | 2026-10-15 | `fit_pptx_frames.py`（按图片真实比例重排图片框）+ 硬规则 12（改动留痕） |
| 1.1.3 | 2026-10-15 | 新增 `check_connectors.py`（连线端点贴合检查，含"端点接母线"合规判定与背景框排除）+ 验收清单第 2 条 |
| 1.1.0 | 2026-10-15 | 新增 `check_consistency.py`（同类元素一致性检查）+ 设计系统表 + 硬规则 13（连线语言）、14（设计系统）+ `case-notes.md` 复盘与外部 skill 调研 |
| 1.0.0 | 2026-10-15 | 首版：五步工作流、12 条硬规则、三类图版式、4 个脚本、模板 |
