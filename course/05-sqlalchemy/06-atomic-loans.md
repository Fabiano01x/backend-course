# Empréstimos atômicos e fronteiras de transação

> **Origem, reorganização e correção:** esta aula integra *ORM CRUD
> Operations* e *Atomic Writes with Database Transactions*. Preservamos
> repository, service, ACID, commit, rollback, flush e Unit of Work, mas não
> criamos uma classe genérica por antecipação. A `AsyncSession` já funciona
> como unidade de trabalho; as novas fronteiras aparecem somente no caso de
> uso que coordena regras e concorrência.

A API cadastra livros e usuários, e o esquema já protege o histórico de
empréstimos. Falta transformar essa estrutura em comportamento: retirar um
livro, impedir uma segunda retirada simultânea e registrar sua devolução.

## O problema

!!! problem "Duas requisições enxergam o mesmo livro disponível"
    Uma implementação ingênua consulta a disponibilidade, recebe `true` em
    duas requisições concorrentes e tenta criar dois empréstimos. Separar
    validação e escrita em commits diferentes abre uma janela em que a regra
    deixa de ser verdadeira.

O caso de uso precisa responder, dentro de uma única fronteira:

1. o usuário existe e está ativo?
2. o livro existe?
3. ainda não existe empréstimo ativo para ele?
4. o novo empréstimo satisfaz as constraints?

Se qualquer passo falhar, nenhuma mudança pode permanecer.

## Por que isso importa

Transações protegem a coerência quando um caso de uso envolve mais de uma
decisão de banco. As propriedades ACID ajudam a analisar essa garantia:

| Propriedade | No empréstimo |
|---|---|
| Atomicidade | a operação inteira confirma ou reverte |
| Consistência | FKs, datas e unicidade parcial continuam válidas |
| Isolamento | requisições concorrentes não confirmam dois empréstimos ativos |
| Durabilidade | depois do commit, o histórico sobrevive ao processo da API |

!!! resource "Referências oficiais"
    Consulte [fronteiras de transação da Session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#framing-out-a-begin-commit-rollback-block),
    [AsyncSession](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
    e [locking clauses do PostgreSQL](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE).

Transação não torna uma regra concorrente segura automaticamente. Se as
duas transações apenas fizerem leituras comuns, ambas podem tomar a mesma
decisão. Precisamos combinar fronteira, lock e constraint.

## O conceito

`session.begin()` devolve um context manager transacional:

```python
async with session.begin():
    session.add(loan)
    await session.flush()
```

Saída normal executa commit. Uma exceção executa rollback e é propagada.
Assim, o caminho de erro não depende de lembrar um rollback em cada `if`.

`flush()` envia mudanças pendentes sem encerrar a transação. Ele é útil para
obter a identidade e deixar constraints falharem dentro da fronteira. `commit()`
é diferente: encerra e torna as mudanças permanentes.

```text
BEGIN
  SELECT user
  SELECT book FOR UPDATE
  SELECT active loan
  INSERT loan        <- flush; ainda reversível
COMMIT               <- somente ao sair sem erro
```

### Unit of Work sem uma classe ornamental

A Session rastreia objetos e controla uma transação: ela já cumpre a função
de unidade de trabalho. Criar `SQLAlchemyUnitOfWork` apenas para delegar
`commit()` e `rollback()` repetiria a API existente sem resolver um problema
novo. Uma abstração própria poderá surgir se houver múltiplos recursos ou se
precisarmos substituir a unidade inteira em testes.

## Modelo mental

!!! mental-model "A transação é uma sala com uma única porta de saída"
    O service entra com a Session, coordena todas as decisões e só sai por
    commit ou rollback. O repository movimenta dados dentro da sala, mas não
    decide quando abrir a porta.

    ```text
    router -> service [BEGIN ------------------------- COMMIT]
                         |      |        |       |
                         v      v        v       v
                    user?   lock book  active?  INSERT
                              |
                              +-- outra retirada espera

    qualquer exceção ------------------------------> ROLLBACK
    ```

Responsabilidades ficam nítidas:

- router traduz HTTP e erros de domínio;
- service coordena regra e transação;
- repository constrói consultas e faz `add`/`flush`;
- PostgreSQL arbitra locks e constraints.

## Exemplo mínimo

Este exemplo isola a fronteira e não representa todas as validações do
checkpoint:

```python
async def save_two(session: AsyncSession, first: Model, second: Model) -> None:
    async with session.begin():
        session.add(first)
        session.add(second)
        await session.flush()
```

Não há commit entre as duas inclusões. Se a segunda violar uma constraint, o
context manager reverte também a primeira.

Operações externas, como e-mail ou chamada HTTP, não pertencem a esse bloco.
Elas mantêm locks por mais tempo e não podem ser revertidas pelo PostgreSQL.

## Aplicando ao projeto

O checkpoint adiciona `POST /loans`, `POST /loans/{loan_id}/return` e
`GET /loans`. O schema de criação exige identificadores positivos e uma data
futura com fuso horário.

### Um repository focado

`LoanRepository` existe porque o service agora coordena diversas consultas.
Ele não possui `commit()` nem `rollback()`:

```python
class LoanRepository:
    async def lock_book(self, book_id: int) -> Book | None:
        statement = (
            select(Book)
            .where(Book.id == book_id)
            .with_for_update()
        )
        return (await self.session.execute(statement)).scalar_one_or_none()
```

Os CRUDs simples de livros e usuários continuam diretos nos routers. Uma nova
camada não precisa ser aplicada retroativamente onde não oferece coordenação.

### O service possui a fronteira

O fluxo resumido de retirada é:

```python
async with session.begin():
    user = await repository.find_user(payload.user_id)
    # validar existência e atividade
    book = await repository.lock_book(payload.book_id)
    # validar existência
    active = await repository.find_active_by_book(payload.book_id)
    # recusar indisponibilidade
    loan = repository.add(**payload.model_dump())
    await repository.flush()
```

Erros de regra são exceções do service, não `HTTPException`. O router converte
ausência em `404` e conflito de estado em `409`. Assim o caso de uso não depende
do transporte HTTP.

### Lock e constraint cumprem papéis diferentes

`SELECT ... FOR UPDATE` bloqueia a linha do livro até o fim da transação.
Uma segunda retirada do mesmo livro espera; quando prossegue, consulta o
empréstimo confirmado pela primeira.

O índice parcial `uq_loans_one_active_per_book` continua indispensável. Ele é
a garantia final se outro caminho de escrita esquecer o lock ou se uma disputa
alcançar o INSERT. A violação durante `flush()` reverte o bloco e vira `409`.

```text
regra no service       -> mensagem clara e fluxo esperado
lock no PostgreSQL     -> serializa decisões sobre o mesmo livro
constraint no esquema  -> impossibilita estado inválido em qualquer escritor
```

### Disponibilidade continua derivada

Criar um empréstimo não atualiza `books.available`, pois essa coluna não
existe. O INSERT do empréstimo ativo é o fato que torna a consulta
`NOT EXISTS` falsa. Na devolução, preencher `returned_at` torna o livro
disponível novamente.

Isso é mais forte do que tentar confirmar dois writes redundantes: não existe
um flag capaz de divergir do histórico.

### Devolução idempotente não foi presumida

O endpoint de devolução bloqueia o empréstimo, recusa um identificador ausente
e responde `409` se ele já foi devolvido. Repetir o comando não é tratado como
sucesso silencioso porque o contrato expõe uma transição de estado inválida.

## Antes e depois

| Antes: M05/A05 | Depois: M05/A06 |
|---|---|
| esquema possui tabela `loans` | empréstimos possuem ciclo HTTP |
| routers fazem CRUD simples e commit direto | service coordena o caso composto |
| nenhum repository é necessário | repository de empréstimos concentra consultas relacionadas |
| disponibilidade é apenas consultada | retirada e devolução alteram o fato que a deriva |
| concorrência é protegida pela constraint | lock previne a disputa e constraint permanece como rede final |

## Como testar

No checkpoint:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Os testes isolados verificam:

- um único begin e um único commit transacional no sucesso;
- rollback automático para usuário, livro ou estado inválido;
- `FOR UPDATE` nas consultas que decidem transições;
- falha de unicidade durante flush convertida em `409`;
- datas sem fuso ou no passado recusadas com `422`;
- listagem, retirada e devolução documentadas no OpenAPI.

Para validar concorrência em PostgreSQL real:

```bash
docker compose up -d --wait
LIBRARY_TEST_POSTGRES=1 pytest -q tests/test_postgres_integration.py
docker compose down -v
```

O teste dispara duas retiradas simultâneas do mesmo livro. Exatamente uma
responde `201`; a outra responde `409`. Depois ele confirma indisponibilidade,
devolução, nova disponibilidade e proteção do histórico contra remoção.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — localize a fronteira</summary>

Percorra `borrow_book` e marque o primeiro e o último statement dentro de
`session.begin()`. Explique por que o router e `to_loan_response` ficam fora da
transação.

</details>

<details markdown="1">
<summary>Teste seu entendimento — flush não é commit</summary>

Explique o que acontece se o INSERT for aceito no `flush`, mas uma linha
posterior levantar exceção antes da saída do bloco. O empréstimo permanece?

</details>

<details markdown="1">
<summary>Desafio — limite por usuário</summary>

Implemente uma regra de no máximo três empréstimos ativos por usuário. Discuta
por que apenas `COUNT` seguido de INSERT ainda possui uma disputa e qual lock
ou constraint poderia sustentar a garantia.

</details>

## Checkpoint

Você concluiu a etapa quando consegue:

- diferenciar `flush`, `commit` e `rollback`;
- justificar por que a fronteira pertence ao service, não ao repository;
- explicar por que `AsyncSession` já é uma Unit of Work;
- combinar regra, `FOR UPDATE` e constraint sob concorrência;
- demonstrar que retirada e devolução mudam a disponibilidade derivada;
- manter operações externas fora da transação.

O estado executável está em
`reference/checkpoints/module-05/lesson-06/`.

## Próximo problema

`GET /loans` retorna apenas os identificadores de usuário e livro. Uma resposta
mais útil precisará de nomes e títulos, mas acessar relacionamentos sem uma
estratégia pode gerar uma consulta por item ou I/O implícito incompatível com o
fluxo assíncrono. Na M05/A07, tornaremos o carregamento previsível e testaremos
o custo das consultas.
