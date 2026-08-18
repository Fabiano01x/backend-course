# Backend Course — Library API

Este repositório transforma a parte de backend do curso **Python full stack
for MNCs** em um percurso prático e cumulativo. A fonte original permanece em
inglês e imutável; o novo curso é escrito em português do Brasil.

O Módulo 4 constrói a fronteira HTTP da Library API ao longo de oito aulas. O
Módulo 5 substitui o estado em memória por persistência relacional e encerra
com transações e leituras previsíveis. O Módulo 6, já importado e planejado,
está adicionando autenticação e segurança; credenciais locais, access tokens
curtos e sessões renováveis já integram a API. PDF continua adiado.

## Estrutura

```text
source/           material original do Grasp (nunca editar)
course/           aulas autorais em Markdown
student/          área de prática manual protegida
reference/pilot/  solução usada para validar a metodologia inicial
reference/checkpoints/ soluções cumulativas, uma por aula concluída
docs/             mapa curricular e memória operacional
scripts/          importação, comparação e validação
tests/            testes das ferramentas do curso
dist/html/        aulas HTML geradas localmente (ignorado pelo Git)
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
.venv/bin/python -m pip install -e './reference/checkpoints/module-06/lesson-03[dev]'
```

## Executar a API

```bash
docker compose -f reference/checkpoints/module-06/lesson-03/compose.yaml up -d --wait
.venv/bin/python -m uvicorn app.main:app --reload \
  --app-dir reference/checkpoints/module-06/lesson-03
```

Documentação interativa: `http://127.0.0.1:8000/docs`.

## Validar

```bash
.venv/bin/python -m pytest -q tests
PYTHONPATH=reference/checkpoints/module-06/lesson-03 \
  .venv/bin/python -m pytest -q reference/checkpoints/module-06/lesson-03/tests
.venv/bin/python scripts/validate_course.py
```

## Gerar a versão visual das aulas

O Markdown é a fonte canônica. A saída abaixo cria uma página HTML contínua
por aula, sem paginação:

```bash
.venv/bin/python -m pip install -r requirements-course.lock
.venv/bin/python scripts/build_course.py --module 4
```

Durante a produção progressiva, uma aula isolada pode ser gerada com
`--lesson 1`. O gerador descobre o diretório temático pelo número do módulo.
Os arquivos ficam em `dist/html/module-<número>/` e não são commitados.

## Praticar sem receber a solução pronta

Escreva seu código em `student/library-api/`. O Codex não altera essa pasta sem
um pedido explícito seu. Depois de concluir uma aula e criar seu commit, compare
com a referência correspondente:

```bash
python3 scripts/compare_checkpoint.py --module 4 --lesson 1
```

O protótipo anterior à sequência permanece em `reference/pilot/` somente como
registro metodológico. Para estudo e comparação, use sempre os checkpoints.

## Commits

Cada aula ou mudança relevante do curso termina em um commit próprio. O Codex
commita somente curso, referências e ferramentas; você cria os commits de
`student/library-api/`.

O estado e a próxima etapa estão registrados em `docs/progress.md`.

## Encerrar e continuar depois

Antes de fechar o projeto, gere uma verificação completa e confirme que todo o
trabalho do curso está commitado:

```bash
.venv/bin/python scripts/resume_status.py --verify
```

Ao voltar, use o mesmo comando sem `--verify` para ver imediatamente o último
commit e a próxima aula. O procedimento completo está em
[`docs/resume.md`](docs/resume.md).
