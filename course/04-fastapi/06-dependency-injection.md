# Dependências e ciclo de vida de recursos

> **Origem e reorganização:** esta aula combina *Dependency Injection for
> Resource Management* com a parte de `Depends` e cache de *Environment
> Variables for Configuration and Secrets*. Settings são aplicados ao projeto;
> sessões de banco permanecem como ponte conceitual para o Módulo 5.

Na aula 5, `Settings` resolveu validação e precedência, mas criou outro
problema: routers importam um objeto global já construído. Para testar outra
configuração, seria preciso alterar o ambiente antes de importar a aplicação.

## O problema

!!! problem "O consumidor conhece a construção da dependência"
    `system.router` quer apenas ler configuração, mas importa a instância que a
    constrói. O teste não possui um ponto explícito para substituir esse valor.
    A mesma dificuldade seria mais grave com uma conexão que também precisa ser
    fechada após o uso.

```text
endpoint ──importa──> settings global ──criado durante importação
```

Precisamos separar duas perguntas:

- do que o endpoint precisa?
- quem cria, reutiliza, substitui ou encerra essa dependência?

## Por que isso importa

Dependency Injection torna a necessidade explícita na assinatura e entrega o
valor por fora. O endpoint usa `Settings`; não decide como ler `.env`, aplicar
cache ou produzir uma versão de teste.

Isso oferece:

- construção centralizada;
- reutilização dentro da requisição;
- substituição por `app.dependency_overrides`;
- composição de dependências;
- setup e teardown confiáveis para recursos com ciclo de vida.

!!! resource "Leitura — dependências no FastAPI"
    Leia [Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/)
    e [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/)
    na documentação oficial.

    !!! guidance "Orientação"
        Primeiro acompanhe provider → `Depends` → parâmetro. Depois observe o
        que ocorre antes e depois de `yield`. Não implemente a sessão de banco
        mostrada na fonte: ela chegará junto com engine e modelos reais.

## O conceito

Uma dependência FastAPI é um callable declarado com `Depends`:

```python
from typing import Annotated

from fastapi import Depends


async def provide_name() -> str:
    return "Library API"


ProvidedName = Annotated[str, Depends(provide_name)]
```

O alias concentra tipo e provider. Um endpoint pede o valor:

```python
async def read_info(name: ProvidedName) -> dict[str, str]:
    return {"name": name}
```

`name` não é query parameter nem corpo. FastAPI resolve `provide_name`, valida
o grafo de dependências e chama o endpoint com o resultado.

### Cache de aplicação e cache de requisição

São mecanismos diferentes:

- `lru_cache` reutiliza o mesmo `Settings` entre chamadas do processo;
- FastAPI reutiliza por padrão o resultado de uma dependência dentro da mesma
  requisição.

O checkpoint separa o carregador cacheado do adaptador injetável:

```python
@lru_cache
def load_settings() -> Settings:
    return Settings()


async def get_settings() -> Settings:
    return load_settings()


AppSettings = Annotated[Settings, Depends(get_settings)]
```

O adaptador assíncrono é pequeno e não ocupa o pool de threads. A função
cacheada também pode ser chamada diretamente durante a inicialização, quando
não existe uma requisição para resolver `Depends`.

### Dependências com `yield`

Um retorno entrega um valor e termina. `yield` divide o provider em três fases:

```text
setup → yield recurso → endpoint → finally/teardown
```

```python
from collections.abc import AsyncIterator


async def get_connection() -> AsyncIterator[Connection]:
    connection = await open_connection()
    try:
        yield connection
    finally:
        await connection.close()
```

O `finally` garante a tentativa de fechamento inclusive quando o endpoint
falha. A dependência possui o ciclo de vida; o endpoint recebe apenas o recurso
pronto.

!!! correction "`yield` não cria um banco"
    O padrão gerencia qualquer recurso existente, mas não justifica inventar
    engine, sessão ou repository. A Library API ainda opera em memória. Quando
    o Módulo 5 introduzir SQLAlchemy, a sessão real ocupará esse ponto sem mudar
    o modelo mental aprendido aqui.

## Modelo mental

!!! mental-model "Um grafo resolvido de fora para dentro"
    O endpoint fica no centro. FastAPI percorre as dependências até os
    providers, monta os valores de fora para dentro e, quando há `yield`,
    desmonta recursos na ordem inversa.

    ```text
    load_settings ──> get_settings ──> endpoint
                           |
                    override em teste

    abrir recurso ──> yield ──> endpoint ──> finally ──> fechar
    ```

## Exemplo mínimo

Este exemplo executável isola substituição sem representar a arquitetura atual:

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


async def get_message() -> str:
    return "produção"


Message = Annotated[str, Depends(get_message)]


@app.get("/message")
async def message(value: Message) -> dict[str, str]:
    return {"message": value}


async def override_message() -> str:
    return "teste"


app.dependency_overrides[get_message] = override_message
```

O endpoint não muda. Somente a composição usada pelo teste muda.

## Aplicando ao projeto

`config.py` passa a conter apenas o contrato `Settings`; a instância global é
removida. `dependencies.py` concentra o carregamento:

```python
@lru_cache
def load_settings() -> Settings:
    return Settings()


async def get_settings() -> Settings:
    return load_settings()


AppSettings = Annotated[Settings, Depends(get_settings)]
```

### Configuração durante requisições

`/info` recebe a dependência:

```python
@router.get("/info", response_model=AppInfo)
async def app_info(settings: AppSettings) -> AppInfo:
    return AppInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
    )
```

A listagem também resolve o limite por requisição. `limit=None` significa “use
o default configurado”; um valor explícito ainda precisa respeitar o máximo da
instalação:

```python
async def list_books(
    settings: AppSettings,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
    ...,
) -> BookPage:
    page_limit = settings.default_page_size if limit is None else limit
    if page_limit > settings.max_page_size:
        raise HTTPException(
            status_code=422,
            detail=f"limit não pode exceder {settings.max_page_size}",
        )
```

O OpenAPI mostra `limit`, mas não mostra `settings`: dependências internas não
viram entradas HTTP.

### Configuração durante inicialização

Metadados do objeto `FastAPI` são necessários antes de qualquer requisição.
Nesse limite, `main.py` chama o mesmo carregador diretamente:

```python
startup_settings = load_settings()

app = FastAPI(
    title=startup_settings.app_name,
    version=startup_settings.app_version,
    debug=startup_settings.debug,
)
```

Um override de requisição altera `/info` e paginação, mas não reconstrói o
objeto `FastAPI`. Configuração de startup e dependência request-scoped não são a
mesma fase.

### Substituição no teste

```python
test_settings = Settings(
    _env_file=None,
    environment="test",
    default_page_size=2,
    max_page_size=3,
)


async def override_settings() -> Settings:
    return test_settings


app.dependency_overrides[get_settings] = override_settings
```

Sem reimportar a aplicação, o teste prova que `/info` usa `test` e que uma
requisição sem `limit` devolve dois itens. Ao final, os overrides são limpos
para não vazar entre testes.

## Antes e depois

| Aula 5 | Aula 6 |
|---|---|
| `settings = Settings()` global | `load_settings()` cacheado |
| routers importam instância | endpoints declaram `AppSettings` |
| teste controla ordem de importação | teste usa `dependency_overrides` |
| limite padrão fixado no decorator | default resolvido pela dependência |
| ciclo de recursos ainda implícito | setup → `yield` → teardown explicado |
| sessão fictícia seria tentadora | banco continua explicitamente adiado |

## Como testar

Consulte o projeto completo em
[lesson-06](../../reference/checkpoints/module-04/lesson-06/).

```bash
cd reference/checkpoints/module-04/lesson-06
python -m pip install -e '.[dev]'
python -m pytest -q
```

Os testes provam cache por identidade, override assíncrono, default e máximo de
paginação por instalação, ausência de `settings` no OpenAPI e preservação dos
contratos anteriores.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — substitua a configuração</summary>

Crie `Settings(environment="test", default_page_size=1)` e sobrescreva
`get_settings`. Prove que `/info` e `/books` mudam sem recarregar módulos. Limpe
`app.dependency_overrides` ao final.

</details>

<details markdown="1">
<summary>Teste seu entendimento — duas fases</summary>

Por que o override muda `/info`, mas não o título de uma instância `FastAPI` já
criada?

Porque `/info` resolve a dependência durante a requisição. O título foi lido na
inicialização, antes do override.

</details>

<details markdown="1">
<summary>Desafio — prove o `finally`</summary>

Crie, apenas no teste, um recurso falso com `closed = False`. Faça uma
dependência com `yield` e `finally`, provoque uma exceção no consumidor e prove
que `closed` terminou como `True`. Não adicione o recurso falso ao projeto.

</details>

## Checkpoint

!!! checkpoint "Aula 6 concluída"
    Settings usados por endpoints são cacheados, injetáveis e substituíveis em
    testes. A fronteira entre startup e requisição está explícita, e o ciclo de
    recursos com `yield` foi preparado sem antecipar o banco.

Mensagem sugerida:

```text
student(m04-l06): inject settings and model resource lifecycle
```

## Próximo problema

A configuração agora distingue ambientes, mas navegadores ainda precisam de
uma política explícita para chamar a API a partir de outra origem. Na aula 7,
usaremos settings injetáveis na composição de CORS e aplicaremos headers de
segurança compatíveis com desenvolvimento e produção.
