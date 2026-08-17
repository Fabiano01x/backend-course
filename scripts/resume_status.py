#!/usr/bin/env python3
"""Mostra um ponto de retomada durável e, opcionalmente, revalida o curso."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def run_git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_modules(root: Path) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    for manifest in sorted((root / "course").glob("[0-9][0-9]-*/module.json")):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        modules.append(payload)
    if not modules:
        raise FileNotFoundError("nenhum manifesto autoral encontrado")
    return modules


def progress_summary(
    modules: list[dict[str, Any]],
) -> tuple[list[tuple[int, int]], tuple[int, dict[str, Any]] | None]:
    completed: list[tuple[int, int]] = []
    next_lesson: tuple[int, dict[str, Any]] | None = None
    for module in sorted(modules, key=lambda item: int(item["module"])):
        module_number = int(module["module"])
        for lesson in module["lessons"]:
            if lesson["status"] == "complete":
                completed.append((module_number, int(lesson["number"])))
            elif next_lesson is None:
                next_lesson = (module_number, lesson)
    return completed, next_lesson


def classify_changes(status_lines: list[str]) -> tuple[list[str], list[str]]:
    course_changes: list[str] = []
    student_changes: list[str] = []
    for line in status_lines:
        path = line[3:] if len(line) >= 4 else line
        target = student_changes if path.startswith("student/") else course_changes
        target.append(line)
    return course_changes, student_changes


def verification_commands(
    root: Path, completed: list[tuple[int, int]]
) -> list[tuple[str, list[str], dict[str, str]]]:
    python = sys.executable
    commands: list[tuple[str, list[str], dict[str, str]]] = [
        ("Testes das ferramentas", [python, "-m", "pytest", "-q", "tests"], {}),
        ("Validação curricular", [python, "scripts/validate_course.py"], {}),
    ]
    if completed:
        latest_module, latest_lesson = completed[-1]
        checkpoint = (
            f"reference/checkpoints/module-{latest_module:02d}/"
            f"lesson-{latest_lesson:02d}"
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(root / checkpoint)
        commands.append(
            (
                f"Checkpoint M{latest_module:02d}/A{latest_lesson:02d}",
                [python, "-m", "pytest", "-q", f"{checkpoint}/tests"],
                environment,
            )
        )
        for module, lesson in completed:
            commands.append(
                (
                    f"HTML M{module:02d}/A{lesson:02d}",
                    [
                        python,
                        "scripts/build_course.py",
                        "--module",
                        str(module),
                        "--lesson",
                        str(lesson),
                    ],
                    {},
                )
            )
    return commands


def verify(root: Path, completed: list[tuple[int, int]]) -> bool:
    for label, command, environment in verification_commands(root, completed):
        print(f"\n[{label}]")
        result = subprocess.run(command, cwd=root, env=environment or None, check=False)
        if result.returncode != 0:
            print(f"Falhou: {label}", file=sys.stderr)
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="executa testes, validador, checkpoint atual e builds concluídos",
    )
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    root = arguments.root.resolve()

    try:
        modules = load_modules(root)
        completed, next_lesson = progress_summary(modules)
        branch = run_git(root, "branch", "--show-current")
        last_commit = run_git(root, "log", "-1", "--pretty=%h %s")
        status = run_git(root, "status", "--porcelain").splitlines()
    except (FileNotFoundError, json.JSONDecodeError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Não foi possível determinar o ponto de retomada: {error}", file=sys.stderr)
        return 1

    print("Backend Course — ponto de retomada")
    print(f"Branch: {branch}")
    print(f"Último commit: {last_commit}")
    completed_label = ", ".join(
        f"M{module:02d}/A{lesson:02d}" for module, lesson in completed
    )
    print(f"Aulas concluídas: {completed_label or 'nenhuma'}")
    if next_lesson is None:
        print("Próxima etapa: todos os módulos planejados estão concluídos")
    else:
        module_number, lesson = next_lesson
        suffix = " (substituir o piloto)" if lesson["status"] == "pilot" else ""
        print(
            f"Próxima etapa: M{module_number:02d}/A{int(lesson['number']):02d} — "
            f"{lesson['title']}{suffix}"
        )

    if arguments.verify and not verify(root, completed):
        return 1

    # Reconsulta porque os testes podem criar apenas artefatos ignorados, mas
    # nunca devemos assumir isso silenciosamente.
    status = run_git(root, "status", "--porcelain").splitlines()
    course_changes, student_changes = classify_changes(status)
    print("\nEstado do trabalho:")
    if course_changes:
        print("- Curso possui alterações pendentes; não encerre como checkpoint concluído.")
        for line in course_changes:
            print(f"  {line}")
    else:
        print("- Curso limpo: todo o trabalho do Codex está persistido em commits.")
    if student_changes:
        print("- A área do aluno possui alterações manuais não commitadas:")
        for line in student_changes:
            print(f"  {line}")
    else:
        print("- Área do aluno sem alterações pendentes.")

    return 1 if course_changes else 0


if __name__ == "__main__":
    raise SystemExit(main())
