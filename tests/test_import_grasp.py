from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_grasp.py"
SPEC = importlib.util.spec_from_file_location("import_grasp", SCRIPT)
assert SPEC and SPEC.loader
import_grasp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(import_grasp)


def fake_payloads() -> dict[str, dict[str, object]]:
    course_url = f"{import_grasp.BASE_URL}/goals/course-id"
    lesson_a_url = f"{import_grasp.BASE_URL}/pathways/lessons/lesson-a"
    lesson_b_url = f"{import_grasp.BASE_URL}/pathways/lessons/lesson-b"
    return {
        course_url: {
            "title": "Course",
            "pathway": {
                "versions": [
                    {
                        "version_number": 3,
                        "lesson_groups": [
                            {
                                "position_in_pathway": 3,
                                "title": "Module",
                                "lessons": [
                                    {
                                        "position_in_lesson_group": 1,
                                        "entity_id": "lesson-b",
                                        "title": "B",
                                    },
                                    {
                                        "position_in_lesson_group": 0,
                                        "entity_id": "lesson-a",
                                        "title": "A",
                                    },
                                ],
                            }
                        ],
                    }
                ]
            },
        },
        lesson_a_url: {"id": "lesson-a", "title": "A", "content": "# A\n"},
        lesson_b_url: {"id": "lesson-b", "title": "B", "content": "# B"},
    }


def test_imports_in_api_order_and_records_hashes(tmp_path: Path) -> None:
    payloads = fake_payloads()
    destination = import_grasp.import_module(
        course_id="course-id",
        version_number=3,
        module_number=4,
        output_dir=tmp_path,
        fetcher=payloads.__getitem__,
    )

    assert (destination / "01.md").read_text() == "# A\n"
    assert (destination / "02.md").read_text() == "# B\n"
    manifest = json.loads((destination / "manifest.json").read_text())
    assert [lesson["lesson_id"] for lesson in manifest["lessons"]] == [
        "lesson-a",
        "lesson-b",
    ]
    assert len(manifest["lessons"][0]["markdown_sha256"]) == 64


def test_refuses_to_overwrite_an_import(tmp_path: Path) -> None:
    payloads = fake_payloads()
    arguments = dict(
        course_id="course-id",
        version_number=3,
        module_number=4,
        output_dir=tmp_path,
        fetcher=payloads.__getitem__,
    )
    import_grasp.import_module(**arguments)

    with pytest.raises(FileExistsError, match="imutáveis"):
        import_grasp.import_module(**arguments)


def test_rejects_missing_version() -> None:
    with pytest.raises(ValueError, match="Versão 3"):
        import_grasp.find_version({"pathway": {"versions": []}}, 3)

