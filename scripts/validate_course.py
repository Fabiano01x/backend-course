#!/usr/bin/env python3
"""Valida fonte, cobertura, aula piloto e estado arquitetural do marco atual."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PILOT_HEADINGS = (
    "Onde estamos",
    "O problema",
    "Por que isso importa",
    "O conceito",
    "Modelo mental",
    "Exemplo mínimo",
    "Aplicando ao projeto",
    "Antes",
    "Depois",
    "O que mudou",
    "Fluxo da requisição",
    "Como testar",
    "Erros comuns",
    "Exercício guiado",
    "Desafio",
    "Checkpoint",
    "Estado atual do projeto",
    "Próximo problema",
)


class Validation:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.errors: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def require_file(self, relative_path: str) -> Path | None:
        path = self.root / relative_path
        if not path.is_file():
            self.error(f"Arquivo obrigatório ausente: {relative_path}")
            return None
        return path

    def validate_source(self) -> list[dict[str, object]]:
        manifest_path = self.require_file("source/module-04/manifest.json")
        if manifest_path is None:
            return []
        try:
            manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError) as error:
            self.error(f"Manifesto inválido: {error}")
            return []

        lessons = manifest.get("lessons", [])
        if manifest.get("version_number") != 3 or manifest.get("module_number") != 4:
            self.error("O manifesto deve representar a versão 3, Módulo 4")
        if len(lessons) != 8:
            self.error(f"Esperadas 8 aulas no manifesto; encontradas {len(lessons)}")

        for expected_position, lesson in enumerate(lessons, start=1):
            if lesson.get("position") != expected_position:
                self.error(f"Posição inválida no manifesto: {lesson!r}")
            for kind in ("json", "markdown"):
                name = lesson.get(f"{kind}_file")
                expected_hash = lesson.get(f"{kind}_sha256")
                path = manifest_path.parent / str(name)
                if not path.is_file():
                    self.error(f"Fonte ausente: {path.relative_to(self.root)}")
                    continue
                actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    self.error(
                        f"Fonte alterada: {path.relative_to(self.root)} não corresponde ao hash"
                    )
        return lessons

    def validate_coverage(self, lessons: list[dict[str, object]]) -> None:
        map_path = self.require_file("docs/curriculum-map.md")
        if map_path is None:
            return
        content = map_path.read_text()
        for lesson in lessons:
            source_path = f"source/module-04/{lesson['markdown_file']}"
            occurrences = content.count(source_path)
            if occurrences != 1:
                self.error(
                    f"{source_path} deve aparecer exatamente uma vez no mapa; "
                    f"aparece {occurrences} vez(es)"
                )

    def validate_pilot(self) -> None:
        pilot = self.require_file("course/04-fastapi/03-apirouter.md")
        if pilot is None:
            return
        content = pilot.read_text()
        headings = set(re.findall(r"^## (.+?)\s*$", content, flags=re.MULTILINE))
        for heading in REQUIRED_PILOT_HEADINGS:
            if heading not in headings:
                self.error(f"Seção ausente na aula piloto: {heading}")
        if "Correção técnica" not in content:
            self.error("A aula piloto deve identificar ao menos uma correção técnica")

        link_pattern = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")
        for target in link_pattern.findall(content):
            if target.startswith(("http://", "https://", "#")):
                continue
            local_target = (pilot.parent / target.split("#", 1)[0]).resolve()
            if not local_target.exists():
                self.error(f"Link local quebrado na aula piloto: {target}")

    def validate_progress_and_project(self) -> None:
        progress = self.require_file("docs/progress.md")
        if progress is not None:
            content = progress.read_text()
            for marker in ("Estado: piloto concluído", "Última aula processada: 03"):
                if marker not in content:
                    self.error(f"Marcador ausente em progress.md: {marker}")

        main = self.require_file("project/backend/app/main.py")
        if main is not None:
            content = main.read_text()
            if "include_router" not in content:
                self.error("main.py não registra APIRouter")
            if re.search(r"@app\.(get|post|put|patch|delete)\(\s*[\"']/((books)|(users))", content):
                self.error("Rotas de domínio não podem permanecer diretamente em main.py")

        for relative_path in (
            "project/backend/app/routers/books.py",
            "project/backend/app/routers/users.py",
            "project/backend/app/routers/system.py",
        ):
            path = self.require_file(relative_path)
            if path is not None and "APIRouter" not in path.read_text():
                self.error(f"{relative_path} não declara APIRouter")

    def run(self) -> list[str]:
        lessons = self.validate_source()
        self.validate_coverage(lessons)
        self.validate_pilot()
        self.validate_progress_and_project()
        for required in (
            "AGENTS.md",
            "README.md",
            "docs/concepts.md",
            "docs/decisions.md",
            "docs/architecture.md",
        ):
            self.require_file(required)
        return self.errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    errors = Validation(arguments.root.resolve()).run()
    if errors:
        print("VALIDAÇÃO FALHOU", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Validação concluída: fonte, cobertura, piloto e projeto estão consistentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

