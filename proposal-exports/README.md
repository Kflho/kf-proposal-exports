# kf-proposal-exports

中文技术申报书 / 方案 / 答辩材料的交付规范：配图（SVG 优先）、页片（PPT）和报告文字。
入口与命令见 [SKILL.md](SKILL.md)；配图/页片/文字的具体规则在 `references/`。

## 测试

```bash
python -m pytest tests -q
```

只测纯逻辑、模板与静态检查；实际 PowerPoint / TeX / 目视验收仍需人工。
