# Decisões arquiteturais e pedagógicas

## ADR-001 — Markdown como fonte autoral e HTML derivado

**Decisão:** aulas novas são mantidas em Markdown semântico. O HTML contínuo é
um artefato local reproduzível, gerado por `scripts/build_course.py`, e não é
versionado. PDF permanece fora do escopo.

O tema adapta a linguagem visual da fonte — fundo bege, títulos serifados,
cartões e código escuro — para a identidade própria Backend Course / Library
API. Não copia marca, controles ou identidade do proprietário da plataforma.
Cada aula gera um único documento de rolagem vertical, sem divisão em páginas.

## ADR-002 — Fonte original imutável

**Decisão:** respostas do Grasp ficam em `source/` como JSON e como o campo
`content` original em Markdown. O manifesto registra hashes. O importador recusa
sobrescritas.

**Proveniência:** a seleção de versão e a navegação da API foram adaptadas do
exportador existente em `AutomçãoCurso/grasp_export_ajustado.py`. Tradução,
HTML e PDF daquele projeto não foram copiados, e o projeto vizinho não foi
alterado.

## ADR-003 — Idioma do novo curso

**Decisão:** fonte em inglês; curso e documentação autoral em português do
Brasil. Tradução não substitui nem altera a fonte.

## ADR-004 — Library API cumulativa

**Decisão:** `User`, `Book` e posteriormente `Loan` formarão o domínio. O
primeiro piloto usa livros e usuários; empréstimos aguardam persistência.

## ADR-005 — APIRouter como mudança permanente

**Decisão:** a aula 3 foi inicialmente usada para validar a metodologia porque
possui dor concreta, refatoração visível e efeito arquitetural permanente. Seu
checkpoint definitivo parte da aula 2 e preserva os contratos HTTP. Depois
dela, todas as rotas do projeto usam `APIRouter`.

## ADR-006 — Banco adiado para o Módulo 5

**Decisão:** exemplos SQLAlchemy encontrados nas aulas originais 4 e 5 não
serão incorporados ao projeto no Módulo 4. DI e contratos de consulta serão
ensinados sem fingir que já existe uma sessão de banco.

## ADR-007 — Correção da explicação assíncrona

**Problema:** a aula original 1 afirma que `await coro_c()` faz outra task
esperar até `coro_a` terminar, mesmo quando `coro_c` executa
`await asyncio.sleep(...)`.

**Decisão:** corrigir o modelo mental. O `await` mantém a relação sequencial
dentro da task atual, mas um ponto de suspensão permite ao event loop executar
outras tasks prontas. `create_task()` cria concorrência independente; não é
necessário envolver toda coroutine aguardada em uma task.

## ADR-008 — Segurança compatível com o ambiente

**Decisão:** HSTS é habilitado apenas quando a aplicação está em produção e
HTTPS foi declarado ativo. Uma CSP genérica não foi copiada; `/docs` e `/redoc`
são testados sem ela, pois uma política arbitrária pode bloquear recursos das
interfaces.

## ADR-009 — Git e commits são obrigatórios

**Contexto:** o marcador inicial não era um repositório funcional. O usuário
inicializou Git na raiz e o estado anterior à reorganização foi preservado no
commit `chore: initialize progressive backend course`.

**Decisão:** toda aula e toda mudança relevante de arquitetura, contrato,
dependência, ferramenta ou correção técnica recebe commit próprio após testes e
validação. Commits do Codex usam staging por caminhos e nunca incluem
`student/`. O aluno cria pessoalmente seus commits de prática.

## ADR-010 — Dependências resolvidas dos checkpoints

**Decisão:** `pyproject.toml` declara faixas compatíveis; o ambiente aprovado é
registrado nos `requirements.lock` dos checkpoints. O checkpoint 05 foi
executado com Python 3.14.6, FastAPI 0.141.1, Pydantic 2.13.4, Pydantic
Settings 2.14.2, python-dotenv 1.2.3, Uvicorn 0.52.3, HTTPX 0.28.1 e pytest
8.4.2.

Os testes HTTP usam `httpx.AsyncClient` com transporte ASGI. Isso testa as rotas
assíncronas diretamente e evita depender da ponte síncrona de `TestClient`.

## ADR-011 — Prática e soluções ficam separadas

**Decisão:** `student/library-api/` é a área manual e protegida do aluno. O Codex
produz soluções somente em `reference/checkpoints/`, com um snapshot completo e
executável por aula. As aulas mostram mudanças guiadas; arquivos completos ficam
nos checkpoints para consulta posterior. O commit de reorganização pode criar
somente o `README.md` inicial que estabelece essa fronteira; depois dele, o
Codex não inclui `student/` em seus commits.

## ADR-012 — Piloto não é checkpoint sequencial

**Decisão:** a implementação inicial da aula 3 fica preservada em
`reference/pilot/` como registro metodológico. O checkpoint definitivo foi
reconstruído a partir do checkpoint 02, sem promover o piloto diretamente à
sequência cumulativa.

## ADR-013 — Componentes visuais continuam legíveis no Markdown

**Decisão:** problema, conceito, modelo mental, correção, recurso, orientação
e checkpoint usam a sintaxe de admonitions do Python-Markdown. Exercícios podem
usar `<details markdown="1">`. O tema converte esses elementos em componentes
visuais sem inserir CSS particular dentro das aulas.

O manifesto `course/04-fastapi/module.json` é a fonte de verdade para ordem,
metadados, proveniência, checkpoint e estado de cada aula.

## ADR-014 — Retomada não depende da sessão aberta

**Decisão:** Git, o manifesto do módulo, `progress.md` e os checkpoints são o
estado durável do trabalho. `scripts/resume_status.py` deriva dessas fontes um
resumo de retomada e pode reexecutar todas as verificações necessárias antes de
uma pausa. Servidores locais e `dist/` são descartáveis.

## ADR-015 — Contrato de consulta antes do banco

**Decisão:** filtros, ordenação e paginação são implementados primeiro sobre a
coleção em memória. `GET /books` passa a responder `BookPage`; filtros são
aplicados antes da ordenação, `total` é calculado antes do recorte e campos de
ordenação são enumerados explicitamente.

SQLAlchemy e `fastapi-pagination`, presentes na fonte, não entram no Módulo 4.
O contrato será traduzido para consultas persistentes no Módulo 5, quando for
possível avaliar custo, contagem e estratégia de paginação com um banco real.

## ADR-016 — Configurar somente necessidades existentes

**Decisão:** a aula 5 introduz `pydantic-settings` para nome, versão, ambiente,
debug e limites de paginação. Não declara URL de banco, JWT ou origens CORS
antes que esses consumidores existam. `.env` é local e ignorado; o arquivo
versionado é `.env.example`, sem segredos.

Uma instância global e congelada de `Settings` foi aceita temporariamente para
tornar visível o custo de substituição em testes. A aula 6 a trocou por uma
dependência cacheada. O endpoint `/info` nunca deve serializar segredos.

## ADR-017 — DI respeita as fases da aplicação

**Decisão:** `load_settings()` é síncrona e cacheada; `get_settings()` é um
adaptador assíncrono usado por `Depends`. Endpoints podem receber overrides sem
reimportar módulos. Metadados e middleware, necessários durante a construção da
aplicação, chamam o carregador diretamente e não fingem ser request-scoped.

O padrão de setup/teardown com `yield` é ensinado, mas nenhum recurso artificial
é incorporado à Library API. Uma sessão real ocupará essa fronteira somente
quando engine, transações e persistência existirem.

## ADR-018 — Políticas de startup usam uma fábrica de aplicação

**Decisão:** `create_app(settings)` compõe middlewares e routers; `app` continua
sendo a instância pronta para o servidor. CORS e HSTS são políticas decididas
na inicialização, portanto recebem `Settings` diretamente em vez de usar
`Depends`, que pertence ao ciclo de requisição.

O middleware de headers defensivos envolve o middleware CORS para que também
as respostas de preflight recebam esses headers. Origens, métodos e headers
permitidos permanecem explícitos; wildcard é rejeitado com credenciais.

## ADR-019 — OpenAPI é contrato testado, não decoração

**Decisão:** a Aula 8 audita `/openapi.json` diretamente. Operações recebem
`operationId` explícito para preservar nomes consumidos por ferramentas mesmo
quando uma função Python for renomeada. Metadados, tags, exemplos, respostas de
sucesso e erros reais são protegidos por testes.

Informações fictícias de contato ou licença e uma rota artificial marcada como
obsoleta não foram copiadas da fonte. `deprecated=True` será usado somente
quando existir uma substituição e um plano real de migração.

## ADR-020 — Módulo 5 introduz persistência em sete problemas

**Decisão:** as sete aulas originais foram preservadas na cobertura, mas
adaptadas à Library API. A sequência parte do esquema, passa pelos modelos,
conexão, CRUD e migrações, e somente então introduz fronteiras de serviço e
repository no caso de uso atômico de empréstimo. Otimização de relacionamentos
encerra o módulo quando as consultas relacionadas realmente existirem.

O curso usará a API tipada do SQLAlchemy 2 (`DeclarativeBase`, `Mapped`,
`mapped_column`, `async_sessionmaker` e `select`). Senhas com caracteres
especiais não serão interpoladas ingenuamente em URLs. `create_all` não será
tratado como migração, autogenerate sempre exigirá revisão e I/O implícito de
relacionamentos não será assumido seguro com `AsyncSession`.

## ADR-021 — Disponibilidade é derivada do histórico

**Decisão:** o esquema relacional não persiste `books.available`. Um livro está
indisponível quando existe um `loan` com o mesmo `book_id` e `returned_at` nulo.
Um índice único parcial garante no banco que apenas um empréstimo ativo exista
por livro.

O campo `available` permanece no contrato HTTP e será calculado pela consulta.
Isso evita duas fontes de verdade. `Loan` é uma entidade associativa, e não uma
tabela `secondary` simples, porque possui datas e histórico próprios.

## ADR-022 — ORM mapeia o esquema antes de conectar

**Decisão:** M05/A02 adiciona somente modelos e SQLAlchemy 2.0.51. A compilação
do metadata com o dialeto PostgreSQL prova tipos, constraints, chaves e o
índice parcial sem criar engine ou sessão.

Schemas Pydantic permanecem contratos HTTP separados. `Loan` é um association
object completo; não usamos `secondary` porque a associação possui atributos.
Estratégias de carregamento também não são antecipadas nesta aula.

## ADR-023 — Engine pertence à aplicação; sessão pertence à requisição

**Decisão:** M05/A03 cria a engine `postgresql+asyncpg` na fábrica da aplicação
e a guarda em `app.state` junto da `async_sessionmaker`. `get_session` cria uma
`AsyncSession` por execução da dependência e o contexto assíncrono garante seu
fechamento. O lifespan libera o pool no shutdown.

A URL é criada com `URL.create()` a partir de campos validados para que senhas
com caracteres especiais não sejam reinterpretadas. `SecretStr` reduz exposição
acidental, mas não transforma variáveis de ambiente em cofre de segredos.

`GET /health/database` executa `SELECT 1`: consultar `session.is_active` apenas
inspecionaria estado local. `create_all` no startup é aceito como ponte curta e
explicitamente temporária; a aula de Alembic deverá removê-lo. Livros e usuários
ainda usam memória para que a conversão do CRUD permaneça o problema da aula 4.

## ADR-024 — CRUD direto antes de camadas de abstração

**Decisão:** M05/A04 remove `data.py` e injeta `AsyncSession` diretamente nos
routers de livros e usuários. Filtros, `EXISTS`, contagem, ordenação e
paginação permanecem visíveis como statements SQLAlchemy. Repository e service
da fonte não são introduzidos por antecipação; o caso de empréstimo da aula 6
deverá revelar a fronteira transacional e de regras necessária.

`available` é calculado por `NOT EXISTS`, preservando a decisão de uma única
fonte de verdade. Escritas confiam nas constraints para resolver concorrência,
convertem `IntegrityError` esperado em `409` e sempre executam rollback antes de
reutilizar a sessão.

`PUT /books/{id}` é substituição completa de título, autor e ISBN. A atualização
parcial mostrada pela fonte não será chamada de `PUT`; um futuro `PATCH` exigirá
schema e necessidade próprios. `DELETE` responde `204`, enquanto
`passive_deletes=True` deixa `ON DELETE RESTRICT` proteger o histórico.

## ADR-025 — Migrações são uma etapa explícita de deploy

**Decisão:** M05/A05 adiciona o Alembic e a baseline
`0001_library_schema`. O ambiente assíncrono usa o mesmo `Settings`,
`build_database_url` e `Base.metadata` da aplicação; `alembic.ini` não contém
credenciais. Constraints recebem nomes estáveis para futuras alterações.

`Base.metadata.create_all` foi removido do lifespan. O processo da API não
cria nem migra tabelas: `alembic upgrade head` deve ocorrer antes da
inicialização. A separação torna um deploy incompleto visível e permite contas
com privilégios diferentes para DDL e operações da aplicação.

Autogenerate será usado apenas como ponto de partida. Cada revisão deve ser
auditada quanto a preservação de dados, ordem, constraints, compatibilidade e
reversão. A baseline foi provada em PostgreSQL real com o ciclo upgrade,
downgrade, novo upgrade e CRUD HTTP.

## ADR-026 — AsyncSession é a unidade de trabalho do empréstimo

**Decisão:** M05/A06 usa `async with session.begin()` como fronteira do
service de retirada e devolução. Não criamos uma classe Unit of Work que apenas
delegaria para `AsyncSession`. `LoanRepository` concentra as consultas que o
caso composto coordena, mas não expõe commit ou rollback. CRUDs simples
continuam diretos nos routers.

A retirada bloqueia a linha de `books` com `SELECT FOR UPDATE`, consulta o
empréstimo ativo e faz INSERT com `flush`. Isso serializa decisões sobre o
mesmo livro; o índice parcial permanece como garantia independente contra
outros escritores. Uma disputa que alcança a constraint é revertida e vira
`409`.

Disponibilidade continua derivada. Criar um `Loan` ativo a torna falsa;
preencher `returned_at` a torna verdadeira. Não adicionamos um segundo write em
`books`, evitando duas fontes de verdade. A concorrência foi validada em
PostgreSQL real com duas requisições simultâneas: uma confirma e uma conflita.

## ADR-027 — O grafo de leitura e seu custo são explícitos

**Decisão:** M05/A07 configura todas as relações com `lazy="raise"`. Endpoints
que percorrem relações precisam declarar loaders; nenhum acesso a atributo deve
iniciar I/O implicitamente. Isso torna esquecimentos visíveis e evita depender
de lazy loading incompatível com pontos assíncronos sem `await` explícito.

`GET /loans` usa `joinedload` para as referências escalares de usuário e livro,
resultando em um statement. `GET /users/{id}` usa `selectinload` para a coleção
de empréstimos e encadeia `joinedload` para os livros, resultando em dois
statements sem duplicar a linha principal do usuário. `User.loans` ordena por
identificador para que o histórico não dependa da ordem incidental do banco.

O contrato de listagem ganha resumos relacionados, enquanto retirada e
devolução preservam a resposta factual simples e não carregam dados que já
foram informados pelo comando. Testes com eventos do SQLAlchemy impõem os
orçamentos de consulta e comprovam que um acesso não planejado falha sem emitir
um statement adicional. Como loaders não mudam o esquema, nenhuma migração foi
criada.

## ADR-028 — Segurança começa pela credencial e pelo modelo de ameaça

**Contexto:** o Módulo 6 original possui seis aulas sobre JWT, refresh tokens,
RBAC, login social, chaves de API e XSS/CSRF. A primeira implementação presume
que usuários já possuem senha verificável, mas o checkpoint M05/A07 armazena
somente nome, e-mail e estado. A fonte também separa decisões de cookie das
ameaças do navegador e usa OAuth 2.0 como sinônimo de autenticação social.

**Decisão:** a sequência autoral terá seis aulas. A primeira introduzirá
credenciais locais e hash resistente; a segunda, access tokens curtos. Refresh
rotation e XSS/CSRF formarão uma única aula porque o transporte em cookie define
o modelo de ameaça. Depois entram RBAC, OIDC e chaves de API.

O access token terá algoritmo permitido fixo e claims verificadas; o cliente
não escolherá o usuário de um empréstimo autenticado. Refresh tokens terão
digest no banco, rotação atômica, família, revogação e detecção de reutilização;
o valor bruto não será persistido. Cookies serão `HttpOnly`, `Secure` em HTTPS e
terão política `SameSite` acompanhada de defesa CSRF compatível com o fluxo.

Papéis persistidos serão a fonte atual de autorização, evitando tratar uma
claim potencialmente obsoleta como verdade permanente. Login social será
ensinado como OpenID Connect sobre Authorization Code, com `state`, `nonce`,
issuer, audience e assinatura validados; identidades externas serão ligadas por
provedor e `subject`, não somente por e-mail. Chaves de API terão identidade,
digest, escopos e revogação, em vez de uma constante compartilhada.

A fronteira pública de usuários também será revista. O cadastro local migrará
para `/auth/register`; permitir que o cliente escolha `user_id` ao retirar um
livro deixará de fazer sentido assim que a identidade autenticada existir. Toda
quebra de contrato será apresentada e testada na aula que resolver o problema,
sem antecipar RBAC ou outras camadas.

## ADR-029 — Conta legada não recebe uma senha fictícia

**Decisão:** M06/A01 adiciona `users.password_hash VARCHAR(255) NULL` pela
revisão `0002_user_password_hash`. Usuários anteriores continuam íntegros, mas
não autenticam localmente enquanto não houver um fluxo legítimo de definição ou
recuperação. Backfill com segredo comum, valor reversível ou hash conhecido foi
rejeitado.

Novas credenciais usam Argon2id com os parâmetros mínimos registrados
`m=19456`, `t=2`, `p=1` por meio de `pwdlib[argon2]`. A senha original existe
somente no contrato de entrada e é processada em worker thread; o modelo,
resposta e logs não precisam dela. O e-mail é normalizado como identificador,
mas a senha é preservada byte a byte conforme recebida dentro dos limites de 12
a 128 caracteres.

`POST /users` deixa de criar contas sem credencial e é substituído por
`POST /auth/register`. Duplicidade produz conflito genérico. O login desta etapa
responde `204` somente para comprovar a verificação; M06/A02 manterá a rota e
substituirá esse sucesso temporário por access token.

Falhas de autenticação usam uma única resposta para usuário ausente, senha
incorreta, conta inativa, conta legada ou hash inválido. Quando não existe hash
real, verificamos um hash Argon2id fictício para evitar um caminho claramente
mais barato. Isso não substitui rate limit, monitoramento ou defesa contra
credential stuffing, que exigirão uma necessidade operacional própria.

## ADR-030 — O comando autenticado não escolhe seu sujeito

**Decisão:** M06/A02 usa PyJWT e HS256 para access tokens de 15 minutos. A
chave simétrica é configuração privada com tamanho mínimo; o valor didático
tem uso somente local e é recusado em produção. O algoritmo permitido permanece
fixo no código em vez de ser escolhido pelo header ou por variável de ambiente.

O perfil usa header `typ=at+jwt` e exige `iss`, `aud`, `sub`, `iat`, `nbf`,
`exp`, `jti` e `token_type=access`. Emissão e validação usam issuer e audience
configurados, audience estrita e regras mutuamente exclusivas que prepararão a
separação do refresh token. Assinatura válida sem contexto compatível é recusada.

`POST /auth/login` passa de `204` temporário a `200` com `access_token`,
`token_type=bearer` e `expires_in`; nenhum refresh token é emitido antes de
existirem rotação e persistência seguras. Falhas continuam genéricas e recebem
`WWW-Authenticate: Bearer`.

`POST /loans` remove `user_id` do request body e deriva a FK de `sub`. A
dependência valida o token sem iniciar I/O de banco e entrega somente uma
identidade pequena. O service consulta existência e estado do usuário dentro da
transação já existente; sujeito ausente ou inativo vira `401`. Essa ordem evita
que uma consulta da dependência abra implicitamente uma transação na mesma
`AsyncSession` antes de `session.begin()`.

Não foi criada revisão Alembic: tokens são autocontidos e esta etapa não
persiste sessão. Revogação, renovação, cookie e ameaças do navegador ficam para
M06/A03; papéis e `403` permanecem para a aula de RBAC.

## ADR-031 — Refresh é opaco, rotativo e ligado ao navegador

**Decisão:** M06/A03 usa refresh tokens opacos com 32 bytes aleatórios. O valor
bruto existe somente no cookie; `refresh_tokens` armazena SHA-256, família,
usuário, timestamps e encadeamento. O digest rápido não substitui Argon2id para
senhas: ele localiza um segredo uniforme de alta entropia.

A revisão `0003_refresh_token_rotation` cria a tabela, constraints, índices e a
FK autorreferente `replaced_by_id`. Cada login cria uma família com expiração
absoluta de sete dias. Rotações herdam esse limite em vez de prolongar a sessão
indefinidamente.

`POST /auth/refresh` bloqueia o digest com `SELECT FOR UPDATE`. A transação
insere o substituto e executa um primeiro flush; só então marca o anterior como
usado, liga `replaced_by_id` e faz o segundo flush. Isso respeita a FK sem commit
intermediário. Duas apresentações concorrentes resultam em uma rotação e uma
detecção de replay; a segunda revoga toda a família, inclusive o substituto.

O cookie `library_refresh` é host-only, `HttpOnly`, `SameSite=Strict` e limitado
a `Path=/auth`; produção sempre recebe `Secure`. O perfil assume frontend
same-site. Refresh e logout exigem `X-CSRF-Protection: 1`, que torna a chamada
não simples, e recusam `Origin` que não seja a origem-alvo nem pertença à
allowlist. CORS permanece explícito e com credenciais.

`HttpOnly` limita roubo do refresh token por XSS, mas não impede um script já
executado na origem confiável de fazer requisições; o header CSRF também não
resolve XSS. O curso não copia exemplos Flask/Jinja para a API nem inventa uma
CSP genérica. Encoding por contexto, sanitização quando necessária e frontend
sem sinks inseguros continuam responsabilidades explícitas.

`POST /auth/logout` revoga somente a família apresentada, é idempotente e
sempre limpa o cookie. Outras sessões do mesmo usuário não são punidas por um
replay isolado. Access tokens emitidos antes da revogação continuam válidos por
até 15 minutos; revogação instantânea não é prometida.

## ADR-032 — Papéis atuais autorizam; propriedade continua contextual

**Decisão:** M06/A04 cria `roles` e `user_roles` pela revisão
`0004_role_assignments`. O catálogo inicial possui `member` e `librarian`; a
migração atribui `member` às contas anteriores e `/auth/register` inclui a mesma
atribuição para novas contas. Elevação a `librarian` não recebe endpoint público
capaz de produzir autoelevação.

O access JWT permanece uma credencial curta de identidade e não incorpora
papéis. `AuthorizationRepository` consulta conta ativa e atribuições atuais em
cada operação protegida. Assim, remover um papel passa a valer com o mesmo JWT;
assinatura válida não transforma uma claim potencialmente obsoleta em fonte
permanente. A consulta adicional é um custo deliberado nesta etapa; cache só
poderá existir com política explícita de invalidação.

`401` identifica falha da credencial ou da identidade atual e inclui o desafio
Bearer. `403` identifica identidade válida sem permissão e não pede nova
autenticação. Escritas de livros, listagens globais e devoluções exigem
`librarian`; retirada exige `member`. O próprio detalhe de usuário usa
propriedade, enquanto outro perfil exige o papel global. RBAC não é usado para
disfarçar uma relação entre sujeito e objeto.

Dependências declarativas protegem CRUDs que podem consultar e confirmar na
mesma sessão. Retirada e devolução consultam a mesma fonte de autorização dentro
do `session.begin()` já existente, preservando a fronteira atômica e evitando
uma transação implícita anterior.

Durante a validação com Python 3.14.6 e AnyIO 4.14.2, a ponte anterior de worker
não propagou a conclusão do Argon2id no ambiente aprovado. O estado atual isola
hash e verify em `run_password_operation`, com `ThreadPoolExecutor` limitado a
quatro workers e espera assíncrona do `Future`. Parâmetros, formato e modelo de
ameaça da senha não mudaram; teste dedicado comprova execução fora da thread do
event loop.

## ADR-033 — Identidade externa é OIDC e vínculo usa issuer/subject

**Decisão:** M06/A05 implementa OpenID Connect Authorization Code em vez de
tratar um access token OAuth 2.0 como prova genérica de identidade. O issuer é
configuração do operador. Discovery precisa retornar esse mesmo valor e
endpoints HTTPS; o cliente aceita apenas ID Tokens RS256 e seleciona uma chave
RSA de assinatura por `kid` no JWKS.

Cada tentativa gera `state`, `nonce`, browser secret e PKCE verifier. O browser
recebe somente browser secret e verifier em cookie `HttpOnly`, `SameSite=Lax`,
restrito a `/auth/oidc`; authorization request recebe state, nonce e challenge
S256. `oidc_login_attempts` guarda somente digests, validade de dez minutos e
`used_at`. Cookie e state precisam localizar a mesma linha bloqueada, e o
verifier apresentado precisa corresponder ao digest. O consumo ocorre antes do
I/O externo; falha exige uma tentativa nova.

O ID Token exige assinatura, issuer, audience, datas, subject e nonce. Quando
`aud` possui mais de um valor, `azp` deve ser o client ID configurado. Subject é
o identificador durável e forma, com issuer, a unicidade de
`external_identities`.

E-mail verificado serve apenas para criar uma conta quando não existe vínculo.
Uma colisão com conta local produz `409` e nunca auto-link; fundir identidades
exige um fluxo futuro iniciado por uma conta local já autenticada. Contas novas
de OIDC preservam `password_hash=NULL` e recebem `member` na mesma transação.

A revisão `0005_oidc_identities` cria tentativas e vínculos. O callback separa
consumo da tentativa, chamadas ao provedor e resolução do vínculo para não
manter transação PostgreSQL durante rede externa. Depois da autenticação OIDC,
a Library API emite seu access JWT e refresh token opaco locais; tokens do
provedor não são persistidos.
