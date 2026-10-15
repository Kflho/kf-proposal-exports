#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""设计令牌（design tokens）——本 skill 出图的**单一真源**。

依据
  · 色板：Wong 无障碍色板（Okabe-Ito 同源），Nature 官方规范推荐
    Wong, B. Points of view: Colour blindness. Nature Methods 8, 441 (2011)
  · 文字：sans-serif；**成品尺寸下 5–7 pt**；面板号 8 pt 粗体小写；**不用彩色文字**
  · 禁用：背景网格、装饰图标、投影、图案填充
  · 交付：矢量优先；栅格图 ≥300 dpi

关键约定：**按成品尺寸设计**。图的 SVG 坐标 = 交付时的 pt（1:1），
于是这里的字号就是最终字号，不再需要换算。
"""

# ---------------- 色板：Wong 无障碍八色 ----------------
WONG = {
    'black':     '#000000',
    'orange':    '#E69F00',
    'sky':       '#56B4E9',
    'green':     '#009E73',
    'yellow':    '#F0E442',
    'blue':      '#0072B2',
    'vermillion': '#D55E00',
    'purple':    '#CC79A7',
}

# ---------------- 语义色（颜色只用于框线/色块/键线，不用于文字）----------------
STRUCT = WONG['blue']          # 结构、主流程
ACCENT = WONG['orange']        # 产出、强调
VERIFY = WONG['green']         # 验证、评测
NEUTRAL = WONG['black']        # 文字、坐标轴
INK = '#000000'                # 正文文字（黑）
MUTED = '#555555'              # 次要文字（灰，非彩色）
# 浅底（同色系 8% 明度，保证黑字对比度 >4.5:1）
STRUCT_BG = '#E8F1FA'
ACCENT_BG = '#FDF3E3'
VERIFY_BG = '#E7F5F0'
BAND_BG = '#EDF3F8'            # 层次带底
SURFACE = '#FFFFFF'

# ---------------- 字号档位（**成品 pt**，按 Nature 规范 5–7 pt）----------------
FS = {
    'title':  9.0,      # 整幅标题（唯一允许 >7pt 的文字）
    'h1':     7.0,      # 层次/行标题（上限 7pt）
    'label':  7.0,      # 格内粗体小标题（上限 7pt）
    'body':   6.5,      # 正文
    'note':   5.5,      # 脚注、边上标注（下限 5pt）
    'panel':  8.0,      # 面板编号 a/b/c：8 pt 粗体、正体
}

# ---------------- 线宽（成品 pt，统一档位，不再 1.5/1.8/2 混用）----------------
LW = {'frame': 0.8, 'connector': 0.6, 'emphasis': 1.2}

# ---------------- 间距（成品 pt）----------------
GAP = {'xs': 3, 'sm': 6, 'md': 9, 'lg': 14, 'xl': 20}
PAD = {'cell_x': 6, 'cell_y': 4}

# ---------------- 字体 ----------------
FONT = 'Arial, Helvetica, Microsoft YaHei, sans-serif'   # 西文标准 + 中文回退

# ---------------- Graphviz 便捷取值 ----------------
GV_NODE = (f'shape=box, style="rounded,filled", fillcolor="{STRUCT_BG}", color="{STRUCT}", '
           f'penwidth={LW["frame"]}, fontname="{FONT}", fontsize={FS["body"]}, '
           f'fontcolor="{INK}", margin="0.10,0.06"')
GV_EDGE = (f'color="{STRUCT}", penwidth={LW["connector"]}, arrowsize=0.7, '
           f'fontname="{FONT}", fontsize={FS["note"]}, fontcolor="{MUTED}"')
GV_GRAPH = (f'fontname="{FONT}", bgcolor="{SURFACE}", nodesep=0.30, ranksep=0.40')


def panel(letter):
    """面板编号（8 pt 粗体、小写、正体）。"""
    return f'<B><FONT POINT-SIZE="{FS["panel"]}">{letter}</FONT></B>'
