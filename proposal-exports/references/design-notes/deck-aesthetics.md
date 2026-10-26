# 设计记录：页片的审美方向（taste-skill 实跑）

> 类型：审美决策留痕　｜　日期：2026-10-26　｜　状态：已定，待落令牌与检查
> 输入：taste-skill（上游 `Leonxlnx/taste-skill`，本地 `~/.dsh/skills/taste-skill`，入口
> `skills/taste-skill/SKILL.md`；v2.1.5，上游 commit 12af471）。
> 证据：`dev/taste/sheet-one-motif.md`、`dev/taste/sheet-type-only.md`（本机跑出的 direction sheet，gitignored）。

## 为什么先做这一步

原来只写了"审美决策引 taste-skill"，没有一次实跑记录，等于审美靠默认值。这次按它的流程
（抽三方向 → 选一个 → 定类型/配色 → 落令牌 → 看成品）走了一遍，把结论固定成可执行令牌。

## 实跑记录

```bash
node ~/.dsh/skills/taste-skill/skills/taste-skill/scripts/draw.mjs \
  --sector dev-tool --brief "中文技术申报/答辩页片：多站联合定位方法研究" \
  --sections intro,how-it-works,proof,stats --tone technical --options 3
```

三个方向（原文名 + 对我们的含义）：

| 方向 | 主张 | 放到答辩页片上 |
|---|---|---|
| `type-only-statement` | 首页只由文字、色与留白构成，图后到、大而少 | 结论页敢留白；图是"证据到货"，不是装点 |
| `product-performs` | 让产物在页面上真的工作（真实界面片段） | 每页摆"能自己说话的图/表/数"，不描述功能 |
| `one-motif` | 取主题里一个形状贯穿全册（裁切、蒙版、分隔带） | 定位几何（测距圆/站间基线）做母题 |

**选定 `type-only-statement`**（seed `557601348`，`--keep palette,type`）。

选它的理由一句话：答辩/申报的载体本来就是"一句结论 + 一份证据"，这个方向强制每页先有结论、
再谈别的；`one-motif` 的大面积裁切形状在评审场景容易被读成装饰，`product-performs` 的
"真实界面片段"我们大多是 MATLAB/SVG 图，已被 `--keep` 下的 figure 版式覆盖。

## 重画（有理由的偏离，逐条登记）

| 槽位 | 处置 | 理由 |
|---|---|---|
| palette / type | 保留项目令牌（`--keep palette,type`） | 申报/答辩语境 + 已有中文令牌；taste-skill 的 soot/lime 深色与 Switzer 不适用 |
| photographs | 不用 | 页片无照片位；"天空/星空"图集与申报无关 |
| motion | 不用 | PPT 静态交付，动效不在交付面 |
| hero 尺寸 | 由 9–14vw 换算为 54pt / 33pt 两档 | 画布是 960×540pt（13.33×7.5in），不是浏览器视口 |
| "one live thing" | 落成"每页一个证据元素" | 页片不能被读者操作；等价物是能被读者验证的图/表/数/结论句 |

## 落成的令牌（唯一真源在 `references/ppt-deck.md`）

| 维度 | 决定 | 来自 |
|---|---|---|
| 字号 | 只四档：**54** 封面与唯一大数字 / **33** 页标题 / **18** 正文·要点·表格 / **12** 图注·来源·页码；去掉 40/30/22/16/14 这些中间档 | taste-skill「两三档做可见工作」 |
| 字体与行距 | 标题 **黑体 SimHei**、正文 **宋体 SimSun**、西文/数字 **Times New Roman**（`project note` 论文撰写-字体）；标题 1.15 行距、正文 1.4 | 用户字体规范 + `deck_fonts.py` 落实 |
| 对齐 | 默认左对齐、左基线统一；**全册只在封面居中一次** | taste-skill「左对齐为默认，居中最多一次」 |
| 色 | 一底一墨一强调：底 `#FFFFFF`、墨 `#1F2937`（正文全墨）、强调 `#E8A33D` **每页 ≤2 处**；弱化 `#6B7A90` 只给图注/来源/页码 | taste-skill「一个强调，出现在动作和最多一处」 |
| 面 | 用色阶 `#F4F7FC` 分块；不画细线框、不加阴影、不用渐变 | taste-skill house rules |
| 版式族 | `claim-led` / `figure-dominant`（图占 55–75%）/ `process-wide` / `comparison` / `metric`；加 `cover` `closing` | type-only 的分节蓝图 + nature-paper2ppt 的 archetype |
| 反模板 | 同一版式连续 ≤3 页；全册 ≥2 种版式；五页以上同一构图即重排（缩略图通看） | nature-paper2ppt「slide-sorter 扫描」 |
| 密度 | 正文每条 ≤18 汉字、每页 ≤3 条；结果页 1 句解读 + ≤2 个标注 | nature-paper2ppt 的 on-slide text budget |

## 怎么证明有效

1. 机械部分进 `deck_check.py`：字号档位（`type-scale`）、强调色预算（`accent-budget`）、
   渐变/阴影（`flat-style`）；
2. 人眼部分看 `render_pptx_png.py` 的预览：标题连读成故事（ghost deck）、同版式连续页数、
   留白是否"有东西"；
3. 与项目笔记的验收口径对齐：页片三件套（`deck_check` 0 error、`text_check` 0 error、逐页目视）
   不变，新增的 token 检查并入 `deck_check`。
