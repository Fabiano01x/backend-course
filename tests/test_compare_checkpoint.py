from __future__ import annotations

import importlib.util
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_checkpoint.py"
SPEC = importlib.util.spec_from_file_location("compare_checkpoint", SCRIPT)
assert SPEC and SPEC.loader
compare_checkpoint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compare_checkpoint)


def test_identical_directories_have_no_differences(tmp_path: Path) -> None:
    student = tmp_path / "student"
    checkpoint = tmp_path / "checkpoint"
    student.mkdir()
    checkpoint.mkdir()
    (student / "main.py").write_text("value = 1\n")
    (checkpoint / "main.py").write_text("value = 1\n")

    output = StringIO()
    differences = compare_checkpoint.compare_directories(student, checkpoint, output)

    assert differences is False
    assert output.getvalue() == ""


def test_comparison_reports_diff_without_changing_student_file(tmp_path: Path) -> None:
    student = tmp_path / "student"
    checkpoint = tmp_path / "checkpoint"
    student.mkdir()
    checkpoint.mkdir()
    student_file = student / "main.py"
    student_file.write_text("value = 1\n")
    (checkpoint / "main.py").write_text("value = 2\n")

    output = StringIO()
    differences = compare_checkpoint.compare_directories(student, checkpoint, output)

    assert differences is True
    assert "-value = 1" in output.getvalue()
    assert "+value = 2" in output.getvalue()
    assert student_file.read_text() == "value = 1\n"


def test_comparison_ignores_student_readme_and_local_caches(tmp_path: Path) -> None:
    student = tmp_path / "student"
    checkpoint = tmp_path / "checkpoint"
    student.mkdir()
    checkpoint.mkdir()
    (student / "README.md").write_text("student instructions\n")
    cache = student / "__pycache__"
    cache.mkdir()
    (cache / "main.pyc").write_bytes(b"cache")

    assert compare_checkpoint.compare_directories(student, checkpoint, StringIO()) is False

