# Aula 03 — Crescendo sem um `main.py` monolítico

> **Origem e adaptação:** esta aula reorganiza o conteúdo de
> [Building Modular FastAPI Apps with Routers](../../source/module-04/02.md).
> O domínio Library API, a progressão problema → refatoração, os testes e as
> decisões arquiteturais são complementações didáticas deste curso.

> **Status do piloto:** esta aula valida o formato, mas ainda não deve ser usada
> como etapa 3 da sua implementação manual. As novas aulas 1 e 2 serão produzidas
> primeiro; depois, esta aula será reconstruída sobre o checkpoint 02.

## Onde estamos

A Library API já responde requisições de livros e usuários. Na aula anterior,
substituímos dicionários sem contrato por modelos Pydantic:

```text
JSON recebido
    ↓
BookCreate ou UserCreate
    ↓
endpoint
    ↓
BookResponse ou UserResponse
    ↓
JSON devolvido
```

O comportamento funciona, mas todas as rotas ainda estão declaradas em
`app/main.py`. Livros, usuários, criação da aplicação e configuração inicial
dividem o mesmo arquivo.

## O problema

Observe uma versão reduzida do estado anterior:

```python
from fastapi import FastAPI, HTTPException, status

from app.schemas import BookCreate, BookResponse, UserCreate, UserResponse

app = FastAPI(title="Library API")


@app.get("/books", response_model=list[BookResponse])
async def list_books():
    ...


@app.post("/books", response_model=BookResponse, status_code=201)
async def create_book(payload: BookCreate):
    ...


@app.get("/users", response_model=list[UserResponse])
async def list_users():
    ...


@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(payload: UserCreate):
    ...
```

Quatro rotas ainda parecem administráveis. Mas o domínio precisa de buscas por
ID, atualização, desativação e, mais tarde, empréstimos. O arquivo passa a ter
três responsabilidades diferentes:

```text
main.py
├── cria a aplicação
├── conhece todas as rotas de livros
└── conhece todas as rotas de usuários
```

Para encontrar uma operação de livro, precisamos navegar por código de outros
domínios. Duas pessoas trabalhando em funcionalidades diferentes também
alterariam o mesmo arquivo, aumentando conflitos.

## Por que isso importa

Organização não é apenas estética. Ela afeta:

- a velocidade para localizar uma rota;
- a chance de alterar o domínio errado;
- a clareza da documentação OpenAPI;
- a divisão do trabalho em equipe;
- a possibilidade de aplicar configuração comum a um grupo de endpoints.

Copiar prefixos também abre espaço para inconsistências como `/book`,
`/books` e `/books/` representando a mesma coleção.

## O conceito

`APIRouter` é um agrupador de operações HTTP. Sua interface para declarar uma
rota é parecida com a de `FastAPI`, mas um router não é a aplicação completa.
Ele precisa ser incluído nela.

```python
from fastapi import APIRouter

router = APIRouter(prefix="/books", tags=["Livros"])


@router.get("")
async def list_books():
    return []
```

As partes importantes são:

- `APIRouter`: classe que registra um grupo de operações;
- `router`: instância usada pelos decorators daquele domínio;
- `prefix="/books"`: trecho comum colocado antes do caminho de cada operação;
- `tags=["Livros"]`: agrupamento exibido na documentação;
- `@router.get("")`: registra `GET /books`, pois o caminho vazio é combinado
  com o prefixo.

No ponto de composição:

```python
app.include_router(router)
```

Sem essa linha, o router existe em Python, mas suas operações não fazem parte
da aplicação.

## Modelo mental

Pense em cada router como um conjunto de tomadas preparado por uma equipe. O
`main.py` é o quadro que conecta esses conjuntos à aplicação:

```text
books.router  ──┐
users.router  ──┤
system.router ──┼──> FastAPI ──> servidor HTTP
                  |
             include_router
```

O router organiza e descreve rotas. Ele não cria um novo servidor e não
substitui a instância de `FastAPI`.

## Exemplo mínimo

Este exemplo usa somente um router para isolar o conceito:

```python
from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix="/messages", tags=["Mensagens"])


@router.get("")
async def list_messages() -> list[str]:
    return ["olá"]


app.include_router(router)
```

O caminho final não é vazio. FastAPI combina:

```text
prefix do router    caminho da operação    caminho final
/messages        +  ""                    =  /messages
```

> **Exemplo isolado:** no projeto principal, o router fica em seu próprio
> módulo. Declará-lo ao lado de `app` aqui reduz o código para destacar apenas
> registro e inclusão.

## Entendendo o código

Ao importar um módulo de router, Python executa seus decorators. Cada decorator
adiciona uma descrição de operação ao objeto `router`. Depois,
`app.include_router(router)` copia essas descrições para a aplicação.

Isso acontece na inicialização, não a cada requisição. Durante uma requisição,
FastAPI já conhece o caminho, os tipos, o status e o modelo de resposta.

### Correção técnica sobre pacotes

A fonte chama os arquivos `__init__.py` de cruciais para que diretórios sejam
pacotes. Eles continuam sendo uma escolha explícita e recomendada neste projeto,
mas Python moderno também possui *namespace packages*, que podem funcionar sem
`__init__.py`. Aqui usamos o arquivo para deixar a fronteira do pacote clara e
controlar o que ele exporta, não porque toda importação moderna falharia sem ele.

## Aplicando ao projeto

Criamos um módulo por grupo de rotas:

```text
reference/pilot/module-04/lesson-03/app/
├── __init__.py
├── data.py
├── main.py
├── schemas.py
└── routers/
    ├── __init__.py
    ├── books.py
    ├── system.py
    └── users.py
```

O router de livros concentra prefixo, tag e operações:

```python
from fastapi import APIRouter, HTTPException, status

from app import data
from app.schemas import BookCreate, BookResponse

router = APIRouter(prefix="/books", tags=["Livros"])


@router.get("", response_model=list[BookResponse])
async def list_books() -> list[BookResponse]:
    return list(data.books.values())


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int) -> BookResponse:
    book = data.books.get(book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro não encontrado",
        )
    return book


@router.post("", response_model=BookResponse, status_code=201)
async def create_book(payload: BookCreate) -> BookResponse:
    return data.create_book(payload)
```

O router de usuários segue a mesma regra, com `prefix="/users"`. A rota de
saúde não pertence a livros nem usuários, portanto fica em `system.router`.

Por fim, `main.py` apenas compõe a aplicação:

```python
from fastapi import FastAPI

from app.routers import books, system, users

app = FastAPI(title="Library API", version="0.3.0")

app.include_router(system.router)
app.include_router(books.router)
app.include_router(users.router)
```

Os arquivos executáveis podem ser consultados em
[referência piloto](../../reference/pilot/module-04/lesson-03/app/).

## Antes

```text
app/main.py
├── cria FastAPI
├── GET /health
├── GET/POST /books
├── GET /books/{book_id}
├── GET/POST /users
└── GET /users/{user_id}
```

Uma alteração em qualquer domínio exigia editar o mesmo arquivo.

## Depois

```text
app/main.py
└── cria FastAPI e inclui routers

app/routers/books.py
└── todas as operações /books

app/routers/users.py
└── todas as operações /users

app/routers/system.py
└── GET /health
```

## O que mudou

| Antes | Depois |
|---|---|
| `@app.get("/books")` | `@router.get("")` com prefixo `/books` |
| prefixo repetido | prefixo declarado uma vez |
| tags por operação ou ausentes | tag comum no router |
| todos os domínios em `main.py` | um módulo de router por domínio |
| aplicação conhece cada operação | aplicação conhece cada router |

Os contratos Pydantic, status HTTP e armazenamento em memória não mudaram.
Esta é uma refatoração estrutural: preservamos o comportamento observável.

## Fluxo da requisição

Para `POST /books`:

```text
Cliente
  |
  | JSON
  v
FastAPI
  |
  | encontra books.router pelo prefixo /books
  v
@router.post("")
  |
  | valida BookCreate
  v
armazenamento temporário
  |
  | produz BookResponse
  v
201 Created
```

`APIRouter` participa do registro e da organização. Ele não substitui
Pydantic nem executa a regra de criação do livro.

## Como testar

Na raiz do repositório, prepare o ambiente uma vez:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e './reference/pilot/module-04/lesson-03[dev]'
```

Execute os testes:

```bash
.venv/bin/python -m pytest -q reference/pilot/module-04/lesson-03/tests
```

Inicie a API:

```bash
.venv/bin/python -m uvicorn app.main:app --reload \
  --app-dir reference/pilot/module-04/lesson-03
```

Teste algumas operações:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/books
curl http://127.0.0.1:8000/users/1
```

Abra `http://127.0.0.1:8000/docs`. As operações devem aparecer agrupadas em
**Sistema**, **Livros** e **Usuários**. Essa é uma verificação observável de que
prefixos, inclusão e tags foram aplicados.

## Erros comuns

### Criar o router e esquecer de incluí-lo

Sintoma: o servidor inicia, mas a rota responde `404`.

```python
# faltou app.include_router(books.router)
```

### Repetir o prefixo

```python
router = APIRouter(prefix="/books")

@router.get("/books")  # caminho final: /books/books
async def list_books():
    ...
```

Dentro desse router, use `""` para a coleção e `"/{book_id}"` para o detalhe.

### Importar `app` dentro do router

O router deve exportar `router`; `main.py` importa esse objeto. Fazer o router
importar a instância `app` cria acoplamento e pode produzir importação circular.

### Voltar para `@app.get()` em outra aula

A partir deste checkpoint, endpoints de domínio usam `APIRouter`. Um exemplo
mínimo pode usar `app.get()` somente se declarar que está isolando um conceito.

### Introduzir uma arquitetura inteira junto com o router

Separar rotas não exige criar services, repositories ou interfaces. Essas
abstrações aparecerão quando o projeto revelar problemas que as justifiquem.

## Exercício guiado

Adicione uma operação estática `GET /books/count` ao router de livros.

1. Abra `app/routers/books.py`.
2. Declare a operação antes de `/{book_id}`.
3. Retorne `{"count": len(data.books)}`.
4. Adicione um teste que espere `{"count": 1}` no estado inicial.
5. Confira se `/books/count` aparece sob a tag **Livros**.

Por que antes de `/{book_id}`? Porque `count` é um caminho fixo, enquanto
`{book_id}` é dinâmico. A ordem explícita evita que a leitura do código sugira
uma ambiguidade e facilita entender as rotas mais específicas primeiro.

## Desafio

Sem criar banco, service ou repository, desenhe um `loans.router` com prefixo
`/loans` e apenas uma operação `GET` que retorne uma lista vazia tipada.

Antes de incorporá-lo ao projeto, responda:

- qual tag ele deve usar;
- em que arquivo deve ficar;
- qual linha precisa entrar em `main.py`;
- qual teste prova que o router realmente foi incluído;
- por que ainda não devemos implementar regras de empréstimo sem persistência.

## Checkpoint

Ao terminar esta aula, você deve conseguir explicar:

- a diferença entre `FastAPI` e `APIRouter`;
- como `prefix` e o caminho do decorator formam o caminho final;
- por que `app.include_router()` é necessário;
- como tags organizam o OpenAPI;
- por que mover rotas não deve mudar seus contratos Pydantic;
- por que ainda não criamos services ou repositories;
- qual regra arquitetural passa a valer nas próximas aulas.

## Estado atual do projeto

```text
Library API v0.3
├── app/main.py              composição
├── app/schemas.py           contratos Pydantic
├── app/data.py              estado temporário
└── app/routers/
    ├── books.py             /books
    ├── users.py             /users
    └── system.py            /health
```

Regra permanente a partir daqui:

> Toda nova operação de domínio entra no router do domínio. `main.py` monta a
> aplicação, mas não volta a acumular endpoints.

## Próximo problema

As listagens agora estão organizadas, mas devolvem todos os registros e não
aceitam critérios do cliente. Conforme a biblioteca cresce, `GET /books` precisa
responder perguntas como:

```text
quais livros estão disponíveis?
quais pertencem a determinado autor?
em que ordem devem aparecer?
quantos itens podem vir por resposta?
```

A próxima aula usará query parameters para introduzir filtros, ordenação e
paginação sem abandonar os routers que acabamos de adotar.
