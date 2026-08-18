# Registro de conceitos

Este arquivo registra o que já faz parte do estado cumulativo das aulas
concluídas.

## FastAPI

- Introduzido: Módulo 4 / aula 1.
- Estado: incorporado.
- Papel: receber requisições HTTP, validar contratos e produzir respostas.
- Regra: `app/main.py` é o ponto de composição, não um catálogo de regras de
  domínio.

## Async e await

- Introduzido: Módulo 4 / aula 1.
- Estado: incorporado.
- `async def` cria uma função coroutine; sua chamada produz uma coroutine.
- `await` suspende a task atual quando a operação aguardada precisa esperar,
  permitindo que o event loop execute outras tasks prontas.
- Correção registrada: aguardar uma coroutine diretamente não impede, por si
  só, que outras tasks executem quando ela alcança um ponto de suspensão.
- `create_task()` agenda trabalho independente; não deve envolver toda
  coroutine apenas para que `await` seja cooperativo.

## Pydantic v2

- Introduzido: Módulo 4 / aula 2.
- Estado: incorporado.
- `BookCreate`/`UserCreate` controlam entrada; `BookResponse`/`UserResponse`
  controlam saída.
- Campos extras são recusados para tornar o contrato explícito.
- A partir daqui, endpoints de criação não recebem `dict` cru.
- `StrictSchema` recusa campos extras; campos obrigatórios são anotados sem
  valor padrão e serializados com `model_dump()`.

## Contratos HTTP

- Introduzido: Módulo 4 / aula 2.
- Criação responde `201`; recurso ausente responde `404`; falhas de tipos,
  limites ou campos extras respondem `422`.
- Os modelos de entrada não aceitam identificadores nem estado controlado pelo
  servidor.
- Na aula 4, `GET /books` passa intencionalmente de um array solto para
  `BookPage`, com `items`, `total`, `limit` e `offset`.

## APIRouter

- Introduzido: Módulo 4 / aula 3.
- Estado: incorporado permanentemente.
- Rotas de livros ficam em `books.router`, usuários em `users.router` e rotas
  operacionais em `system.router`.
- Prefixos e tags comuns pertencem ao construtor de `APIRouter`.
- `app.include_router()` é o ponto explícito de montagem.
- Exceção: um exemplo mínimo pode usar `app.get()` se declarar que serve
  apenas para isolar um conceito. O projeto principal continuará com routers.

## Armazenamento em memória

- Estado: substituído em M05/A04.
- Serviu como implementação temporária, sem fingir durabilidade ou repository.
- `app/data.py` não faz parte do estado atual; livros e usuários usam
  PostgreSQL.

## Query parameters

- Introduzido: Módulo 4 / aula 4.
- Estado: incorporado na listagem de livros.
- `available` distingue ausência (`None`) de filtro explícito por `false`.
- `author` faz busca parcial sem diferença entre maiúsculas e minúsculas.
- `sort_by` aceita somente `id`, `title` e `author`; `order` aceita `asc` e
  `desc`.
- Valores fora do contrato respondem `422` antes do endpoint.

## Paginação limit-offset

- Introduzido: Módulo 4 / aula 4.
- Pipeline permanente: filtrar → ordenar → contar → recortar.
- `limit` aceita de 1 a 100 e `offset` deve ser maior ou igual a zero.
- `total` representa a quantidade depois dos filtros e antes do recorte.
- Em M05/A04, filtros, contagem, ordem, limite e offset são executados pelo
  PostgreSQL. A paginação ainda pode deslocar itens sob escritas concorrentes;
  cursor será considerado quando essa necessidade aparecer.

## Pydantic Settings

- Introduzido: Módulo 4 / aula 5.
- `Settings` centraliza nome, versão, ambiente, debug e limites de paginação.
- O prefixo externo é `LIBRARY_`; argumentos explícitos prevalecem sobre
  variáveis do processo, que prevalecem sobre `.env` e defaults.
- `.env` é ignorado pelo Git; `.env.example` contém apenas exemplos seguros.
- Campos isolados usam `Field`; `model_validator` garante que o tamanho padrão
  não supere o máximo.
- A configuração é congelada depois de validada e uma inconsistência impede a
  inicialização.
- O objeto global da aula 5 foi substituído por dependência cacheada na aula 6.

## Configuração pública

- `GET /info` expõe somente nome, versão, ambiente e debug por meio de
  `AppInfo`.
- Variáveis de ambiente não são tratadas como cofre de segredos.
- Configurações privadas de banco nunca entram nessa resposta; JWT continua
  adiado porque ainda não possui consumidor.

## Dependency Injection

- Introduzido: Módulo 4 / aula 6.
- `load_settings()` mantém uma instância por processo com `lru_cache`.
- `get_settings()` é o provider assíncrono; `AppSettings` combina tipo e
  `Depends`.
- `/info` e `GET /books` recebem settings durante a requisição.
- Testes substituem o provider com `app.dependency_overrides` e limpam o
  override depois de cada caso.
- Metadados de `FastAPI` pertencem à inicialização e chamam o carregador
  diretamente; overrides de requisição não reconstroem a aplicação.

## Dependências com yield

- Modelo de ciclo: setup → `yield` → consumidor → `finally`/teardown.
- O fechamento deve ficar em `finally` para também ocorrer em falhas.
- Desde M05/A03, `get_session` cria e fecha uma `AsyncSession` real; em M05/A04,
  os routers de domínio passam a consumi-la.

## CORS e preflight

- Introduzido: Módulo 4 / aula 7.
- CORS é uma política do navegador; não autentica clientes nem impede que
  outros programas chamem a API.
- Origens permitidas são explícitas e vêm de `Settings`; wildcard é recusado
  porque a API permite credenciais.
- Métodos e headers também formam uma lista permitida explícita.
- O preflight `OPTIONS` deve receber tanto os headers CORS quanto os headers
  defensivos da aplicação.

## Headers de segurança

- Introduzido: Módulo 4 / aula 7.
- Um middleware adiciona `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy` e `Permissions-Policy` a todas as respostas.
- HSTS só é emitido quando `environment=production` e `https_enabled=true`.
- Nenhuma CSP genérica é aplicada: `/docs` e `/redoc` continuam disponíveis,
  e uma política futura deverá ser projetada a partir dos recursos realmente
  usados pelas interfaces.
- `create_app(settings)` permite testar políticas definidas na inicialização
  sem depender de reimportação ou estado global.

## OpenAPI como contrato

- Introduzido: Módulo 4 / aula 8.
- `/openapi.json` é a fonte legível por máquina usada por Swagger UI, ReDoc e
  geradores de clientes.
- Metadados da aplicação descrevem somente recursos realmente implementados;
  contato, licença e deprecação não são inventados para ornamentar a interface.
- Tags possuem descrição e ordem explícitas.
- Cada operação possui `operationId` único e estável, resumo e descrição da
  resposta principal.
- `ErrorResponse` documenta os `404` realmente produzidos por consultas de
  livro e usuário; o `422` de validação continua gerado pelo FastAPI.
- `BookCreate` e `UserCreate` publicam exemplos no JSON Schema.
- Testes inspecionam o JSON publicado, não apenas a disponibilidade visual de
  `/docs` e `/redoc`.

## Esquema relacional

- Introduzido: Módulo 5 / aula 1.
- `users`, `books` e `loans` separam fatos com identidade própria.
- Chaves estrangeiras de `loans` usam `ON DELETE RESTRICT` para preservar o
  histórico de livros e usuários.
- E-mail e ISBN possuem unicidade; checks protegem texto e ordem temporal.
- `books.available` não é persistido: disponibilidade deriva da ausência de um
  empréstimo com `returned_at IS NULL`.
- Um índice único parcial permite histórico, mas impede dois empréstimos ativos
  para o mesmo livro.
- Autores ainda não são entidades porque não possuem ciclo de vida próprio no
  escopo atual.

## Modelos SQLAlchemy 2

- Introduzido: Módulo 5 / aula 2.
- `Base` herda de `DeclarativeBase` e concentra o metadata de `users`, `books`
  e `loans`.
- Colunas usam `Mapped`, `mapped_column` e tipos explícitos do SQLAlchemy 2.
- `ForeignKey` expressa integridade no banco; `relationship` oferece navegação
  bidirecional entre objetos.
- `Loan` usa association object porque a relação possui `borrowed_at`, `due_at`
  e `returned_at`.
- O metadata preserva constraints nomeadas e o índice parcial PostgreSQL.
- A separação entre schemas Pydantic e modelos ORM continua permanente.

## PostgreSQL assíncrono e sessões

- Introduzido: Módulo 5 / aula 3.
- `URL.create()` recebe os componentes separadamente e evita interpretar `@`,
  `/` e outros caracteres da senha como estrutura da URL.
- `create_async_engine()` configura o dialeto `postgresql+asyncpg`; conexões
  são obtidas somente quando existe I/O.
- `async_sessionmaker` é a fábrica compartilhada; `AsyncSession` é criada e
  fechada por requisição por uma dependência com `yield`.
- A engine pertence ao ciclo da aplicação e é descartada no shutdown.
- `GET /health/database` executa `SELECT 1`; `session.is_active` não comprova
  conectividade com o servidor.
- Desde M05/A05, o lifespan não executa DDL; ele apenas descarta a engine no
  shutdown. O esquema é atualizado explicitamente antes de iniciar a API.

## CRUD persistente com SQLAlchemy

- Introduzido: Módulo 5 / aula 4.
- CRUDs simples de livros e usuários usam `AsyncSession` diretamente. Desde
  M05/A06, somente o caso composto de empréstimo usa repository e service.
- `POST` usa `add`, `commit` e `refresh`; violações de unicidade provocam
  rollback e resposta `409 Conflict`.
- `select()` constrói consultas; `execute`, `scalar`, `scalars` e `session.get`
  materializam resultados conforme o formato selecionado.
- `GET /books` executa filtros, contagem, ordenação determinística, limite e
  offset no PostgreSQL.
- Disponibilidade é projetada com `NOT EXISTS` sobre empréstimos ativos; não
  existe coluna `books.available`.
- `%`, `_` e `\` são escapados na busca literal com `ILIKE`.
- `PUT /books/{id}` exige representação completa dos campos editáveis;
  atualização parcial exigiria um contrato `PATCH` separado.
- `DELETE /books/{id}` responde `204` sem corpo; histórico protegido por
  `ON DELETE RESTRICT` gera `409`.

## Migrações com Alembic

- Introduzido: Módulo 5 / aula 5.
- Revisões formam um grafo por `revision` e `down_revision`; `head` representa
  a ponta esperada e `alembic_version` registra o estado do banco.
- A baseline `0001_library_schema` cria e reverte `users`, `books`, `loans`,
  constraints e o índice único parcial.
- `target_metadata = Base.metadata` permite comparar modelos e banco.
- Autogenerate cria uma candidata, não uma migração confiável sem revisão.
- O ambiente Alembic reutiliza `Settings` e `build_database_url`; credenciais
  não são persistidas no INI.
- A conexão `asyncpg` executa as operações síncronas do Alembic por
  `connection.run_sync`, com `NullPool` e descarte da engine ao final.
- Migrações são etapa de deploy: `alembic upgrade head` acontece antes do
  processo da API e nunca dentro de seu startup.

## Transações e empréstimos atômicos

- Introduzido: Módulo 5 / aula 6.
- `async with session.begin()` confirma na saída normal e reverte quando uma
  exceção atravessa a fronteira.
- `flush()` envia mudanças e verifica constraints sem encerrar a transação;
  `commit()` torna o conjunto permanente.
- A `AsyncSession` já rastreia mudanças e controla a transação, portanto não
  foi envolvida por uma classe Unit of Work que apenas repetiria sua API.
- `LoanRepository` executa consultas, `add` e `flush`, mas nunca commit ou
  rollback. O service de empréstimos possui a fronteira transacional e as regras.
- `SELECT FOR UPDATE` serializa retiradas que decidem sobre o mesmo livro. O
  índice parcial continua sendo a garantia final contra dois ativos.
- `POST /loans` exige usuário ativo, livro existente, disponibilidade e prazo
  futuro com fuso; ausências retornam `404` e conflitos de estado, `409`.
- `POST /loans/{loan_id}/return` preenche `returned_at`; disponibilidade muda
  por derivação do histórico, sem atualizar um flag redundante em `books`.
- I/O externo não pertence a uma transação de banco curta.
