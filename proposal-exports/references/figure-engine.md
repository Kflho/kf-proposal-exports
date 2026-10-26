# 出图引擎：画布、排版、设计语言、选型

> 从 SKILL.md 下沉；出图前按需读，版式判据仍以 `figure-types.md` 与 SKILL 的两句话规则为准。

## 画布尺寸

- **进 PPT / 答辩**：`960×540pt`（13.33×7.5in，16:9 全幅 1:1）。`viewBox="0 0 960 540"`，
  坐标与字号就是最终 pt：正文 ≥ 10pt、图注 ≥ 9pt。
- **进 A4 申报书**：`842×595pt`（A4 横向）；双栏图宽 `519pt`（183mm）。
- `assets/template.svg` 就是按 `960×540pt` 画的（1 坐标单位 = 1pt）：框间距 12 / 24，
  单元格内文字间距 24 / 48；模板自检 `check_overlap` / `check_symbols` / `check_spacing` 全过。

## 图片排版调整

先调版式，再调文案：图例 / 坐标轴 / 标签的层级、留白、对齐先定下来，再改文字；
不要用改字号、挪一两个像素来掩盖结构问题。版式稳定后跑 `check_overlap.py` / `check_symbols.py`，
最后目视核对图与正文、图与指标一致。

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

**Graphviz 的写法**（只给存量图参考，完整踩坑见 `references/graphviz-usage.md`）：`rankdir` / `rank=same` 分层，
`subgraph cluster_x` 表并列，
边上 `label=` 自动避让；中文断行仍用 `scripts/gv_figure.py`（内部 `_wrap_dp.py` 做 DP 断行）。
装了 Graphviz 才能用这条路：`winget install Graphviz.Graphviz`。
