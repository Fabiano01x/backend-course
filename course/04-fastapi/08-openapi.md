# OpenAPI como contrato executável

> **Origem e complementação:** esta aula adapta *Interactive API Docs with
> Swagger UI & ReDoc*. A fonte apresenta metadados e descrições; aqui também
> estabilizamos `operationId`, documentamos erros reais, adicionamos exemplos e
> testamos diretamente o contrato em `/openapi.json`.

A Library API já oferece Swagger UI e ReDoc. As telas abrem, mas isso não
garante que um frontend encontre nomes estáveis, respostas completas e exemplos
úteis.

## O problema

!!! problem "Documentação automática também pode estar incompleta"
    FastAPI conhece paths, tipos e status principais, mas não consegue adivinhar
    a intenção de cada operação. Antes desta aula, erros `404` existiam no código
    sem aparecer no schema, os exemplos de cadastro estavam ausentes e os
    identificadores das operações dependiam da geração automática.

Uma interface bonita pode esconder esse problema. O consumidor real usa o
contrato: pessoas o leem e ferramentas geram clientes, testes e integrações a
partir dele.

## Por que isso importa

`/docs` e `/redoc` são duas visualizações do mesmo documento:

```text
decorators + tipos + schemas + metadados
                    |
                    v
              /openapi.json
               /          \
              v            v
       Swagger UI        ReDoc
       interativo        referência
                    |
                    v
           geradores de clientes
```

Se o JSON estiver errado, ambas as interfaces repetem o erro. Por isso a
auditoria deve começar pelo schema, não por uma inspeção visual isolada.

!!! resource "Leitura — metadados e operações no FastAPI"
    Consulte [Metadata and Docs URLs](https://fastapi.tiangolo.com/tutorial/metadata/)
    e [Path Operation Configuration](https://fastapi.tiangolo.com/tutorial/path-operation-configuration/)
    na documentação oficial.

    !!! guidance "Orientação"
        Relacione `openapi_tags`, `summary`, `description` e
        `response_description` aos campos produzidos no JSON. Observe que a
        ordem dos metadados de tags também organiza as interfaces.

## O conceito

OpenAPI é uma descrição legível por máquina da API. Cada combinação de path e
método é uma **operação**. Ela pode declarar:

- tag, resumo e descrição;
- parâmetros e corpo de entrada;
- status e schemas das respostas;
- exemplos;
- um `operationId` único.

Os modelos Pydantic geram JSON Schema dentro de `components.schemas`. Um
`response_model` não serve apenas para a tela: ele documenta, valida, serializa
e filtra a resposta.

!!! correction "Automático não significa sem projeto"
    O framework extrai muito do código, mas nomes e omissões continuam sendo
    decisões da equipe. Um `404` produzido pelo endpoint precisa ser declarado
    como resposta adicional para aparecer no contrato.

!!! correction "Não invente informações profissionais"
    A fonte usa contato, licença e endpoint obsoleto como exemplos. A Library
    API não publica suporte ou licença inexistentes e não cria uma rota legada
    apenas para mostrar `deprecated=True`. Deprecação pertence a uma migração
    real.

## Modelo mental

!!! mental-model "O código executa; o schema promete"
    Uma mudança de rota pode continuar passando em testes funcionais e ainda
    quebrar consumidores se alterar `operationId`, status ou formato
    documentado. Testamos comportamento e promessa.

    ```text
    implementação ──teste HTTP──> resposta real
          |
          └────teste OpenAPI──> contrato publicado
    ```

## Exemplo mínimo

Este exemplo isola metadados e não representa a arquitetura atual, que continua
usando `APIRouter`:

```python
from fastapi import FastAPI

app = FastAPI(title="Example API", version="1.0.0")


@app.get(
    "/items/{item_id}",
    operation_id="getItem",
    summary="Consultar um item",
    response_description="O item encontrado.",
)
async def get_item(item_id: int) -> dict[str, int]:
    return {"id": item_id}
```

## Aplicando ao projeto

A fábrica da aplicação recebe descrição Markdown e metadados para as tags já
usadas pelos routers:

```python
OPENAPI_TAGS = [
    {"name": "Sistema", "description": "Saúde e configuração pública."},
    {"name": "Livros", "description": "Consulta e cadastro do acervo."},
    {"name": "Usuários", "description": "Consulta e cadastro de usuários."},
]

application = FastAPI(
    title=startup_settings.app_name,
    summary="API didática para gerenciar uma biblioteca.",
    description=API_DESCRIPTION,
    version=startup_settings.app_version,
    openapi_tags=OPENAPI_TAGS,
)
```

Cada operação ganha um identificador estável e texto específico:

```python
@router.post(
    "",
    response_model=BookResponse,
    status_code=201,
    operation_id="createBook",
    summary="Cadastrar um livro",
    response_description="O livro criado com identificador gerado pela API.",
)
async def create_book(payload: BookCreate) -> BookResponse:
    return data.create_book(payload)
```

Os endpoints que realmente retornam `404` compartilham um contrato de erro:

```python
class ErrorResponse(StrictSchema):
    detail: str


responses = {
    404: {"model": ErrorResponse, "description": "Livro não encontrado."}
}
```

Os modelos de entrada fornecem exemplos com `json_schema_extra`. Swagger UI
consegue preencher um corpo inicial sem duplicar um exemplo em cada endpoint:

```python
class BookCreate(StrictSchema):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Kindred",
                    "author": "Octavia E. Butler",
                    "isbn": "9780807083697",
                }
            ]
        }
    )
```

!!! resource "Leitura — clientes gerados"
    A documentação oficial mostra em
    [Generating SDKs](https://fastapi.tiangolo.com/advanced/generate-clients/)
    por que tags, schemas e `operationId` afetam os nomes e tipos de um cliente.

## Antes e depois

| Aula 7 | Aula 8 |
|---|---|
| metadados mínimos | descrição honesta do escopo atual |
| tags apenas agrupam | tags possuem descrição e ordem explícitas |
| IDs automáticos | `operationId` único e estável |
| `404` existe só no código | schema de erro documentado |
| corpos sem exemplo | exemplos nos schemas de entrada |
| docs conferidas pela abertura da página | contrato JSON protegido por testes |

## Como testar

Consulte [lesson-08](../../reference/checkpoints/module-04/lesson-08/).

```bash
cd reference/checkpoints/module-04/lesson-08
python -m pip install -e '.[dev]'
python -m pytest -q
```

Um teste percorre as oito operações e garante que cada `operationId` esperado é
único e tem resumo. Outros verificam metadados, ordem das tags, exemplos,
resposta `201`, erros `404` e validação `422` no JSON publicado.

Para explorar manualmente:

```text
http://localhost:8000/openapi.json
http://localhost:8000/docs
http://localhost:8000/redoc
```

## Exercícios

<details markdown="1">
<summary>Exercício guiado — leia a promessa</summary>

Abra `/openapi.json`, encontre `POST /books` e siga a referência do request body
até `BookCreate`. Identifique campos obrigatórios, limites e exemplo.

</details>

<details markdown="1">
<summary>Teste seu entendimento — resposta esquecida</summary>

Remova temporariamente `responses={404: ...}` de `GET /books/{book_id}`. O
endpoint ainda retorna `404`, mas qual consumidor deixa de conhecer esse
contrato? Todo consumidor que depende do OpenAPI, inclusive as duas interfaces
e clientes gerados.

</details>

<details markdown="1">
<summary>Desafio — estabilidade dos IDs</summary>

Renomeie a função Python de listagem sem alterar `operation_id="listBooks"`.
Comprove que o identificador publicado permanece estável. Depois retire o
`operation_id` e observe a diferença gerada pelo FastAPI.

</details>

## Checkpoint

!!! checkpoint "Aula 8 e Módulo 4 concluídos"
    A Library API publica metadados honestos, operações identificáveis,
    exemplos e respostas reais. Swagger UI e ReDoc continuam disponíveis, e o
    contrato que os alimenta está protegido por testes.

Mensagem sugerida:

```text
student(m04-l08): audit the OpenAPI contract
```

## Próximo problema

O contrato HTTP está organizado, configurável, seguro para a integração local e
documentado. O estado, porém, desaparece a cada reinicialização e não funciona
de forma consistente com múltiplos processos. O próximo módulo introduzirá
modelagem relacional e persistência somente porque esse problema agora é
visível.
