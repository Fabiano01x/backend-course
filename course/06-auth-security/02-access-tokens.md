# Access tokens curtos e identidade autenticada

> **Origem, reorganização e correção:** a fonte *JWT Authentication with
> Access and Refresh Tokens* apresenta JWT, access token, refresh token e login
> em uma única aula. Nesta sequência, M06/A01 construiu primeiro a credencial
> local que a fonte pressupunha. Agora implementamos somente o access token,
> com algoritmo fixo, chave validada, claims obrigatórias e contexto explícito.
> Refresh token, cookie e revogação pertencem ao próximo problema.

O servidor já compara uma senha apresentada com o hash Argon2id do banco. O
`204` temporário de `POST /auth/login`, porém, encerra toda informação sobre o
login naquela resposta. Na requisição seguinte, o cliente ainda não consegue
provar quem autenticou.

## O problema

!!! problem "Uma senha válida em uma requisição não cria identidade na próxima"
    `POST /loans` recebe `user_id` no JSON. Nada relaciona esse número com a
    pessoa que acabou de informar a senha. Um cliente pode trocar `1` por `7`
    e tentar retirar um livro em nome de outra conta.

Reenviar e-mail e senha em toda operação ampliaria a exposição da credencial
de longa duração. Precisamos de uma credencial curta, limitada e verificável:

```text
e-mail + senha -> login -> access token curto
                             |
                             v
Authorization: Bearer <token> -> identidade da requisição
```

## Por que isso importa

Autenticação não é apenas verificar uma senha. A API precisa ligar cada
ação posterior a um sujeito que o servidor reconheça. Se o corpo da própria
requisição escolhe esse sujeito, o identificador é somente dado não confiável.

Um access token reduz a frequência com que a senha circula, mas passa a ser uma
credencial por si só. Quem o obtiver pode usá-lo até a expiração. Por isso esta
aula escolhe 15 minutos, não dias, e não promete logout instantâneo para um JWT
autocontido.

!!! resource "Referências normativas e oficiais"
    O [JWT Best Current Practices, RFC 8725](https://www.rfc-editor.org/info/rfc8725/)
    exige que a aplicação fixe os algoritmos aceitos e recomenda contexto e
    tipos mutuamente exclusivos. A
    [documentação do PyJWT](https://pyjwt.readthedocs.io/en/latest/usage.html)
    mostra validação de expiração, issuer, audience e claims obrigatórias. O
    [tutorial oficial do FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
    demonstra o transporte Bearer e o uso de `sub` como sujeito.

## O conceito

JWT é um formato de token. O access token desta aula é um JWT assinado:

```text
base64url(header).base64url(payload).base64url(signature)
```

Header e payload são codificados, não criptografados. Qualquer portador consegue
ler as claims. A assinatura detecta alteração e prova que uma parte com a chave
correta produziu o valor; ela não oferece confidencialidade.

!!! correction "Assinado não significa secreto"
    Nunca coloque senha, hash de senha, documento pessoal ou outro segredo no
    payload. O token viaja como um cartão de identificação legível com um selo
    inviolável, não como um cofre.

### Um perfil de access token, não qualquer JWT

O checkpoint define um único perfil:

| Parte | Valor | Pergunta respondida |
|---|---|---|
| `alg` | `HS256` | Como a assinatura é verificada? |
| `typ` | `at+jwt` | Que tipo de JWT é este? |
| `iss` | `urn:library-api` | Quem emitiu? |
| `aud` | `library-api` | Para qual destinatário? |
| `sub` | ID do usuário como string | Quem é o sujeito? |
| `iat` | instante de emissão | Quando nasceu? |
| `nbf` | instante inicial de validade | Desde quando pode ser usado? |
| `exp` | emissão + 15 minutos | Quando deixa de valer? |
| `jti` | UUID aleatório | Qual é a identidade do token? |
| `token_type` | `access` | Qual fluxo pode consumi-lo? |

`jti` apenas identifica este token. Não existe blocklist nesta etapa e seu
valor, sozinho, não impede replay. Ele prepara rastreabilidade e a separação
do refresh token que virá depois.

### O algoritmo aceito vem da aplicação

O token carrega `alg` no header, mas esse valor não escolhe a política:

```python
jwt.decode(
    token,
    secret,
    algorithms=["HS256"],
    audience=settings.jwt_audience,
    issuer=settings.jwt_issuer,
    options={"require": REQUIRED_CLAIMS, "strict_aud": True},
)
```

A lista é fixa no código. Um token que declare `HS384`, `none` ou qualquer
outro algoritmo é recusado mesmo que o cliente o tenha montado corretamente.

### A chave de assinatura é configuração privada

HS256 usa a mesma chave para assinar e verificar. A Library API exige pelo
menos 32 caracteres e documenta a geração de 256 bits aleatórios:

```bash
openssl rand -hex 32
```

O repositório contém somente uma chave didática de desenvolvimento. `Settings`
recusa essa chave quando `environment="production"`; o deploy deve fornecer
`LIBRARY_JWT_SECRET_KEY`. O algoritmo não é configurável por ambiente, pois
trocar política criptográfica não é a mesma coisa que trocar segredo.

## Modelo mental

!!! mental-model "O token é uma afirmação assinada, validada dentro de um contexto"
    Verificar apenas a assinatura responde "foi produzido com esta chave".
    A API ainda precisa confirmar "foi emitido por quem aceito, para mim, no
    intervalo correto, com o tipo e as claims que este fluxo exige".

    ```text
    assinatura correta
          + alg permitido
          + typ/token_type de access
          + iss esperado
          + aud esperada
          + nbf <= agora < exp
          + sub e jti bem formados
          = identidade criptograficamente aceitável
    ```

O `sub` ainda não garante que a conta permaneça ativa. Ao retirar um livro, o
service consulta o usuário dentro da mesma transação que protege as regras do
empréstimo. Conta ausente ou inativa invalida a credencial para essa operação.

## Exemplo mínimo

O exemplo abaixo isola apenas a ideia. Ele **não representa todo o estado atual
do projeto**, que também valida issuer, audience, tipo, datas e formatos:

```python
from datetime import UTC, datetime, timedelta

import jwt


def create_token(user_id: int, secret: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=15)},
        secret,
        algorithm="HS256",
    )


def read_subject(token: str, secret: str) -> str:
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    return payload["sub"]
```

O ponto essencial é a assimetria de confiança: `sub` no JSON do cliente não
tem assinatura; `sub` extraído depois da validação do token tem.

## Aplicando ao projeto

### 1. Login emite somente access token

O sucesso de `POST /auth/login` muda de `204` para `200`:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

Não há `refresh_token` escondido nessa resposta. A próxima aula precisará
modelar persistência, rotação, cookie e reutilização antes de emitir um.

### 2. Uma dependência valida o Bearer token

`HTTPBearer(auto_error=False)` publica o esquema de segurança no OpenAPI. A
dependência converte ausência, formato inválido, assinatura errada, expiração
ou claim incompatível na mesma fronteira:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer
Content-Type: application/json

{"detail":"Credencial de acesso inválida"}
```

Ela retorna uma `AuthenticatedIdentity` pequena, não um modelo ORM carregado.
Assim, a consulta do usuário acontece dentro da transação do caso de uso, sem
abrir implicitamente outra transação na mesma `AsyncSession` antes de
`session.begin()`.

### 3. O comando deixa de escolher a identidade

Antes:

```json
{
  "user_id": 7,
  "book_id": 2,
  "due_at": "2030-09-01T18:00:00Z"
}
```

Depois:

```http
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "book_id": 2,
  "due_at": "2030-09-01T18:00:00Z"
}
```

`LoanCreate` usa `extra="forbid"`; tentar recolocar `user_id` produz `422`.
O `Loan.user_id` gravado vem exclusivamente de `identity.user_id`.

## Antes e depois

| Aspecto | M06/A01 | M06/A02 |
|---|---|---|
| Login válido | `204` vazio | `200` com access token |
| Identidade seguinte | inexistente | Bearer JWT validado |
| Usuário do empréstimo | escolhido no JSON | derivado de `sub` |
| Algoritmo | não se aplica | `HS256` fixo |
| Validade | não se aplica | 15 minutos |
| Conta atual | consultada no login | revalidada no caso de uso |
| Migração | revisão `0002` | nenhuma mudança de esquema |

## Como testar

No checkpoint:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Os testes comprovam:

- header `alg=HS256` e `typ=at+jwt`;
- presença e valores de todas as claims obrigatórias;
- duração exata de 15 minutos e `jti` UUID;
- rejeição de expiração, assinatura, issuer, audience, tipo e algoritmo;
- uma resposta `401` genérica com `WWW-Authenticate: Bearer`;
- ausência de refresh token no contrato;
- remoção de `user_id` da entrada e uso do sujeito assinado;
- preservação da transação e da concorrência dos empréstimos;
- esquema Bearer e segurança da operação publicados no OpenAPI.

O teste opcional de PostgreSQL executa migrações, login, duas retiradas
concorrentes autenticadas e todo o ciclo de devolução:

```bash
docker compose up -d --wait
LIBRARY_TEST_POSTGRES=1 pytest -q tests/test_postgres_integration.py
docker compose down -v
```

## Exercícios

<details markdown="1">
<summary>Exercício guiado — inspecione sem confiar</summary>

Separe um JWT nas três partes, decodifique header e payload em uma ferramenta
local e confirme que `sub`, `iss` e `aud` são legíveis. Depois altere um caractere
do payload e observe a validação recusar a assinatura.

</details>

<details markdown="1">
<summary>Teste seu entendimento — assinatura correta basta?</summary>

Explique por que um token assinado com a chave correta, mas destinado a outra
audience ou marcado como refresh token, não deve ser aceito por `POST /loans`.

</details>

<details markdown="1">
<summary>Desafio — rota de identidade atual</summary>

Desenhe `GET /users/me` usando `CurrentIdentity`. Decida em qual fronteira o
usuário deve ser consultado e como responder quando a conta foi desativada
depois da emissão. Não exponha o token na resposta nem aceite ID por query.

</details>

## Checkpoint

Você concluiu a etapa quando consegue:

- diferenciar codificação, assinatura e criptografia;
- explicar por que algoritmo, issuer, audience e tipo são validados;
- manter uma chave de desenvolvimento fora de produção;
- emitir um token curto sem antecipar refresh token;
- transformar Bearer token em identidade da requisição;
- impedir o cliente de escolher `user_id` ao retirar um livro;
- distinguir `401` de autenticação inválida do futuro `403` de autorização;
- provar o fluxo contra PostgreSQL sem mudar o esquema.

O estado executável está em
`reference/checkpoints/module-06/lesson-02/`.

## Próximo problema

Quinze minutos limitam o dano de um access token roubado, mas exigiriam novo
login frequente. Na M06/A03, a Library API ganhará sessões renováveis com
refresh token rotativo, digest persistido, detecção de reutilização e transporte
em cookie analisado junto das defesas contra CSRF e XSS.
