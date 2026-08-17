# Contratos de entrada e saída com Pydantic v2

> **Origem e reorganização:** esta aula adapta *Pydantic Data Models for
> Request/Response Validation*. Ela foi antecipada para que os contratos
> existam antes da refatoração com routers. Os nomes do domínio, a validação
> estrita e os testes são complementações autorais.

Na aula 1, `/books` e `/users` devolvem listas de dicionários. Eles parecem
organizados, mas nada impede um campo ausente, um tipo inesperado ou uma chave
interna de escapar na resposta.

## O problema

!!! problem "Dicionários não declaram um acordo"
    Um cliente precisa saber quais campos enviar e receber. Se o endpoint
    trabalha com `dict` cru, esse acordo vive apenas na cabeça de quem escreveu
    o código. Erros aparecem tarde e cada rota pode interpretar os dados de um
    jeito diferente.

Considere esta entrada:

```json
{
  "title": "",
  "author": "Octavia E. Butler",
  "isbn": "curto",
  "available": false,
  "internal_note": "não deveria ser aceito"
}
```

Sem um contrato, teríamos de verificar cada chave manualmente. Ainda seria
fácil esquecer que `available` é controlado pelo servidor e não pelo cliente.

## Por que isso importa

Um contrato de dados centraliza quatro responsabilidades:

- descreve campos e tipos;
- rejeita entradas inválidas antes da lógica do endpoint;
- filtra e verifica a saída;
- alimenta automaticamente o OpenAPI.

O erro de validação padrão do FastAPI usa status `422` e informa a localização
de cada problema. Isso é mais previsível para o frontend que mensagens criadas
de maneira diferente em cada rota.

!!! resource "Leitura — Request Body no FastAPI"
    Leia [Request Body](https://fastapi.tiangolo.com/tutorial/body/) na
    documentação oficial.

    !!! guidance "Orientação"
        Observe como um modelo usado como parâmetro vira corpo da requisição.
        Repare também no schema que aparece automaticamente em `/docs`.

## O conceito

Um schema Pydantic é uma classe que herda de `BaseModel`. Anotações de tipo
definem a forma básica; `Field` adiciona limites declarativos.

```python
from pydantic import BaseModel, Field


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    isbn: str = Field(min_length=10, max_length=17)
```

O modelo de entrada representa o que o cliente controla. O de saída inclui
campos gerados pela aplicação:

```python
class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    available: bool
```

Separar `BookCreate` de `BookResponse` evita pedir `id` e `available` na
criação. A mesma ideia produz `UserCreate` e `UserResponse`.

### Entrada estrita

Por padrão, Pydantic pode ignorar campos extras. Neste curso, entradas HTTP
usarão uma base estrita para revelar erros de digitação:

```python
from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
```

!!! correction "Complementação para Pydantic v2"
    A fonte mistura formas de declarar campos obrigatórios e menciona APIs
    antigas. Em Pydantic v2, um campo anotado sem valor padrão já é obrigatório;
    não precisamos usar `...`. Para serializar usamos `model_dump()`, e
    validadores customizados usam `@field_validator`.

## Modelo mental

!!! mental-model "Duas catracas, dois contratos"
    O schema de entrada é a catraca antes da função: somente dados válidos
    chegam ao endpoint. O `response_model` é a catraca da saída: ele confirma e
    filtra o que será entregue ao cliente.

```text
JSON do cliente
      |
      v
BookCreate ----422----> erro detalhado
      |
      v
função do endpoint
      |
      v
BookResponse ----------> JSON público
```

Pydantic valida dados; ele não salva no banco, não organiza rotas e não contém
automaticamente regras de negócio complexas.

## Exemplo mínimo

```python
from fastapi import FastAPI, status
from pydantic import BaseModel, Field

app = FastAPI()


class MessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=140)


class MessageResponse(BaseModel):
    id: int
    text: str


@app.post(
    "/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(payload: MessageCreate) -> MessageResponse:
    return MessageResponse(id=1, text=payload.text)
```

O FastAPI interpreta `payload` como JSON, constrói `MessageCreate` e só então
chama a função. O status `201 Created` torna explícito que um novo recurso foi
criado.

## Aplicando ao projeto

Crie `app/schemas.py` com quatro contratos. O e-mail usa uma expressão regular
simples para manter este checkpoint sem a dependência opcional `email-validator`:

```python
from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BookCreate(StrictSchema):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    isbn: str = Field(min_length=10, max_length=17)


class BookResponse(StrictSchema):
    id: int
    title: str
    author: str
    isbn: str
    available: bool


class UserCreate(StrictSchema):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )


class UserResponse(StrictSchema):
    id: int
    name: str
    email: str
    active: bool
```

O estado temporário fica em `app/data.py`. Ainda não é uma camada de
persistência: são dicionários reiniciados entre testes.

As rotas continuam diretamente em `main.py`. Isso é intencional: queremos ver
o arquivo crescer antes de justificar `APIRouter`.

```python
@app.post(
    "/books",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_book(payload: BookCreate) -> BookResponse:
    return data.create_book(payload)


@app.get("/books/{book_id}", response_model=BookResponse)
async def get_book(book_id: int) -> BookResponse:
    book = data.books.get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return book
```

O mesmo desenho é aplicado a usuários. Agora a API diferencia:

- `201`: recurso criado;
- `404`: identificador não existe;
- `422`: formato de entrada ou parâmetro inválido.

## Antes e depois

| Aula 1 | Aula 2 |
|---|---|
| Dicionários sem contrato | Schemas Pydantic v2 |
| Somente listagem | Listagem, detalhe e criação |
| Forma da resposta implícita | `response_model` explícito |
| Sem erros de domínio | `404` e `422` testados |
| Um arquivo pequeno | `main.py` começa a concentrar domínios |

Essa última consequência não é um acidente. Ela criará a necessidade da
aula 3 sem antecipar a solução.

## Como testar

Consulte o projeto completo em
[lesson-02](../../reference/checkpoints/module-04/lesson-02/).

```bash
cd reference/checkpoints/module-04/lesson-02
python -m pip install -e '.[dev]'
python -m pytest -q
```

Exemplos manuais:

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"Kindred","author":"Octavia E. Butler","isbn":"9780807083697"}'

curl http://127.0.0.1:8000/books/999
```

Teste pelo menos um sucesso, um `404`, um `422`, os campos da resposta e os
schemas publicados em `/openapi.json`.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — contratos de livro</summary>

Parta da sua aula 1. Digite `StrictSchema`, `BookCreate` e `BookResponse`.
Implemente primeiro somente o `POST /books` e escreva um teste que prove que o
cliente não pode escolher `available`.

</details>

<details markdown="1">
<summary>Teste seu entendimento — entrada e saída</summary>

Por que não reutilizamos `BookResponse` como corpo do POST?

Porque isso obrigaria o cliente a enviar campos que pertencem ao servidor,
como `id` e `available`, misturando responsabilidades distintas.

</details>

<details markdown="1">
<summary>Desafio — valide um usuário</summary>

Implemente os contratos e endpoints de usuário sem olhar o checkpoint. Cubra
nome curto, e-mail inválido e campo extra com testes `422`.

</details>

## Checkpoint

!!! checkpoint "Aula 2 concluída"
    A Library API possui contratos separados de entrada e saída, cria livros e
    usuários, busca por identificador e responde de maneira previsível a dados
    e recursos inválidos.

Mensagem sugerida:

```text
student(m04-l02): add Pydantic contracts
```

## Próximo problema

`main.py` agora conhece saúde, livros, usuários, schemas, status e erros. Os
contratos estão bons, mas localizar uma rota exige navegar por domínios
misturados. Na aula 3 reorganizaremos esse código sem mudar a API observável.
