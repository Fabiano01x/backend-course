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
    modules = [
        {
            "module": 4,
            "lessons": [
                {"number": 1, "status": "complete", "title": "One"},
                {"number": 2, "status": "complete", "title": "Two"},
            ],
        },
        {
            "module": 5,
            "lessons": [
                {"number": 1, "status": "pilot", "title": "Three"},
                {"number": 2, "status": "planned", "title": "Four"},
            ],
        },
    ]

    completed, next_lesson = resume_status.progress_summary(modules)

    assert completed == [(4, 1), (4, 2)]
    assert next_lesson == (5, modules[1]["lessons"][0])


def test_verification_uses_latest_checkpoint_across_modules(tmp_path: Path) -> None:
    commands = resume_status.verification_commands(
        tmp_path, [(4, 8), (5, 1)]
    )

    labels = [label for label, _, _ in commands]
    checkpoint = next(command for label, command, _ in commands if label.startswith("Checkpoint"))

    assert "Checkpoint M05/A01" in labels
    assert "reference/checkpoints/module-05/lesson-01/tests" in checkpoint
    assert "HTML M04/A08" in labels
    assert "HTML M05/A01" in labels


def test_classifies_student_changes_separately() -> None:
    course, student = resume_status.classify_changes(
        [" M docs/progress.md", "?? student/library-api/app.py"]
    )

    assert course == [" M docs/progress.md"]
    assert student == ["?? student/library-api/app.py"]
