# Mapa curricular

## Escopo analisado

- Curso: **Python full stack for MNCs**
- Course ID: `3b30bbfd-e48e-4883-8450-8fca5452c8d1`
- Versão: `3`
- Módulo original: **Modern Python Backend with FastAPI**
- Total: 8 aulas

Os títulos e conceitos abaixo vieram da fonte. Os novos títulos, a ordem e
as decisões de implementação são reorganização pedagógica deste projeto.

## Cobertura e reorganização

| Ordem original | Aula original | Fonte | Conceitos identificados | Nova posição | Nova aula | Status | Justificativa |
|---:|---|---|---|---:|---|---|---|
| 1 | Asynchronous Python: Coroutines and Async/Await | `source/module-04/01.md` | I/O-bound, coroutine, `async`, `await`, event loop, task, `gather` | 1 | Primeira Library API e programação assíncrona | Concluído e corrigido | O FastAPI mínimo dá contexto ao async. A explicação incorreta sobre aguardar uma coroutine foi corrigida e comprovada por exemplo. |
| 2 | Building Modular FastAPI Apps with Routers | `source/module-04/02.md` | `APIRouter`, prefix, tags, packages, `include_router`, organização por domínio | 3 | Crescendo sem um `main.py` monolítico | Concluído | Primeiro tornamos a dor visível com rotas de livros e usuários; depois adotamos routers permanentemente. |
| 3 | Pydantic Data Models for Request/Response Validation | `source/module-04/03.md` | `BaseModel`, request body, `response_model`, `Field`, validadores | 2 | Contratos de entrada e saída com Pydantic v2 | Concluído e reordenado | Os contratos aparecem antes da refatoração estrutural, permitindo comprovar depois que mover uma rota não muda seu contrato HTTP. |
| 4 | Dependency Injection for Resource Management | `source/module-04/04.md` | `Depends`, `yield`, setup/teardown, substituição em testes, sessão de banco | 6 | Dependências e ciclo de vida de recursos | Concluído e dividido | DI foi aplicada a configurações e o ciclo com `yield` foi preparado. `AsyncSession` ficou como ponte para o Módulo 5, sem banco fictício. |
| 5 | Advanced RESTful API Design | `source/module-04/05.md` | query parameters, filtros, ordenação, limit/offset, paginação, SQLAlchemy | 4 | Filtros, ordenação e paginação | Concluído e dividido | O contrato REST foi implementado com a coleção em memória. Queries SQLAlchemy e bibliotecas de paginação serão retomadas quando houver banco. |
| 6 | Securing FastAPI: CORS and Essential Headers | `source/module-04/06.md` | same-origin policy, preflight, `CORSMiddleware`, headers, middleware | 7 | Integração segura com o frontend | Concluído e complementado | CORS foi ligado à configuração por ambiente. HSTS ficou condicionado a HTTPS e produção; uma CSP genérica foi omitida e Swagger/ReDoc foram testados. |
| 7 | Environment Variables for Configuration and Secrets | `source/module-04/07.md` | variáveis de ambiente, `.env`, `BaseSettings`, `lru_cache`, settings como dependência | 5 | Configuração por ambiente | Concluído e dividido | A configuração foi externalizada com `BaseSettings`; a refatoração para `Depends` e cache ficou como problema concreto da aula seguinte. |
| 8 | Interactive API Docs with Swagger UI & ReDoc | `source/module-04/08.md` | OpenAPI, Swagger UI, ReDoc, metadados, tags, descrições | 8 | OpenAPI como contrato executável | Concluído e complementado | O módulo foi encerrado com metadados, exemplos, respostas de erro e `operationId` estáveis, todos auditados diretamente em `/openapi.json`. |

## Sequência aprovada

1. Primeira Library API e programação assíncrona.
2. Contratos de entrada e saída com Pydantic v2.
3. Crescendo sem um `main.py` monolítico.
4. Filtros, ordenação e paginação.
5. Configuração por ambiente.
6. Dependências e ciclo de vida de recursos.
7. Integração segura com o frontend.
8. OpenAPI como contrato executável.

As aulas são concluídas sequencialmente. O status de cada linha distingue
conteúdo produzido de planejamento aprovado.

## Módulo 5 — Database Modeling with SQLAlchemy

- Fonte importada integralmente: 7 aulas da versão 3.
- Projeto cumulativo preservado: a Library API substitui gradualmente o estado
  em memória por PostgreSQL.

| Ordem original | Aula original | Fonte | Conceitos identificados | Nova posição | Nova aula | Status | Justificativa |
|---:|---|---|---|---:|---|---|---|
| 1 | Database Schema Design for Full-Stack Applications | `source/module-05/01.md` | normalização, entidades, chaves, restrições, integridade referencial | 1 | Do dicionário ao esquema relacional | Concluído e adaptado | O exemplo de plataforma de cursos cedeu lugar a `users`, `books` e `loans`; o esquema nasceu do problema de perda de estado da Library API. |
| 2 | SQLAlchemy Models & Relationships | `source/module-05/02.md` | `DeclarativeBase`, `Mapped`, `mapped_column`, `ForeignKey`, relacionamentos | 2 | Modelos e relações com SQLAlchemy 2 | Concluído e complementado | `Loan` foi implementada como entidade associativa, pois a relação possui datas e estado próprios; uma tabela `secondary` simples perderia esses atributos. |
| 3 | FastAPI & SQLAlchemy: PostgreSQL Integration | `source/module-05/03.md` | engine assíncrona, `AsyncSession`, DI, PostgreSQL, Docker, lifespan | 3 | Sessões assíncronas e PostgreSQL | Analisado e corrigido | Usaremos `async_sessionmaker`, configuração validada e URL segura. `create_all` será somente uma ponte temporária e sairá quando Alembic entrar. |
| 4 | ORM CRUD Operations | `source/module-05/04.md` | `select`, create/read/update/delete, schemas, repository, service | 4 e 6 | CRUD persistente; Empréstimos atômicos | Analisado e dividido | O ORM aparece diretamente nos routers primeiro. Repository e service só entram quando o caso de empréstimo exigir coordenação e fronteira transacional. |
| 5 | Alembic Migrations: Managing Database Schema Changes | `source/module-05/05.md` | revisões, `upgrade`, `downgrade`, autogenerate, `target_metadata` | 5 | Evoluindo o esquema com Alembic | Analisado e corrigido | Autogenerate produz uma migração candidata que deve ser revisada; a aplicação deixa de criar tabelas no startup. |
| 6 | Atomic Writes with Database Transactions | `source/module-05/06.md` | ACID, commit, rollback, Unit of Work, fronteiras transacionais | 6 | Empréstimos atômicos e fronteiras de transação | Analisado e integrado | A transação responde ao caso real: criar o histórico e tornar o livro indisponível juntos. `AsyncSession` fornece a unidade de trabalho sem uma classe genérica prematura. |
| 7 | Optimizing Relationship Loading for N+1 Query Prevention | `source/module-05/07.md` | lazy loading, N+1, `selectinload`, `joinedload`, `lazy="raise"` | 7 | Consultas previsíveis sem N+1 | Analisado e corrigido | Em código assíncrono, I/O implícito também pode falhar; as relações serão carregadas explicitamente e o número de consultas será testado. |

### Sequência planejada

1. Do dicionário ao esquema relacional.
2. Modelos e relações com SQLAlchemy 2.
3. Sessões assíncronas e PostgreSQL.
4. CRUD persistente sem esconder o ORM.
5. Evoluindo o esquema com Alembic.
6. Empréstimos atômicos e fronteiras de transação.
7. Consultas previsíveis sem N+1.
