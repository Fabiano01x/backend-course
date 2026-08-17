# Arquitetura da Library API

## Estado sequencial atual: checkpoint da aula 01

```text
Cliente HTTP
    |
    v
FastAPI (app/main.py)
    |
    +--> GET /health
    +--> GET /books --> lista temporária
    +--> GET /users --> lista temporária
```

A implementação sequencial está em
`reference/checkpoints/module-04/lesson-01/`. `app/main.py` ainda concentra as
três rotas porque a aplicação é pequena e o problema de organização ainda não
foi criado. O piloto com routers continua preservado separadamente.

## Separação pedagógica

```text
course/                         mudanças guiadas que o aluno digita
student/library-api/            implementação manual protegida
reference/checkpoints/...       solução cumulativa por aula
reference/pilot/...             protótipo anterior à sequência completa
```

## Camada de apresentação do curso

```text
course/04-fastapi/*.md + module.json
                  |
                  v
       scripts/build_course.py
                  |
                  v
 dist/html/module-04/*.html (não versionado)
```

Markdown continua sendo a fonte editável. O gerador aplica o tema compartilhado
de `course/theme/`, cria o índice e a navegação, e produz uma página contínua
por aula. O processo não altera os Markdown nem a área do aluno.

## Limites intencionais

- O estado em `app/data.py` não é persistente nem adequado para múltiplos
  processos. Ele torna visível o problema que motivará o módulo de banco.
- Ainda não existem service layer, repository, ORM, migrations ou transações.
- `Loan` será introduzido quando houver persistência suficiente para expressar
  disponibilidade e devolução corretamente.
- As funções são `async` para preservar o caminho pedagógico, mas o estado
  atual não realiza I/O. Nenhuma operação bloqueante deve ser adicionada a elas.

## Evolução planejada no Módulo 4

```text
rotas modulares
    → listagens com query parameters
    → configuração validada
    → configuração injetável
    → CORS e headers por ambiente
    → contrato OpenAPI auditado
```

Banco de dados, autenticação e containers permanecem nos módulos posteriores.
