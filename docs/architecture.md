# Arquitetura da Library API

## Estado sequencial atual: checkpoint da aula 05

```text
Cliente HTTP
    |
    v
FastAPI (app/main.py)
    |
    +--> system.router --> GET /health
    +--> books.router  --> GET /books
    |                         |
    |                         v
    |                 filtrar → ordenar → contar → recortar
    |                         |
    |                         v
    |                      BookPage
    |
    +--> books.router  --> POST /books, GET /books/{book_id}
    +--> users.router  --> GET/POST /users, GET /users/{user_id}
                                  |
                                  v
                            schemas Pydantic
                                  |
                                  v
                      coleções temporárias em memória

defaults + .env + variáveis do processo
                  |
                  v
          Settings (app/config.py)
             |       |       |
             v       v       v
          FastAPI  /info  limites de /books
```

A implementação sequencial está em
`reference/checkpoints/module-04/lesson-05/`. `app/main.py` cria a aplicação e
inclui os routers; cada módulo em `app/routers/` concentra um grupo de rotas.
`schemas.py` declara os contratos e `data.py` guarda estado temporário
reinicializável. A listagem de livros aplica seu pipeline diretamente no router
porque ainda existe uma única consulta simples. O piloto anterior continua
preservado separadamente.

`config.py` valida fontes externas e cria uma instância global congelada.
`main.py`, `books.router` e `system.router` importam essa instância. Esse
acoplamento é temporário e fornece o problema concreto da aula 6.

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
- Paginação por offset sobre uma coleção mutável não oferece snapshot estável;
  esse limite é explícito até a introdução do banco.
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
