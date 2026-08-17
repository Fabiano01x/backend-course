# Integração segura com o frontend

> **Origem e complementação:** esta aula adapta *Securing FastAPI: CORS and
> Essential Headers*. Origens passam por `Settings`; HSTS depende de produção
> com HTTPS; uma CSP genérica foi omitida porque quebraria Swagger e ReDoc.

O frontend local roda em `http://localhost:5173` e a API em
`http://localhost:8000`. Para o navegador, portas diferentes formam origens
diferentes, mesmo no mesmo computador.

## O problema

!!! problem "O navegador bloqueia uma integração que a API nunca autorizou"
    A Same-Origin Policy impede que scripts leiam livremente respostas de outra
    origem. Liberar tudo com `*` evita o erro local, mas abandona a decisão de
    quais frontends podem usar a API e conflita com credenciais.

Além de CORS, as respostas ainda não orientam o navegador a evitar inferência
de MIME, enquadramento por terceiros ou envio excessivo de referência.

## Por que isso importa

Uma origem combina protocolo, host e porta:

```text
http://localhost:5173  !=  http://localhost:8000
https://library.dev    !=  http://library.dev
```

CORS é uma política declarada pelo servidor e aplicada pelo navegador. Ele não
autentica usuários nem bloqueia clientes como `curl`; apenas autoriza leitura
cross-origin no contexto do browser.

!!! resource "Leitura — CORS no FastAPI"
    Leia [Cross-Origin Resource Sharing](https://fastapi.tiangolo.com/tutorial/cors/)
    na documentação oficial.

    !!! guidance "Orientação"
        Observe requisições simples e preflight. Relacione `allow_origins`,
        métodos, headers e credenciais; não trate wildcard como default seguro.

## O conceito

Para certos métodos e headers, o browser envia primeiro um `OPTIONS` preflight:

```text
browser ──OPTIONS + Origin──> API
        <──permissões CORS────
browser ──POST real─────────> API
```

`CORSMiddleware` responde ao preflight e acrescenta headers às respostas. O
checkpoint permite somente origens configuradas, credenciais, `GET`, `POST`,
`OPTIONS`, `Authorization` e `Content-Type`.

Headers defensivos possuem outro papel:

- `X-Content-Type-Options: nosniff` impede adivinhação de MIME;
- `X-Frame-Options: DENY` evita enquadramento e clickjacking;
- `Referrer-Policy: no-referrer` reduz vazamento de URL;
- `Permissions-Policy` desabilita câmera, microfone e geolocalização;
- HSTS manda preferir HTTPS em acessos futuros.

!!! correction "HSTS exige HTTPS real"
    Enviar HSTS em desenvolvimento HTTP ensina uma política que o ambiente não
    cumpre. A Library API só o habilita quando `environment=production` e
    `https_enabled=true`.

!!! correction "CSP não aceita copiar e colar"
    `default-src 'self'` bloqueia os recursos externos usados pelas interfaces
    `/docs` e `/redoc`. Não publicamos uma CSP falsa. Ela será desenhada e
    testada quando os recursos e origens da documentação forem definidos.

## Modelo mental

!!! mental-model "CORS abre uma porta; headers colocam instruções na saída"
    CORS decide quais origens do navegador atravessam a fronteira. O middleware
    de segurança acrescenta instruções a toda resposta, inclusive ao preflight.

    ```text
    request → SecurityHeaders → CORS → router
    response ← headers seguros ← headers CORS ← endpoint
    ```

## Exemplo mínimo

Este exemplo isola CORS e não representa toda a arquitetura atual:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Authorization"],
)
```

## Aplicando ao projeto

`Settings` ganha valores consumidos agora:

```python
allowed_origins: list[str] = ["http://localhost:5173"]
https_enabled: bool = False
```

Com credenciais habilitadas, wildcard é recusado. Produção também recusa
origens HTTP:

```python
if "*" in self.allowed_origins:
    raise ValueError("allowed_origins não aceita wildcard com credenciais")
if self.environment == "production" and any(
    not origin.startswith("https://") for origin in self.allowed_origins
):
    raise ValueError("origens de produção devem usar HTTPS")
```

Como middleware pertence ao startup, `main.py` ganha uma fábrica testável:

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    startup_settings = settings or load_settings()
    application = FastAPI(...)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=startup_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=(
            startup_settings.environment == "production"
            and startup_settings.https_enabled
        ),
    )
    ...
    return application
```

O middleware de segurança é adicionado por último para envolver CORS e aplicar
headers também às respostas de preflight tratadas antes do router.

`.env.example` representa listas como JSON, formato entendido por Pydantic
Settings:

```dotenv
LIBRARY_ALLOWED_ORIGINS='["http://localhost:5173"]'
LIBRARY_HTTPS_ENABLED="false"
```

## Antes e depois

| Aula 6 | Aula 7 |
|---|---|
| browser sem autorização cross-origin | origens explícitas em settings |
| nenhum preflight tratado | `OPTIONS` respondido pelo middleware |
| headers defensivos ausentes | conjunto mínimo em toda resposta |
| HSTS poderia ser copiado sem contexto | somente produção + HTTPS |
| CSP genérica sugerida pela fonte | CSP adiada para não quebrar docs |
| app construída diretamente | `create_app(settings)` testável |

## Como testar

Consulte [lesson-07](../../reference/checkpoints/module-04/lesson-07/).

```bash
cd reference/checkpoints/module-04/lesson-07
python -m pip install -e '.[dev]'
python -m pytest -q
```

Os testes cobrem origem permitida e negada, preflight, credenciais, headers,
HSTS condicionado, validação de settings e disponibilidade de `/docs` e
`/redoc` sem CSP incompatível.

## Exercícios

<details markdown="1">
<summary>Exercício guiado — nova origem local</summary>

Inclua `http://localhost:3000` no JSON de `LIBRARY_ALLOWED_ORIGINS`. Reinicie e
prove com um preflight que ambas as origens locais são aceitas.

</details>

<details markdown="1">
<summary>Teste seu entendimento — CORS não é autenticação</summary>

Por que uma origem negada ainda pode chamar a API com `curl`? Porque CORS é uma
política aplicada pelo navegador; controle de identidade exige autenticação e
autorização próprias.

</details>

<details markdown="1">
<summary>Desafio — produção sem HSTS</summary>

Crie uma aplicação com ambiente `production`, origem HTTPS e
`https_enabled=false`. Prove que a origem é válida, mas HSTS permanece ausente.

</details>

## Checkpoint

!!! checkpoint "Aula 7 concluída"
    A Library API aceita somente frontends configurados, trata preflight e
    envia headers defensivos. HSTS respeita HTTPS real e a documentação
    interativa continua funcional.

Mensagem sugerida:

```text
student(m04-l07): configure CORS and security headers
```

## Próximo problema

A API já gera OpenAPI, Swagger UI e ReDoc, mas nomes, descrições, exemplos e
respostas ainda não foram auditados como um contrato para consumidores. A aula
8 encerrará o módulo refinando e testando essa documentação executável.
