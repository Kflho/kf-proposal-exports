# 页片外部能力：调用清单与契约

> 本文件只写**何时调谁、给什么、拿回什么、回来查什么**；规则正文在上游，不复制。
> 研究快照：`nature-paper2ppt`（镜像仓 `ypan50918-ops/Yuan1z0825-nature-skills`，sparse
> `skills/nature-paper2ppt` + `skills/nature-shared`）、`academic-ppt`（`PHY041/claude-skill-academic-ppt`，
> commit `43c2a0c`）。本机 git 走 `ssh://git@ssh.github.com:443`（https:443 不通）。

## 1 选路

| 手上的东西 | 要的东西 | 走谁 |
|---|---|---|
| 论文 / PDF / LaTeX / 图注 | **中文**文献汇报、组会、答辩 deck | `nature-paper2ppt` |
| 论文 / PDF / LaTeX | 英文学术报告，需要 **Q&A 预测**与逐页口播模板 | `academic-ppt` |
| 只有讲稿 / 申报书正文 / 要点清单 | 申报、答辩、项目汇报页片 | **本仓** `assets/deck/gen_deck.js`（`references/ppt-deck.md`） |
| 已有一版 `.pptx` | 换图、按比例重排图片框 | 本仓 `scripts/update_pptx_images.py`、`fit_pptx_frames.py` |
| 已有一版 `.pptx` | 加页 / 删页 / 改 XML / schema 校验 | 官方 `pptx` skill（本机**未装**，见 §4） |

判定顺序：先看输入是"论文"还是"讲稿"，再看语言，最后看要不要改已有 deck。**不要两种方式各做一半**：
外部 skill 出的 deck 就用它的版式，本仓只做检查与补图。

## 2 `nature-paper2ppt`（中文论文汇报）

安装（本机验证过的镜像路线）：

```bash
git clone --depth 1 --filter=blob:none --sparse \
  ssh://git@ssh.github.com:443/ypan50918-ops/Yuan1z0825-nature-skills.git <目标目录>
git -C <目标目录> sparse-checkout set skills/nature-paper2ppt skills/nature-shared
# 上游正规路线（需 https 可达）：npx skills add Yuan1z0825/nature-skills --skill nature-paper2ppt --skill nature-shared
```

调用契约：

| 项 | 内容 |
|---|---|
| 输入给它 | 论文来源（PDF/文本/图注）、场景（组会 / 答辩）、页数或时长预算、图表资产清单、语言=中文 |
| 它会做 | 判论文类型 → 只加载对应 fragment → 建论证链 → 选图与裁切 → 写中文页面与口播 → 生成 `.pptx` → `audit_pptx_quality.py` 自检 |
| 产物 | `output/final_presentation_cn.pptx`、`output/qa_report.md`、`output/assets/figures/`、`output/asset_manifest.md` |
| 回来必查 | 它自己的 `qa_report.md`（high 级问题=0）+ 本仓 `deck_check.py` + `text_check.py` + 预览逐页目视 |

它的设计/排版规则（页面密度、版式族、反模板、对齐、中文去套话）见其 `references/design-and-layout.md`；
本仓 `references/ppt-deck.md` 只引用、不重写。它的审计脚本 `scripts/audit_pptx_quality.py`
（纯 python-pptx 读 OOXML：出界、文字过载、图片裁剪、小图、近身对齐、AI 模板短语）由
`scripts/deck_gate.py` 自动接上。

## 3 `academic-ppt`（答辩结构 + Q&A）

安装：

```bash
git clone --depth 1 ssh://git@ssh.github.com:443/PHY041/claude-skill-academic-ppt.git <目标目录>
pip install python-pptx matplotlib seaborn pymupdf Pillow Pygments   # 可选：google-genai / @mermaid-js/mermaid-cli
```

调用契约：

| 项 | 内容 |
|---|---|
| 输入给它 | `--latex` 或 PDF 或文字描述；`--scene defense|conference|seminar`；`--time`；`--lang zh` |
| 它会做 | 金字塔结构（Situation → Complication → Resolution）→ action title + ghost deck 自检 → 图（Matplotlib / Gemini / Mermaid）→ 装配 pptx → 结构 QA + 数字溯源提示 |
| 产物 | `<name>.pptx`、`<name>_figures/`、`<name>_matplotlib_code/`、`<name>_log.txt` |
| 回来必查 | 页数是否合时长、数字是否都能在正文找到出处、图是否按真实比例入槽、本仓三项检查 |

它的口播模板（说什么 / 要点 / 时长 / 过渡 / 预判提问）与 Q&A 五类问题，是本仓没有的能力：
要口播稿时直接用它的模板，不在本仓另写一套。

## 4 官方 `pptx` skill（未装，只作回退说明）

本机 `~/.dsh`、`~/.claude`、`~/.codex` 均无 `skills/pptx`，所以"跑 `validate.py`"这条**目前不可执行**。
它的能力面（`html2pptx.js` 把 HTML 转原生 pptx；`thumbnail.py` / `inventory.py` / `rearrange.py` /
`replace.py`；OOXML schema + `validate.py`）与本仓的分工：**结构性编辑与 schema 校验归它**，
本仓只做换图与自检。装好后按 `add_slide.py` / `clean.py` / `validate.py` 的原命令调用；
未装时结构性编辑走人工，不假装有闸门。

## 5 回退与失败处理

| 情况 | 处理 |
|---|---|
| 外部 skill 未装 / 网络不通 | 本仓 `gen_deck.js` + `ppt-deck.md` 五步；在交付说明里写明走了回退 |
| 外部生成失败 | 保留它的 `qa_report.md` / figure plan 当素材，转本仓模板重排 |
| 外部版式与项目令牌冲突 | 以外部为准（它管叙事与版式），本仓只追加令牌检查；冲突写进交付说明 |
| 外部审计脚本路径不确定 | `deck_gate.py --external-script <path>` 显式指定；找不到就跳过并在汇总里标 `skipped` |

**分工红线**：外部 skill 管"论文→页片"的叙事与版式；本仓管中文申报令牌、指标表述、图与公式、
换图、自检封装。外部有的规则**只引用**，不在本仓重写第二套（重复的口径必然漂移）。
