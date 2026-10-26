"""check_connectors / check_consistency：反证测试（坏样例必须被拦，模板必须过）。

判据：
- 连线端点离方框 >0.5px = 悬空 → 退出码 1，并给出最近边与建议坐标；
- 同一组单元格（同宽高、同相对 y）锚点不一致 → 退出码 1；
- `assets/template.svg` 两个检查都必须 0（模板自己也要过自己的检查）。
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONN = ROOT / "scripts" / "check_connectors.py"
CONS = ROOT / "scripts" / "check_consistency.py"
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200">'
BOXES = ('<rect x="20" y="40" width="100" height="60" fill="#fff" stroke="#000"/>'
         '<rect x="240" y="40" width="100" height="60" fill="#fff" stroke="#000"/>')


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)


def write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(HEAD + body + "</svg>", encoding="utf-8")
    return path


def test_template_passes_both_checks():
    template = str(ROOT / "assets" / "template.svg")
    assert run(CONN, template).returncode == 0
    assert run(CONS, template).returncode == 0


def test_dangling_connector_is_flagged(tmp_path):
    good = write(tmp_path, "good.svg", BOXES + '<line x1="120" y1="70" x2="240" y2="70" '
                                         'stroke="#000" marker-end="url(#a)"/>')
    assert run(CONN, str(good)).returncode == 0

    bad = write(tmp_path, "bad.svg", BOXES + '<line x1="130" y1="70" x2="240" y2="70" '
                                        'stroke="#000" marker-end="url(#a)"/>')
    proc = run(CONN, str(bad))
    assert proc.returncode == 1, proc.stdout
    assert "距最近方框" in proc.stdout and "120" in proc.stdout


def test_mixed_anchor_in_same_cell_group_is_flagged(tmp_path):
    cells = ('<rect x="20" y="20" width="100" height="60"/>'
             '<rect x="140" y="20" width="100" height="60"/>')
    good = write(tmp_path, "good_anchor.svg",
                 cells + '<text x="70" y="45" text-anchor="middle">甲</text>'
                         '<text x="190" y="45" text-anchor="middle">乙</text>')
    assert run(CONS, str(good), "--min-cells", "2").returncode == 0

    bad = write(tmp_path, "bad_anchor.svg",
                cells + '<text x="70" y="45" text-anchor="middle">甲</text>'
                        '<text x="190" y="45" text-anchor="start">乙</text>')
    proc = run(CONS, str(bad), "--min-cells", "2")
    assert proc.returncode == 1, proc.stdout
    assert "锚点不一致" in proc.stdout
