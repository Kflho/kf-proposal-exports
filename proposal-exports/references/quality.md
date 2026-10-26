# 反模式与交付标准

> 从 SKILL.md 下沉；交付前逐条打勾。

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

**MATLAB 数据图交付前**：

- [ ] 走 `run_visualization`，无 `[run_visualization] 标题超宽` 告警
- [ ] PNG、≥300 dpi、双语路径（或单语一致），重跑前清旧图
- [ ] 逐张目视；论文里的图按页渲染核对，插入 PPT/Word 不变形

**页片（PPT）交付前**：

- [ ] `deck_gate.py` 命中 **0 error**（字体 + 静态 + 文字 + 审美 + 外部审计）
- [ ] `*_critique.md` 存在：无 FAIL，REVIEW 逐条有理由，人工三项逐页签过
- [ ] `text_check.py` 命中 **0 error**（无禁用词；标题是结论）
- [ ] 每页标题连读能成故事（"ghost deck" 自测）
- [ ] 公式图透明、图片按真实比例入槽
- [ ] `render_pptx_png.py` 出图成功，**逐页目视**（溢出/重叠/对比度/图注错位）
- [ ] 每页有口播备注（≤120 字），与页面内容一致

## Integration

## 与 `paper-experiment` 的分工（按图种切，不按工序切）

| 维度 | `paper-experiment`（数据图） | 本 skill（结构图） |
| --- | --- | --- |
| 图种 | 实验/数据图：曲线、分布、柱状、箱线、对比图 | 结构示意图：总体框架、技术路线、研究计划矩阵、指标体系、组织/进度 |
| 生成方式 | **代码出图**（MATLAB/Python + `run_visualization`），版式由脚本统一 | **手写 SVG**，版式即坐标，逐图设计 |
| 载体与语言 | PNG，中英双语，进论文与实验 Note | SVG（可转 PPT/PNG），中文申报材料，单语 |
| 规范核心 | 图表清单在设计阶段定、参数入图例标题留目标、标题单行不超宽、路径与引用三处同步 | 版式类别、配色字体令牌、文字与符号规范、指标表述规范、几何自检、图↔文↔方案一致 |

**共享三条原则**（两边同源，勿各写一套）：**先设计后出图**、**术语与符号有出处**、**出图后必须看图**。
数据图侧的"看图"可直接套用本 skill `references/verification.md` 的做法：可疑区域**裁切放大**再核、
**换一个查看器**再看一遍（不同查看器对字体与换行处理不同）。

MATLAB 数据图的实现由共享库 `matlab-project-utils`（`visualizations/run_visualization`、
`plots/export_fig_paper`）负责；**产物标准**（PNG/600 dpi、双语路径、标题单行、重跑清理、
目视）在本 skill 的 `references/matlab-figures.md`，实现与标准分开放。

**本 skill 不管**：数据图的绘图实现（曲线/分布/柱状怎么画）、`run_visualization` 的内部实现、
论文/Note 的图片引用同步——这些归 `paper-experiment` / `matlab-project-utils`；
**产物标准**（PNG/分辨率/双语路径/标题/导出/目视）见 `references/matlab-figures.md`。

**上游**：写作/评审类 skill 给出正文与术语口径 → 本 skill 出图并核对一致性。
**下游**：图交付后，正文里的"如图 N 所示"、图号、图注由文档侧统一编号；
若图随文提交，图的指标表述要与正文考核指标逐字对齐。

与其他 skill 的分工：**数据图**→ 实现走 `paper-experiment` / `matlab-project-utils`，
产物规范走 `references/matlab-figures.md`；
**论文投稿插图**→ 期刊图表规范（caption/字号/分辨率/矢量图要求）；
**页片的生成/编辑**→ 本 skill 的 `ppt-deck.md`（新生成）+ 官方 `pptx` skill（改已有 `.pptx`、OOXML、
`add_slide`/`clean`/`validate`）；**文字规范**→ `references/text-quality.md`（标题 action title、禁用词、
句式），去 AI 味的完整规则仍以 `kf-personal-development` 的 `text-review.md` 为准；
本 skill 专治**工程类申报书/技术方案的结构图、路线图、计划矩阵与页片交付**。

## 与 `kf-personal-development` 的分工

| 事情 | `kf-personal-development` | 本 skill |
| --- | --- | --- |
| 仓库 README、用法/API 文档、开发文档 | 负责 | — |
| 代码注释、commit/release 文案、发布说明 | 负责 | — |
| humanizer-zh 通用去 AI 味 | 规则正文 + `text_review.py` | 引用，不重写 |
| 申报书/方案/答辩材料：结构图、页片、指标表述、报告段落 | — | 负责 |

判断：跟着仓库走、给跑项目的人看 → development；交出去给评审、客户、导师看 → 本 skill。
README 即使随申报材料一起提交，结构仍按 development 的 `readme.md`，交付文字再按本 skill 的
`text-quality.md` 检查。

## 与官方 `pptx` skill 的分工

| 事情 | 谁做 |
| --- | --- |
| 论文 → 页片（叙事与版式） | `nature-paper2ppt` / `academic-ppt`（见 `references/external-deck.md`） |
| 从讲稿/申报正文生成页片 | 本 skill（`gen_deck.js` + `formula_png.py` + `deck_gate.py`） |
| 编辑已有 `.pptx`、套模板、复制/清理页、schema 校验 | 官方 `pptx` skill（`add_slide.py`、`clean.py`、`validate.py`） |
| 读别人给的 deck（提文字、页序、缩略图网格） | 官方 `pptx` skill（`markitdown`、`thumbnail.py`） |
| 换图不改版式 / 按比例重排图片框 | 本 skill（`update_pptx_images.py`、`fit_pptx_frames.py`） |

> 版本与变更记录见 [CHANGELOG.md](../CHANGELOG.md)。
