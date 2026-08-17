from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_course.py"
SPEC = importlib.util.spec_from_file_location("build_course", SCRIPT)
assert SPEC and SPEC.loader
build_course = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_course)


def test_renders_semantic_cards_code_details_and_language() -> None:
    rendered = build_course.markdown_to_html(
        '''# Aula

!!! problem "O problema"
    Um arquivo cresceu demais.

```python
print("olá")
```

<details markdown="1">
<summary>Teste seu entendimento</summary>

Resposta em **Markdown**.

</details>
'''
    )

    assert 'class="admonition problem"' in rendered
    assert 'class="code-card" data-language="python"' in rendered
    assert 'class="copy-code"' in rendered
    assert "<details>" in rendered
    assert "<strong>Markdown</strong>" in rendered


def test_builds_single_continuous_lesson_and_index(tmp_path: Path) -> None:
    root = tmp_path
    module_dir = root / "course" / "05-sqlalchemy"
    theme_dir = root / "course" / "theme"
    source_dir = root / "source" / "module-05"
    module_dir.mkdir(parents=True)
    theme_dir.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    (theme_dir / "grasp-inspired.css").write_text("body{background:#e3ded2}")
    (theme_dir / "lesson.js").write_text("// js")
    (source_dir / "01.md").write_text("source")
    manifest = {
        "module": 5,
        "title": "Módulo",
        "description": "Descrição",
        "lessons": [
            {
                "number": 1,
                "slug": "one",
                "file": "01-one.md",
                "title": "Aula um",
                "summary": "Resumo",
                "sources": ["source/module-05/01.md"],
                "checkpoint": "reference/checkpoints/module-05/lesson-01",
                "status": "complete",
            }
        ],
    }
    (module_dir / "module.json").write_text(json.dumps(manifest))
    (module_dir / "01-one.md").write_text("# Aula um\n\n## O problema\n\nTexto.")

    written = build_course.build(root, 5, None, root / "dist/html")
    lesson_html = (root / "dist/html/module-05/01.html").read_text()

    assert len(written) == 2
    assert '<html lang="pt-BR">' in lesson_html
    assert lesson_html.count("<main") == 1
    assert "Aula 1 de 1" in lesson_html
    assert "page-break" not in lesson_html
    assert "@page" not in lesson_html
    assert (root / "dist/html/module-05/index.html").is_file()


def test_rejects_missing_lesson(tmp_path: Path) -> None:
    module_dir = tmp_path / "course" / "04-fastapi"
    module_dir.mkdir(parents=True)
    (module_dir / "module.json").write_text(
        json.dumps(
            {
                "module": 4,
                "lessons": [
                    {
                        "number": 1,
                        "slug": "one",
                        "file": "missing.md",
                        "title": "Missing",
                        "summary": "Missing",
                        "sources": [],
                        "checkpoint": "checkpoint",
                        "status": "planned",
                    }
                ],
            }
        )
    )
    (tmp_path / "course/theme").mkdir()
    (tmp_path / "course/theme/grasp-inspired.css").write_text("")
    (tmp_path / "course/theme/lesson.js").write_text("")

    try:
        build_course.build(tmp_path, 4, None, tmp_path / "dist")
    except ValueError as error:
        assert "Aula ainda não produzida" in str(error)
    else:
        raise AssertionError("missing lesson should fail")
