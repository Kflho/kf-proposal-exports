#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""note_dedup.py 的判定用例：每条规则一个好例，外加「干净笔记不误报」反证。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))

import note_dedup  # noqa: E402


def write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def rules(findings: list[dict]) -> list[str]:
    return [item['rule'] for item in findings]


def test_clean_notes_have_no_findings(tmp_path):
    write(tmp_path, 'data note.md', '# 概论\n1. 管理建议\n\n## 去除重复\n1. 一个信息只记在一个地方\n')
    write(tmp_path, 'note note.md', '# 概论\n1. 笔记规范\n\n## 更新笔记\n1. 更新包括记录和修改\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert findings == []


def test_missing_reference_target_is_error(tmp_path):
    write(tmp_path, 'data note.md', '1. 相册模板：见 painting note\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    errors = [item for item in findings if item['severity'] == 'error']
    assert len(errors) == 1
    assert errors[0]['rule'] == 'N3'
    assert 'painting note' in errors[0]['matched']


def test_section_missing_everywhere_suggests_real_title(tmp_path):
    write(tmp_path, 'data note.md', '1. 合并条目\n\n## 去除内容重复\n1. 一个信息只记在一个地方\n')
    write(tmp_path, 'note note.md', '1. 去重：见 data note-去除重复\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    warns = [item for item in findings if item['rule'] == 'N3']
    assert len(warns) == 1
    assert warns[0]['severity'] == 'error'
    assert '去除内容重复' in warns[0]['advice']


def test_reference_to_list_item_is_fine(tmp_path):
    write(tmp_path, 'data note.md', '1. 模板：见 note note\n')
    write(tmp_path, 'note note.md', '# 规范\n1. 模板：允许引用模板\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert [item for item in findings if item['rule'] == 'N3'] == []


def test_same_target_twice_in_one_file_is_reported(tmp_path):
    write(tmp_path, 'project note.md', '# 概论\n1. 项目\n')
    write(tmp_path, 'data note.md',
          '# 概论\n1. 单一功能：参考 project note\n2. 其它\n3. 又见 project note\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    dup = [item for item in findings if item['rule'] == 'N4']
    assert len(dup) == 1
    assert 'project note' in dup[0]['matched']


def test_same_line_in_two_files_is_reported(tmp_path):
    line = '1. 单一功能原则要求一份文件只承担一项功能，不得混着写'
    write(tmp_path, 'data note.md', f'# 概论\n{line}\n')
    write(tmp_path, 'note note.md', f'# 概论\n{line}\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    dup = [item for item in findings if item['rule'] == 'N2']
    assert len(dup) == 1


def test_same_line_twice_in_one_file_is_reported(tmp_path):
    line = '1. 直接在对应领域建立相关项目文件夹，不统一放在项目文件夹里'
    write(tmp_path, 'project note.md', f'# 概论\n{line}\n\n# 文件模板\n## 建议\n{line}\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert 'N2' in rules(findings)


def test_reference_to_template_section_is_not_title_restatement(tmp_path):
    write(tmp_path, 'template note.md',
          '## 实例建立流程\n1. 见文件模板-实例建立流程\n\n'
          '## 框架\n1. 框架：根据实例建立流程写框架\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert [item for item in findings if item['rule'] == 'N1' and item['line'] == 2] == []


def test_section_in_note_outside_checked_dir_resolves(tmp_path):
    vault = tmp_path / 'vault'
    write(vault, 'other note.md', '# 概论\n1. 内容\n\n## 目标节\n1. 说明\n')
    write(vault, 'data note.md', '1. 相册：见 other note-目标节\n')
    findings = note_dedup.check(vault / 'data note.md', vault)
    assert [item for item in findings if item['rule'] == 'N3'] == []


def test_trash_copy_does_not_shadow_real_note(tmp_path):
    write(tmp_path, 'other note.md', '# 概论\n\n## 目标节\n1. 说明\n')
    write(tmp_path, '.trash/locally-save/other note.md', '# 概论\n\n## 旧标题\n1. 旧内容\n')
    write(tmp_path, 'data note.md', '1. 相册：见 other note-目标节\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert [item for item in findings if item['rule'] == 'N3'] == []


def test_pure_reference_lines_do_not_count_as_duplication(tmp_path):
    line = '1. 单一功能原则见 project note 相关部分'
    write(tmp_path, 'data note.md', f'# 概论\n{line}\n')
    write(tmp_path, 'note note.md', f'# 概论\n{line}\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert 'N2' not in rules(findings)


def test_same_heading_same_body_in_two_files_is_reported(tmp_path):
    body = '## 去除重复\n1. 作用：提高效率\n2. 内容：功能与内容\n'
    write(tmp_path, 'project note.md', body)
    write(tmp_path, 'template note.md', body)
    findings = note_dedup.check(tmp_path, tmp_path)
    assert 'N6' in rules(findings)


def test_same_heading_with_different_bodies_is_fine(tmp_path):
    write(tmp_path, 'template note.md',
          '## 实例建立流程\n1. 写分类模板\n2. 按分类模板整理文件夹\n\n'
          '## 实例建立流程\n1. 按照框架模板建立对应\n')
    write(tmp_path, 'project note.md', '## 实例建立流程\n1. 先写任务书再拆子任务\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert 'N7' not in rules(findings)
    assert 'N6' not in rules(findings)


def test_same_heading_twice_with_same_body_is_reported(tmp_path):
    body = '## 实例建立流程\n1. 按照框架模板建立对应\n2. 按步骤填充内容\n'
    write(tmp_path, 'template note.md', body + '\n' + body)
    findings = note_dedup.check(tmp_path, tmp_path)
    assert 'N7' in rules(findings)


def test_reference_only_section_is_not_counted_as_duplicate(tmp_path):
    write(tmp_path, 'template note.md', '## 实例建立流程\n1. 按照框架模板建立对应\n')
    write(tmp_path, 'data note.md', '## 实例建立流程\n1. 见 template note-实例建立流程\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert 'N6' not in rules(findings)


def test_filler_restatement_is_reported(tmp_path):
    write(tmp_path, 'data note.md', '## 去除重复\n1. 去除重复\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    filler = [item for item in findings if item['rule'] == 'N1']
    assert len(filler) == 1
    assert filler[0]['matched'] == '去除重复'


def test_restatement_with_new_information_is_fine(tmp_path):
    write(tmp_path, 'data note.md',
          '## 去除重复\n1. 去除重复能提高效率\n\n## 数据迁移\n1. 数据迁移：把数据迁移到合适的位置\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert [item for item in findings if item['rule'] == 'N1'] == []


def test_scaffold_heading_body_is_not_reported(tmp_path):
    write(tmp_path, 'data note.md', '## 规范介绍\n1. 规范：强制遵循的约束，如格式、命名等\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert 'N1' not in rules(findings)


def test_distant_references_to_same_note_are_fine(tmp_path):
    write(tmp_path, 'project note.md', '# 概论\n1. 项目\n')
    write(tmp_path, 'data note.md',
          '# 概论\n1. 单一功能：参考 project note\n' + '\n'.join('2. 内容' for _ in range(6))
          + '\n3. 又见 project note\n')
    findings = note_dedup.check(tmp_path, tmp_path)
    assert 'N4' not in rules(findings)


def test_strict_flag_controls_low_confidence_items(tmp_path):
    write(tmp_path, 'project note.md', '## 目录\n1. 项目\n')
    write(tmp_path, 'data note.md',
          '1. 目标：见 project note-目录\n2. 又见 project note-目录\n')
    default = run_cli('--root', str(tmp_path), '--json')
    strict = run_cli('--root', str(tmp_path), '--json', '--strict')
    assert json.loads(default.stdout) == []
    payload = json.loads(strict.stdout)
    assert any(item['rule'] == 'N4' for item in payload)


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / 'note_dedup.py'), *args],
        capture_output=True, text=True, encoding='utf-8', errors='replace')


def test_cli_exit_code_follows_errors(tmp_path):
    write(tmp_path, 'clean.md', '# 概论\n1. 内容\n')
    run = run_cli('--root', str(tmp_path))
    assert run.returncode == 0, run.stdout + run.stderr

    write(tmp_path, 'broken.md', '1. 相册：见 painting note\n')
    run = run_cli('--root', str(tmp_path), '--json')
    assert run.returncode == 1
    payload = json.loads(run.stdout)
    assert any(item['severity'] == 'error' for item in payload)


def test_missing_root_reports_usage_error(tmp_path):
    run = run_cli('--root', str(tmp_path / 'nope'))
    assert run.returncode == 2
