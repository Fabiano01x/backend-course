#!/usr/bin/env python3
"""Compara a área do aluno com um checkpoint sem alterar nenhum arquivo."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
IGNORED_ROOT_FILES = {"README.md"}


def collect_files(root: Path) -> dict[Path, Path]:
    """Retorna caminhos relativos comparáveis, ignorando somente artefatos locais."""

    files: dict[Path, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRECTORIES or part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        if len(relative.parts) == 1 and relative.name in IGNORED_ROOT_FILES:
            continue
        files[relative] = path
    return files


def read_text(path: Path) -> list[str] | None:
    try:
        return path.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return None


def compare_directories(student: Path, checkpoint: Path, output: object = sys.stdout) -> bool:
    """Exibe um diff unificado e retorna True quando existem diferenças."""

    student_files = collect_files(student)
    checkpoint_files = collect_files(checkpoint)
    differences = False

    for relative in sorted(student_files.keys() | checkpoint_files.keys()):
        student_path = student_files.get(relative)
        checkpoint_path = checkpoint_files.get(relative)
        if student_path is None:
            print(f"Somente no checkpoint: {relative}", file=output)
            differences = True
            continue
        if checkpoint_path is None:
            print(f"Somente na área do aluno: {relative}", file=output)
            differences = True
            continue
        if student_path.read_bytes() == checkpoint_path.read_bytes():
            continue

        differences = True
        student_text = read_text(student_path)
        checkpoint_text = read_text(checkpoint_path)
        if student_text is None or checkpoint_text is None:
            print(f"Arquivo binário diferente: {relative}", file=output)
            continue
        diff = difflib.unified_diff(
            student_text,
            checkpoint_text,
            fromfile=f"student/{relative}",
            tofile=f"checkpoint/{relative}",
        )
        print("".join(diff), end="", file=output)

    return differences


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=int, required=True)
    parser.add_argument("--lesson", type=int, required=True)
    parser.add_argument("--student", type=Path, default=ROOT / "student" / "library-api")
    parser.add_argument(
        "--reference-root", type=Path, default=ROOT / "reference" / "checkpoints"
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    student = arguments.student.resolve()
    checkpoint = (
        arguments.reference_root
        / f"module-{arguments.module:02d}"
        / f"lesson-{arguments.lesson:02d}"
    ).resolve()
    if not student.is_dir():
        print(f"Área do aluno não encontrada: {student}", file=sys.stderr)
        return 2
    if not checkpoint.is_dir():
        print(
            f"Checkpoint ainda não disponível: {checkpoint}. "
            "Conclua a refatoração da aula antes de comparar.",
            file=sys.stderr,
        )
        return 2

    differences = compare_directories(student, checkpoint)
    if differences:
        print("\nExistem diferenças entre sua implementação e o checkpoint.")
        return 1
    print("Sua implementação corresponde ao checkpoint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

