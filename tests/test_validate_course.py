from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_course.py"
SPEC = importlib.util.spec_from_file_location("validate_course", SCRIPT)
assert SPEC and SPEC.loader
validate_course = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_course)


def test_detects_modified_source_file(tmp_path: Path) -> None:
    destination = tmp_path / "source" / "module-04"
    destination.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "source" / "module-04", destination)

    pristine = validate_course.Validation(tmp_path)
    pristine.validate_source()
    assert pristine.errors == []

    with (destination / "01.md").open("a") as source_file:
        source_file.write("altered\n")

    changed = validate_course.Validation(tmp_path)
    changed.validate_source()
    assert any("Fonte alterada" in error for error in changed.errors)


def test_detects_lesson_missing_from_curriculum_map(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "curriculum-map.md").write_text("# empty\n")
    validation = validate_course.Validation(tmp_path)

    validation.validate_coverage([{"markdown_file": "01.md"}])

    assert validation.errors == [
        "source/module-04/01.md deve aparecer exatamente uma vez no mapa; aparece 0 vez(es)"
    ]


def test_detects_missing_complete_lesson_sections_and_broken_link(tmp_path: Path) -> None:
    course_dir = tmp_path / "course" / "04-fastapi"
    source_dir = tmp_path / "source" / "module-04"
    checkpoint = tmp_path / "reference" / "checkpoints" / "module-04" / "lesson-01"
    course_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    (checkpoint / "tests").mkdir(parents=True)
    for number in range(1, 9):
        (source_dir / f"{number:02d}.md").write_text("source")
    (course_dir / "01-one.md").write_text("# Aula\n\n[missing](does-not-exist.md)\n")
    lessons = []
    for number in range(1, 9):
        lessons.append(
            {
                "number": number,
                "file": "01-one.md" if number == 1 else f"{number:02d}.md",
                "sources": [f"source/module-04/{number:02d}.md"],
                "checkpoint": f"reference/checkpoints/module-04/lesson-{number:02d}",
                "status": "complete" if number == 1 else "planned",
            }
        )
    (course_dir / "module.json").write_text(json.dumps({"module": 4, "lessons": lessons}))
    validation = validate_course.Validation(tmp_path)

    validation.validate_module()

    assert any("Seção ausente" in error for error in validation.errors)
    assert any("Link local quebrado" in error for error in validation.errors)
