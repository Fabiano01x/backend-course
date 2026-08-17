# Sessões assíncronas e PostgreSQL

> **Origem, reorganização e correção:** esta aula adapta *FastAPI &
> SQLAlchemy: PostgreSQL Integration*. Preservamos engine assíncrona,
> `AsyncSession`, injeção, PostgreSQL local e lifespan. Atualizamos
> `sessionmaker` para `async_sessionmaker`, construímos a URL sem interpolar
> credenciais e trocamos o teste enganoso de `session.is_active` por `SELECT 1`.

Os modelos agora descrevem as tabelas, mas ainda não podem executar uma
consulta. Nesta aula, a Library API ganha o recurso que conecta o metadata ao
PostgreSQL e entrega uma sessão isolada a cada requisição.

## O problema

!!! problem "Um modelo desconectado ainda não persiste nada"
    `Book`, `User` e `Loan` conhecem colunas e relacionamentos, mas não sabem
    onde o banco está, como obter uma conexão nem quando devolver esse recurso.
    Abrir conexões dentro de cada endpoint repetiria configuração e facilitaria
    vazamentos.

A API também é assíncrona. Usar um driver bloqueante dentro de `async def`
impediria o event loop de atender outras tasks enquanto espera pelo banco.

## Por que isso importa

Uma aplicação web recebe requisições concorrentes. Elas podem compartilhar a
engine e seu pool, mas não devem compartilhar a mesma `AsyncSession`: a sessão
mantém identidade de objetos e estado transacional mutável.

O ciclo desejado é:

```text
processo inicia  → engine e pool ficam disponíveis
requisição A    → sessão A → consulta → fechamento
requisição B    → sessão B → consulta → fechamento
processo encerra → engine libera o pool
```

!!! resource "Leituras oficiais"
    Consulte [Asynchronous I/O](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
    e [Database URLs](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls)
    no SQLAlchemy, além de
    [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) no FastAPI.

## O conceito

Quatro objetos possuem responsabilidades distintas:

| Peça | Responsabilidade | Duração |
|---|---|---|
| `URL` | representar dialeto, credenciais e endereço | configuração |
| `AsyncEngine` | administrar dialeto, conexões e pool | aplicação |
| `async_sessionmaker` | fabricar sessões com a mesma configuração | aplicação |
| `AsyncSession` | executar trabalho ORM e transacional | requisição |

`create_async_engine()` não abre imediatamente uma conexão. A conexão é
obtida quando uma operação realmente precisa acessar o banco.

`async_sessionmaker` também não é uma sessão. É uma fábrica tipada; cada
chamada `sessions()` cria uma nova `AsyncSession`.

## Modelo mental

!!! mental-model "Engine é a infraestrutura; sessão é a unidade de conversa"
    Imagine a engine como a central que administra canais com o PostgreSQL. A
    sessão é uma conversa de uma requisição usando um desses canais quando
    necessário. Encerrar a sessão devolve recursos; encerrar a engine descarta o
    pool do processo.

    ```text
    FastAPI
       |
       +-- request 1 -- AsyncSession 1 --+
       +-- request 2 -- AsyncSession 2 --+--> AsyncEngine --> PostgreSQL
       +-- request 3 -- AsyncSession 3 --+
    ```

Uma `AsyncSession` não deve ser compartilhada entre tasks concorrentes. Uma
requisição recebe a sua instância e o provider a fecha mesmo quando o endpoint
falha.

## Exemplo mínimo

Este exemplo isola a fábrica e não representa toda a composição atual do
projeto:

```python
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

engine = create_async_engine("postgresql+asyncpg://localhost/example")
sessions = async_sessionmaker(engine, expire_on_commit=False)


async def read_something() -> None:
    async with sessions() as session:
        await session.execute(text("SELECT 1"))
```

No projeto, credenciais não ficam em uma string literal e a sessão chega ao
router por `Depends`.

## Aplicando ao projeto

O checkpoint adiciona `asyncpg` como driver PostgreSQL e amplia `Settings` com
host, porta, banco, usuário e senha. `SecretStr` impede que a senha apareça por
acidente na representação do objeto, embora variáveis de ambiente continuem
não sendo um cofre de segredos.

### URL sem ambiguidade

A resposta da fonte para a senha `s3cure_p@ss` interpola o valor diretamente:

```text
postgresql+asyncpg://webapp:s3cure_p@ss@prod-db.../main_app
```

Isso é incorreto: `@` e `/` têm significado estrutural em uma URL textual.
Poderíamos codificá-los, mas é mais seguro nem submeter a senha ao parser:

```python
def build_database_url(settings: Settings) -> URL:
    return URL.create(
        "postgresql+asyncpg",
        username=settings.database_user,
        password=settings.database_password.get_secret_value(),
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database_name,
    )
```

`str(url)` oculta a senha. Para logs, nunca renderize a URL com
`hide_password=False`.

### Engine e fábrica

`app/database.py` concentra a infraestrutura sem recriar a `Base` dos modelos:

```python
@dataclass(frozen=True, slots=True)
class Database:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]


def create_database(url: str | URL, *, echo: bool = False) -> Database:
    engine = create_async_engine(url, echo=echo)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    return Database(engine=engine, sessions=sessions)
```

`expire_on_commit=False` evita que atributos já carregados expirem depois do
commit e tentem realizar I/O implícito quando forem serializados. Isso não
elimina a necessidade de carregar relacionamentos explicitamente, problema que
será tratado na aula 7.

### Uma sessão por requisição

O provider encontra o recurso pertencente à instância da aplicação:

```python
async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.sessions() as session:
        yield session


DatabaseSession = Annotated[AsyncSession, Depends(get_session)]
```

O `yield` separa setup e teardown. O `async with` fecha a sessão ao concluir a
resposta ou propagar um erro. O cache de dependências do FastAPI reutiliza o
resultado do mesmo provider dentro de uma requisição; uma nova requisição
executa o provider novamente.

### Startup, shutdown e uma ponte temporária

`create_app()` recebe opcionalmente um `Database`, permitindo testes sem
alterar módulos globais. O lifespan cria as tabelas no startup e descarta o pool
no shutdown:

```python
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield
    finally:
        await database.engine.dispose()
```

!!! warning "create_all não é uma estratégia de migração"
    Ele cria estruturas ausentes, mas não registra histórico nem descreve com
    segurança como transformar dados existentes. Esta é uma ponte didática
    explícita. A aula 5 instalará Alembic e removerá `create_all` do startup.

### Uma verificação que realmente consulta

O novo `GET /health/database` consome `DatabaseSession`:

```python
async def database_health_check(
    session: DatabaseSession,
) -> DatabaseHealthStatus:
    await session.execute(text("SELECT 1"))
    return DatabaseHealthStatus(status="ok", database="reachable")
```

Consultar `session.is_active`, como sugere a fonte, informa estado transacional
local; não prova que host, credenciais, rede e PostgreSQL funcionam. `SELECT 1`
obriga uma ida real ao banco.

### PostgreSQL local reproduzível

`compose.yaml` usa a imagem oficial PostgreSQL 18.4 e valores locais alinhados
aos defaults de desenvolvimento:

```bash
docker compose \
  -f reference/checkpoints/module-05/lesson-03/compose.yaml \
  up -d --wait
```

O volume nomeado preserva os dados entre reinícios do container. No PostgreSQL
18, a [imagem oficial](https://github.com/docker-library/docs/blob/master/postgres/README.md#pgdata)
moveu o volume para `/var/lib/postgresql`; o checkpoint usa esse novo destino.
A senha `local-library-password` é apenas uma convenção didática local;
ambientes reais devem sobrescrevê-la por um mecanismo de segredos apropriado.

Depois, execute a API:

```bash
.venv/bin/python -m uvicorn app.main:app --reload \
  --app-dir reference/checkpoints/module-05/lesson-03
```

## Antes e depois

| M05/A02 | M05/A03 |
|---|---|
| metadata sem conexão | `AsyncEngine` com driver `asyncpg` |
| nenhuma fábrica de sessão | `async_sessionmaker` tipado |
| settings sem banco | componentes de conexão validados |
| nenhuma dependência de banco | `DatabaseSession` por requisição |
| importação sem I/O | conexão somente quando necessária |
| nenhum processo local de banco | PostgreSQL reproduzível com Compose |
| sem teste operacional do banco | `GET /health/database` executa `SELECT 1` |

Os endpoints de livros e usuários ainda usam a memória. A engine foi
integrada por uma rota operacional; o CRUD só será migrado quando consultas e
commits forem o problema visível da próxima aula.

## Como testar

Consulte [lesson-03](../../reference/checkpoints/module-05/lesson-03/).

```bash
PYTHONPATH=reference/checkpoints/module-05/lesson-03 \
  .venv/bin/python -m pytest -q \
  reference/checkpoints/module-05/lesson-03/tests
```

Os testes verificam que caracteres especiais não quebram a URL, a engine usa
`asyncpg`, cada execução do provider cria e fecha uma sessão, o lifespan chama
`create_all` e `dispose`, e a rota de saúde realmente executa `SELECT 1`.
Substitutos controlados mantêm a suíte rápida e independente de um servidor;
o `compose.yaml` é validado separadamente.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — siga o ciclo da sessão</summary>

Marque onde `get_session` cria, entrega e fecha a `AsyncSession`. Depois,
explique por que o endpoint não deve chamar `session.close()` por conta própria.

</details>

<details markdown="1">
<summary>Teste seu entendimento — senha com caracteres especiais</summary>

Use `s3cure_p@ss/word` como senha em um `Settings` de teste. Confira
`url.password`, `str(url)` e `url.render_as_string(hide_password=False)`. Qual
representação pode ser registrada em logs?

</details>

<details markdown="1">
<summary>Desafio — prove o teardown em uma falha</summary>

Crie um endpoint de teste que recebe `DatabaseSession` e levanta uma exceção.
Use uma fábrica registradora para provar que o contexto ainda foi encerrado.

</details>

## Checkpoint

!!! checkpoint "M05/A03 concluída"
    A Library API possui configuração PostgreSQL validada, URL segura, engine
    e fábrica assíncronas, uma sessão fechada por requisição, lifecycle da
    engine e uma consulta operacional real. `create_all` está identificado como
    ponte temporária.

Mensagem sugerida:

```text
student(m05-l03): connect async sessions to PostgreSQL
```

## Próximo problema

O banco responde, mas livros e usuários ainda são lidos e cadastrados em
dicionários. A próxima aula traduzirá filtros, ordenação, paginação e escrita
para operações ORM, sem esconder o SQLAlchemy atrás de camadas prematuras.
