# 页片生成器：生成 + 回灌

> 交付物 `.pptx` 是会被**人**改的（评审批注、老师要求、补图改字）。生成器和产物是两份真相，
> 只做单向生成，下一次重跑就把人工改动覆盖掉。这一页定义回路：**代码生成页片，页片里的修改能同步回代码**。

## 生成器契约

| 契约 | 做法 | 检查 |
| --- | --- | --- |
| 内容与版式分离 | 每页文案集中在「内容区」或 `deck-content.json`；版式函数不写具体句子 | 改文案只动一处 |
| 页数断言 | `if (pres.slides.length !== N) throw new Error(...)` | 删/加页必须先改断言 |
| 页码由代码算 | `${n} / ${total}`，不手写 | `deck_check` 不把它当正文 |
| 令牌常量化 | 字体、字号、颜色走常量（`TITLE_FONT` / `T` / 配色常量） | `deck_check --scale` 过 |
| 幂等 | 同一输入重跑，`deck_spec.py --compare` 为 0 差异 | 回灌后的验收 |

## 回灌流程（五步）

```bash
# 1) 生成器出基线版
node gen_deck.js --out out/deck_v1.pptx

# 2) 在 PowerPoint 里改（评审意见、补图、改文字）→ deck_v2.pptx

# 3) 比差异：逐页逐项列出新增/删除/文字变了/位置变了
python scripts/deck_spec.py --compare out/deck_v1.pptx out/deck_v2.pptx

# 4) 按差异回灌内容区 / 版式函数 / 图片路径（图片落到项目 data 路径，别嵌在 pptx 里当唯一副本）

# 5) 重生成并复验：只剩预期差异才算回灌完成
node gen_deck.js --out out/deck_v1b.pptx
python scripts/deck_spec.py --compare out/deck_v1b.pptx out/deck_v2.pptx
python scripts/deck_gate.py out/deck_v1b.pptx --strict --require-notes
```

`deck_spec.py` 还可以只拆不比较：

```bash
python scripts/deck_spec.py out/deck_v2.pptx --out out/deck_v2.spec.json --assets out/assets
```

## 差异怎么读

| 差异 | 含义 | 处理 |
| --- | --- | --- |
| `added` / `removed` | 内容或形状增删（文字变了也会显示成一对增删） | 必须回灌：文字进内容区，形状进版式函数 |
| `moved` | 位置/尺寸变了 | 回灌坐标；若只是手工微调，登记「下次生成会丢」 |
| `notes` | 口播备注改了 | 回内容区 |
| `page-count` | 页数变了 | 先改页数断言与页码，再补内容 |

**预期差异**（不算回灌失败）：字体名不同（`deck_fonts.py` 统一改写）、页码文本、形状顺序。
比之前可先用 `deck_gate.py`（含 `fonts` 步）把两边字体对齐，差异会干净很多。

## 限制

- PowerPoint 的 SmartArt、原生图表、内嵌视频只能识别到形状级别，回灌要人工；
- 图片按资产名比较，同名不同内容不报差异（要严格时按哈希另存新名再比）；
- 生成器改完必须重跑 `deck_gate.py` + 预览：`deck_spec` 只比结构，不比"这页说不说得通"。

## 反例

- 只改 `.pptx`、不回灌：下次 `node gen_deck.js` 全丢（lab12 的真实事故：10-22 生成 13 页 →
  10-25 生成器删成 11 页 → 产物没重跑 → 10-26 又有人手改产物，源和产物彻底分叉）；
- 回灌时把内容写进版式函数：下次改文案要翻函数体，`--compare` 也会因为位置跟着变而报一堆 `moved`。
