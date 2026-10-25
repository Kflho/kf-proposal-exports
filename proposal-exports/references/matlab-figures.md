# MATLAB 数据图产物规范

> 本文件管**图本身**：走哪个统一入口、输出什么格式、放哪、怎么验收。
> 不管 MATLAB 代码风格与环境检测（在 `kf-personal-development` 的
> `references/appendix/matlab-style.md`、`matlab-env.md`）；也不管曲线怎么选型、
> 数据怎么算（绘图实现由项目和共享库负责）。

## 1 统一入口

MATLAB 项目用共享库 `matlab-project-utils`，不在每个脚本里重复设字体、线宽、图例：

| 入口 | 作用 |
| --- | --- |
| `visualizations/run_visualization(fig)` | 统一图窗、坐标轴、标签、标题、图例；数据线 1.5 pt，参考线 1.0 pt；标题超宽只告警，不自动换行 |
| `plots/plot_signals_v5(...)`、`plots/add_threshold(...)` | 只管数据与图例，格式交给 `run_visualization` |
| `plots/export_fig_paper(fig, name, widthInch)` | 按论文宽度导出 PNG，600 dpi；默认宽 5.5 in |

库根用 `addpath(genpath('matlab-project-utils'))` 加入路径；模块清单与最小调用示例见该库
`README.md`（`calculations`、`initialization`、`plots`、`visualizations`、`simulink`）。
画图与排版分开的约定也在那份 README 里。

## 2 封装：export_figure.m

把“统一格式 + 600 dpi 导出 + sgtitle 字体”封成一个函数（模板在
`assets/matlab/export_figure.m`）：

```matlab
fname = export_figure(fig, outDir, name);        % 报告/PPT，默认 7.5 in
fname = export_figure(fig, outDir, name, 5.5);   % 论文单栏
```

- 内部：`run_visualization(fig)` → 统一 `sgtitle` 字体 → `export_fig_paper(..., widthInch)`
  （600 dpi PNG，不存 `.fig`）；
- 依赖 `matlab-project-utils` 已在路径上；缺库直接报错，不静默降级；
- 宽度按目标版式定：报告/PPT 7.5 in，论文单栏 3.5、双栏 7.0。

## 3 常用用例

可运行样例：`assets/matlab/figure_cases.m`（单图 / 循环 / 分栏 / 半对数 + 参考线）。

### 3.1 单图

```matlab
fig = figure('Visible', 'off', 'Position', [60 60 1000 420]);
plot(t, y, 'LineWidth', 1.6); grid on;
xlabel('t [s]'); ylabel('y');
title('单图：衰减振荡');
legend({'y'}, 'Location', 'best');
export_figure(fig, outDir, 'case_single');
close(fig);
```

### 3.2 循环中出图

```matlab
for k = 1:3
    fig = figure('Visible', 'off', 'Position', [60 60 1000 420]);
    plot(t, sin(k * t), 'LineWidth', 1.6); grid on;
    xlabel('t [s]'); ylabel('y');
    title(sprintf('循环出图：k = %d', k));
    export_figure(fig, outDir, sprintf('case_loop_%02d', k));
    close(fig);
end
```

要点：每轮**新建** `figure`，文件名唯一，导出后 `close(fig)`；不要复用同一句柄、
不要在图窗里累积旧曲线。重跑前清空该实验的旧图。

### 3.3 分栏图（tiledlayout）

```matlab
fig = figure('Visible', 'off', 'Position', [60 60 1100 700]);
tiledlayout(fig, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');
for i = 1:4
    nexttile;
    plot(t, Y(:, i), 'LineWidth', 1.6); grid on;
    xlabel('t [s]'); ylabel(sprintf('y_%d', i));
    title(sprintf('子图 %d', i));
end
sgtitle('分栏图：2×2 子图');
export_figure(fig, outDir, 'case_tiles', 7.5);
close(fig);
```

要点：`run_visualization` 一次遍历整个 figure 的全部 axes，**只调一次**，不要在每个
`nexttile` 里重复调；`sgtitle` 由封装统一字体。

### 3.4 半对数 + 参考线

```matlab
fig = figure('Visible', 'off', 'Position', [60 60 1000 420]);
semilogy(t, abs(e), 'LineWidth', 1.6); hold on;
yline(1e-2, '--', '阈值 0.01'); grid on;
xlabel('t [s]'); ylabel('|e(t)|');
title('半对数图：误差与阈值');
legend({'|e(t)|', '阈值'}, 'Location', 'best');
export_figure(fig, outDir, 'case_log');
close(fig);
```

`xline`/`yline` 是 `ConstantLine`，封装把数据线设 1.5 pt、参考线 1.0 pt。

## 4 产物规则

- 只输出 PNG，不保存 `.fig`；不引入第三方绘图库；
- 中英双语各一套，写 `bin/exports/figures/{cn,eng}/experiment_XX/`；语言无关图放
  `bin/exports/figures/` 根目录。单语课程报告可以平铺 `figures/`，但同一交付内路径要一致；
- 标题单行，不带实验编号；超宽时精简措辞，数值参数放图例。`run_visualization` 以
  48 个半角宽为上限，出现 `[run_visualization] 标题超宽` 告警必须改标题后重跑；
- 重跑前清空该实验已有产出，避免新旧图混在一起；
- 图片只标注论文已定义的参数，实现细节（Monte Carlo 次数、仿真步数）不进图；
- 图片由实验脚本生成，写作阶段不重画；正文 `\includegraphics` 路径、图号/图注与图文件
  三处同步；
- 位图 ≥300 dpi（`export_fig_paper` 默认 600 dpi）；插入 PPT/Word 前确认图片比例与
  目标框一致，不拉伸；
- 论文/Note 里的“如图 N 所示”、图号、图注由文档侧统一编号，图文件不承担编号；
- 图注/表注/坐标轴单位的文字写法（指标名 + 口径 + 单位，与图内文字逐字一致）见
  `text-quality.md`。

## 5 交付前自检

- [ ] 所有图走 `run_visualization`，没有逐脚本设字体/线宽；
- [ ] 输出为 PNG、无 `.fig`，分辨率 ≥300 dpi；
- [ ] `bin/exports/figures/...` 路径与语言版本齐全（或单语路径一致）；
- [ ] 无 `[run_visualization] 标题超宽` 告警；标题单行、不带实验编号；
- [ ] 重跑前旧图已清理；
- [ ] 逐张打开看过：非空白、曲线与坐标图例符合预期；
- [ ] 论文里的图按页渲染核对，插入 PPT/Word 不变形。
