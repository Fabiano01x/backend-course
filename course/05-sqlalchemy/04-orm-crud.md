# CRUD persistente sem esconder o ORM

> **Origem, reorganização e correção:** esta aula adapta *ORM CRUD
> Operations*. Preservamos `add`, `select`, `commit`, `refresh`, `delete` e o
> primeiro contato direto dos endpoints com a sessão. Atualizamos `.dict()`
> para `model_dump()`, usamos `select` da API SQLAlchemy 2 e corrigimos o
> exemplo da fonte que chama uma atualização parcial de `PUT`. Repository e
> service foram adiados até existir um caso de uso que justifique essas
> fronteiras.

A Library API já abre sessões, mas livros e usuários ainda vivem em
dicionários Python. A conexão só se torna persistência quando as operações HTTP
passam a ler e escrever os modelos ORM.

## O problema

!!! problem "Dois estados contam histórias diferentes"
    O PostgreSQL possui tabelas vazias enquanto os routers respondem com dados
    de `data.py`. Reiniciar o processo apaga cadastros; iniciar dois workers
    cria duas bibliotecas diferentes. A engine existe, mas o domínio não a usa.

Copiar o antigo pipeline para uma lista carregada inteira do banco apenas
mudaria o lugar do problema: filtros, contagem e paginação continuariam
consumindo memória da aplicação.

## Por que isso importa

Persistência altera onde cada responsabilidade é executada:

```text
HTTP valida parâmetros e payloads
SQLAlchemy constrói statements
PostgreSQL filtra, ordena, conta e restringe
AsyncSession delimita o trabalho da requisição
Pydantic serializa a resposta
```

Uma escrita também pode falhar depois da validação HTTP. Duas requisições
podem tentar o mesmo ISBN simultaneamente; somente a constraint do banco decide
qual vence. A API precisa transformar essa falha previsível em `409 Conflict` e
restaurar a sessão com rollback.

!!! resource "Leituras oficiais"
    Consulte [Using SELECT Statements](https://docs.sqlalchemy.org/en/20/tutorial/data_select.html),
    [Using the Session](https://docs.sqlalchemy.org/en/20/orm/session.html) e
    [Asynchronous I/O](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
    na documentação do SQLAlchemy 2.

## O conceito

CRUD descreve quatro intenções, não quatro métodos mágicos:

| Intenção | HTTP no projeto | Operação ORM principal |
|---|---|---|
| Create | `POST /books` | `add` + `commit` + `refresh` |
| Read | `GET /books` e `GET /books/{id}` | `select` + `execute` |
| Update | `PUT /books/{id}` | alterar objeto rastreado + `commit` |
| Delete | `DELETE /books/{id}` | `delete` + `commit` |

`select(Book)` cria uma descrição imutável da consulta. Somente
`await session.execute(statement)` realiza I/O. Quando o statement seleciona
uma entidade e uma expressão calculada, o resultado possui linhas; quando
seleciona somente uma entidade, `result.scalars()` remove o invólucro de linha.

Objetos carregados pela sessão são rastreados. Alterar `book.title` é
suficiente para que o próximo flush gere `UPDATE`; não é necessário chamar
`add()` novamente.

## Modelo mental

!!! mental-model "A sessão é uma bancada de trabalho transacional"
    `add()` coloca uma peça nova na bancada. Consultas trazem objetos
    rastreados para ela. Alterar ou marcar um objeto para remoção prepara
    trabalho; `commit()` confirma o conjunto no banco. Se o banco recusar,
    `rollback()` limpa a transação falha antes de qualquer nova operação.

    ```text
    transient --add--> pending --flush--> persistent --commit--> confirmado
                                   |
                                   +-- falha --> rollback
    persistent --delete--> deleted --commit--> removido
    ```

Uma sessão não é o banco e `add()` não significa INSERT imediato. O flush,
normalmente acionado pelo commit ou por uma consulta, envia as mudanças.

## Exemplo mínimo

Este exemplo isola uma criação e não representa todos os contratos atuais do
projeto:

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Book
from app.schemas import BookCreate


async def create_one(payload: BookCreate, session: AsyncSession) -> Book:
    book = Book(**payload.model_dump())
    session.add(book)
    await session.commit()
    await session.refresh(book)
    return book
```

`refresh()` consulta novamente a linha e obtém valores definidos pelo banco,
como a identidade gerada.

## Aplicando ao projeto

O checkpoint remove `app/data.py`. Livros e usuários agora consomem
`DatabaseSession` diretamente nos routers; ainda não existe uma camada
intermediária.

### Disponibilidade sem uma coluna duplicada

`available` continua no contrato HTTP, mas não existe em `books`. A consulta
calcula o valor pela ausência de empréstimo ativo:

```python
def active_loan_expression() -> ColumnElement[bool]:
    return (
        select(Loan.id)
        .where(Loan.book_id == Book.id, Loan.returned_at.is_(None))
        .exists()
    )


is_available = ~active_loan_expression()
statement = select(Book, is_available.label("available"))
```

O PostgreSQL recebe `NOT EXISTS` para livros disponíveis e `EXISTS` para
indisponíveis. Não carregamos `book.loans` para decidir, evitando I/O implícito
e mantendo uma única fonte de verdade.

### O pipeline da listagem virou SQL

O contrato criado no Módulo 4 permanece:

```text
filtrar → ordenar → contar → recortar
```

Agora ele produz dois statements:

```python
count_statement = select(func.count(Book.id)).where(*filters)

page_statement = (
    select(Book, is_available.label("available"))
    .where(*filters)
    .order_by(*ordering)
    .limit(limit)
    .offset(offset)
)
```

A contagem não recebe `ORDER BY`, `LIMIT` nem `OFFSET`. A página aplica uma
ordenação determinística: `title` e `author` usam `lower(...)` e desempate por
`id` na mesma direção.

A busca parcial usa `ILIKE`. `%`, `_` e `\` enviados pelo cliente são escapados
para continuarem caracteres literais, em vez de virarem curingas SQL.

### Create com conflito e rollback

```python
book = Book(**payload.model_dump())
session.add(book)
try:
    await session.commit()
except IntegrityError as error:
    await session.rollback()
    raise HTTPException(status_code=409, detail="ISBN já cadastrado") from error
await session.refresh(book)
```

Consultar o ISBN antes de inserir não substituiria a constraint: outra
requisição poderia inserir no intervalo entre `SELECT` e `INSERT`. Capturar a
falha do banco preserva a garantia sob concorrência.

O mesmo padrão protege o e-mail único de `POST /users`.

### Read por identidade

Para livros, a resposta precisa da expressão de disponibilidade e usa um
`select(Book, available)`. Para usuários, a chave primária basta:

```python
user = await session.get(User, user_id)
if user is None:
    raise HTTPException(status_code=404, detail="Usuário não encontrado")
```

`session.get()` expressa diretamente uma busca por chave primária e também
pode aproveitar um objeto que já esteja no mapa de identidade da sessão.

### Update: PUT substitui; PATCH alteraria parcialmente

A fonte usa `PUT`, mas chama `dict(exclude_unset=True)`, comportamento de
atualização parcial. O checkpoint torna a semântica explícita:

- `BookUpdate` exige `title`, `author` e `isbn`;
- `PUT /books/{id}` substitui os três campos;
- `available` não entra no payload porque é derivado;
- payload parcial responde `422`.

```python
for field, value in payload.model_dump().items():
    setattr(book, field, value)
await session.commit()
await session.refresh(book)
```

Se uma necessidade real de alteração parcial aparecer, adicionaremos `PATCH`
com contrato próprio em vez de dar dois significados a `PUT`.

### Delete: sucesso vazio e histórico protegido

```python
book = await session.get(Book, book_id)
if book is None:
    raise HTTPException(status_code=404, detail="Livro não encontrado")

await session.delete(book)
await session.commit()
return Response(status_code=204)
```

`204 No Content` retorna corpo vazio. Se houver histórico de empréstimo, a
foreign key `ON DELETE RESTRICT` recusa a remoção e a API responde `409`.
`passive_deletes=True` impede o ORM de tentar anular as chaves antes que o banco
aplique essa regra.

### Por que não criar repository e service agora?

!!! correction "Profissional não significa mais camadas por padrão"
    A fonte afirma que repository é superior para aplicações profissionais e
    facilitaria trocar PostgreSQL por MongoDB. Essa troca alteraria consultas,
    consistência e modelo de dados; uma interface CRUD genérica não apaga essas
    diferenças.

Neste ponto, cada operação possui um consumidor e a regra está legível ao lado
do contrato HTTP. Extrair classes agora esconderia justamente o ORM que estamos
aprendendo. Na aula 6, criar um empréstimo coordenará usuário, livro, histórico
e uma transação; essa pressão concreta definirá a fronteira apropriada.

## Antes e depois

| M05/A03 | M05/A04 |
|---|---|
| `data.py` guarda dicionários | estado de domínio no PostgreSQL |
| sessão usada apenas na saúde | sessão injetada nos routers |
| filtros executados em listas | filtros, ordem e recorte em SQL |
| `available` copiado no objeto | `available` calculado com `NOT EXISTS` |
| somente GET e POST | ciclo de livros com GET, POST, PUT e DELETE |
| IDs gerados por `itertools.count` | identidades geradas pelo banco |
| falhas de unicidade ausentes | conflito `409` + rollback |
| nenhum repository | continua sem abstração prematura |

## Como testar

Consulte [lesson-04](../../reference/checkpoints/module-05/lesson-04/).

Suíte isolada, usada pela validação cotidiana:

```bash
PYTHONPATH=reference/checkpoints/module-05/lesson-04 \
  .venv/bin/python -m pytest -q \
  reference/checkpoints/module-05/lesson-04/tests
```

Ela verifica contratos HTTP, sequência de commit/refresh/rollback, conflitos,
SQL PostgreSQL compilado, `EXISTS`, escaping de `ILIKE`, ordenação e paginação.
O teste marcado como `integration` é ignorado sem opt-in.

Para provar o caminho real em um banco dedicado:

```bash
LIBRARY_DATABASE_PORT=55432 docker compose \
  -p backend-course-m05-l04 \
  -f reference/checkpoints/module-05/lesson-04/compose.yaml \
  up -d --wait

LIBRARY_TEST_POSTGRES=1 \
LIBRARY_TEST_DATABASE_PORT=55432 \
PYTHONPATH=reference/checkpoints/module-05/lesson-04 \
  .venv/bin/python -m pytest -q -m integration \
  reference/checkpoints/module-05/lesson-04/tests

LIBRARY_DATABASE_PORT=55432 docker compose \
  -p backend-course-m05-l04 \
  -f reference/checkpoints/module-05/lesson-04/compose.yaml \
  down -v
```

O projeto e a porta diferentes isolam container, rede e volume do banco de
desenvolvimento comum.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — acompanhe uma criação</summary>

Liste os estados de `Book` antes de `add`, depois de `add`, depois de `commit` e
depois de `refresh`. Em qual etapa a identidade passa a existir?

</details>

<details markdown="1">
<summary>Teste seu entendimento — conte antes de recortar</summary>

Explique por que o statement de contagem recebe os filtros, mas não recebe
ordenação, limite ou offset. Qual valor incorreto apareceria em `total` se a
contagem fosse feita apenas sobre a página?

</details>

<details markdown="1">
<summary>Desafio — conflito de remoção</summary>

No teste de integração, crie diretamente um `Loan` para um livro. Tente remover
o livro e comprove `409`; depois explique o papel combinado de
`passive_deletes` e `ON DELETE RESTRICT`.

</details>

## Checkpoint

!!! checkpoint "M05/A04 concluída"
    Livros e usuários deixaram o estado em memória. A listagem preserva filtros,
    ordenação, contagem e paginação no PostgreSQL; disponibilidade é derivada.
    Livros possuem Create, Read, Update e Delete, com rollback e conflitos HTTP
    explícitos, sem repository ou service prematuros.

Mensagem sugerida:

```text
student(m05-l04): persist library CRUD with SQLAlchemy
```

## Próximo problema

`create_all` consegue criar um banco vazio, mas não consegue explicar como um
schema existente deve evoluir sem perder dados. A próxima aula introduzirá
Alembic, uma revisão inicial auditável e a remoção de `create_all` do startup.
