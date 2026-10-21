# Graphviz 正确用法（含踩坑记录）

> 依据官方文档：[Node Shapes / HTML-Like Labels](https://graphviz.org/doc/info/shapes.html)、
> [Attributes](https://graphviz.org/doc/info/attrs.html)、[dot 布局](https://graphviz.org/docs/layouts/dot/)、
> [DOT 语言](https://graphviz.org/doc/info/lang.html)。本文件只记**会踩坑**的部分。

## 0. 一句话原则

**对齐、分栏、表格式版式 → 用 HTML 表格（一个节点装整张表）；只有"有向流程"才用 dot 的多节点布局。**
把"精确版式"交给多节点自由布局，是本节所有事故的总根源。

## 1. HTML-like label（表格）

```dot
n [shape=plaintext, margin=0, label=<
  <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="4" CELLPADDING="8">
    <TR><TD COLSPAN="3" BGCOLOR="#0072B2"><FONT COLOR="white">标题</FONT></TD></TR>
    <TR>
      <TD PORT="a" WIDTH="120" FIXEDSIZE="TRUE" HEIGHT="40">甲</TD>
      <TD PORT="b" ROWSPAN="2" WIDTH="200">乙（纵跨两行）</TD>
      <TD PORT="c" WIDTH="120">丙</TD>
    </TR>
    <TR><TD PORT="d">丁</TD><TD PORT="e">戊</TD></TR>
  </TABLE>>];
```

规则（都是踩过的坑）：

| 项 | 规则 |
| --- | --- |
| 外层尖括号 | `label=< … >` 里必须是**恰好一张** `<TABLE>`；少一层尖括号 → `syntax error near '>'` |
| 换行 | HTML label 里用 `<BR/>`；**普通** label 用 `\n`。混用会把 `<BR/>` 原样打出来 |
| 字号 | HTML label 内用 `<FONT POINT-SIZE="9">`，**不是 `fontsize=`**；因此按比例缩放脚本必须同时处理 `fontsize=` 与 `POINT-SIZE=` |
| 尺寸 | `WIDTH`/`HEIGHT` 默认是**最小值**，内容大会撑开；要**精确等宽**必须加 `FIXEDSIZE="TRUE"`（且 WIDTH/HEIGHT 都要给） |
| 对齐 | `ALIGN="LEFT|CENTER|RIGHT"`（水平）、`BALIGN`（垂直）；`<BR ALIGN="LEFT"/>` 控制单行对齐 |
| 跨格 | `ROWSPAN` / `COLSPAN` 可用；`PORT` 加在 `<TD>` 上，边用 `node:port` 引用 |
| 不支持的属性 | `PENWIDTH` 在 `<TD>` 上**非法**（会被忽略并告警）；线宽只能靠最外层 `penwidth` 或嵌套 `<TABLE>` |
| 节点外壳 | 用表格做版式时节点要 `shape=plaintext, margin=0`，否则外面多一圈框 |

### 1.1 为什么"多行 = 多节点"必然对不齐

实测（本项目图3 的 Graphviz 版）：每行做成独立节点后，`dot` **逐个节点居中**，而每行的表宽由内容决定 →
`行1 左标签列 x=3.0`、`行2 左标签列 x=57.5`，**差 54.5pt**，列自然全部错开。

两条正解：

1. **整张表装进一个节点**（推荐）：所有行列由同一张 `<TABLE>` 决定，列边界**不可能**不一致。
   代价：同一节点内的单元格之间**不能画边**（边只能连不同节点）。
2. **多节点但几何锁死**：每个格都 `FIXEDSIZE="TRUE"` + 相同 `WIDTH`/`HEIGHT`，使每行表宽逐点相同，
   再靠 `dot` 居中 → 行与行重合。可行但脆（改一个字就可能越界），只在"行间必须画箭头"时用。

## 2. 布局控制（dot 引擎）

| 目标 | 正确做法 | 不要用 |
| --- | --- | --- |
| 同排 | `{rank=same; a; b; c}` | 靠声明顺序猜 |
| 层距 / 同层间距 | `ranksep` / `nodesep`（英寸） | 塞空格 |
| 精确画布尺寸 | `size="11.2,6.3!"` + `ratio=fill`；实测 **`ratio=<数值>` 取的是 高/宽**（`rankdir=TB` 下） | 事后拉伸位图 |
| 让边拉直 | `weight`（同向累加）、`group="g"`（同组边尽量成直线） | 手工调坐标 |
| 允许逆向边 | `constraint=false`（**不参与分层**，但会绕远） | 到处 `constraint=false`（会把布局拉散） |
| 并列嵌套 | `subgraph cluster_x { … }`，跨 cluster 连边要 `compound=true` + `lhead/ltail` | 用不可见边硬拉 |
| 正交折线 | `splines=ortho`（对 cluster/rank 敏感，易崩或绕远）；一般用 `splines=polyline` | 指望 `ortho` 自动好看 |
| 节点精确尺寸 | `fixedsize=true` + `width/height`（**英寸**，非像素） | 用像素值 |

**单位陷阱**：`width`/`height`/`ranksep`/`nodesep`/`margin` 是**英寸**；`fontsize` 是**点**；`dpi` 只影响栅格输出。
按比例缩放时这几类**都要一起缩放**（漏掉 `width` 会让节点不肯变小，字号被越缩越小、迭代不收敛）。

## 3. 输出

```bash
dot -Tsvg fig.gv -o fig.svg          # 矢量；无 <style>/无内嵌字体/base64，文字可编辑
dot -Tpng -Gdpi=300 fig.gv -o fig.png # 位图；300dpi 起步
```

SVG 的 `width/height` 默认带 `pt`；有些工具（含本 skill 早期的 `render_svg.py`）只认纯数字，
解析失败会**回退默认窗口** → 图缩在角落。跨工具流转时把宽高写成无单位像素、`viewBox` 保留 pt。

## 4. 检查清单（出图前过一遍）

1. 表格版式是否只用了**一张表**（或每格都 `FIXEDSIZE`）？
2. `label=` 的尖括号层次对不对？`<BR/>` 用对了吗？
3. 需要精确尺寸的格有没有 `FIXEDSIZE="TRUE"` + WIDTH/HEIGHT？
4. `fontsize` 与 `POINT-SIZE` 是否都被缩放覆盖？
5. 单位是否分清了英寸/点？
6. 出图后跑 `check_overlap.py`，并**亲眼看渲染图**。

## 5. 本项目事故记录（供后人避坑）

| 事故 | 根因 |
| --- | --- |
| 图1 版式被摊成大网 | 把"严格 1-3-1 版式"交给 dot 的自由布局，又用 `rank=same`/cluster 硬拧 |
| 图3 行列对不齐 | 每行一个独立节点，行宽由内容决定 → 居中位置各行不同 |
| 边标注压线/被框盖住 | 依赖引擎自动放标注，且线画在框**下层**；正解是标注挂水平短段并整块置于线上方，或自行在槽位内摆位 |
| 字号失衡（边标注大、节点字小） | 缩放脚本只改 `fontsize=`，漏了 HTML label 里的 `POINT-SIZE` |
| 迭代缩尺不收敛 | 漏缩 `width`（英寸硬下限） |
