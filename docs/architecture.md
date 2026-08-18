# Arquitetura da Library API

## Estado sequencial atual: checkpoint M05/A07

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
    |                  --> GET /health/database
    |                               |
    |                               v
    |                       DatabaseSession
    |                               |
    |                               v
    |                        SELECT 1 no PostgreSQL
    +--> books.router  --> GET /books
    |                         |
    |                         v
    |                   filtros SQL
    |                  /           \
    |                 v             v
    |              COUNT       ORDER BY → LIMIT/OFFSET
    |                                  |
    |                                  v
    |                     Book + disponibilidade por NOT EXISTS
    |
    +--> books.router  --> GET/POST/PUT/DELETE /books...
    +--> users.router  --> GET/POST /users...
    |                  --> GET /users/{id}
    |                               |
    |                               v
    |                    selectinload(User.loans)
    |                    + joinedload(Loan.book)
    |                         2 statements
    +--> loans.router  --> GET/POST /loans
    |                  --> POST /loans/{id}/return
    |                         |             |
    |                         v             v
    |               GET: joinedload     writes: Loan service
    |                user + book        session.begin() boundary
    |                 1 statement              |
    |                                          v
    |                                   LoanRepository
    |                               SELECT ... FOR UPDATE
    |                                   add + flush
    |                                          |
    +-------------------------------+
                                  |
                                  v
                   schemas Pydantic + DatabaseSession
                                  |
                                  v
                  SQLAlchemy ORM → asyncpg → PostgreSQL

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

componentes validados de banco
              |
              v
         URL.create()
              |
              v
 AsyncEngine + async_sessionmaker
      |                  |
      v                  v
lifespan             get_session() + yield
dispose                 |
                        └--> uma AsyncSession por requisição

deploy / desenvolvimento
          |
          v
alembic upgrade head
          |
          v
0001_library_schema -> PostgreSQL
```

A implementação sequencial está em
`reference/checkpoints/module-05/lesson-07/`. `app/main.py` cria a aplicação,
configura os middlewares e inclui os routers; cada módulo em `app/routers/`
concentra um grupo de rotas.
`schemas.py` declara os contratos. `data.py` foi removido. CRUDs simples
consomem a sessão diretamente; o caso composto de empréstimo usa service e
repository focados. O piloto anterior continua preservado separadamente.

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
associativa `Loan`. `app/database.py` cria a URL segura, a engine e a fábrica de
sessões. A fábrica da aplicação aceita esse recurso por argumento, o guarda em
`app.state` e liga seu startup e shutdown ao lifespan.

`get_session()` cria uma `AsyncSession` por requisição e fecha o contexto após
o consumidor. Livros e usuários usam esse recurso para leituras e escritas.
`GET /books` emite uma contagem e uma consulta de página; disponibilidade é
projetada por `NOT EXISTS`. ISBN e e-mail duplicados viram `409` após rollback.
`PUT` substitui os campos editáveis do livro; `DELETE` retorna `204` ou preserva
histórico por `ON DELETE RESTRICT`.

Retirada e devolução usam uma fronteira `session.begin()` no service.
`LoanRepository` executa consultas e flush, mas não controla commit. A retirada
bloqueia o livro com `FOR UPDATE`; o índice parcial permanece como garantia
final contra dois empréstimos ativos. Disponibilidade muda pela criação ou
encerramento do fato `Loan`, sem flag redundante em `Book`.

As relações ORM usam `lazy="raise"`, portanto nenhuma serialização pode iniciar
I/O implicitamente. A listagem de empréstimos declara `joinedload(Loan.user)` e
`joinedload(Loan.book)` e materializa o contrato enriquecido em um statement. O
detalhe de usuário declara `selectinload(User.loans)` encadeado a
`joinedload(Loan.book)` e usa dois statements fixos. Testes contam as consultas
executadas e falham se esse orçamento ou a proibição de lazy loading regredir.

`alembic/env.py` reutiliza `Settings`, `build_database_url` e `Base.metadata`.
Credenciais não ficam em `alembic.ini`. A baseline cria as três tabelas e suas
invariantes; `alembic_version` registra a revisão aplicada. Migrações pertencem
à etapa de deploy. O lifespan da API não executa DDL e somente descarta a
engine no encerramento.

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

- Paginação por offset no PostgreSQL ainda pode deslocar itens sob escritas
  concorrentes; cursor permanece adiado até essa garantia ser necessária.
- Service e repository existem somente no caso composto de empréstimo; não
  foram generalizados para CRUDs simples nem envolvidos por interfaces vazias.
- Autogenerate fornece somente uma candidata; toda nova revisão exige revisão
  humana e teste de upgrade e downgrade.
- O histórico incluído em `GET /users/{id}` ainda não possui paginação; um
  endpoint de coleção separado será necessário quando o volume justificar.
- Usuários possuem Create e Read; Update e Delete ainda não foram exigidos pelo
  projeto. Livros possuem o ciclo CRUD completo.

## Evolução concluída no Módulo 4

```text
rotas modulares
    → listagens com query parameters
    → configuração validada
    → configuração injetável
    → CORS e headers por ambiente
    → contrato OpenAPI auditado
```

O Módulo 5 encerra com carregamento previsível de relacionamentos.
Autenticação permanece fora do escopo dos checkpoints atuais.
