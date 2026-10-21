# 设计令牌与学术作图规范

> 本文件是出图的**唯一真源**。改配色、字号、线宽只改 `scripts/tokens.py`，不要在单个图里硬编码。
> 依据：Nature 官方图规范（[preparing figures](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/)、
> [building panels](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)）、
> Wong 无障碍色板（Wong, *Nature Methods* **8**, 441 (2011)）、
> Rougier et al. [Ten Simple Rules for Better Figures](https://journals.plos.org/ploscompbiol/article/figure?id=10.1371/journal.pcbi.1003833.g007)（PLOS Comput Biol 2014）。

## 1. 按成品尺寸设计（最重要的一条）

以前的坑：先画大图再缩进 PPT，字号被动缩放、失控。
**现在：SVG 的坐标单位 = 交付时的 pt，1:1。** 图的成品尺寸就是 PPT 里图片框的尺寸：

| 图 | 成品尺寸 | 说明 |
| --- | --- | --- |
| 图1 / 图2 | 11.20 × 6.30 in（806 × 454 pt） | 通栏 |
| 图3 | 7.56 × 6.30 in（544 × 454 pt） | 半栏 |

出图命令里用 `--fit "11.2x6.3"` 让 `gv_figure.py` 把 dot 的输出缩放到该尺寸并重写
`width/height/viewBox`，于是 `tokens.py` 里的字号**就是最终 pt**。

## 2. 色彩

| 令牌 | 值 | 用途 |
| --- | --- | --- |
| `STRUCT` | `#0072B2` | 结构、主流程（框线/连线） |
| `ACCENT` | `#E69F00` | 产出、强调 |
| `VERIFY` | `#009E73` | 验证、评测 |
| `INK` | `#000000` | **所有正文文字** |
| `MUTED` | `#555555` | 次要文字（灰，非彩色） |
| 浅底 | `#E8F1FA` / `#FDF3E3` / `#E7F5F0` | 与上面三色配套的 8% 明度底 |

**硬规则**（Nature「We avoid」）：
- **文字一律黑或白**，不用彩色文字；要区分类别用**色块 + 键线**，不要给文字上色
- 不用红绿组合、不用彩虹色阶、不用图案填充、不用投影、不加背景网格
- 不用装饰性图标（能用文字说清就用文字）
- 文字与底色的对比度 > 4.5:1（WCAG AA）

## 3. 文字

| 令牌 | 成品 pt | 用途 |
| --- | --- | --- |
| `FS['title']` | 9.0 | 整幅标题（唯一允许超 7pt 的文字） |
| `FS['h1']` | 7.0 | 层次/行标题 |
| `FS['label']` | 7.0 | 格内粗体小标题 |
| `FS['body']` | 6.5 | 正文 |
| `FS['note']` | 5.5 | 边上标注、脚注 |
| `FS['panel']` | 8.0 | 面板编号 a/b/c（粗体、正体、小写） |

- 字体：`Arial / Helvetica`（西文标准）+ `Microsoft YaHei`（中文回退）
- **最小 5 pt、最大 7 pt**（标题与面板号除外）——低于 5pt 印不出来，高于 7pt 会挤压版面
- 文字**必须可编辑**（不转曲）；导出矢量时嵌 TrueType 2/42
- 中文断行：用 `_wrap_dp.py`（标点禁行首、行宽均衡、末行不过短），不交给 Graphviz 自动折行

## 4. 版式

- 面板按**字母序**排列，最小化空白；**让内容决定面板大小**，不要等分
- 线宽只用三档：`LW['frame']=0.8` / `LW['connector']=0.6` / `LW['emphasis']=1.2` pt
- 间距只用 `GAP` 档位（3 / 6 / 9 / 14 / 20 pt），不写散值
- 同级元素必须同字号、同线宽、同圆角——用 `check_consistency.py` 兜底

## 5. 交付

- **矢量优先**：Graphviz 出 SVG（干净、无内嵌字体、文字可编辑）→ 交付时优先用 SVG/EMF
- 必须用位图时：**≥300 dpi**（`gv_figure.py --dpi 300`），且按成品尺寸 1:1 出，不做二次缩放
- 进 PPT：`update_pptx_images.py` 换图；**位图会被拉伸，尺寸比例必须与图片框一致**（`--fit` 已保证）
- 最终一页多图时给面板编号 a/b/c，图注里写清每块在看什么（图注不是可选项）
