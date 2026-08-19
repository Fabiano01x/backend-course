# Arquitetura da Library API

## Estado sequencial atual: checkpoint M06/A04

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
    +--> books.router  --> GET /books... (público)
    |                  --> POST/PUT/DELETE /books... + librarian atual
    +--> auth.router   --> POST /auth/register
    |                         |
    |                         v
    |              pool limitado de worker threads
    |                         |
    |                         v
    |                  Argon2id -> password_hash
    |                  --> POST /auth/login
    |                         |
    |                         v
    |                   SELECT user + verify
    |                         |
    |                         v
    |                  access JWT (15 min)
    |                  + cookie refresh HttpOnly
    |                         |
    |                         v
    |                POST /auth/refresh + header CSRF
    |                         |
    |                         v
    |              SELECT digest FOR UPDATE
    |              INSERT substituto -> UPDATE anterior
    |              replay -> revoga família
    |                  --> POST /auth/logout
    |                         |
    |                         v
    |                  revoga família + limpa cookie
    +--> users.router  --> GET /users... + librarian
    |                  --> GET /users/{id} + proprietário ou librarian
    |                               |
    |                               v
    |                    selectinload(User.loans)
    |                    + joinedload(Loan.book)
    |                         2 statements
    +--> loans.router  --> GET /loans + librarian
    |                  |      |
    |                  |      v
    |                  | joinedload(user + book): 1 statement
    |                  |
    |                  --> POST /loans + Bearer token + member atual
    |                  |      |
    |                  |      v
    |                  | CurrentIdentity(sub do JWT)
    |                  |      |
    |                  |      v
    |                  --> POST /loans/{id}/return + librarian atual
    |                         |
    |                         v
    |                    Loan service
    |               session.begin() boundary
    |                         |
    |                         v
    |        papéis atuais + regras + LoanRepository
    |                SELECT ... FOR UPDATE + add/flush
    |                         |
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
0001_library_schema -> 0002_user_password_hash
                        -> 0003_refresh_token_rotation
                        -> 0004_role_assignments -> PostgreSQL
```

A implementação sequencial está em
`reference/checkpoints/module-06/lesson-04/`. `app/main.py` cria a aplicação,
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
`books`, `loans`, `refresh_tokens`, `roles` e `user_roles` para metadata
SQLAlchemy tipado, incluindo as entidades associativas `Loan` e `UserRole` e a
cadeia autorreferente da rotação. `app/database.py`
cria a URL segura, a engine e a fábrica de sessões. A fábrica da aplicação aceita
esse recurso por argumento, o guarda em `app.state` e liga seu startup e shutdown
ao lifespan.

`get_session()` cria uma `AsyncSession` por requisição e fecha o contexto após
o consumidor. Livros, usuários e autenticação usam esse recurso para leituras
e escritas.
`GET /books` emite uma contagem e uma consulta de página; disponibilidade é
projetada por `NOT EXISTS`. ISBN e e-mail duplicados viram `409` após rollback.
O conflito de ISBN é específico; o cadastro local usa mensagem genérica para
não confirmar a existência de um e-mail.
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

`auth.router` concentra cadastro, login, refresh e logout. `POST /auth/register`
normaliza o e-mail, desloca Argon2id para um pool limitado de workers e persiste
somente `password_hash`, junto da atribuição `member`. `POST /auth/login`
consulta o usuário, verifica a senha fora do event loop, emite um access JWT de
15 minutos e inicia uma família renovável.
Conta ausente, senha errada,
usuário inativo, conta legada e hash inválido produzem o mesmo `401`; os caminhos
sem hash real usam `DUMMY_PASSWORD_HASH`.

`security/tokens.py` fixa HS256 e o perfil `at+jwt`. Emissão e validação exigem
issuer, audience estrita, sujeito, datas, UUID em `jti` e
`token_type=access`. A chave usa `SecretStr`; a chave didática não é aceita em
produção. Tokens não são criptografados e não carregam dados confidenciais.

`get_current_identity` converte `Authorization: Bearer` em um sujeito validado
sem consultar o banco. `get_current_principal` usa esse sujeito para consultar
conta ativa e atribuições atuais; `require_librarian` transforma ausência do
papel em `403`. O JWT não contém papéis e uma remoção no banco vale na próxima
requisição mesmo com o mesmo token.

`POST /loans` remove `user_id` do corpo e passa o sujeito ao service. Dentro do
`session.begin()`, `AuthorizationRepository` recusa conta ausente ou inativa
com `401`, exige `member` com `403` e só então aplica as regras do livro. A
devolução exige `librarian` na mesma fronteira. Assim, autorização não abre uma
transação implícita antes do caso de uso atômico.

CRUDs de livro, listagem global de usuários e listagem de empréstimos recebem
`LibrarianPrincipal`. `GET /users/{id}` compara o sujeito com o recurso: o
próprio usuário pode ler seu perfil; outro perfil exige `librarian`. Papel
organizacional e propriedade permanecem políticas distintas.

Refresh tokens são valores opacos de 32 bytes aleatórios. Somente SHA-256 entra
em `refresh_tokens`; o valor bruto é transportado em cookie host-only,
`HttpOnly`, `SameSite=Strict`, `Path=/auth` e `Secure` em produção. A família
possui validade absoluta de sete dias.

`RefreshTokenRepository` bloqueia o digest e revoga famílias sem controlar
commit. `services/sessions.py` mantém a fronteira transacional: insere e faz
flush do substituto antes de ligar a FK `replaced_by_id` e marcar o elo anterior
como usado. Uma segunda apresentação encontra `used_at` e revoga a família.

Refresh e logout exigem `X-CSRF-Protection: 1`; navegadores cross-origin precisam
de preflight e a origem deve ser a própria API ou pertencer à allowlist.
`HttpOnly` limita extração por XSS, mas não impede um script executado na origem
confiável de emitir requisições. CORS e CSRF não são apresentados como defesa
contra XSS.

`alembic/env.py` reutiliza `Settings`, `build_database_url` e `Base.metadata`.
Credenciais não ficam em `alembic.ini`. A baseline cria as três tabelas e suas
invariantes; `alembic_version` registra a revisão aplicada. Migrações pertencem
à etapa de deploy. O lifespan da API não executa DDL e somente descarta a
engine no encerramento.

A revisão `0002_user_password_hash` adiciona uma coluna anulável. O `NULL`
preserva contas criadas antes de M06/A01 sem inventar uma credencial; somente
`/auth/register` cria novas identidades locais. O downgrade remove a coluna e
mantém a baseline separada.

M06/A02 não altera o esquema. A revisão `0003_refresh_token_rotation` cria
`refresh_tokens`, duas FKs, unicidade de digest/substituição, constraints
temporais e índices por família e usuário. O downgrade remove somente essa
tabela e preserva credenciais locais.

A revisão `0004_role_assignments` cria o catálogo `roles`, a associação
`user_roles` com chave composta, cadastra `member` e `librarian` e atribui
`member` aos usuários anteriores. O downgrade remove somente a associação e o
catálogo; as contas permanecem preservadas.

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
- Usuários possuem Read; criação pública migrou para `/auth/register`. Update e
  Delete ainda não foram exigidos. Livros possuem o ciclo CRUD completo.
- O access token expira em 15 minutos e não possui revogação individual. Logout
  encerra renovação, mas um access JWT emitido continua válido até expirar.
- Ainda não existem rate limit ou recuperação de senha.
- O cookie `SameSite=Strict` pressupõe frontend same-site. Um deploy cross-site
  exige rever transporte, `SameSite=None; Secure` e as camadas CSRF.
- Papéis são consultados a cada operação protegida. Um cache futuro precisará
  declarar sua janela de obsolescência e mecanismo de invalidação.
- Elevação a `librarian` é uma operação administrativa fora da API pública; não
  existe endpoint de autoelevação.

## Evolução concluída no Módulo 4

```text
rotas modulares
    → listagens com query parameters
    → configuração validada
    → configuração injetável
    → CORS e headers por ambiente
    → contrato OpenAPI auditado
```

O Módulo 5 encerra com carregamento previsível de relacionamentos. O Módulo 6
já possui credencial local, access token curto, sessão renovável rotativa e
autorização atual por papel/propriedade; identidade externa via OpenID Connect
forma o próximo problema.
