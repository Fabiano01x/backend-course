# Backend Course — Library API

Este repositório transforma a parte de backend do curso **Python full stack
for MNCs** em um percurso prático e cumulativo. A fonte original permanece em
inglês e imutável; o novo curso é escrito em português do Brasil.

O primeiro marco cobre a análise do Módulo 4 e uma aula piloto sobre
`APIRouter`. Banco de dados, autenticação, Docker, HTML e PDF foram
intencionalmente adiados.

## Estrutura

```text
source/           material original do Grasp (nunca editar)
course/           aulas autorais em Markdown
project/backend/  Library API executável
docs/             mapa curricular e memória operacional
scripts/          importação e validação
tests/            testes das ferramentas do curso
```

## Importar a fonte

O comando abaixo consulta a versão 3 e importa somente o Módulo 4. Ele recusa
sobrescrever uma importação existente.

```bash
python3 scripts/import_grasp.py
```

## Preparar o ambiente

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e './project/backend[dev]'
```

## Executar a API

```bash
.venv/bin/python -m uvicorn app.main:app --reload --app-dir project/backend
```

Documentação interativa: `http://127.0.0.1:8000/docs`.

## Validar

```bash
.venv/bin/python -m pytest -q tests project/backend/tests
.venv/bin/python scripts/validate_course.py
```

O estado e a próxima etapa estão registrados em `docs/progress.md`.

