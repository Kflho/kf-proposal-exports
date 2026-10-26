# 页片（PPT）交付流程

> 本文件管**整册页片**：把一页一页的内容 + 公式 + 图排成可编辑的 `.pptx`，并做可执行的质检。
> 图本身的规范（框架图/路线图/计划矩阵、几何自检）在 `SKILL.md` 与 `figure-types.md`，这里不重复。
> 生成用 `pptxgenjs`（Node），检查用 `deck_check.py`（python-pptx），预览用 `render_pptx_png.py`（PowerPoint COM）。

## 什么时候走这条流程

- 要交**页片**：组会/答辩/项目汇报，材料里有公式、矩阵、对比表、实验曲线；
- 已有一版 `.pptx` 要**改内容或换图**（换图优先用 `update_pptx_images.py`，见 SKILL.md「交付物是 PPT 时的收尾」）；
- 要把 `bin/exports/` 里的讲稿（每页：版面 + 口播 + 时长）落成页片。

不适用：网页版 deck、要复杂动画/交互的演示（不在本 skill 范围）。

## 五步流程（顺序不可颠倒）

| 步 | 做什么 | 产出 | 卡点 |
| --- | --- | --- | --- |
| 1 页计划 | 每页一句结论（action title，**≤16 汉字、一行**）+ 支撑证据（图/公式/表）+ 口播；论文输入先按 `external-deck.md` 选路 | `deck-plan.md`（页号、标题、版面、素材、口播） | 标题写名词短语 = 返工（要写成结论） |
| 2 定令牌 | 选浅色/深色、字号档、边距；从 `assets/deck/gen_deck.js` 拷模板 | `gen_deck.js` 里的常量段 | 跳过这步会一页一个样 |
| 3 备素材 | 公式 → `formula_png.py`；图 → 本 skill 的 SVG 导出或 MATLAB 出的 PNG（MATLAB 图按 `matlab-figures.md` 出）；表格 → 原生表格 | `assets/…png` + `sizes.json` | 公式白底不透明 → 浅色卡片上露白块 |
| 4 生成 | `node gen_deck.js` → `deck.pptx` | pptx + 每页 notes | 中文标点孤行、下标写成 `u_r` |
| 5 质检 | `deck_check.py` → `render_pptx_png.py` → 逐页目视 | 报告 + `preview/*.png` | 只看缩略图看不出 0.1in 越界 |

### 命令

```bash
# ① 公式（透明 PNG + sizes.json）
python scripts/formula_png.py assets/deck/formulas.example.json --out assets/deck/formulas

# ② 生成页片（先 npm i pptxgenjs；模板里改内容）
node assets/deck/gen_deck.js --out out/项目汇报.pptx

# ③ 交付闸门：字体落实 → 静态检查 → 文字检查 → 外部审计
python scripts/deck_gate.py out/项目汇报.pptx --strict --require-notes --scale 54,33,18,12

# ④ 预览（PowerPoint COM）
python scripts/render_pptx_png.py out/项目汇报.pptx --out out/preview

# ⑤ 逐页看图：预判不到的缺陷（重叠、对比度、图注错位）只能人眼
```

有 `.pptx` 模板要套时，先看官方 `pptx` skill 的 `thumbnail.py` + `markitdown`（需要 LibreOffice），
或用 PowerPoint COM 先截图定位版式，再按本流程填内容。

## 版式与令牌

画布 13.333 × 7.5 in（16:9）；安全边距 0.5 in；块间距 0.3 in 起。

| 令牌 | 值 |
| --- | --- |
| 中文字体 | 标题 **黑体 SimHei**、正文 **宋体 SimSun**；西文/数字 **Times New Roman**（`deck_fonts.py` 写进 run 的 `a:ea`/`a:latin`，换机器不走系统回退） |
| 字号 | 只四档：**54** 封面与唯一大数字 / **33** 页标题 / **18** 正文·要点·表格 / **12** 图注·来源·页码 |
| 行距 | 标题 1.15 / 正文 1.4（中文字面比西文满，1.2 会挤） |
| 浅色令牌 | 底 `#FFFFFF`；文字 `#1F2937`；主色 `#1E2761`；强调 `#E8A33D`；弱化 `#6B7A90`；卡片底 `#F4F7FC` |
| 深色令牌 | 底 `#1E2761`；主文字 `#FFFFFF`；次文字 `#CADCFC`；强调 `#E8A33D` |
| 结构 | 深—浅—深（封面/收尾深色，内容浅色）或全深色；不要浅深交替 |
| 禁用 | 标题下划线、页眉色条、侧边竖条、彩色正文、渐变底 |

版式族（够用即可，别每页换新花样）：

| layout | 组成 | 用在 |
| --- | --- | --- |
| `cover` | 眉题 + 大标题 + 副标题 + 署名 + 一个母题图形（如轨道环） | 封面 |
| `bullets` | 标题 + 3–5 条「粗体引导词：一句说明」 | 概念页 |
| `bullets_formula` | 左要点 + 右侧浅底卡片里叠公式图 | 模型/推导页 |
| `figure` | 大图（按真实比例）+ 一行图注 + 右侧 2–3 条结论 | 结果页 |
| `table` | 原生表格（表头深底白字，重点行浅橙底）+ 右侧大数字 | 对比/能控性页 |
| `closing` | 三条结论（粗体关键词）+ 下一步 + 谢谢 | 收尾 |

## 五条本地纪律（实测踩出来的）

1. **校验前设 UTF-8**：中文 Windows 下官方 `validate.py` 会按 GBK 解码 XML 而崩。
   `$env:PYTHONUTF8=1` 再跑（本 skill 的 `deck_check.py` 已自带 UTF-8 重配，不受影响）。
2. **公式 PNG 必须透明**：`formula_png.py` 默认就做白→透明；放在浅色卡片上不会露白块。
   若用别的工具出图，务必检查 alpha。
3. **中文按字断行**：PowerPoint 逐字折行，句号/顿号可能被挤到下一行单独成行。
   生成前按「框宽(in) × 72 ÷ 字号(pt)」估每行字数，超了就缩字号或改文案；`deck_check.py` 会把
   估算溢出报成 warning（`--strict` 变 error）。
4. **预览用 PowerPoint COM**：`render_pptx_png.py` 导出的是 PowerPoint 自己的渲染，没有字体替换；
   LibreOffice 预览在中文下会出现"框里放得下、实际放不下"的假象。
   **依赖 `pywin32`**（`pip install pywin32`），缺了脚本会直接报错退出——它不会静默降级到别处。
5. **`text_check.py` 的要点数是估的**：它把 10–22pt 的所有段落都当要点，图注、大数字标签也算，
   所以 `too-many-bullets` 常常虚高；先看 `--json` 里具体条目，再决定是否真的删内容。

## 质检（缺一不可）

| 层 | 检查 | 通过判据 |
| --- | --- | --- |
| 静态 | `deck_check.py` | 0 error；warning 逐条能解释 |
| 字体 | `deck_fonts.py`（gate 里自动跑） | 标题 SimHei / 正文 SimSun / 西文 Times New Roman，0 个 run 待改 |
| 文件 | 官方 `validate.py`（可选，装好 pptx skill 时） | `All validations PASSED` |
| 渲染 | `render_pptx_png.py` | 每页 PNG 都生成 |
| 目视 | 逐页看（可疑处放大 2 倍） | 无溢出/重叠/低对比/图注错位 |
| 内容 | 备注是否与页面一致（口播稿 ≤120 字/页） | 逐页对照页计划 |

## 常见缺陷（都是实测过的）

| 现象 | 根因 | 处理 |
| --- | --- | --- |
| 公式周围有白框/横线 | 公式 PNG 白底，落在浅色卡片上 | `formula_png.py` 默认透明；不要用 `--no-alpha` |
| 句号独占一行 | 文本框宽度差一个字 | 加宽 0.2in 或缩一句；`deck_check.py --strict` 会报 |
| 图片被压扁/拉长 | 按框硬拉，没算真实比例 | 用 `sizes.json` 的宽高比算高度（模板里的 `hOf()`） |
| 要点像代码（`u_r`） | 下标写成纯文本 | 用 run + `subscript: true`；表格单元格同样支持 |
| 标题下划色条 | 模板残留/AI 味 | 删掉，用留白或底色分区 |
| 宽矩阵公式字太小 | A、B、C 塞一张图，按卡片宽度等比缩后不足 15pt | 拆成两三张图（A/B 并排、C 另起一行），各自给 `maxW` |
| 改完忘了重跑检查 | 只改一处 | 每次改内容都重跑 `deck_check` + 预览 |

## 与官方 `pptx` skill 的分工

| 事情 | 谁做 |
| --- | --- |
| 从零生成页片 | 本 skill（`gen_deck.js` + 三条脚本） |
| 编辑已有 `.pptx` / 套模板 / 复制页 / 清理孤儿 | 官方 `pptx` skill（`add_slide.py`、`clean.py`、`validate.py`） |
| 读别人给的 deck（提文字、看页序） | 官方 `pptx` skill（`markitdown`、`thumbnail.py`） |
| 原生图表（`addChart`） | 本 skill 的 `gen_deck.js` 里直接调 pptxgenjs |

**不要**在本 skill 里重写 OOXML 手术：`update_pptx_images.py` / `fit_pptx_frames.py` 只做"换图/重排框"，
其余编辑交给官方 skill。
