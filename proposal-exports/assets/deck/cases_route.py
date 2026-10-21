# -*- coding: utf-8 -*-
"""layout_flow.py 的路线图案例：8 站组网协作调度的技术路线。

用法：
    python scripts/layout_flow.py assets/deck/cases_route.py --out out/route.svg --apply --report
"""

CANVAS_W = 1600
STRIP_X = 40
STRIP_W = 70
MARGIN_L = 40
COL_W = 440
GUTTER = 40
PAD_X = 24
PAD_V = 20
FS_LABEL = 20
FS_BODY = 24
FS_TITLE = 28
FS_FULL = 22
LH = 1.5
GAP_LABEL = 16
TOP = 100
ROW_GAP = 40
STRIP_FS = 13
TITLE = "组网协作调度技术路线"

ROWS = [
    {
        "kind": "full",
        "name": "前期调研",
        "fs": FS_FULL,
        "text": [
            "研究背景：遮挡导致单站测距掉点",
            "研究现状：国内外机构、成果、应用、论文与专利",
        ],
    },
    {
        "kind": "cols",
        "name": "研究内容",
        "labels": ["4-1", "4-2", "4-3"],
        "label_fs": 18,
        "text": [
            "联合资源分配",
            "遮挡检测与替补",
            "外场验证",
        ],
    },
    {
        "kind": "full",
        "name": "课题分解",
        "fs": FS_FULL,
        "text": [
            "研究内容 → 目标与子课题；目标可量化、可验证",
        ],
    },
    {
        "kind": "cols",
        "name": "实验验证",
        "labels": ["定性", "定量", "外场"],
        "label_fs": 18,
        "text": [
            "遮挡 30% 有提升",
            "500 次蒙特卡洛",
            "3 个真实场景",
        ],
    },
    {
        "kind": "full",
        "name": "结论",
        "fs": FS_FULL,
        "text": [
            "8 站、100 ms 下可用率 96%；50% 遮挡需加站",
        ],
    },
]
