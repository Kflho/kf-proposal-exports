# 设计记录：proposal-exports 加入 PPT 交付能力

> 类型：技术方案（skill 结构变更）
> 日期：2026-10　｜　状态：实现中
> 关联证据：`references/case-notes.md` §5（外部 skill 调研）、`../../sk_05/RESEARCH-ppt-skills.md` §6（官方 pptx skill 本机实测）

## 问题

申报书/答辩材料有**两种交付物**：结构图（SVG/PNG）与**页片（PPT）**。本 skill 原来只覆盖前一半：

1. 图有规范与 5 个几何/一致性检查，页片没有；
2. 中文技术页片的三个高频缺陷（公式白底、标点孤行、图片拉伸）没有机械检查，只能靠目视；
3. skill 名叫 `proposal-pictures`，但实际交付面已经包含整册页片，名字与职责不符。

完成判据：**两类交付物都能被同一个 skill 用同一套"先设计、后生成、再自检"的流程产出，且新增页片能力有可执行的检查脚本与测试。**

## 证据

| 证据 | 结论 |
|---|---|
| `sk_05/RESEARCH-ppt-skills.md` §6：官方 `pptx` skill 5 页实测（3 轮迭代） | pptxgenjs 路线可用；暴露 3 个中文场景缺陷：公式白底、CJK 标点孤行、拉伸；另发现 `validate.py` 在 GBK 下崩、预览依赖 LibreOffice |
| 同文档 §6.6：PowerPoint COM 导出 PNG | 本机已装 Office，COM 预览成功，中文渲染正常；可替代 LibreOffice |
| `scripts/update_pptx_images.py`、`fit_pptx_frames.py` | 已有"改图不毁版式""按真实比例重排图片框"两块能力，属于页片侧，可保留并归入新的 PPT 章节 |
| 官方 `pptx` skill（anthropics/skills） | 生成/编辑/校验/QA 的权威做法；本 skill **不复写** OOXML 手术，只引用它 |

## 方案

**做什么**

1. 重命名：`proposal-pictures` → `proposal-exports`（目录、frontmatter `name`、README、引用）；
2. 新增三条页片工具链脚本：
   - `formula_png.py`：LaTeX → 透明 PNG（400 dpi，裁白边，可选透明），产出 `sizes.json`；
   - `deck_check.py`：`.pptx` 静态检查（16:9、安全边距、文字溢出估算、图片比例、备注、占位符）；
   - `render_pptx_png.py`：PowerPoint COM 逐页导出 PNG（无 Office 时明确报错，不静默降级）；
3. 新增 `references/ppt-deck.md`：页片五步流程、版式令牌、四条本地纪律、QA 清单；
4. 新增 `assets/deck/`：`gen_deck.js` 起手模板（3 种版式 + 备注）+ `formulas.example.json`；
5. 新增 `tests/`：pytest 覆盖三条脚本的关键行为与结构回归（旧名字不得再出现）。

**不做什么**

- 不自己写 OOXML 生成器（用 `pptxgenjs`），不重写官方的 `add_slide/clean/validate`；
- 不做 HTML/网页版 deck（不在本 skill 交付面）；
- 不引入 LibreOffice（本机用 PowerPoint COM，更接近用户最终打开效果）；
- 不把 PPT 模板做成"任意主题可换肤"——先固定两套令牌（浅色/深色），等第二个用例再抽象。

**接口**

```
formulas.json  --formula_png.py-->  out/*.png + out/sizes.json
gen_deck.js（复制改）--node-->      deck.pptx
deck.pptx      --deck_check.py-->   问题清单（0 error 才可交付）
deck.pptx      --render_pptx_png.py--> preview/*.png（目视）
```

## 假设

1. **H1**：把"公式透明 + 文本框宽度按字数估 + 图片按真实比例入槽"做成脚本检查后，v1→v3 暴露的三类缺陷可以被机械拦住（不需要每轮靠眼睛发现）。
2. **H2**：`deck_check.py` 用 python-pptx 读几何 + Pillow 量字，在 16:9、文本框不自动缩放的前提下，误报率可接受（容差 2%/5%）。
3. **H3**：重命名只影响文档与 frontmatter，脚本无绝对路径依赖，旧的图流程（Graphviz/SVG/检查）不受影响。

## 变量

- 自变量：是否启用透明公式、是否跑 `deck_check`、文本框宽度/字号；
- 因变量：`deck_check` 的 error/warning 数、目视缺陷数、pytest 结果；
- 控制：同一份 v3 页片（`sk_05/ppt-skill-test/ex01_v3.pptx`）作为回归样本。

## 指标

| 指标 | 方式 | 目标 |
|---|---|---|
| 脚本行为 | `pytest -q` | 全绿 |
| 误报 | `deck_check.py` 跑 v3 样本 | 0 error（warning ≤ 2，且每条都能解释） |
| 漏报 | 人工构造坏样例（拉伸图、越界、占位符、无备注） | 全部被报出（测试覆盖） |
| 规范 | `manage.py check` + `privacy/scan.py` + `text_review.py` | 0 error |

## 对照

- 基线：v1 页片（白底公式、无加粗、无检查）→ 3 轮目视返工；
- 新流程：`formula_png.py --alpha` + `deck_check.py` → 同样的缺陷在导出前被报出；
- 对照判据：v3 样本通过，v1 的缺陷能在坏样例里复现并被拦住。

## 失败判据

- 若 `deck_check.py` 对 v3 样本报出**无法解释的 error**，或对"白底公式/拉伸图/占位符"三类坏样例**全部漏报**，则 H1/H2 不成立，回退到"纯目视 + 四条纪律"的手工流程；
- 若重命名后任一旧脚本/文档断链（引用 404），或 `proposal-pictures` 字符串仍出现在跟踪文件里，则 H3 不成立；
- 若新增脚本引入不可安装依赖（非 pip 包、非系统已有工具）且无明确报错，方案作废。

## 风险与回退

| 风险 | 影响 | 回退 |
|---|---|---|
| python-pptx / Pillow 依赖 | 无 pip 环境跑不了检查 | 脚本缺失依赖时明确报错并给安装命令；纯手工流程仍可用 |
| PowerPoint COM 仅 Windows | 换机器无预览 | 文档给官方 skill 的 soffice 路线；`render_pptx_png.py` 报错并提示 |
| pptxgenjs 需 Node | 无 Node 无法生成 | 文档写明；也可用 python-pptx 手工写（不在脚本里做） |
| 文字溢出估算不准 | 误报/漏报 | 容差保守（+5% 才报 warning）；默认 warning 不阻断，`--strict` 才拦 |

## 决策留痕

- 重命名理由：交付面从"图"扩到"图 + 页片"（依据：本文问题 1–3）。
- 用 python-pptx 做检查而非自写 XML 解析：读几何/图片原生尺寸的成本低，且与官方 skill 的编辑路线不冲突（工程选择）。
- 公式走 LaTeX→PNG 而非 PPT 原生 OMML：v1 实测图片效果更好、无字体替换风险；OMML 留作 v2（依据：`sk_05` §6.4）。
- 预览用 COM 而非 LibreOffice：本机无 LibreOffice，且 COM 渲染即用户所见（依据：§6 实测）。
