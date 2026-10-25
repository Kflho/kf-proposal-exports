# PPT / Illustrator 绘图能力调研（2026-10-19）

> 你问的是："他们能调用 PowerPoint 或 Illustrator 来绘图"——这条能力到底是什么、
> 怎么实现的、我们能不能直接用。
> 结论先说：**能，而且不需要它们的付费接口。** 本机已跑通 PPT 全链路；Illustrator
> 因本机未安装，只做了机制拆解，未实测。

## 0 一句话结论

他们不是"在 PPT 里手画"，而是把 SVG 的**几何**翻成 PowerPoint 的 **DrawingML 原生路径**、
把**文字**翻成**原生文本框**，再调本机 PowerPoint / Illustrator 做**实际渲染验收**。
交付物是"能在 PPT/AI 里逐字改、逐个拖"的对象，不是贴图。

## 1 三层架构

| 层 | 做什么 | 关键文件 | 用的东西 |
| --- | --- | --- | --- |
| **几何** | SVG 路径 → PPT 原生 freeform（`a:custGeom`） | `svg_native_geometry.py` | cairosvg / cairocffi 解析，`skia-pathops` 做布尔（裁剪、描边转轮廓），fontTools 解析路径 |
| **文字** | SVG 文本 → PowerPoint 原生文本框 | `native_text.py` | Python-pptx + cairosvg 的文本布局（基线/字号/变换），逐字体基线校准 |
| **验收** | 打开真软件、导出真预览、留哈希回执 | `display_check.py`、`import_illustrator.ps1` | `win32com.client.Dispatch('PowerPoint.Application')`；PowerShell `New-Object -ComObject Illustrator.Application` + ExtendScript |

上游：`yrui-cmd/Cell_CNS_Figure`，MIT，commit `a4ef1e9`。**付费的只是它的出图 API，转换与验收全在本地。**

## 2 几何：SVG → DrawingML 原生路径

- 输入先被 `illustrator_svg.expand()` 展开：CSS（`cssselect2`/`tinycss2`）、`transform`、嵌套 `svg`、`use`；
- 路径变换用 `cairocffi` 矩阵，**描边转轮廓、裁剪求交**用 `skia-pathops`；
- 每个结果写成 `a:custGeom/a:pathLst` 的 freeform（形状类型 5），不是图片、不是内嵌 SVG。

实测我们的模板图：**25 个 freeform**，`clipped_paths=25`，`gradient_objects=0`。

## 3 文字：原生文本框 + 逐字体基线校准

流程（`native_text.py`）：

1. 用 cairosvg 的 `SVGSurface` 拿到每段文字的**基线、字号、字体、旋转**（不是只读 `x/y`）；
2. 用 python-pptx 建文本框，**关自动换行/自动缩放/内边距**，按原字号摆放；
3. 旋转以中心为轴换算（PowerPoint 与 SVG 的旋转原点不同）；
4. **基线校准**：生成一张每字体一行的校准 PPTX，调 PowerPoint 实际渲染，量墨迹包围盒，
   算出该字体的首行偏移，写进 `native.json`。

实测：Microsoft YaHei 粗/常规两条校准，偏移 **−0.104 px**，`text_mode=editable_text`，
`outlined_text=false`，`font_fallback_glyphs=0`，**25 个原生文本 run**。

## 4 验收：真软件、真预览、真回执

### PowerPoint（`display_check.render_powerpoint`）

```python
app = win32com.client.Dispatch('PowerPoint.Application')
pres = app.Presentations.Open(deck, -1, 0, 0)      # 只开私有副本
w, h = pres.PageSetup.SlideWidth, pres.PageSetup.SlideHeight
slide.Export(preview_png, 'PNG', 1200, round(1200*h/w))
```

同时 `inspect_pptx()` 数形状类型：`5` = 原生 freeform、`13` = 位图、`28` = 内嵌 SVG。
**判定 `native_paths` 的条件是：有 freeform，且位图=0、内嵌 SVG 图元=0。**
没有 PowerPoint 时不是"跳过"，而是明确报错，不冒充通过。

### Illustrator（`import_illustrator.ps1`）

```powershell
$app = New-Object -ComObject Illustrator.Application
$result = $app.DoJavaScript($script)   # ExtendScript
```

ExtendScript 里做四件事：

1. `app.open(svg)` → `saveAs(.ai, pdfCompatible=true)` → **关闭再重开**（验的是存盘结果，不是内存里的导入态）；
2. 合并 Illustrator 把"填充+描边"拆出的**两份同位文本框**（只合并相邻、内容/字体/字号/位置完全相同的一对）；
3. 写 `audit.json`：路径数、文本框数、位图数、画板、每段文字的字体/位置/字号；
4. `ExportOptionsPNG24` 导出实际预览；返回 `OK|reused|paths|textFrames|rasterItems`。

**本机没有 Illustrator（注册表无 `Illustrator.Application`），这条未验证。**

## 5 本机实测（PowerPoint 全链路）

| 项 | 结果 |
| --- | --- |
| 转换入口 | `~/.dsh/tools/svg-native-pptx/powerpoint_native.py --svg assets/template.svg --output …` |
| PPTX | `editable.pptx` 33.7 KB |
| 形状构成 | **25 freeform + 25 文本框 + 0 位图 + 0 内嵌 SVG** |
| PowerPoint 实渲染 | 通过，`mode=native_paths`，版本 16.0 |
| 与 SVG 渲染的平均通道误差 | **2.15 / 255**；画布比例差 0.0 |
| 基线校准 | −0.104 px（YaHei 粗/常规） |
| 用时 | 约 20–40 秒（含校准 + 预览 + 对照页） |

对照图见 `%TEMP%\full_convert\display\powerpoint.png` 与 `svg.png`：箭头、圆角、浅底、
通栏文字均保留，肉眼几乎无差。

## 6 三个实测坑

1. **全角空格 U+3000 会把一句话拆成逐字文本框。**
   `层次一　阶段名` → 6 个单字文本框（普通空格 `层次一 阶段名` → 1 个框，旋转文字也正常）。
   对策：文本里别用 U+3000；要视觉间距就用两个 `<text>` 或改用普通空格加 `textLength`。
2. **输出目录必须不存在**，否则 `[WinError 183]`（脚本用 `mkdir(exist_ok=False)`）。
3. **PowerPoint 里的换行与浏览器不同**：SVG 里不压线的段落，进 PPT 可能被挤成两行。
   所以"实际预览 + 差异图"是必看项，不能只看 SVG。

## 7 我们怎么用（已落地）

工具**独立安装**在 `~/.dsh/tools/svg-native-pptx/`，**不在本仓库、不在本 skill 包内**；
我们的 skill 只写调用说明（`proposal-exports/references/external-calls.md`）。

| 动作 | 命令 |
| --- | --- |
| 转原生 PPT | `python ~/.dsh/tools/svg-native-pptx/powerpoint_native.py --svg 图1.svg --output out/图1-ppt` |
| 转原生 AI（需装 Illustrator） | `python ~/.dsh/tools/svg-native-pptx/illustrator_native.py --svg 图1.svg --output out/图1-ai` |
| 依赖 | `pip install python-pptx CairoSVG cairocffi skia-pathops fonttools svgelements pywin32 svgpathtools cssselect2 tinycss2 pillow` |
| 来源/许可 | 工具目录内 `SOURCE.md` + `LICENSE`（MIT，未修改） |

不调用其付费出图接口。


与现有 `update_pptx_images.py` 的分工：

- **图已定稿**、只要塞进模板 → 换图（快、字节级不动版式）；
- **评审要改字/挪框** → 转原生（慢几十秒，但每个字都能改）。

## 8 局限与风险

- **平台绑定**：需要 Windows + 桌面版 PowerPoint；Illustrator 路线还需要 AI。无 Office 的机器只能拿 pptx，不能出预览。
- **近似项**：渐变转色带、成组透明度近似（`gradient_objects` / `group_opacity_approximations` 会计数），复杂蒙版不保证。
- **字体**：本机缺字体会走后备并记 `font_fallback_glyphs`；申报书建议统一 `Microsoft YaHei` / `SimHei`。
- **第三方代码**：独立安装、原样使用；升级时整目录替换并重跑第 5 节验收数字；MIT 要求保留 `LICENSE` 与来源说明。
- **PowerPoint 自动化**：会短暂启动 POWERPNT 进程（实测退出后无残留），在无桌面会话的服务器上不可用。

## 9 与"AI 生图"的边界

| 路线 | 产物 | 能改哪个字 | 费用 |
| --- | --- | --- | --- |
| cell_cns 付费 API | 一张图（SVG/位图） | 能改的只有它给的矢量整图 | 20/45 额度、约 3 小时 |
| GPT-Image2 | 位图 | 不能 | 按次计费 |
| **本文这条（本地转换）** | PPT 原生形状 + 文本框 / AI 原生文档 | **逐字、逐框** | **0（只用本机软件）** |

## 10 下一步（建议）

1. 把 `powerpoint_native.py` 写进 PPT 交付清单（与换图并列，按"是否要改"选）；
2. 清理模板里的 U+3000（`assets/template.svg` 的 `层次一　阶段名`），否则演示转换会拆字；
3. 若你机器上装了 Illustrator，我再跑一次 `illustrator_native.py` 验证 AI 路线；
4. 长期：跟踪上游 commit，升级时整目录替换 + 重跑本文第 5 节的验收数字。
