function fname = export_figure(fig, outDir, name, widthInch)
%EXPORT_FIGURE  按统一规范导出 PNG（600 dpi，不存 .fig）。
%
%   fname = export_figure(fig, outDir, name)
%   fname = export_figure(fig, outDir, name, widthInch)
%
%   依赖 matlab-project-utils 已在路径上（run_visualization、export_fig_paper）。
%   流程：run_visualization 统一坐标轴/标签/标题/图例/线宽 → 统一 sgtitle 字体
%         → export_fig_paper 以 600 dpi 导出 PNG。
%
%   widthInch：成品宽度（in）。报告/PPT 默认 7.5；论文单栏 3.5、双栏 7.0。
%   规则见 kf-proposal-exports/references/matlab-figures.md。

if nargin < 4 || isempty(widthInch), widthInch = 7.5; end
if ~exist(outDir, 'dir'), mkdir(outDir); end
if ~exist('run_visualization', 'file') || ~exist('export_fig_paper', 'file')
    error(['先把 matlab-project-utils 加入路径：' ...
           'addpath(genpath(''<path-to>/matlab-project-utils''))']);
end

% 统一坐标轴、标签、标题、图例、线宽
run_visualization(fig);

% run_visualization 不处理 sgtitle，这里统一一次（仅布局文本，不碰坐标轴标题）
hText = findall(fig, 'Type', 'Text');
for k = 1:numel(hText)
    if isa(hText(k), 'matlab.graphics.layout.Text')
        set(hText(k), 'FontName', '宋体', 'FontSize', 12, 'FontWeight', 'bold');
    end
end

fname = fullfile(outDir, [name '.png']);
export_fig_paper(fig, fullfile(outDir, name), widthInch);
end
