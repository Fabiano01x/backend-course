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
| 3 | FastAPI & SQLAlchemy: PostgreSQL Integration | `source/module-05/03.md` | engine assíncrona, `AsyncSession`, DI, PostgreSQL, Docker, lifespan | 3 | Sessões assíncronas e PostgreSQL | Concluído e corrigido | Usamos `async_sessionmaker`, configuração validada e `URL.create`; a saúde executa `SELECT 1` em vez de inspecionar estado local. O `create_all` introduzido como ponte nesta etapa foi removido em M05/A05. |
| 4 | ORM CRUD Operations | `source/module-05/04.md` | `select`, create/read/update/delete, schemas, repository, service | 4 e 6 | CRUD persistente; Empréstimos atômicos | Concluído, corrigido e dividido | M05/A04 traduz o contrato simples para SQLAlchemy direto e corrige `PUT`; M05/A06 introduz repository e service somente quando a retirada exige coordenação transacional real. |
| 5 | Alembic Migrations: Managing Database Schema Changes | `source/module-05/05.md` | revisões, `upgrade`, `downgrade`, autogenerate, `target_metadata` | 5 | Evoluindo o esquema com Alembic | Concluído e corrigido | Autogenerate produz uma migração candidata que deve ser revisada; a aplicação deixa de criar tabelas no startup. A baseline assíncrona foi testada nas duas direções em PostgreSQL real. |
| 6 | Atomic Writes with Database Transactions | `source/module-05/06.md` | ACID, commit, rollback, Unit of Work, fronteiras transacionais | 6 | Empréstimos atômicos e fronteiras de transação | Concluído, integrado e corrigido | A transação coordena regras, lock e INSERT; disponibilidade deriva do histórico em vez de exigir um segundo write. `AsyncSession` fornece a unidade de trabalho sem uma classe genérica prematura. |
| 7 | Optimizing Relationship Loading for N+1 Query Prevention | `source/module-05/07.md` | lazy loading, N+1, `selectinload`, `joinedload`, `lazy="raise"` | 7 | Consultas previsíveis sem N+1 | Concluído e corrigido | Em código assíncrono, I/O implícito também pode falhar; as relações são carregadas explicitamente, `lazy="raise"` impede surpresas e testes protegem o número real de consultas. |

### Sequência concluída

1. Do dicionário ao esquema relacional.
2. Modelos e relações com SQLAlchemy 2.
3. Sessões assíncronas e PostgreSQL.
4. CRUD persistente sem esconder o ORM.
5. Evoluindo o esquema com Alembic.
6. Empréstimos atômicos e fronteiras de transação.
7. Consultas previsíveis sem N+1.

## Módulo 6 — Backend Authentication and Security

- Fonte importada integralmente: 6 aulas da versão 3.
- A sequência autoral começa pela credencial que o modelo atual ainda não
  possui e integra cada mecanismo à Library API.

| Ordem original | Aula original | Fonte | Conceitos identificados | Nova posição | Nova aula | Status | Justificativa |
|---:|---|---|---|---:|---|---|---|
| 1 | JWT Authentication with Access and Refresh Tokens | `source/module-06/01.md` | JWT, claims, access token, refresh token, login, armazenamento no cliente | 1 e 2 | Identidade local sem armazenar senhas; Access tokens curtos e identidade autenticada | Analisado, dividido e corrigido | A fonte pressupõe um `authenticate_user` inexistente. Primeiro adicionaremos hash e verificação de senha; depois emitiremos JWT com algoritmo fixo, claims validadas e identidade derivada do token. Refresh não será estático nem entregue antes de seu ciclo seguro. |
| 2 | Secure Refresh Token Management | `source/module-06/02.md` | rotação, `jti`, persistência, revogação, reutilização, logout | 3 | Sessões renováveis sob um navegador hostil | Analisado, integrado e corrigido | Rotação e proteção do transporte pertencem ao mesmo problema. O servidor armazenará digest, família e estado transacional em vez de token bruto ou uma tabela chamada blocklist que também funciona como allowlist. |
| 3 | Implementing RBAC Systems | `source/module-06/03.md` | AuthN versus AuthZ, roles, associação muitos-para-muitos, claims, dependências, `403` | 4 | Autorização explícita com papéis | Analisado e corrigido | Papéis serão consultados como estado atual para que remoções tenham efeito imediato; claims de longa validade não serão tratadas como fonte autoritativa. Propriedade e papel continuarão regras distintas. |
| 4 | Implementing OAuth2 for Social Login | `source/module-06/04.md` | Authorization Code, redirect URI, state, client secret, callback, login social | 5 | Login social é OpenID Connect | Analisado e corrigido | OAuth 2.0 delega autorização; identidade requer OIDC. Além de `state`, validaremos issuer, audience, nonce e assinatura, e vincularemos a conta por `(provider, subject)` em vez de confiar apenas no e-mail. |
| 5 | API Key Authentication for Service-to-Service Communication | `source/module-06/05.md` | credencial de máquina, header, comparação segura, hash, prefixo, chamada entre serviços | 6 | Chaves de API com ciclo de vida | Analisado e complementado | Uma constante global não identifica clientes nem permite rotação. A chave terá prefixo público, segredo exibido uma vez, digest, escopos, expiração opcional e revogação; TLS continua obrigatório. |
| 6 | Preventing XSS and CSRF Attacks | `source/module-06/06.md` | XSS, encoding, cookies, CSRF, SameSite, token, Fetch Metadata, defesa em profundidade | 3 | Sessões renováveis sob um navegador hostil | Analisado, antecipado e integrado | O risco nasce quando o refresh token entra em cookie. A aula combinará `HttpOnly`, `Secure`, `SameSite`, origem/CSRF e limites do backend contra XSS, sem copiar exemplos Flask/Jinja como se fossem a arquitetura atual. |

### Sequência planejada

1. Identidade local sem armazenar senhas.
2. Access tokens curtos e identidade autenticada.
3. Sessões renováveis sob um navegador hostil.
4. Autorização explícita com papéis.
5. Login social é OpenID Connect.
6. Chaves de API com ciclo de vida.
