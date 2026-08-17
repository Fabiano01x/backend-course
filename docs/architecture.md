# Arquitetura da Library API

## Estado sequencial atual: checkpoint M05/A02

```text
Cliente HTTP
    |
    v
SecurityHeadersMiddleware
    |
    v
CORSMiddleware (origens explícitas por ambiente)
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

routers + schemas + metadados
              |
              v
        /openapi.json
          |       |
          v       v
       /docs    /redoc

defaults + .env + variáveis do processo
                  |
                  v
       load_settings() + lru_cache
             |                         |
             v                         v
  create_app() + middlewares     get_settings() + Depends
                                        |
                                        +--> /info
                                        └--> limites de /books
```

A implementação sequencial está em
`reference/checkpoints/module-05/lesson-02/`. `app/main.py` cria a aplicação,
configura os middlewares e inclui os routers; cada módulo em `app/routers/`
concentra um grupo de rotas.
`schemas.py` declara os contratos e `data.py` guarda estado temporário
reinicializável. A listagem de livros aplica seu pipeline diretamente no router
porque ainda existe uma única consulta simples. O piloto anterior continua
preservado separadamente.

`config.py` declara o contrato sem criar instância. `dependencies.py` separa o
carregador cacheado do provider injetável. Startup chama o carregador; endpoints
recebem o provider por `Depends`. `create_app(settings)` torna testáveis as
políticas de startup. CORS aceita apenas origens, métodos e headers declarados;
o middleware externo aplica headers defensivos inclusive ao preflight. HSTS
exige simultaneamente produção e HTTPS, enquanto CSP permanece adiada para não
quebrar Swagger e ReDoc com uma política genérica.

O contrato OpenAPI agrega metadados da aplicação, descrições das tags,
identificadores estáveis das operações, schemas Pydantic e respostas adicionais.
Testes consultam `/openapi.json` para proteger esse contrato; Swagger UI e
ReDoc apenas o apresentam de formas diferentes.

`schema.sql` registra o desenho de dados. `app/models.py` traduz `users`,
`books` e `loans` para metadata SQLAlchemy tipado, incluindo a entidade
associativa `Loan`. A API ainda usa as coleções em memória; engine e sessão
entram na aula seguinte.

## Separação pedagógica

```text
course/                         mudanças guiadas que o aluno digita
student/library-api/            implementação manual protegida
reference/checkpoints/...       solução cumulativa por aula
reference/pilot/...             protótipo anterior à sequência completa
```

## Camada de apresentação do curso

```text
course/<módulo>/*.md + module.json
                  |
                  v
       scripts/build_course.py
                  |
                  v
 dist/html/module-<número>/*.html (não versionado)
```

Markdown continua sendo a fonte editável. O gerador aplica o tema compartilhado
de `course/theme/`, cria o índice e a navegação, e produz uma página contínua
por aula. O processo não altera os Markdown nem a área do aluno.

## Limites intencionais

- O estado em `app/data.py` não é persistente nem adequado para múltiplos
  processos. Ele torna visível o problema que motivará o módulo de banco.
- Paginação por offset sobre uma coleção mutável não oferece snapshot estável;
  esse limite é explícito até a introdução do banco.
- Ainda não existem service layer, repository, engine, sessão, migrations ou
  transações. O ORM mapeia apenas a estrutura nesta etapa.
- `Loan` já faz parte do esquema conceitual, mas ainda não possui rota nem
  modelo Python.
- As funções são `async` para preservar o caminho pedagógico, mas o estado
  atual não realiza I/O. Nenhuma operação bloqueante deve ser adicionada a elas.

## Evolução concluída no Módulo 4

```text
rotas modulares
    → listagens com query parameters
    → configuração validada
    → configuração injetável
    → CORS e headers por ambiente
    → contrato OpenAPI auditado
```

Banco de dados, autenticação e containers permanecem nos módulos posteriores.
