% FIGURE_CASES  按 matlab-figures.md 的出图用例（可直接运行）
%
%   前置：把 matlab-project-utils 加入路径，或设置环境变量 MATLAB_PROJECT_UTILS：
%       addpath(genpath('<path-to>/matlab-project-utils'));
%
%   运行：
%       matlab -batch "run('figure_cases.m')"
%
%   产物默认写到系统临时目录 matlab_figure_cases/；运行前设 outDir=... 可改。
%   四种用例：
%       1. 单图
%       2. 循环中出图（每轮新建 figure，导出后 close）
%       3. 分栏图（tiledlayout，2×2）
%       4. 半对数图 + 参考线 + 图例

thisDir = fileparts(mfilename('fullpath'));
addpath(thisDir);                       % export_figure.m 在本目录

utilsRoot = getenv('MATLAB_PROJECT_UTILS');
if ~isempty(utilsRoot)
    addpath(genpath(utilsRoot));
end
if ~exist('run_visualization', 'file') || ~exist('export_fig_paper', 'file')
    error('先把 matlab-project-utils 加入路径，或设置 MATLAB_PROJECT_UTILS。');
end

if ~exist('outDir', 'var') || isempty(outDir)
    outDir = fullfile(tempdir, 'matlab_figure_cases');
end
t = linspace(0, 10, 600);

%% 1. 单图
fig = figure('Visible', 'off', 'Position', [60 60 1000 420]);
plot(t, exp(-0.4 * t) .* sin(2 * t), 'LineWidth', 1.6);
grid on;
xlabel('t [s]'); ylabel('y(t)');
title('单图：衰减振荡');
legend({'y(t)'}, 'Location', 'best');
export_figure(fig, outDir, 'case_single');
close(fig);

%% 2. 循环中出图
for k = 1:3
    fig = figure('Visible', 'off', 'Position', [60 60 1000 420]);
    plot(t, sin(k * t), 'LineWidth', 1.6);
    grid on;
    xlabel('t [s]'); ylabel('y(t)');
    title(sprintf('循环出图：k = %d', k));
    export_figure(fig, outDir, sprintf('case_loop_%02d', k));
    close(fig);
end

%% 3. 分栏图（tiledlayout）
fig = figure('Visible', 'off', 'Position', [60 60 1100 700]);
tiledlayout(fig, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');
for i = 1:4
    nexttile;
    plot(t, exp(-0.2 * i * t) .* cos(i * t), 'LineWidth', 1.6);
    grid on;
    xlabel('t [s]'); ylabel(sprintf('y_%d', i));
    title(sprintf('子图 %d', i));
end
sgtitle('分栏图：2×2 子图');
export_figure(fig, outDir, 'case_tiles', 7.5);
close(fig);

%% 4. 半对数图 + 参考线
fig = figure('Visible', 'off', 'Position', [60 60 1000 420]);
semilogy(t, exp(-t) + 1e-4, 'LineWidth', 1.6);
hold on;
yline(1e-2, '--', '阈值 0.01');
grid on;
xlabel('t [s]'); ylabel('|e(t)|');
title('半对数图：误差与阈值');
legend({'|e(t)|', '阈值'}, 'Location', 'best');
export_figure(fig, outDir, 'case_log');
close(fig);

fprintf('出图样例已写入：%s\n', outDir);
