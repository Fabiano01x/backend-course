# Primeira Library API e programação assíncrona

> **Origem e adaptação:** esta aula reorganiza *Asynchronous Python:
> Coroutines and Async/Await*. A Library API, o FastAPI mínimo, os testes e a
> correção sobre tasks são complementações autorais deste curso.

Nesta primeira etapa você criará uma API pequena, executável e deliberadamente
incompleta. Ela ainda não aceita cadastros: primeiro precisamos entender como
uma requisição chega a uma função assíncrona.

## O problema

!!! problem "Uma API passa boa parte do tempo esperando"
    Servidores consultam bancos, chamam outros serviços e leem dados pela rede.
    Se o processo ficar parado a cada espera, outras requisições prontas também
    demoram. Precisamos permitir que o servidor aproveite esses intervalos.

Um programa síncrono executa uma instrução por vez. Uma operação bloqueante,
como `time.sleep()`, segura a thread até terminar. Para uma API, isso pode
significar manter várias requisições esperando sem necessidade.

## Por que isso importa

Programação assíncrona é especialmente útil para trabalho **I/O-bound**:
situações em que o tempo é dominado por rede, disco ou banco de dados. Ela não
torna cálculos pesados mais rápidos e não significa, por si só, executar em
vários núcleos.

| Situação | Gargalo principal | Async costuma ajudar? |
|---|---|---|
| Esperar uma resposta HTTP | Rede | Sim |
| Consultar um banco remoto | Rede/disco | Sim |
| Calcular milhões de hashes | CPU | Não; avalie processos |
| Usar `time.sleep()` dentro de `async def` | Thread bloqueada | Não; é um erro |

!!! resource "Leitura — asyncio na documentação do Python"
    Consulte [Coroutines and Tasks](https://docs.python.org/3/library/asyncio-task.html)
    para rever a terminologia oficial.

    !!! guidance "Orientação"
        Concentre-se nas definições de coroutine, task e `await`. Não tente
        memorizar toda a API de `asyncio` agora.

## O conceito

Uma função declarada com `async def` é uma **função coroutine**. Chamá-la não
executa imediatamente o corpo; a chamada cria um **objeto coroutine**.

```python
async def greet() -> str:
    return "olá"


coroutine = greet()  # o corpo ainda não executou
```

Esse objeto precisa ser aguardado por outra coroutine ou entregue a um event
loop. `asyncio.run()` cria o loop para um programa Python independente:

```python
import asyncio


async def main() -> None:
    message = await greet()
    print(message)


asyncio.run(main())
```

Dentro de uma coroutine, `await` preserva a ordem daquela tarefa: a linha
seguinte só executa depois do resultado. Quando a operação aguardada precisa
esperar, ela pode suspender cooperativamente a task atual e devolver controle
ao event loop.

!!! correction "Correção técnica da fonte"
    A fonte afirma que aguardar diretamente uma coroutine impede outras tasks
    de executar até ela terminar. Isso está incorreto. Se a coroutine aguardada
    alcançar um ponto de suspensão real, como `await asyncio.sleep()`, o event
    loop pode executar outras tasks prontas. `create_task()` é necessário para
    agendar trabalho independente, não para tornar todo `await` cooperativo.

## Modelo mental

!!! mental-model "Uma fila cooperativa"
    Imagine uma pessoa atendendo vários pedidos. Enquanto um pedido depende de
    uma resposta externa, ele é colocado de lado e outro pedido pronto avança.
    O event loop coordena a fila; as tasks são as unidades agendadas; `await`
    marca os pontos em que uma task pode precisar ceder a vez.

```text
Task A executa ──> await I/O ──┐
                              ├─> event loop executa Task B
I/O fica pronto <─────────────┘
Task A retoma
```

Uma coroutine e uma task não são sinônimos:

- **coroutine:** descreve o trabalho suspensível;
- **task:** agenda uma coroutine para que o loop a execute independentemente;
- **await:** espera um resultado sem perder a ordem da task atual.

## Exemplo mínimo

O exemplo a seguir comprova a correção. `sibling` é agendada, enquanto
`parent` aguarda `child` diretamente. Mesmo assim, `sibling` executa durante o
`sleep` de `child`.

```python
import asyncio


async def child() -> None:
    print("child: antes da espera")
    await asyncio.sleep(0.1)
    print("child: depois da espera")


async def sibling() -> None:
    print("sibling: executou")


async def parent() -> None:
    sibling_task = asyncio.create_task(sibling())
    await child()
    await sibling_task


asyncio.run(parent())
```

Saída esperada:

```text
child: antes da espera
sibling: executou
child: depois da espera
```

`create_task()` separa `sibling` como trabalho independente. O `await child()`
continua sequencial dentro de `parent`, mas a suspensão de `child` libera o
loop.

## Aplicando ao projeto

Comece com um único arquivo. Neste momento, um `main.py` pequeno é mais fácil
de entender que uma arquitetura dividida prematuramente.

```python
from fastapi import FastAPI

app = FastAPI(title="Library API", version="0.1.0")

books = [
    {
        "id": 1,
        "title": "Clean Architecture",
        "author": "Robert C. Martin",
        "available": True,
    }
]

users = [
    {"id": 1, "name": "Ada Lovelace", "active": True}
]


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/books")
async def list_books() -> list[dict[str, object]]:
    return books


@app.get("/users")
async def list_users() -> list[dict[str, object]]:
    return users
```

Quando uma requisição encontra `/books`, o FastAPI chama `list_books()` e
aguarda sua coroutine. Os dados em memória não fazem I/O e, portanto, não há
ganho de concorrência nesta função ainda. O `async def` prepara o caminho para
operações assíncronas reais sem fingir que uma lista local precisa de `await`.

> **Limite intencional:** não use `await` em valores comuns e não acrescente
> `asyncio.sleep()` apenas para o código parecer assíncrono.

## Antes e depois

Antes desta aula não havia servidor nem contrato HTTP. Depois dela:

```text
Cliente HTTP
    |
    v
FastAPI
    +--> GET /health
    +--> GET /books --> lista temporária
    +--> GET /users --> lista temporária
```

Ainda faltam entrada validada, criação, busca por identificador e respostas de
erro. Essas ausências são o problema visível da próxima aula.

## Como testar

O checkpoint completo está em
[lesson-01](../../reference/checkpoints/module-04/lesson-01/).

```bash
cd reference/checkpoints/module-04/lesson-01
python -m pip install -e '.[dev]'
python -m pytest -q
python -m uvicorn app.main:app --reload
```

Em outro terminal:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/books
curl http://127.0.0.1:8000/users
```

Os testes usam um cliente ASGI assíncrono. Assim, exercitam as coroutines da
aplicação sem abrir uma porta de rede.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — escreva a sua primeira rota</summary>

Na sua área `student/library-api/`, crie o projeto e digite as três rotas. Em
seguida, adicione `GET /welcome`, que devolve `{"message": "Bem-vindo"}`.

Confirme manualmente que a rota aparece em `/docs`. Não copie o checkpoint
antes de tentar.

</details>

<details markdown="1">
<summary>Teste seu entendimento — coroutine ou task?</summary>

Ao executar `result = list_books()`, `result` contém a lista de livros?

Não. A chamada cria uma coroutine. O corpo executa quando a coroutine é
aguardada. No fluxo HTTP, o FastAPI faz esse agendamento para você.

</details>

<details markdown="1">
<summary>Desafio — observe o event loop</summary>

Execute o exemplo `parent`/`child` e depois troque `asyncio.sleep()` por
`time.sleep()`. Observe a ordem da saída e explique por que a segunda versão
bloqueia `sibling`.

</details>

## Checkpoint

!!! checkpoint "Aula 1 concluída"
    Você possui uma Library API executável com três endpoints de leitura,
    entende a diferença entre coroutine e task e sabe que `await` só cede
    controle quando a operação aguardada realmente suspende.

Mensagem sugerida para o seu commit:

```text
student(m04-l01): implement the first Library API
```

## Próximo problema

Hoje os endpoints devolvem dicionários sem declarar quais campos são
obrigatórios. Também não existe entrada de dados. Na aula 2 usaremos Pydantic v2
para transformar essas suposições em contratos verificáveis.
