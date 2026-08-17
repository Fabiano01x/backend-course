# Arquitetura da Library API

## Estado atual: referência piloto da aula 03

```text
Cliente HTTP
    |
    v
FastAPI (app/main.py)
    |
    +--> system.router --> GET /health
    +--> books.router  --> GET/POST /books, GET /books/{id}
    +--> users.router  --> GET/POST /users, GET /users/{id}
             |
             v
       schemas Pydantic
             |
             v
   coleções temporárias em memória
```

Essa implementação está preservada em
`reference/pilot/module-04/lesson-03/`. Ela valida a metodologia, mas ainda não
é o checkpoint sequencial definitivo, pois as novas aulas 1 e 2 não foram
produzidas.

`app/main.py` é o ponto de composição: cria `FastAPI` e inclui routers. Cada
router possui prefixo, tags, status HTTP e modelos de resposta do seu domínio.

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
