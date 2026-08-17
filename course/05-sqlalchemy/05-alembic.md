# Evoluindo o esquema com Alembic

> **Origem, reorganização e correção:** esta aula adapta *Alembic
> Migrations: Managing Database Schema Changes*. Preservamos revisões,
> `upgrade`, `downgrade`, `autogenerate` e `target_metadata`. Corrigimos a ideia
> de que autogenerate entrega uma migração pronta: ele produz uma candidata
> que precisa de revisão humana. Também retiramos credenciais do `alembic.ini`
> e separamos migração de inicialização da aplicação.

A Library API já persiste o CRUD, mas ainda executa
`Base.metadata.create_all()` ao iniciar. Isso cria tabelas ausentes; não
descreve como um banco existente chegou ao estado atual nem como deve evoluir.

## O problema

!!! problem "Um modelo mudou; os dados precisam continuar"
    Adicionar uma coluna ao modelo Python não altera com segurança uma tabela
    que já possui dados. `create_all()` não transforma a tabela existente e
    tampouco registra quais alterações cada ambiente recebeu. Reiniciar a API
    não pode ser uma estratégia de implantação do esquema.

## Por que isso importa

Desenvolvimento, testes e produção precisam executar a mesma sequência de
mudanças. Sem histórico versionado, um `ALTER TABLE` esquecido transforma a
primeira consulta da API em erro. Com migrações, o deploy possui duas etapas
explícitas:

```text
alembic upgrade head  -> banco alcança a revisão esperada
uvicorn app.main:app  -> aplicação usa o esquema; não o modifica
```

Esse limite reduz privilégios e torna falhas observáveis antes de receber
tráfego. A aplicação ainda descarta a engine no encerramento, mas seu lifespan
não executa DDL.

!!! resource "Documentação oficial"
    Consulte o [tutorial do Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html),
    [autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
    e o [modelo assíncrono](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic).

## O conceito

Uma revisão é um arquivo versionado com duas direções:

```python
revision = "0001_library_schema"
down_revision = None


def upgrade() -> None:
    op.create_table(...)


def downgrade() -> None:
    op.drop_table(...)
```

`revision` identifica o novo estado; `down_revision` aponta para o estado
anterior. Esses ponteiros formam um grafo. `head` é a ponta mais recente e a
tabela `alembic_version` registra a revisão aplicada no banco.

| Comando | Papel |
|---|---|
| `alembic revision --autogenerate -m "mensagem"` | compara metadados e banco para gerar uma candidata |
| `alembic upgrade head` | aplica revisões pendentes |
| `alembic downgrade -1` | reverte uma revisão |
| `alembic current` | mostra a revisão do banco |
| `alembic history` | mostra o histórico do projeto |

Autogenerate reconhece muitas mudanças, mas não compreende intenções como
renomear em vez de remover e recriar. Também não inventa migrações de dados.
Por isso o fluxo correto é **gerar, revisar, testar e só então versionar**.

## Modelo mental

!!! mental-model "Modelos são o mapa; revisões são a rota percorrida"
    `Base.metadata` descreve onde o esquema deve chegar. Os arquivos em
    `alembic/versions/` registram cada passo necessário para chegar lá. O mapa
    não substitui a rota: dois bancos podem ter o mesmo destino desejado, mas
    partir de revisões diferentes.

    ```text
    base --0001_library_schema--> head
      ^                              |
      +----------- downgrade --------+
    ```

Uma convenção de nomes em `Base.metadata` torna constraints identificáveis e
permite referenciá-las em revisões futuras. Constraints importantes do domínio
continuam com nomes explícitos.

## Exemplo mínimo

O exemplo abaixo ilustra uma mudança futura e não representa a revisão inicial
completa do checkpoint:

```python
def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column("published_year", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("books", "published_year")
```

Fazer a coluna nascer anulável pode ser uma etapa deliberada: preencher dados
antigos viria antes de torná-la obrigatória. Uma migração real deve considerar
linhas existentes, tempo de lock e compatibilidade entre versões da API.

## Aplicando ao projeto

O checkpoint adiciona `alembic.ini`, o ambiente assíncrono em `alembic/env.py`
e a revisão `0001_library_schema`.

### Uma configuração para API e migração

O INI não guarda usuário nem senha. `env.py` reutiliza `Settings` e
`build_database_url`, o mesmo contrato validado usado pela aplicação:

```python
def database_url():
    return build_database_url(Settings())


target_metadata = Base.metadata
```

A URL permanece como objeto pelo maior tempo possível. Somente a configuração
da engine assíncrona recebe a string completa; caracteres especiais da senha já
estão escapados pelo SQLAlchemy.

### A ponte entre Alembic síncrono e asyncpg

As operações do Alembic são síncronas, enquanto a conexão é assíncrona. A
ponte é `run_sync` sobre uma conexão da `AsyncEngine`:

```python
async with connectable.connect() as connection:
    await connection.run_sync(do_run_migrations)
```

A engine de migração usa `NullPool` e é descartada ao final. Ela não é a
engine de longa duração da API.

### Uma baseline auditável

A revisão inicial cria `users`, `books` e `loans`, com chaves, checks,
unicidade e o índice parcial que permite somente um empréstimo ativo por livro.
Sua ordem inversa remove primeiro o índice e a tabela dependente `loans`, depois
`books` e `users`.

A baseline foi escrita e comparada com os modelos. Em evoluções futuras,
autogenerate pode iniciar o arquivo, mas o diff precisa responder:

- o `upgrade` preserva dados existentes?
- o `downgrade` realmente desfaz a mudança?
- tipos, defaults, nomes e constraints representam o domínio?
- a operação é compatível com a versão da API durante o deploy?

### Startup sem DDL

O lifespan agora possui somente a fronteira de recurso:

```python
@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await database.engine.dispose()
```

Se a migração não foi aplicada, a API falha ao consultar o banco. Essa falha é
correta: esconder um deploy incompleto criando tabelas silenciosamente seria
mais perigoso.

## Antes e depois

| Antes: M05/A04 | Depois: M05/A05 |
|---|---|
| startup executa `create_all` | startup não executa DDL |
| esquema deriva apenas do estado atual dos modelos | esquema possui histórico de revisões |
| tabela ausente pode ser criada silenciosamente | deploy executa `alembic upgrade head` |
| não existe caminho de reversão | baseline possui `downgrade` testado |
| credenciais pertencem à configuração da API | Alembic reutiliza a mesma configuração validada |

## Como testar

No checkpoint:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Os testes normais validam o grafo, renderizam SQL de upgrade e downgrade sem
abrir conexão, conferem que o INI não possui credenciais e protegem o startup
contra regressões para `create_all`.

Para a prova com PostgreSQL real, use uma instância descartável:

```bash
docker compose up -d --wait
LIBRARY_TEST_POSTGRES=1 pytest -q tests/test_postgres_integration.py
docker compose down -v
```

O teste aplica `upgrade head`, inspeciona as tabelas, executa `downgrade base`,
confirma a remoção, aplica novamente e só então percorre o CRUD HTTP.

Para iniciar a aplicação manualmente:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## Exercícios

<details markdown="1">
<summary>Exercício guiado — leia a baseline</summary>

Percorra `upgrade()` na ordem das tabelas e explique por que `loans` vem por
último. Depois percorra `downgrade()` e justifique a ordem inversa.

</details>

<details markdown="1">
<summary>Teste seu entendimento — autogenerate detectou um rename?</summary>

Imagine que `books.title` virou `books.name`. A candidata remove uma coluna e
cria outra. Que dados seriam perdidos? Reescreva a operação como rename e
explique por que a revisão humana é indispensável.

</details>

<details markdown="1">
<summary>Desafio — adicione ano de publicação</summary>

Adicione `published_year` ao modelo, gere uma candidata, revise o arquivo e
teste upgrade e downgrade. Não altere a baseline: bancos que já a aplicaram
precisam receber uma nova revisão.

</details>

## Checkpoint

Você concluiu a etapa quando consegue:

- explicar a diferença entre estado dos modelos e histórico de migrações;
- localizar `revision`, `down_revision`, `upgrade` e `downgrade`;
- justificar por que autogenerate gera uma candidata;
- aplicar e reverter a baseline em PostgreSQL vazio;
- iniciar a API sem qualquer criação automática de tabelas.

O estado executável está em
`reference/checkpoints/module-05/lesson-05/`.

## Próximo problema

O esquema agora evolui de modo previsível, mas uma regra de empréstimo envolve
várias leituras e escritas que precisam vencer ou falhar juntas. Na M05/A06,
criaremos empréstimos atômicos e tornaremos explícita a fronteira da transação.
