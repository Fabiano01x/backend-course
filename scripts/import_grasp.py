#!/usr/bin/env python3
"""Importa uma versão de um módulo do Grasp sem alterar seu conteúdo."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


BASE_URL = "https://paths.grasp.study/api"
DEFAULT_COURSE_ID = "3b30bbfd-e48e-4883-8450-8fca5452c8d1"
DEFAULT_VERSION = 3
DEFAULT_MODULE = 4
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "source"
REQUEST_TIMEOUT = 30

JsonObject = dict[str, Any]
Fetcher = Callable[[str], JsonObject]


def fetch_json(url: str) -> JsonObject:
    """Busca JSON público do Grasp com um identificador de cliente explícito."""

    request = Request(url, headers={"User-Agent": "backend-course-importer/1.0"})
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:  # noqa: S310
        payload = response.read()
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError(f"Resposta inesperada em {url}: o JSON não é um objeto")
    return data


def find_version(course_data: JsonObject, version_number: int) -> JsonObject:
    """Encontra uma versão pelo número, sem usar a versão corrente implícita."""

    versions = course_data.get("pathway", {}).get("versions", [])
    for version in versions:
        if version.get("version_number") == version_number:
            return version
    raise ValueError(f"Versão {version_number} não encontrada no curso")


def find_module(version: JsonObject, module_number: int) -> JsonObject:
    """Encontra um módulo usando a posição oficial zero-based da API."""

    groups = version.get("lesson_groups", [])
    for group in groups:
        if group.get("position_in_pathway") == module_number - 1:
            return group
    raise ValueError(f"Módulo {module_number} não encontrado na versão selecionada")


def canonical_json(data: JsonObject) -> bytes:
    """Serializa o payload sem tradução ou alteração semântica."""

    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()


def source_markdown(lesson_data: JsonObject) -> bytes:
    """Extrai literalmente o campo Markdown fornecido pela API."""

    content = lesson_data.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"A aula {lesson_data.get('id', '<sem id>')} não possui conteúdo")
    return (content if content.endswith("\n") else content + "\n").encode()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def import_module(
    *,
    course_id: str = DEFAULT_COURSE_ID,
    version_number: int = DEFAULT_VERSION,
    module_number: int = DEFAULT_MODULE,
    output_dir: Path = DEFAULT_OUTPUT,
    fetcher: Fetcher = fetch_json,
) -> Path:
    """Importa um módulo de forma atômica e recusa qualquer sobrescrita."""

    module_dir = output_dir / f"module-{module_number:02d}"
    if module_dir.exists():
        raise FileExistsError(
            f"{module_dir} já existe; arquivos de source/ são imutáveis"
        )

    course_url = f"{BASE_URL}/goals/{course_id}"
    course_data = fetcher(course_url)
    version = find_version(course_data, version_number)
    module = find_module(version, module_number)
    lessons = sorted(
        module.get("lessons", []), key=lambda item: item["position_in_lesson_group"]
    )
    if not lessons:
        raise ValueError(f"Módulo {module_number} não possui aulas")

    output_dir.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=".grasp-import-", dir=output_dir))
    temporary_module = temporary_root / module_dir.name
    temporary_module.mkdir()

    try:
        manifest_lessons: list[JsonObject] = []
        expected_positions = list(range(len(lessons)))
        actual_positions = [lesson["position_in_lesson_group"] for lesson in lessons]
        if actual_positions != expected_positions:
            raise ValueError(
                "As posições das aulas não formam uma sequência contígua: "
                f"{actual_positions}"
            )

        for lesson_summary in lessons:
            position = lesson_summary["position_in_lesson_group"] + 1
            lesson_id = lesson_summary["entity_id"]
            lesson_url = f"{BASE_URL}/pathways/lessons/{lesson_id}"
            lesson_data = fetcher(lesson_url)
            if lesson_data.get("id") not in (None, lesson_id):
                raise ValueError(f"A API retornou outra aula para {lesson_id}")

            json_payload = canonical_json(lesson_data)
            markdown_payload = source_markdown(lesson_data)
            json_name = f"{position:02d}.json"
            markdown_name = f"{position:02d}.md"
            (temporary_module / json_name).write_bytes(json_payload)
            (temporary_module / markdown_name).write_bytes(markdown_payload)

            manifest_lessons.append(
                {
                    "position": position,
                    "lesson_id": lesson_id,
                    "title": lesson_data.get("title", lesson_summary.get("title", "")),
                    "api_url": lesson_url,
                    "json_file": json_name,
                    "json_sha256": sha256(json_payload),
                    "markdown_file": markdown_name,
                    "markdown_sha256": sha256(markdown_payload),
                }
            )

        manifest: JsonObject = {
            "schema_version": 1,
            "course_id": course_id,
            "course_title": course_data.get("title", ""),
            "version_number": version_number,
            "module_number": module_number,
            "module_title": module.get("title", ""),
            "course_api_url": course_url,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "markdown_derivation": "verbatim lesson.content with one trailing newline",
            "lessons": manifest_lessons,
        }
        (temporary_module / "manifest.json").write_bytes(canonical_json(manifest))
        temporary_module.replace(module_dir)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    else:
        shutil.rmtree(temporary_root, ignore_errors=True)

    return module_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importa um módulo original do Grasp para source/."
    )
    parser.add_argument("--course-id", default=DEFAULT_COURSE_ID)
    parser.add_argument("--version", type=int, default=DEFAULT_VERSION)
    parser.add_argument("--module", type=int, default=DEFAULT_MODULE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    destination = import_module(
        course_id=arguments.course_id,
        version_number=arguments.version,
        module_number=arguments.module,
        output_dir=arguments.output,
    )
    print(f"Fonte importada sem tradução: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

