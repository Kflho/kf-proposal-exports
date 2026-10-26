"""layout_flow.py：生成前验收能拦住"超宽/行首标点/越界"。

判据（scripts/layout_flow.py 的 verify + post_check）：
- 正常 case：--apply 返回 0，产出 SVG，回读校验通过；
- 坏 case（通栏以标点开头）：返回 1 并打印"生成前验收失败"，不写文件。
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "layout_flow.py"

BASE = """
CANVAS_W = 960
STRIP_X = 24
STRIP_W = 56
STRIP_FS = 14
COL_W = 264
GUTTER = 24
MARGIN_L = 24
PAD_X = 12
PAD_V = 12
FS_LABEL = 12
FS_BODY = 14
FS_TITLE = 16
FS_FULL = 15
LH = 1.5
GAP_LABEL = 8
TOP = 90
ROW_GAP = 26
TITLE = "方法流程"
ROWS = [
    {"kind": "cols", "name": "阶段一", "labels": ["输入", "处理", "输出"],
     "text": ["测距数据", "联合分配", "可用率"]},
    {"kind": "full", "name": "通栏", "text": [%s], "fs": FS_FULL},
]
"""


def case(tmp_path: Path, name: str, full_text: str) -> Path:
    path = tmp_path / name
    path.write_text(BASE % full_text, encoding="utf-8")
    return path


def run(case_path: Path, out: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(case_path),
                           "--out", str(out), *extra],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


def test_good_case_applies(tmp_path):
    good = case(tmp_path, "good_case.py", '"8 站场景下的可用率对照"')
    out = tmp_path / "fig.svg"
    proc = run(good, out, "--apply")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert out.is_file() and out.stat().st_size > 500
    assert "回读校验" in proc.stdout


def test_bad_case_blocked_before_writing(tmp_path):
    bad = case(tmp_path, "bad_case.py", '"，这一行以标点开头"')
    out = tmp_path / "bad.svg"
    proc = run(bad, out, "--apply")
    assert proc.returncode == 1, proc.stdout
    assert "生成前验收失败" in proc.stdout and "行首标点" in proc.stdout
    assert not out.exists(), "验收失败时不该写文件"
