# Modelos e relações com SQLAlchemy 2

> **Origem e complementação:** esta aula adapta *SQLAlchemy Models &
> Relationships* para a sintaxe tipada atual. A relação muitos-para-muitos
> genérica da fonte é aplicada como a entidade associativa `Loan`, pois um
> empréstimo possui datas e identidade próprias.

`schema.sql` descreve o banco desejado, mas a aplicação ainda não conhece essas
tabelas. Precisamos representar o mesmo desenho em Python antes de abrir uma
conexão.

## O problema

!!! problem "O blueprint e o código falam linguagens diferentes"
    FastAPI manipula objetos Python e schemas Pydantic. PostgreSQL manipula
    tabelas, chaves e constraints. Copiar dados manualmente entre esses mundos
    espalharia SQL textual e conversões por toda a aplicação.

Um ORM resolve o mapeamento, mas não deve redesenhar o domínio. Se os modelos
omitirem uma constraint ou reduzirem `Loan` a uma lista mágica, o código deixa
de corresponder ao esquema aprovado.

## Por que isso importa

O metadata do SQLAlchemy será usado depois para criar consultas e comparar
mudanças com Alembic. Um erro aqui se propaga para migrações e produção.

Os modelos também oferecem tipos ao editor:

```text
Mapped[int]             atributo obrigatório
Mapped[datetime | None] atributo anulável
Mapped[list[Loan]]      coleção relacionada
```

!!! resource "Leitura — mapeamento declarativo"
    Consulte [Table Configuration with Declarative](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html)
    e [Relationship Configuration](https://docs.sqlalchemy.org/en/20/orm/relationships.html)
    na documentação oficial do SQLAlchemy 2.

## O conceito

O mapeamento declarativo associa uma classe a uma `Table`:

- `DeclarativeBase` mantém o registro e o `MetaData` comum;
- `__tablename__` escolhe a tabela;
- `Mapped[T]` descreve o tipo Python do atributo;
- `mapped_column()` configura tipo e regras da coluna;
- `relationship()` liga objetos, mas não cria uma coluna;
- `ForeignKey` cria integridade referencial no schema.

Pydantic e SQLAlchemy não são substitutos:

| Pydantic | SQLAlchemy ORM |
|---|---|
| valida entrada e saída HTTP | mapeia estado persistente |
| `BookCreate` e `BookResponse` | `Book` |
| recusa payload inválido | expressa colunas e relações |
| vive na fronteira da API | vive na fronteira do banco |

## Modelo mental

!!! mental-model "Classe é o mapa; objeto é uma possível linha"
    Declarar `Book` não consulta nem cria uma tabela. A classe registra como
    atributos correspondem a colunas. Engine e sessão, ainda ausentes, usarão
    esse mapa nas aulas seguintes.

    ```text
    classe User ──> metadata.tables["users"] ──> futuro PostgreSQL
       ^                                              |
       └──────────── objeto carregado ───────────────┘
    ```

## Exemplo mínimo

Este exemplo isola uma tabela e não representa todo o estado do projeto:

```python
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
```

Nenhuma conexão é aberta ao importar esse arquivo.

## Aplicando ao projeto

O checkpoint adiciona `app/models.py`. Todos os modelos compartilham a base:

```python
class Base(DeclarativeBase):
    pass
```

`User` preserva nomes e constraints do blueprint:

```python
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("btrim(name) <> ''", name="ck_users_name_not_blank"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )
    loans: Mapped[list["Loan"]] = relationship(back_populates="user")
```

`Book` possui `title`, `author`, `isbn` e `loans`. Ele deliberadamente não
possui coluna `available`, mantendo a decisão da aula anterior.

`Loan` mapeia as duas chaves estrangeiras e os lados orientados a objetos:

```python
class Loan(Base):
    __tablename__ = "loans"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_loans_user", ondelete="RESTRICT")
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", name="fk_loans_book", ondelete="RESTRICT")
    )
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="loans")
    book: Mapped[Book] = relationship(back_populates="loans")
```

`ForeignKey` e `relationship` possuem papéis diferentes. A primeira existe no
banco; a segunda permite navegar `loan.user`, `user.loans`, `loan.book` e
`book.loans` em Python.

!!! correction "Uma tabela secondary simples perderia o empréstimo"
    `secondary=` serve bem quando a associação contém somente duas chaves. Como
    precisamos de `borrowed_at`, `due_at` e `returned_at`, `Loan` é uma classe
    mapeada completa: o padrão association object.

O índice parcial usa uma opção específica do dialeto PostgreSQL:

```python
Index(
    "uq_loans_one_active_per_book",
    "book_id",
    unique=True,
    postgresql_where=text("returned_at IS NULL"),
)
```

Não introduzimos engine, sessão, repository ou rota de empréstimo. Os modelos
podem ser inspecionados e compilados sem I/O, exatamente o limite desta aula.

## Antes e depois

| M05/A01 | M05/A02 |
|---|---|
| DDL PostgreSQL | classes mapeadas tipadas |
| relações no diagrama | `ForeignKey` + `relationship` |
| `Loan` como entidade conceitual | association object executável |
| constraints em SQL | constraints no metadata |
| sem dependência de ORM | SQLAlchemy 2.0.51 resolvido |
| nenhum acesso ao banco | ainda nenhum acesso ao banco |

## Como testar

Consulte [lesson-02](../../reference/checkpoints/module-05/lesson-02/).

```bash
PYTHONPATH=reference/checkpoints/module-05/lesson-02 \
  .venv/bin/python -m pytest -q \
  reference/checkpoints/module-05/lesson-02/tests
```

Os testes inspecionam `Base.metadata`, compilam tabelas e índice com o dialeto
PostgreSQL e provam que os relacionamentos bidirecionais sincronizam objetos.
Nenhum servidor de banco é necessário.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — coluna ou relationship?</summary>

Liste os atributos de `Loan`. `user_id` e `book_id` são colunas; `user` e `book`
são relacionamentos ORM. Explique qual par aparece fisicamente na tabela.

</details>

<details markdown="1">
<summary>Teste seu entendimento — nulabilidade tipada</summary>

Por que `returned_at` usa `Mapped[datetime | None]`, mas `due_at` usa
`Mapped[datetime]`? Um empréstimo ativo ainda não foi devolvido; todo empréstimo
deve possuir vencimento.

</details>

<details markdown="1">
<summary>Desafio — detecte deriva</summary>

Altere temporariamente o tamanho de `Book.isbn` para 20 e execute os testes.
Identifique qual afirmação falha e relacione-a ao limite de `schema.sql`.

</details>

## Checkpoint

!!! checkpoint "M05/A02 concluída"
    `User`, `Book` e `Loan` traduzem o esquema relacional para SQLAlchemy 2 com
    tipos, constraints e relacionamentos bidirecionais. A API anterior continua
    funcional e nenhum recurso de banco foi criado antes da necessidade.

Mensagem sugerida:

```text
student(m05-l02): map relational models with SQLAlchemy
```

## Próximo problema

Os modelos agora descrevem tabelas, mas continuam desconectados. A próxima aula
configurará uma engine assíncrona, uma fábrica de sessões e exatamente uma
sessão por requisição, usando PostgreSQL sem expor credenciais no código.
