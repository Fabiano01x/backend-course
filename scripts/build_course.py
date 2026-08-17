#!/usr/bin/env python3
"""Gera as aulas Markdown como HTML contínuo e responsivo."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, NamedTuple

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound


ROOT = Path(__file__).resolve().parents[1]
ESSENTIAL_HEADINGS = (
    "O problema",
    "Por que isso importa",
    "O conceito",
    "Modelo mental",
    "Exemplo mínimo",
    "Aplicando ao projeto",
    "Antes e depois",
    "Como testar",
    "Exercícios",
    "Checkpoint",
    "Próximo problema",
)


class Lesson(NamedTuple):
    number: int
    slug: str
    file: str
    title: str
    summary: str
    sources: tuple[str, ...]
    checkpoint: str
    status: str


def load_manifest(root: Path, module: int) -> tuple[dict[str, Any], list[Lesson], Path]:
    module_dir = root / "course" / f"{module:02d}-fastapi"
    manifest_path = module_dir / "module.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Manifesto ausente: {manifest_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Manifesto inválido: {error}") from error

    raw_lessons = payload.get("lessons")
    if payload.get("module") != module or not isinstance(raw_lessons, list):
        raise ValueError("O manifesto não corresponde ao módulo solicitado")
    lessons = [
        Lesson(
            number=item["number"],
            slug=item["slug"],
            file=item["file"],
            title=item["title"],
            summary=item["summary"],
            sources=tuple(item["sources"]),
            checkpoint=item["checkpoint"],
            status=item["status"],
        )
        for item in raw_lessons
    ]
    if [lesson.number for lesson in lessons] != list(range(1, len(lessons) + 1)):
        raise ValueError("As aulas devem estar numeradas em ordem contínua")
    return payload, lessons, module_dir


def validate_lesson(markdown_text: str, lesson: Lesson, root: Path) -> list[str]:
    errors: list[str] = []
    if not re.search(r"^#\s+\S", markdown_text, flags=re.MULTILINE):
        errors.append("título H1 ausente")
    if "```json" in markdown_text and '"type"' in markdown_text:
        errors.append("possível componente JSON bruto do Grasp")
    for source in lesson.sources:
        if not (root / source).is_file():
            errors.append(f"fonte ausente: {source}")
    return errors


def render_code_cards(fragment: str) -> str:
    pattern = re.compile(
        r'<pre><code(?: class="language-([\w+-]+)")?>(.*?)</code></pre>',
        flags=re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        language = match.group(1) or "text"
        source = html.unescape(match.group(2))
        try:
            lexer = get_lexer_by_name(language)
        except ClassNotFound:
            lexer = TextLexer()
        highlighted = highlight(source, lexer, HtmlFormatter(nowrap=True)).rstrip("\n")
        safe_language = html.escape(language)
        return (
            f'<div class="code-card" data-language="{safe_language}">'
            '<div class="code-toolbar">'
            f'<span>{safe_language}</span><button class="copy-code" type="button" '
            'aria-label="Copiar código">Copiar</button></div>'
            f'<pre><code>{highlighted}</code></pre></div>'
        )

    return pattern.sub(replace, fragment)


def markdown_to_html(markdown_text: str) -> str:
    fragment = markdown.markdown(
        markdown_text,
        extensions=(
            "admonition",
            "attr_list",
            "fenced_code",
            "md_in_html",
            "sane_lists",
            "tables",
            "toc",
        ),
        extension_configs={"toc": {"permalink": False}},
        output_format="html5",
    )
    return render_code_cards(fragment)


def nav_item(lesson: Lesson | None, direction: str) -> str:
    if lesson is None:
        return '<span class="empty" aria-hidden="true"></span>'
    label = "Aula anterior" if direction == "prev" else "Próxima aula"
    return (
        f'<a class="{direction}" href="{lesson.number:02d}.html">'
        f'<small>{label}</small><strong>{html.escape(lesson.title)}</strong></a>'
    )


def page_shell(*, title: str, body: str, description: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(description, quote=True)}">
  <title>{html.escape(title)} — Backend Course</title>
  <link rel="stylesheet" href="../assets/grasp-inspired.css">
</head>
<body>
  <header class="site-header"><div class="brand"><span class="brand-mark">BC</span> Backend Course <span aria-hidden="true">/</span> Library API</div></header>
  {body}
  <footer class="site-footer">Backend Course · Library API · conteúdo autoral em português do Brasil</footer>
  <script src="../assets/lesson.js" defer></script>
</body>
</html>
"""


def render_lesson(
    manifest: dict[str, Any], lessons: list[Lesson], lesson: Lesson, markdown_text: str
) -> str:
    index = lesson.number - 1
    previous = lessons[index - 1] if index > 0 and lessons[index - 1].status == "complete" else None
    following = lessons[index + 1] if index + 1 < len(lessons) and lessons[index + 1].status == "complete" else None
    content = markdown_to_html(markdown_text)
    body = f"""
  <section class="lesson-hero">
    <p class="eyebrow">Módulo {manifest['module']} · Aula {lesson.number} de {len(lessons)}</p>
    <h1>{html.escape(lesson.title)}</h1>
    <p class="lesson-summary">{html.escape(lesson.summary)}</p>
  </section>
  <main class="lesson-content" id="conteudo">
    {content}
    <nav class="lesson-nav" aria-label="Navegação entre aulas">
      {nav_item(previous, 'prev')}
      {nav_item(following, 'next')}
    </nav>
  </main>"""
    return page_shell(title=lesson.title, body=body, description=lesson.summary)


def render_index(manifest: dict[str, Any], lessons: list[Lesson], available: set[int]) -> str:
    tiles: list[str] = []
    for lesson in lessons:
        status = "Disponível" if lesson.number in available else "Em preparação"
        if lesson.number in available:
            opening, closing = f'<a class="lesson-tile" href="{lesson.number:02d}.html">', "</a>"
        else:
            opening, closing = '<article class="lesson-tile">', "</article>"
        tiles.append(
            f"{opening}<span class=\"lesson-number\">{lesson.number:02d}</span>"
            f"<div><h2>{html.escape(lesson.title)}</h2><p>{html.escape(lesson.summary)}</p></div>"
            f"<span class=\"lesson-status\">{status}</span>{closing}"
        )
    body = f"""
  <section class="module-hero">
    <p class="eyebrow">Módulo {manifest['module']} · {len(lessons)} aulas</p>
    <h1>{html.escape(manifest['title'])}</h1>
    <p class="lesson-summary">{html.escape(manifest['description'])}</p>
  </section>
  <main class="lesson-grid">{''.join(tiles)}</main>"""
    return page_shell(title=manifest["title"], body=body, description=manifest["description"])


def build(root: Path, module: int, lesson_number: int | None, output: Path) -> list[Path]:
    manifest, lessons, module_dir = load_manifest(root, module)
    selected = lessons
    if lesson_number is not None:
        selected = [lesson for lesson in lessons if lesson.number == lesson_number]
        if not selected:
            raise ValueError(f"Aula inexistente: {lesson_number}")

    output_dir = output / f"module-{module:02d}"
    assets_dir = output / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "course/theme/grasp-inspired.css", assets_dir / "grasp-inspired.css")
    shutil.copyfile(root / "course/theme/lesson.js", assets_dir / "lesson.js")

    written: list[Path] = []
    available = {lesson.number for lesson in lessons if (module_dir / lesson.file).is_file()}
    for lesson in selected:
        markdown_path = module_dir / lesson.file
        if not markdown_path.is_file():
            raise ValueError(f"Aula ainda não produzida: {markdown_path}")
        markdown_text = markdown_path.read_text(encoding="utf-8")
        errors = validate_lesson(markdown_text, lesson, root)
        if errors:
            raise ValueError(f"Aula {lesson.number:02d} inválida: {'; '.join(errors)}")
        target = output_dir / f"{lesson.number:02d}.html"
        target.write_text(render_lesson(manifest, lessons, lesson, markdown_text), encoding="utf-8")
        written.append(target)

    index_path = output_dir / "index.html"
    index_path.write_text(render_index(manifest, lessons, available), encoding="utf-8")
    written.append(index_path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=int, default=4)
    parser.add_argument("--lesson", type=int)
    parser.add_argument("--output", type=Path, default=Path("dist/html"))
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    output = arguments.output if arguments.output.is_absolute() else root / arguments.output
    try:
        written = build(root, arguments.module, arguments.lesson, output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERRO: {error}", file=sys.stderr)
        return 1
    for path in written:
        print(path.relative_to(root) if path.is_relative_to(root) else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
