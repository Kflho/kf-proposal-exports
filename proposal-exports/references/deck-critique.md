# 页片审美评估：两个接入点，一条可查的留痕

> taste-skill 是**网页**的设计 skill（浏览器检查器 `inspect.mjs` 读不了 `.pptx`）。能搬的是它的
> **法条**：两三档字号、一个强调、左对齐、居中最多一次、不空不挤、不用渐变阴影。
> 本文件把"审美"从一句口号变成流程里的两步 + 一份可查的报告。

## 接入点 1：定令牌之前（决策）

拿 `taste-skill` 的 `draw.mjs` 抽三个方向，选一个并写一行理由，落到
`references/design-notes/`（已有实例：`deck-aesthetics.md`，含 seed 与重画登记）。
**不写这一步就不改令牌**——否则审美只是默认值。

## 接入点 2：交付之前（评估）

```bash
python scripts/deck_critique.py out/deck.pptx --md out/deck_critique.md
# 或者直接走闸门（critique 是默认步之一）
python scripts/deck_gate.py out/deck.pptx --strict --require-notes
```

`deck_critique.py` 把可算的法条做成 8 条：

| 规则 | 判据 | 级别 |
| --- | --- | --- |
| L1 字号档位 | 一页 ≤5 档；最小 ≥8pt | FAIL |
| L2 强调色 | 每页 ≤2 处 | FAIL |
| L3 平色 | 无渐变、无阴影 | FAIL |
| L4 居中克制 | 全册居中标题 ≤1 页 | REVIEW |
| L5 轴线 | 标题与正文左缘对齐（或都居中） | REVIEW |
| L6 页满度 | 内容覆盖 30%–92% | REVIEW |
| L7 字体族 | 全册 ≤2 条非等宽族 | REVIEW |
| L8 主导 | 最大字号 ≥ 次大 × 1.6 | REVIEW |

**判读**：FAIL 必修；REVIEW 逐条写理由（模板决定的、刻意留白的都行）；最后人工三项必须逐页看过：

- [ ] 图注贴在图上、来源可查
- [ ] 每个数字都能在正文/方案里找到出处
- [ ] 标题连读能讲完故事

报告默认落在 deck 旁边的 `<deck>_critique.md`，随交付物一起留痕；不写这份文件等于没做审美评估。

## 和 deck_gate 的关系

`deck_gate` 的步骤是：`fonts → deck_check → text_check → critique → external`。
critique 挂在这里的意义是**每次生成都会跑**，而不是"想起来才看一眼"；它对不上模板时按
REVIEW 报，不阻断交付，但要有结论。

## 已知边界

- 机械规则判断不了"这一页想说什么"；L4–L8 只负责把可疑页挑出来；
- 模板决定的版式（居中标题、留白比例）常触发 REVIEW，这是预期，写理由而不是改模板；
- 真正的审美方向选择在接入点 1，这里只做验收。
