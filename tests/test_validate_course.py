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


def test_detects_missing_pilot_sections_and_broken_link(tmp_path: Path) -> None:
    pilot_dir = tmp_path / "course" / "04-fastapi"
    pilot_dir.mkdir(parents=True)
    (pilot_dir / "03-apirouter.md").write_text(
        "# Pilot\n\nCorreção técnica\n\n[missing](does-not-exist.md)\n"
    )
    validation = validate_course.Validation(tmp_path)

    validation.validate_pilot()

    assert any("Seção ausente" in error for error in validation.errors)
    assert any("Link local quebrado" in error for error in validation.errors)

