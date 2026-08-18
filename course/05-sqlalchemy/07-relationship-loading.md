# Consultas previsíveis sem N+1

> **Origem, adaptação e correção:** esta aula adapta *Optimizing Relationship
> Loading for N+1 Query Prevention* à Library API. Preservamos lazy loading,
> `selectinload`, `joinedload` e `lazy="raise"`. Em vez de recomendar logs como
> garantia, transformamos o custo em testes. Também explicitamos um risco
> adicional do SQLAlchemy assíncrono: acessar uma relação descarregada pode
> tentar fazer I/O fora de um `await` visível.

`GET /loans` já devolve o histórico, mas somente com `user_id` e `book_id`.
Quem consome a API precisa de nomes e títulos. O formato enriquecido parece
uma mudança pequena; o custo da consulta pode não ser.

## O problema

!!! problem "Um loop inocente multiplica viagens ao banco"
    Buscar N empréstimos e acessar `loan.user` e `loan.book` dentro de um loop
    pode executar uma consulta inicial e até duas consultas extras por item.
    Com 50 empréstimos, o endpoint pode chegar a 101 statements.

```python
loans = (await session.execute(select(Loan))).scalars().all()

for loan in loans:
    print(loan.user.name, loan.book.title)
```

Esse código esconde I/O atrás de acesso a atributos. No fluxo assíncrono, além
do N+1, a tentativa de lazy loading pode falhar porque não existe um `await`
explícito no ponto em que o atributo é lido.

## Por que isso importa

Uma consulta cujo custo cresce com a quantidade de linhas degrada sem mudar o
código. Testes funcionais podem continuar verdes enquanto latência, conexões e
carga no PostgreSQL aumentam.

```text
quantidade de empréstimos:  1    10    50
consulta principal:         1     1     1
usuário + livro lazy:       2    20   100
total:                      3    21   101
```

O problema não é o ORM executar mais de uma consulta. Duas consultas fixas
podem ser a estratégia correta. O problema é o número de consultas depender de
N sem que o contrato de leitura deixe isso visível.

!!! resource "Referências oficiais"
    Consulte [técnicas de carregamento de relações](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)
    e [prevenção de I/O implícito com AsyncSession](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#preventing-implicit-io-when-using-asyncsession).

## O conceito

Uma estratégia de loader define como relações necessárias chegam à memória.
Ela não muda as linhas de domínio que a consulta representa; muda a forma e o
custo de materializá-las.

### `joinedload` para referências escalares

Cada empréstimo aponta para um usuário e um livro. São relações muitos-para-um:
cada item precisa de exatamente uma linha relacionada. `joinedload` inclui as
duas referências com `LEFT OUTER JOIN` na consulta principal:

```python
statement = (
    select(Loan)
    .options(joinedload(Loan.user), joinedload(Loan.book))
    .order_by(Loan.id)
)
```

O orçamento de `GET /loans` passa a ser uma consulta, independentemente da
quantidade de empréstimos retornada.

### `selectinload` para coleções

No detalhe do usuário, `User.loans` é uma coleção. Um JOIN repetiria os dados
do usuário para cada empréstimo e poderia inflar o resultado. `selectinload`
faz duas consultas previsíveis:

1. busca o usuário;
2. busca todos os empréstimos dos usuários selecionados com `IN (...)`.

```python
statement = (
    select(User)
    .where(User.id == user_id)
    .options(selectinload(User.loans).joinedload(Loan.book))
)
```

O loader da coleção é encadeado com `joinedload(Loan.book)`. A segunda consulta
já traz os livros de cada empréstimo; não reaparece uma consulta por item.

### `lazy="raise"` como proteção

As quatro relações do modelo passam a recusar carregamento implícito:

```python
user: Mapped[User] = relationship(back_populates="loans", lazy="raise")
```

Se uma rota esquecer sua estratégia, o acesso levanta `InvalidRequestError`
em vez de surpreender com SQL escondido. O erro aparece durante o
desenvolvimento, perto da consulta que precisa ser corrigida.

## Modelo mental

!!! mental-model "A consulta declara o grafo que a resposta vai percorrer"
    Antes de executar SQL, desenhe os atributos relacionados usados na
    serialização. Cada aresta precisa de uma estratégia explícita.

    ```text
    GET /loans
    Loan ── user (um)  ── joinedload ─┐
         └─ book (um)  ── joinedload ─┴─ 1 statement

    GET /users/{id}
    User ── loans (muitos) ── selectinload ─┐
                    └─ book (um) ─ joinedload┴─ 2 statements
    ```

`joinedload` não significa sempre melhor, e `selectinload` não significa
sempre mais lento. A escolha parte da cardinalidade, do volume e do grafo que
a resposta realmente percorre.

## Exemplo mínimo

Este exemplo isola uma coleção e não representa toda a arquitetura atual:

```python
statement = select(User).options(selectinload(User.loans))
users = (await session.execute(statement)).scalars().all()

for user in users:
    print(len(user.loans))
```

O custo é duas consultas: usuários e empréstimos. A quantidade de usuários não
adiciona novos statements. Se a resposta não usar `loans`, o loader também não
deve ser adicionado por hábito.

## Aplicando ao projeto

O checkpoint enriquece dois contratos existentes.

### Histórico com nomes e títulos

`GET /loans` passa de `LoanResponse` para `LoanDetailResponse`:

```json
{
  "id": 7,
  "user_id": 1,
  "book_id": 2,
  "borrowed_at": "2030-08-01T12:00:00Z",
  "due_at": "2030-08-15T12:00:00Z",
  "returned_at": null,
  "user": {"id": 1, "name": "Ada Lovelace"},
  "book": {
    "id": 2,
    "title": "Kindred",
    "author": "Octavia E. Butler"
  }
}
```

Os identificadores continuam presentes para preservar o fato original. Os
objetos resumidos adicionam os dados de apresentação pedidos pelo consumidor.
As rotas de retirada e devolução mantêm `LoanResponse`: elas não precisam
carregar relações apenas para repetir dados já conhecidos pelo comando.

### Detalhe do usuário com histórico

`GET /users/{user_id}` passa a usar `UserDetailResponse` e inclui `loans`.
Cada item traz o livro relacionado, mas não repete o usuário dentro do próprio
usuário. Schemas diferentes evitam uma estrutura recursiva, e o relacionamento
ordena o histórico por identificador para manter a resposta determinística.

### Sem migração de banco

`lazy="raise"`, `joinedload` e `selectinload` configuram materialização no ORM;
eles não adicionam colunas, tabelas ou índices. Por isso a revisão Alembic
continua `0001_library_schema` e `alembic upgrade head` não recebe uma nova
migração.

### Logs ajudam; testes protegem

O `echo` da engine pode ajudar numa investigação local, mas logs não impõem um
orçamento e podem expor parâmetros. Os testes conectam um contador de eventos
ao SQLAlchemy e afirmam:

- lista enriquecida de empréstimos: exatamente 1 statement;
- usuário com coleção e livros: exatamente 2 statements;
- acesso sem loader: erro, sem statement adicional.

Assim, uma refatoração que reintroduza N+1 falha automaticamente.

## Antes e depois

| Antes: M05/A06 | Depois: M05/A07 |
|---|---|
| empréstimo expõe somente IDs | histórico inclui usuário e livro resumidos |
| detalhe de usuário não inclui histórico | coleção é carregada em consulta separada e fixa |
| relações aceitam lazy loading padrão | relações recusam I/O implícito com `lazy="raise"` |
| custo relacional não está protegido | testes impõem orçamentos de 1 e 2 statements |
| modelo relacional está completo | leitura do grafo também se torna explícita |

## Como testar

No checkpoint:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Os testes em memória executam as consultas ORM reais e contam statements. Eles
não simulam o comportamento central do loader. O teste opcional de PostgreSQL
continua validando migração, concorrência e o contrato HTTP completo:

```bash
docker compose up -d --wait
LIBRARY_TEST_POSTGRES=1 pytest -q tests/test_postgres_integration.py
docker compose down -v
```

## Exercícios

<details markdown="1">
<summary>Exercício guiado — desenhe o grafo da resposta</summary>

Marque todos os acessos relacionais feitos por `to_loan_detail_response` e
relacione cada um ao loader de `build_loan_detail_query`. Remova um loader e
observe qual proteção falha.

</details>

<details markdown="1">
<summary>Teste seu entendimento — uma ou duas consultas?</summary>

Explique por que duas consultas fixas de `selectinload(User.loans)` não são um
N+1. Qual variável deveria permanecer constante quando a quantidade de
usuários aumenta?

</details>

<details markdown="1">
<summary>Desafio — paginação do histórico</summary>

O detalhe de um usuário pode acumular milhares de empréstimos. Proponha um
endpoint paginado para esse histórico. Compare consultar `Loan` diretamente
com carregar toda a coleção `User.loans`; preserve `lazy="raise"` em ambas as
alternativas.

</details>

## Checkpoint

Você concluiu a etapa quando consegue:

- identificar o crescimento 1 + N e distingui-lo de um custo fixo;
- escolher `joinedload` para referências escalares usadas pela resposta;
- escolher `selectinload` para coleções sem inflar a linha principal;
- encadear loaders para um grafo relacionado;
- usar `lazy="raise"` para impedir I/O implícito;
- testar o número real de statements, não apenas o conteúdo da resposta.

O estado executável está em
`reference/checkpoints/module-05/lesson-07/`.

!!! checkpoint "Módulo 5 concluído"
    A Library API agora possui esquema relacional, modelos tipados, sessões
    assíncronas, CRUD persistente, migrações, transações concorrentes e
    carregamento previsível de relações.

## Próximo problema

Persistência e leitura já possuem fronteiras claras, mas qualquer cliente ainda
pode cadastrar usuários e movimentar empréstimos. O próximo módulo deverá
introduzir identidade e autorização a partir desse risco concreto. Autenticação
permanece fora deste checkpoint e será integrada sem reescrever as decisões de
persistência concluídas aqui.
