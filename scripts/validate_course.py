#!/usr/bin/env python3
"""Valida fonte, manifesto, aulas e checkpoints progressivos do curso."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = "reference/pilot/module-04/lesson-03"
REQUIRED_LESSON_HEADINGS = (
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

    def validate_local_links(self, path: Path, content: str) -> None:
        link_pattern = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")
        for target in link_pattern.findall(content):
            if target.startswith(("http://", "https://", "#")):
                continue
            local_target = (path.parent / target.split("#", 1)[0]).resolve()
            if not local_target.exists():
                self.error(f"Link local quebrado em {path.relative_to(self.root)}: {target}")

    def validate_module(self) -> list[dict[str, object]]:
        manifest_path = self.require_file("course/04-fastapi/module.json")
        if manifest_path is None:
            return []
        try:
            manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError) as error:
            self.error(f"Manifesto autoral inválido: {error}")
            return []
        lessons = manifest.get("lessons", [])
        if manifest.get("module") != 4 or len(lessons) != 8:
            self.error("module.json deve descrever as oito aulas do Módulo 4")
            return lessons

        covered_sources: set[str] = set()
        for expected, lesson in enumerate(lessons, start=1):
            if lesson.get("number") != expected:
                self.error(f"Ordem inválida em module.json: aula esperada {expected}")
            status = lesson.get("status")
            if status not in {"planned", "pilot", "complete"}:
                self.error(f"Estado inválido na aula {expected}: {status}")
            for source in lesson.get("sources", []):
                covered_sources.add(str(source))
                self.require_file(str(source))

            lesson_path = self.root / "course/04-fastapi" / str(lesson.get("file"))
            if status == "planned":
                continue
            if not lesson_path.is_file():
                self.error(f"Aula marcada como {status}, mas ausente: {lesson_path.relative_to(self.root)}")
                continue
            content = lesson_path.read_text()
            if "```json" in content and '"type"' in content:
                self.error(f"Componente JSON bruto encontrado em {lesson_path.relative_to(self.root)}")
            self.validate_local_links(lesson_path, content)

            if status == "complete":
                headings = set(re.findall(r"^## (.+?)\s*$", content, flags=re.MULTILINE))
                for heading in REQUIRED_LESSON_HEADINGS:
                    if heading not in headings:
                        self.error(
                            f"Seção ausente na aula {expected:02d}: {heading}"
                        )
                checkpoint = self.root / str(lesson.get("checkpoint"))
                if not checkpoint.is_dir():
                    self.error(f"Checkpoint ausente da aula {expected:02d}: {checkpoint}")
                elif not (checkpoint / "tests").is_dir():
                    self.error(f"Testes ausentes no checkpoint da aula {expected:02d}")

        expected_sources = {f"source/module-04/{number:02d}.md" for number in range(1, 9)}
        missing = expected_sources - covered_sources
        if missing:
            self.error(f"Fontes sem mapeamento em module.json: {', '.join(sorted(missing))}")
        return lessons

    def validate_progress_and_project(self, module_lessons: list[dict[str, object]]) -> None:
        progress = self.require_file("docs/progress.md")
        if progress is not None:
            content = progress.read_text()
            completed = [item for item in module_lessons if item.get("status") == "complete"]
            last = max((int(item["number"]) for item in completed), default=0)
            expected_marker = f"Última aula processada: {last:02d}"
            if expected_marker not in content:
                self.error(f"Marcador ausente em progress.md: {expected_marker}")

        completed = [item for item in module_lessons if item.get("status") == "complete"]
        if completed:
            latest = max(completed, key=lambda item: int(item["number"]))
            project_root = str(latest["checkpoint"])
        else:
            project_root = PILOT_ROOT
        main = self.require_file(f"{project_root}/app/main.py")
        if main is not None:
            content = main.read_text()
            latest_number = max((int(item["number"]) for item in completed), default=3)
            if latest_number >= 3:
                if "include_router" not in content:
                    self.error("main.py não registra APIRouter a partir da aula 03")
                if re.search(r"@app\.(get|post|put|patch|delete)\(\s*[\"']/((books)|(users))", content):
                    self.error("Rotas de domínio não podem permanecer diretamente em main.py")

    def run(self) -> list[str]:
        lessons = self.validate_source()
        self.validate_coverage(lessons)
        module_lessons = self.validate_module()
        self.validate_progress_and_project(module_lessons)
        for required in (
            "AGENTS.md",
            "README.md",
            "docs/concepts.md",
            "docs/decisions.md",
            "docs/architecture.md",
            "student/library-api/README.md",
            "reference/checkpoints/README.md",
            "scripts/compare_checkpoint.py",
        ):
            self.require_file(required)

        agents = self.require_file("AGENTS.md")
        if agents is not None:
            content = agents.read_text()
            if "Nunca criar, alterar, formatar, remover" not in content:
                self.error("AGENTS.md não protege explicitamente a área do aluno")
            if "Git e commits obrigatórios" not in content:
                self.error("AGENTS.md não registra a política obrigatória de commits")
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
    print("Validação concluída: fonte, aulas, checkpoints e projeto estão consistentes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
