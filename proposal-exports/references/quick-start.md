# Quick Start、依赖与输出格式

> 从 SKILL.md 下沉；首次使用或安装环境时读这一份。

## Quick Start

```bash
# ---- 配图：拷模板 → 改文案 → 自检 → 目视 ----
cp assets/template.svg 图1_总体框架.svg
python scripts/render_svg.py 图1_总体框架.svg --png out/f1.png     # 渲染
python scripts/check_overlap.py 图1_总体框架.svg                    # 几何：越界/压线
python scripts/check_symbols.py 图1_总体框架.svg                    # 记法：禁用符号
python scripts/audit_text.py 图1_总体框架.svg                       # 文字清单

# ---- 页片：公式 → 生成 → 闸门（字体→静态→文字→外部审计）→ 预览 ----
python scripts/formula_png.py assets/deck/formulas.example.json --out assets/deck/formulas
node assets/deck/gen_deck.js --out out/deck.pptx
python scripts/deck_gate.py out/deck.pptx --strict --require-notes --scale 54,33,18,12
python scripts/render_pptx_png.py out/deck.pptx --out out/preview

# ---- MATLAB 数据图：统一格式 → 600 dpi PNG ----
# 拷 assets/matlab/export_figure.m 到项目；MATLAB 里：
#   export_figure(fig, outDir, 'name');          % 报告/PPT，默认 7.5 in
#   export_figure(fig, outDir, 'name', 5.5);     % 论文单栏
# 单图/循环/分栏/半对数用例见 references/matlab-figures.md

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

## 输出格式（交付物）

1. **SVG 文件**（每图一个，自包含）；
2. **结构说明**（版式、每格文案、连线语义、图↔文对照表；可合并为 `图_xx_结构.md`）；
3. **自检记录**（脚本命中数 + 目视结论 + 已知偏差）；
4. 若涉及他人给的示例：**差异/待定清单**（哪些按示例原样、哪些待对方确认）。

## 脚本表

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
| `scripts/deck_check.py` | **页片静态自检**：16:9、安全边距、图片拉伸、文字溢出、备注、占位符，加令牌（字号档位/强调色/渐变阴影）与字体（族/中英分工/角色） | `deck.pptx [--strict] [--require-notes] [--scale 54,33,18,12] [--title-ea SimHei --body-ea SimSun]` |
| `scripts/deck_fonts.py` | **字体规范落实**：给每个 run 写 `a:latin`/`a:ea`（标题黑体、正文宋体、西文 Times New Roman），默认干跑 | `deck.pptx [--apply] [--title-min-pt 30]` |
| `scripts/deck_gate.py` | **页片交付闸门**：字体 → 静态 → 文字 → 外部审计，一条命令；外部脚本找不到标 skipped | `deck.pptx [--strict] [--steps ...] [--external-script path]` |
| `scripts/deck_spec.py` | **回灌**：把 `.pptx` 拆成 spec（文字/位置/表格/图片/备注），或比两版差异 | `deck.pptx --out spec.json [--assets dir]`；`--compare old new [--json]` |
| `scripts/deck_template.py` | **按模板出片**：抽主题色/字体/版式占位符；按 plan 套版式或复制页替换文字与图片 | `模板.pptx --tokens tokens.json`；`--list`；`--plan plan.json --out deck.pptx` |
| `scripts/deck_critique.py` | **审美评估**：8 条 taste-skill 法条（字号档/强调色/平色/居中/轴线/页满度/字体族/主导）+ 人工三项 | `deck.pptx [--md critique.md] [--json]` |
| `scripts/capabilities.py` | **能力清单**：脚本/文档/测试/闸门一表；`--report` 看覆盖率与缺口 | `--report [--json]` |
| `scripts/text_check.py` | **文字自检**：标题像话题、长句、要点过多、口播过长、禁用词 | `deck.pptx｜report.md [--json]` |
| `scripts/text_consistency.py` | **一致性检查**：文档术语/标题层级/相对链接；`--exports` 加报告图片链接、alt、图注、图号、孤立图 | `--root . [--exports] [--json]` |
| `scripts/render_pptx_png.py` | **页片预览**：PowerPoint COM 逐页导出 PNG（替代 LibreOffice） | `deck.pptx --out preview [--width 1600]` |

脚本只做机械判定，**结论一律以"命中 0 + 目视通过"共同成立为准**。

> MATLAB 数据图不走本 skill 的脚本：统一格式与 600 dpi 导出用共享库 `matlab-project-utils` 的
> `run_visualization`、`export_fig_paper`；产物规则见 `references/matlab-figures.md`。

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
