# Configuração por ambiente

> **Origem e reorganização:** esta aula adapta *Environment Variables for
> Configuration and Secrets*. A fonte também apresenta configuração de banco,
> JWT, CORS, `Depends` e `lru_cache`. Aqui configuramos somente valores já
> usados pela Library API; banco e autenticação aguardam seus módulos, CORS
> chega na aula 7 e injeção de dependência será o problema da aula 6.

Na aula 4, a API ganhou paginação. Para isso, alguns valores foram escritos
diretamente no código:

```python
app = FastAPI(title="Library API", version="0.4.0")

Query(ge=1, le=100)
```

O código funciona, mas agora uma mudança de nome, modo de depuração ou limite
de página exige editar arquivos e criar uma nova versão da aplicação.

## O problema

!!! problem "Código e ambiente mudam por motivos diferentes"
    A regra “uma página nunca ultrapassa o máximo permitido” pertence ao
    programa. Já o valor desse máximo pode variar entre execução local, testes
    e produção. Quando os dois ficam misturados, trocar configuração parece uma
    mudança de lógica.

Também não existe hoje um lugar único que responda:

```text
qual é o nome desta instalação?
em que ambiente ela está?
debug está habilitado?
qual é o tamanho padrão de página?
```

Ler cada valor com `os.getenv()` dentro do arquivo que o consome espalharia
nomes de variáveis, conversões e defaults pela aplicação. Uma string inválida
como `LIBRARY_DEFAULT_PAGE_SIZE=muitos` só falharia quando algum trecho tentasse
usá-la como número.

## Por que isso importa

Separar configuração do código permite executar o mesmo artefato em ambientes
diferentes. A implantação fornece valores externos; a aplicação declara o
contrato e recusa combinações inválidas.

```text
mesmo código
   ├── desenvolvimento: debug=true, página padrão=10
   ├── testes:          ambiente=test, página padrão=5
   └── produção:        debug=false, página padrão=20
```

Isso reduz três riscos:

- valores específicos de uma instalação entrarem no Git;
- texto recebido do ambiente ser usado sem conversão ou validação;
- defaults diferentes surgirem em módulos diferentes.

!!! resource "Leitura — settings no FastAPI"
    Leia [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)
    na documentação oficial do FastAPI.

    !!! guidance "Orientação"
        Nesta aula, concentre-se em tipos, `BaseSettings`, variáveis de ambiente
        e arquivos `.env`. Pare antes de transformar settings em dependência;
        faremos essa refatoração depois de observar a limitação do objeto global.

## O conceito

### `BaseSettings` é um contrato de entrada da aplicação

`BaseSettings`, do pacote `pydantic-settings`, usa anotações e validações do
Pydantic, mas procura valores também em fontes externas:

```python
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LIBRARY_")

    app_name: str = "Library API"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    default_page_size: int = Field(default=20, ge=1, le=100)
```

Com o prefixo, o atributo `default_page_size` lê
`LIBRARY_DEFAULT_PAGE_SIZE`. O shell continua fornecendo texto, mas Pydantic
converte `"10"` para `10` e `"true"` para `True` antes de entregar o objeto.

### Defaults não são valores obrigatórios

Cada campo desta aula tem um default seguro, então a API continua iniciando sem
arquivo `.env`. Uma variável externa substitui o default apenas naquela
execução.

Campos sem default são obrigatórios e uma ausência causa `ValidationError` na
inicialização. Usaremos isso quando o projeto realmente depender de um valor que
não possa ter fallback; não criaremos agora chaves de JWT ou URLs de banco sem
consumidores.

### Precedência

Neste checkpoint, as fontes relevantes seguem esta prioridade:

```text
argumento passado a Settings(...)
        ↓ prevalece
variável do processo
        ↓ prevalece
arquivo .env
        ↓ prevalece
default da classe
```

Assim, `.env` facilita desenvolvimento local, enquanto a plataforma de
produção pode sobrescrever seus valores com variáveis do processo sem alterar
o arquivo nem o código.

### `.env` e `.env.example` têm papéis diferentes

```text
.env          valores locais reais       ignorado pelo Git
.env.example  nomes e exemplos seguros   versionado
```

O repositório já ignora `.env`. O checkpoint também possui sua própria regra
para continuar seguro quando for copiado isoladamente.

!!! correction "Variável de ambiente não é um cofre"
    Retirar um segredo do código evita commitá-lo, mas não o torna invisível.
    Processos, logs, painéis de implantação e permissões incorretas ainda podem
    expô-lo. Quando a Library API tiver segredos reais, eles serão entregues por
    um mecanismo apropriado e nunca aparecerão em `/info`, exemplos preenchidos
    ou mensagens de erro.

## Modelo mental

!!! mental-model "Uma portaria antes da aplicação"
    O ambiente não entra diretamente nos routers. `Settings` recebe textos de
    fontes externas, resolve precedência, converte tipos e valida relações. Só
    um objeto aceito chega à aplicação.

    ```text
    defaults ─┐
    .env ─────┼──> Settings ──válido──> FastAPI e routers
    ambiente ─┤         |
    argumentos┘         └──inválido──> falha ao iniciar
    ```

Falhar na inicialização é melhor que subir uma aplicação com configuração
contraditória e descobrir o problema apenas na primeira requisição afetada.

## Exemplo mínimo

Este exemplo isola carregamento e validação; não representa a arquitetura atual
do projeto completo:

```python
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKER_")

    environment: Literal["development", "production"] = "development"
    concurrency: int = 2


settings = WorkerSettings()
```

Uma execução pode substituir os defaults sem editar Python:

```bash
WORKER_ENVIRONMENT=production WORKER_CONCURRENCY=8 python worker.py
```

Se `WORKER_CONCURRENCY=alto`, a construção de `WorkerSettings` falha porque
`alto` não é um inteiro.

## Aplicando ao projeto

### Dependência declarada

O checkpoint adiciona `pydantic-settings` às dependências:

```toml
dependencies = [
  "fastapi>=0.116,<1.0",
  "pydantic>=2.11,<3.0",
  "pydantic-settings>=2.14,<3.0",
  "uvicorn>=0.35,<1.0",
]
```

O ambiente aprovado registra também a dependência transitiva `python-dotenv`,
responsável pela leitura do arquivo local.

### Um arquivo para o contrato

Criamos `app/config.py`:

```python
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix="LIBRARY_",
        extra="forbid",
        frozen=True,
    )

    app_name: str = Field(default="Library API", min_length=1, max_length=100)
    app_version: str = Field(default="0.5.0", pattern=r"^\d+\.\d+\.\d+$")
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=100)
```

O caminho absoluto ancora `.env` na raiz do checkpoint. Assim, o resultado não
depende do diretório em que o comando foi executado. `extra="forbid"` faz um
nome desconhecido no arquivo local revelar um possível erro de digitação, e
`frozen=True` impede mutar a configuração depois de validada.

Cada campo isolado pode ser válido e ainda formar uma combinação impossível.
O tamanho padrão não pode superar o máximo:

```python
@model_validator(mode="after")
def default_page_size_cannot_exceed_maximum(self) -> Self:
    if self.default_page_size > self.max_page_size:
        raise ValueError("default_page_size não pode exceder max_page_size")
    return self
```

Por fim, esta etapa cria uma única instância durante a importação:

```python
settings = Settings()
```

Isso evita reler o ambiente a cada requisição, mas cria uma dependência global.
É uma decisão temporária e visível: substituí-la em um teste HTTP exige controlar
o ambiente antes de importar a aplicação. Essa dor motivará a aula 6.

### Configuração consumida

`main.py` deixa de repetir metadados:

```python
app = FastAPI(
    title=settings.app_name,
    description="Projeto cumulativo do curso de backend Python.",
    version=settings.app_version,
    debug=settings.debug,
)
```

O router de livros usa os limites validados:

```python
limit: Annotated[
    int,
    Query(ge=1, le=settings.max_page_size),
] = settings.default_page_size
```

E `system.router` publica somente informações não sensíveis:

```python
@router.get("/info", response_model=AppInfo)
async def app_info() -> AppInfo:
    return AppInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
    )
```

### Arquivo de exemplo

O checkpoint versiona `.env.example`:

```dotenv
LIBRARY_APP_NAME="Library API - Desenvolvimento"
LIBRARY_APP_VERSION="0.5.0"
LIBRARY_ENVIRONMENT="development"
LIBRARY_DEBUG="true"
LIBRARY_DEFAULT_PAGE_SIZE="10"
LIBRARY_MAX_PAGE_SIZE="100"
```

Para experimentar localmente, copie para `.env` e edite a cópia. Nunca renomeie
o exemplo de forma que o arquivo real entre no commit.

## Antes e depois

| Aula 4 | Aula 5 |
|---|---|
| metadados escritos em `main.py` | `Settings` fornece nome, versão e debug |
| limites `20` e `100` no router | limites validados e configuráveis |
| sem identidade do ambiente | `development`, `test` ou `production` |
| mudar valor exige editar Python | ambiente sobrescreve o default |
| nenhuma verificação entre limites | default não pode superar máximo |
| apenas `/health` operacional | `/info` expõe configuração pública |

Schemas de livros e usuários, routers, filtros, ordenação, paginação e
armazenamento em memória continuam presentes.

## Como testar

Consulte o projeto completo em
[lesson-05](../../reference/checkpoints/module-04/lesson-05/).

```bash
cd reference/checkpoints/module-04/lesson-05
python -m pip install -e '.[dev]'
python -m pytest -q
```

Execute com os defaults:

```bash
.venv/bin/python -m uvicorn app.main:app --reload \
  --app-dir reference/checkpoints/module-04/lesson-05
```

Ou sobrescreva alguns valores apenas para o processo:

```bash
LIBRARY_APP_NAME='Minha Biblioteca' \
LIBRARY_ENVIRONMENT=test \
LIBRARY_DEFAULT_PAGE_SIZE=2 \
.venv/bin/python -m uvicorn app.main:app \
  --app-dir reference/checkpoints/module-04/lesson-05
```

Confira `GET /info`, `GET /books` e `/openapi.json`. Nome, ambiente, tamanho
padrão, limite máximo e metadados devem refletir a configuração escolhida.

Os testes provam:

- defaults válidos sem `.env`;
- conversão de strings do ambiente para booleano e inteiro;
- variável do processo prevalecendo sobre `.env`;
- versão, ambiente e limites inválidos causando `ValidationError`;
- relação `default_page_size <= max_page_size`;
- integração dos settings com `/info`, paginação e OpenAPI;
- contratos das aulas anteriores preservados.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — altere sem editar Python</summary>

Copie `.env.example` para `.env`, configure o nome como `Library API Local` e o
tamanho padrão como `2`. Reinicie a aplicação e prove a mudança consultando
`/info`, `/books` e `/openapi.json`.

</details>

<details markdown="1">
<summary>Teste seu entendimento — precedência</summary>

Se `.env` contém `LIBRARY_DEBUG=false`, mas o processo inicia com
`LIBRARY_DEBUG=true`, qual valor chega à aplicação?

`True`, porque a variável do processo tem prioridade maior que o arquivo
`.env`.

</details>

<details markdown="1">
<summary>Desafio — configuração pública versus segredo</summary>

Adicione `support_email` com default seguro e publique-o em `AppInfo`. Depois
explique por que uma futura `jwt_secret` não deveria entrar na mesma resposta,
mesmo sendo carregada por `Settings`.

</details>

## Checkpoint

!!! checkpoint "Aula 5 concluída"
    A Library API carrega configuração tipada de defaults, `.env` e variáveis
    do processo. Valores inválidos impedem a inicialização; metadados e limites
    deixam de ficar espalhados pelo código; nenhum segredo fictício foi criado.

Mensagem sugerida:

```text
student(m04-l05): add validated environment settings
```

## Próximo problema

`main.py`, `books.router` e `system.router` importam o mesmo objeto global
`settings`. Ele é criado uma vez, mas um teste HTTP que queira outra configuração
precisa controlar o momento da importação. Na aula 6, transformaremos settings
em uma dependência cacheada e substituível, antes de aprender o ciclo de vida de
recursos com `yield`.
