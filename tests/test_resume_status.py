from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "resume_status.py"
SPEC = importlib.util.spec_from_file_location("resume_status", SCRIPT)
assert SPEC and SPEC.loader
resume_status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(resume_status)


def test_progress_summary_finds_first_unfinished_lesson() -> None:
    lessons = [
        {"number": 1, "status": "complete", "title": "One"},
        {"number": 2, "status": "complete", "title": "Two"},
        {"number": 3, "status": "pilot", "title": "Three"},
        {"number": 4, "status": "planned", "title": "Four"},
    ]

    completed, next_lesson = resume_status.progress_summary(lessons)

    assert completed == [1, 2]
    assert next_lesson == lessons[2]


def test_classifies_student_changes_separately() -> None:
    course, student = resume_status.classify_changes(
        [" M docs/progress.md", "?? student/library-api/app.py"]
    )

    assert course == [" M docs/progress.md"]
    assert student == ["?? student/library-api/app.py"]
