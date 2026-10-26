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
