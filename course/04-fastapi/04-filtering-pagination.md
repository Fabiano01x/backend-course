# Filtros, ordenação e paginação

> **Origem e reorganização:** esta aula adapta *Advanced RESTful API Design*.
> A fonte demonstra consultas SQLAlchemy e a biblioteca `fastapi-pagination`;
> aqui isolamos primeiro o contrato HTTP e executamos o mesmo pipeline sobre a
> coleção em memória. SQLAlchemy permanece adiado para o Módulo 5.

Na aula 3, cada domínio ganhou seu próprio router. `GET /books` está no lugar
certo, mas ainda devolve toda a coleção de uma só vez:

```text
GET /books
    |
    v
todos os livros, sempre na mesma resposta
```

Isso funciona enquanto a biblioteca tem poucos registros. O contrato começa a
falhar quando o cliente quer somente livros disponíveis, procura um autor ou
precisa carregar a coleção em partes.

## O problema

!!! problem "Uma listagem sem limites transfere a decisão errada"
    Sem parâmetros de consulta, o servidor envia dados que o cliente talvez
    descarte. Sem paginação, o tamanho da resposta cresce junto com a coleção.
    E sem uma ordenação declarada, `offset` não define uma janela previsível.

Imagine mil livros e uma tela que mostra vinte. Baixar tudo para filtrar no
frontend desperdiça memória, rede e tempo. Também torna impossível responder de
forma consistente a perguntas como:

```text
quais livros estão disponíveis?
quais autores contêm "martin" no nome?
quais são os próximos vinte títulos em ordem alfabética?
```

O caminho continua sendo `/books`; o que muda é a consulta feita sobre essa
coleção.

## Por que isso importa

Query parameters permitem variar uma leitura sem inventar um endpoint para
cada combinação:

```text
GET /books?available=true
GET /books?author=martin
GET /books?sort_by=title&order=desc
GET /books?limit=20&offset=40
```

Esses parâmetros fazem parte do contrato HTTP. Portanto, precisam ter nomes,
tipos, valores permitidos, limites e significado documentados.

!!! resource "Leitura — validação de query parameters"
    Leia [Query Parameters and String Validations](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/)
    na documentação oficial do FastAPI.

    !!! guidance "Orientação"
        Observe como `Query` acrescenta restrições e descrições ao OpenAPI. Não
        avance ainda para dependências reutilizáveis: neste checkpoint, os
        parâmetros pertencem somente à listagem de livros.

## O conceito

### Query parameters

Tudo que aparece depois de `?` compõe a consulta. Pares são separados por `&`:

```text
/books?available=true&limit=10&offset=20
        └──────┬──────┘ └───┬──┘ └───┬───┘
             filtro       tamanho   início
```

FastAPI converte os textos da URL conforme as anotações da função. `bool`,
`int` e `Literal` deixam de ser convenções informais e passam a ser entradas
validadas antes do endpoint.

### Filtros opcionais

Um filtro opcional só participa quando foi enviado. Isso é especialmente
importante para booleanos:

```python
if available is not None:
    books = [book for book in books if book.available is available]
```

Testar apenas `if available` confundiria `false` com ausência. `None` significa
“o cliente não escolheu esse filtro”; `False` significa “quero os
indisponíveis”.

### Ordenação com valores permitidos

O cliente escolhe apenas campos públicos previamente autorizados:

```python
BookSortField = Literal["id", "title", "author"]
SortOrder = Literal["asc", "desc"]
```

Um dicionário associa cada nome público à chave de ordenação. Não usamos
`getattr` com texto livre recebido na URL:

```python
sort_keys = {
    "id": lambda book: (book.id,),
    "title": lambda book: (book.title.casefold(), book.id),
    "author": lambda book: (book.author.casefold(), book.id),
}
books.sort(key=sort_keys[sort_by], reverse=order == "desc")
```

Além de rejeitar erros de digitação com `422`, a lista permitida evita expor
campos internos por acidente quando o modelo crescer. O `id` como segunda chave
desempata títulos ou autores iguais e produz uma ordem total determinística.

### Paginação limit-offset

`limit` é a quantidade máxima devolvida. `offset` é quantos elementos já
ordenados devem ser ignorados:

```python
page_items = books[offset : offset + limit]
```

O cliente também precisa de `total`, calculado depois dos filtros e antes do
recorte. Sem ele, não sabe se existe uma próxima página.

```json
{
  "items": [],
  "total": 37,
  "limit": 20,
  "offset": 20
}
```

## Modelo mental

!!! mental-model "Um funil antes da janela"
    A coleção atravessa um pipeline em ordem definida. Filtros reduzem os
    candidatos; a ordenação estabiliza a sequência; a contagem registra quantos
    candidatos existem; só então `offset` e `limit` abrem uma janela.

    ```text
    coleção
       |
       v
    filtrar ──> ordenar ──> contar total ──> recortar ──> BookPage
    ```

Trocar essa ordem muda o significado. Paginar antes de filtrar poderia devolver
uma página vazia mesmo quando existem correspondências mais adiante. Contar
depois de recortar faria `total` representar apenas o tamanho da página.

!!! correction "Limite do offset"
    Paginação por offset é simples e adequada para aprender o contrato, mas uma
    coleção que muda entre duas requisições pode deslocar itens entre páginas.
    Paginação por cursor será discutida quando houver persistência e uma ordem
    estável no banco. Este checkpoint não promete um snapshot transacional.

## Exemplo mínimo

Este exemplo isola validação numérica. Ele não representa a arquitetura atual
do projeto, que continua usando routers:

```python
from typing import Annotated

from fastapi import FastAPI, Query

app = FastAPI()
numbers = list(range(100))


@app.get("/numbers")
async def list_numbers(
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, int | list[int]]:
    return {
        "items": numbers[offset : offset + limit],
        "total": len(numbers),
        "limit": limit,
        "offset": offset,
    }
```

`limit=0`, `limit=51` e `offset=-1` recebem `422` sem que a função seja
executada.

## Aplicando ao projeto

Primeiro, declaramos em `app/schemas.py` o envelope público da listagem:

```python
class BookPage(StrictSchema):
    items: list[BookResponse]
    total: int
    limit: int
    offset: int
```

Esse schema torna explícita uma mudança de contrato: `GET /books` deixa de
responder com um array solto e passa a responder com metadados de paginação.
As operações de detalhe e criação continuam usando `BookResponse`.

No `books.router`, `Query` descreve e restringe os parâmetros:

```python
@router.get("", response_model=BookPage)
async def list_books(
    available: Annotated[
        bool | None,
        Query(description="Filtra pela disponibilidade do livro."),
    ] = None,
    author: Annotated[
        str | None,
        Query(min_length=1, max_length=120, description="Busca parcial por autor."),
    ] = None,
    sort_by: Annotated[BookSortField, Query()] = "id",
    order: Annotated[SortOrder, Query()] = "asc",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BookPage:
    ...
```

O corpo aplica o pipeline sem criar uma camada prematura:

```python
filtered_books = list(data.books.values())

if available is not None:
    filtered_books = [
        book for book in filtered_books if book.available is available
    ]

if author is not None:
    normalized_author = author.casefold()
    filtered_books = [
        book
        for book in filtered_books
        if normalized_author in book.author.casefold()
    ]

filtered_books.sort(key=sort_keys[sort_by], reverse=order == "desc")

return BookPage(
    items=filtered_books[offset : offset + limit],
    total=len(filtered_books),
    limit=limit,
    offset=offset,
)
```

O estado inicial agora possui quatro livros para tornar combinações de filtro e
ordenação observáveis. `data.py` continua sendo armazenamento temporário, não
um repository.

!!! correction "O que foi adiado da fonte"
    A fonte constrói consultas SQLAlchemy e recomenda `fastapi-pagination`.
    Copiar esse código agora exigiria inventar sessão, modelo ORM e banco antes
    da necessidade prevista no curso. No Módulo 5, o mesmo pipeline será
    traduzido para `where`, `order_by`, `offset` e `limit`; a escolha de uma
    biblioteca será reavaliada com o banco real.

## Antes e depois

| Aula 3 | Aula 4 |
|---|---|
| `GET /books` devolve array completo | devolve `BookPage` |
| nenhuma seleção do cliente | filtros `available` e `author` |
| ordem implícita da coleção | `sort_by` e `order` enumerados |
| resposta sem limite | `limit` entre 1 e 100 |
| sem posição inicial | `offset` maior ou igual a zero |
| OpenAPI descreve somente o caminho | OpenAPI descreve a consulta completa |

Os routers, contratos de criação, respostas `201`, `404` e `422` e a área do
aluno permanecem como estavam.

## Como testar

Consulte o projeto completo em
[lesson-04](../../reference/checkpoints/module-04/lesson-04/).

```bash
cd reference/checkpoints/module-04/lesson-04
python -m pip install -e '.[dev]'
python -m pytest -q
```

Na raiz do repositório, inicie a API:

```bash
.venv/bin/python -m uvicorn app.main:app --reload \
  --app-dir reference/checkpoints/module-04/lesson-04
```

Experimente o pipeline completo:

```bash
curl 'http://127.0.0.1:8000/books?available=true&sort_by=title&order=desc&limit=2&offset=1'
curl 'http://127.0.0.1:8000/books?author=martin'
curl 'http://127.0.0.1:8000/books?sort_by=isbn'
```

O último exemplo deve responder `422`, porque `isbn` não pertence à enumeração
pública de ordenação.

Os testes precisam provar:

- valores padrão e metadados da página;
- filtro booleano distinguindo `false` de ausência;
- busca parcial de autor sem diferença entre maiúsculas e minúsculas;
- filtro antes da contagem e da paginação;
- ordenação ascendente e descendente;
- limites inválidos e opções desconhecidas respondendo `422`;
- query parameters e `BookPage` publicados no OpenAPI;
- contratos anteriores de criação, detalhe e usuários preservados.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — apenas indisponíveis</summary>

Escreva primeiro um teste para `GET /books?available=false`. Depois implemente o
filtro usando `available is not None`. Confirme que a resposta contém o livro
indisponível e que `total` vale `1`.

</details>

<details markdown="1">
<summary>Teste seu entendimento — ordem do pipeline</summary>

Por que `total` é calculado depois dos filtros, mas antes de `limit` e `offset`?

Porque ele representa todas as correspondências da consulta, não toda a base e
nem somente os itens visíveis na página atual.

</details>

<details markdown="1">
<summary>Desafio — busca por título</summary>

Adicione um parâmetro opcional `title` com busca parcial sem diferença entre
maiúsculas e minúsculas. Restrinja seu tamanho com `Query`, atualize o OpenAPI e
cubra a combinação `title` + `available` em um teste. Não crie um service para
isso: o checkpoint ainda possui uma única consulta simples.

</details>

## Checkpoint

!!! checkpoint "Aula 4 concluída"
    `GET /books` possui um contrato paginado e validado. O cliente pode filtrar,
    ordenar e escolher uma janela; o servidor responde com os itens e o total
    da consulta sem abandonar `APIRouter` nem antecipar o banco de dados.

Mensagem sugerida:

```text
student(m04-l04): add book filtering sorting and pagination
```

## Próximo problema

A API agora possui valores fixos espalhados pelo código: título, versão e
limites padrão pertencem ao ambiente atual, mas alguns deles precisarão variar
entre desenvolvimento, testes e produção. Na aula 5, vamos externalizar
configurações e validá-las sem usar variáveis globais soltas.
