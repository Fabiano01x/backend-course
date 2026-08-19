# Login social é OpenID Connect

> **Origem, reorganização e correção:** esta aula adapta *Implementing OAuth2
> for Social Login*. A fonte ensina Authorization Code, redirect URI, `state`
> e troca do código no backend, mas chama OAuth 2.0 de autenticação, busca o
> perfil por access token e liga contas apenas por e-mail. A Library API usa
> OpenID Connect, valida um ID Token assinado e vincula a identidade pelo par
> estável `(issuer, subject)`. Também acrescentamos `nonce`, PKCE S256,
> discovery estrito e uma tentativa vinculada ao navegador.

Até a M06/A04, a Library API só reconhece uma senha criada localmente. Isso
obriga cada pessoa a manter outra credencial e obriga a aplicação a oferecer,
no futuro, recuperação, troca e políticas operacionais de senha.

Queremos aceitar uma autenticação realizada por um provedor confiável sem
receber a senha usada nesse provedor.

## O problema

!!! problem "Um access token de terceiro não diz automaticamente quem entrou"
    OAuth 2.0 delega acesso a recursos. Um access token responde “este cliente
    pode chamar determinada API”, não define por si só um contrato universal de
    identidade para a Library API.

OpenID Connect adiciona a camada de identidade sobre OAuth 2.0. Ao solicitar o
scope `openid`, o cliente recebe um **ID Token** com issuer, subject, audience,
datas e nonce. Só depois de validar esse contrato o backend possui uma
identidade externa autenticada.

Também não basta aceitar um callback que contenha `code`. Sem ligação com o
navegador que iniciou o fluxo, um atacante pode tentar injetar seu próprio
código, trocar o contexto do provedor ou provocar login CSRF.

## Por que isso importa

O fluxo atravessa três sistemas e duas credenciais diferentes:

```text
navegador             Library API             provedor OIDC
    |                       |                       |
    | GET /auth/oidc/login  |                       |
    |---------------------->|                       |
    |  cookie de tentativa  |                       |
    |<----------------------|                       |
    |                                               |
    | redirect + state + nonce + PKCE challenge     |
    |---------------------------------------------->|
    |                                               |
    | callback: code + state                        |
    |---------------------->|                       |
    |                       | code + PKCE verifier  |
    |                       |---------------------->|
    |                       | ID Token              |
    |                       |<----------------------|
    |                       | validar tudo           |
    | access JWT local + cookie refresh             |
    |<----------------------|                       |
```

O authorization code é curto e de uso único. O ID Token autentica a pessoa
para este cliente. Depois disso, a Library API emite suas próprias credenciais;
o token do provedor nunca vira autorização direta para livros e empréstimos.

!!! resource "Referências atuais"
    O [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0-18.html)
    define ID Token e a validação de `iss`, `sub`, `aud`, assinatura e `nonce`.
    O [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html)
    define metadata como `issuer`, `authorization_endpoint`, `token_endpoint`
    e `jwks_uri`. O
    [OAuth 2.0 Security Best Current Practice, RFC 9700](https://www.rfc-editor.org/info/rfc9700/)
    recomenda PKCE também para clientes web confidenciais e exige que PKCE ou
    nonce seja específico da transação e ligado ao navegador. A transformação
    S256 está definida na [RFC 7636](https://www.rfc-editor.org/info/rfc7636/).

## O conceito

### OAuth 2.0 delega; OpenID Connect autentica

| Artefato | Consumidor | Finalidade |
|---|---|---|
| authorization code | token endpoint do provedor | trocar uma autorização curta por tokens |
| access token do provedor | API do provedor | acessar recursos autorizados naquele provedor |
| ID Token | Library API, como cliente OIDC | autenticar o usuário para este `client_id` |
| access JWT local | rotas da Library API | autenticar a identidade local |
| refresh token local | `/auth/refresh` | renovar a sessão da Library API |

A API não usa access token do provedor como se fosse seu. Isso evita confundir
audiences, políticas de validade e semânticas de autorização diferentes.

### Três valores, três ameaças

`state`, `nonce` e PKCE não são nomes intercambiáveis:

- `state` correlaciona o callback com a tentativa iniciada e ajuda a impedir
  login CSRF;
- `nonce` é enviado na requisição e precisa reaparecer dentro do ID Token,
  ligando a prova de identidade à transação;
- PKCE cria um `code_verifier` secreto e envia apenas
  `BASE64URL(SHA256(verifier))` como `code_challenge`; um código interceptado
  não pode ser trocado sem o verifier.

Todos são aleatórios por tentativa. Constantes de configuração anulam sua
função.

### A tentativa pertence ao navegador

Guardar `state` em uma tabela global sem vínculo com o browser ainda permite
que uma tentativa iniciada pelo atacante seja apresentada a outra pessoa. O
checkpoint combina:

```text
query do callback: state bruto
cookie HttpOnly:   browser_secret.code_verifier
banco:             digest(browser_secret)
                   digest(state)
                   digest(nonce)
                   digest(code_verifier)
```

O cookie `library_oidc_attempt` usa:

- `HttpOnly`, para não expor browser secret e verifier ao JavaScript;
- `SameSite=Lax`, porque o callback chega por navegação superior vinda de outro
  site;
- `Path=/auth/oidc`, limitando onde ele é enviado;
- `Secure` em produção ou quando HTTPS foi declarado;
- validade de dez minutos.

Somente digests de 64 caracteres entram em `oidc_login_attempts`. O callback
precisa apresentar cookie e `state` correspondentes, bloqueia a linha com
`SELECT FOR UPDATE`, marca `used_at` e não aceita replay.

!!! mental-model "Uma retirada de bagagem com três metades"
    O navegador guarda uma parte, o callback devolve outra e o ID Token contém
    a terceira. A API só entrega a sessão quando todas apontam para a mesma
    tentativa ainda válida.

### Discovery é configuração autenticável, não redirecionamento livre

O issuer é configuração do operador, nunca um parâmetro enviado pelo cliente.
A API consulta:

```text
{issuer}/.well-known/openid-configuration
```

e exige que o `issuer` retornado seja exatamente o configurado. Authorization,
token e JWKS endpoints precisam ser HTTPS. O provider também deve declarar
RS256 para ID Tokens e PKCE S256.

Isso evita transformar `/auth/oidc/login?issuer=...` em um fetch arbitrário ou
aceitar metadata de outro emissor.

### Validar ID Token é uma sequência, não um decode conveniente

O callback só aceita o ID Token depois de verificar:

1. header `alg=RS256` fixo e `kid` presente;
2. chave RSA de assinatura encontrada uma única vez no JWKS HTTPS;
3. assinatura válida;
4. `iss` exatamente igual ao issuer configurado;
5. `aud` contendo o `client_id` da Library API;
6. `azp` igual ao cliente quando existem múltiplas audiences;
7. `exp` e `iat`, com tolerância curta de relógio;
8. `nonce` com digest igual ao da tentativa;
9. `sub` ASCII, não vazio e com no máximo 255 caracteres.

O e-mail e o nome são atributos auxiliares. Não substituem `sub`.

## Modelo mental

!!! mental-model "O provedor assina um passaporte; a API emite seu crachá"
    O ID Token é o passaporte temporário apresentado pelo issuer e válido para
    o client ID da Library API. A API confere emissor, destinatário, assinatura,
    validade e o selo específico daquela viagem (`nonce`). Depois localiza o
    registro durável por issuer/subject e entrega um crachá local. O passaporte
    externo não abre diretamente as portas do domínio.

## Exemplo mínimo

PKCE S256 é uma transformação simples, mas o verifier nunca viaja na primeira
requisição:

```python
def code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
```

A autorização contém apenas o challenge:

```text
response_type=code
client_id=library-web
redirect_uri=https://api.example/auth/oidc/callback
scope=openid email profile
state=<aleatório>
nonce=<aleatório>
code_challenge=<S256>
code_challenge_method=S256
```

O token endpoint recebe `code_verifier` pelo canal servidor-servidor, junto da
autenticação `client_secret_basic`. O client secret nunca entra na URL, cookie,
OpenAPI ou código do frontend.

## Aplicando ao projeto

### Configuração completa ou recurso desabilitado

Quatro valores precisam existir juntos:

```text
LIBRARY_OIDC_ISSUER
LIBRARY_OIDC_CLIENT_ID
LIBRARY_OIDC_CLIENT_SECRET
LIBRARY_OIDC_REDIRECT_URI
```

Configuração parcial falha no startup. Issuer sempre exige HTTPS; redirect URI
pode usar HTTP apenas em desenvolvimento/teste e precisa usar HTTPS em
produção. Sem configuração, as rotas existem no contrato, mas respondem `503`.

### Revisão `0005_oidc_identities`

A migração cria duas entidades:

| Tabela | Responsabilidade |
|---|---|
| `oidc_login_attempts` | estado curto, digests, expiração e consumo único |
| `external_identities` | vínculo durável entre `users` e `(issuer, subject)` |

`external_identities` possui unicidade composta. Uma conta local pode receber
mais de uma identidade externa no futuro, mas o mesmo sujeito de um issuer não
pode apontar para duas contas.

### Vínculo seguro não é busca por e-mail

Depois de validar o ID Token, a resolução segue esta ordem:

```text
existe (issuer, subject)?
    sim -> usar a conta já vinculada, se ativa
    não -> e-mail foi verificado pelo provedor?
             não -> 403
             sim -> e-mail já existe localmente?
                       sim -> 409; exigir vínculo autenticado explícito
                       não -> criar User externo + member + ExternalIdentity
```

!!! correction "E-mail igual não comprova que duas contas devem ser fundidas"
    Auto-link por e-mail pode entregar uma conta local ao sujeito errado se o
    provedor tiver semântica diferente de verificação, reatribuição de endereço
    ou configuração comprometida. A M06/A05 recusa a colisão. Um fluxo futuro
    de vínculo deverá exigir que a pessoa já esteja autenticada na conta local
    e confirme a nova identidade externa.

Usuários criados pelo provedor mantêm `password_hash=NULL`; isso significa
“sem credencial local”, não senha vazia. Eles recebem `member` na mesma
transação.

### O callback não segura transação durante I/O externo

O fluxo separa três fronteiras:

```text
transação 1: bloquear e consumir tentativa OIDC
fora do banco: trocar code e buscar JWKS
transação 2: resolver/criar vínculo externo
commit curto: iniciar família local de refresh token
```

Uma chamada de rede lenta não mantém locks PostgreSQL. Consumir a tentativa
antes da troca significa que uma falha exige reiniciar o login; isso é seguro e
compatível com o code de uso único.

### A sessão volta a ser local

Sucesso em `/auth/oidc/callback` produz o mesmo contrato da senha local:

- access JWT local de 15 minutos no JSON;
- refresh token opaco no cookie `library_refresh`;
- papel consultado no banco a cada operação protegida.

ID Token e tokens do provedor não são persistidos nem devolvidos.

## Antes e depois

| Antes da M06/A05 | Depois da M06/A05 |
|---|---|
| somente senha local | senha local ou provedor OIDC configurado |
| OAuth social era apenas planejamento | Authorization Code executável |
| nenhum estado de callback | tentativa curta, vinculada e de uso único |
| sem proteção contra code injection | PKCE S256 e nonce por transação |
| nenhuma chave externa validada | RS256 fixo e JWKS do issuer |
| e-mail poderia parecer identidade | vínculo durável por `(issuer, subject)` |
| colisão de e-mail sem política | `409`, sem auto-link |
| schema terminava em `0004` | `0005` cria tentativas e identidades externas |

## Como testar

O checkpoint cobre:

- configuração OIDC completa, issuer HTTPS e redirect HTTPS em produção;
- geração aleatória e armazenamento somente de digests;
- cookie `HttpOnly`, `SameSite=Lax`, path, expiração e `Secure` condicional;
- URL Authorization Code com scopes, `state`, `nonce` e PKCE S256;
- discovery com issuer exato e endpoints HTTPS;
- autenticação `client_secret_basic` no token endpoint;
- assinatura RS256 com chave selecionada por `kid` no JWKS;
- issuer, audience, `azp`, datas, subject e nonce;
- consumo único e replay recusado;
- criação de usuário externo com `member` e sem senha local;
- login posterior pelo vínculo estável, mesmo que o e-mail do provedor mude;
- e-mail não verificado recusado e colisão local sem auto-link;
- access/refresh locais e limpeza do cookie de tentativa;
- upgrade, downgrade, autogenerate limpo e tabelas em PostgreSQL real;
- contrato OpenAPI das duas rotas.

## Exercícios

Implemente no seu projeto manual um endpoint autenticado
`POST /auth/oidc/link`.

Requisitos:

1. exigir access JWT local válido e conta ativa;
2. iniciar outra tentativa OIDC ligada ao `user_id` autenticado;
3. usar `state`, `nonce`, PKCE e cookie próprios;
4. no callback, validar o ID Token antes de criar o vínculo;
5. recusar `(issuer, subject)` já ligado a outra conta;
6. não usar igualdade de e-mail como prova;
7. testar duas tentativas concorrentes e replay.

<details markdown="1">
<summary>Checkpoint de raciocínio</summary>

Por que não adicionar `user_id` à query do callback?

Porque query é entrada controlada pelo cliente. O alvo do vínculo deve vir da
tentativa curta criada enquanto a conta já estava autenticada, protegida no
banco e correlacionada pelo cookie/state. Caso contrário, trocar um número na
URL tentaria ligar a identidade a outra pessoa.

</details>

## Checkpoint

Compare somente em leitura com
`reference/checkpoints/module-06/lesson-05/`. Execute:

```bash
pytest -q
alembic upgrade head
alembic downgrade 0004_role_assignments
alembic upgrade head
```

Ao revisar, localize separadamente:

- configuração do issuer e cliente;
- segredos efêmeros da tentativa;
- cliente HTTP e validação do ID Token;
- fronteiras transacionais;
- vínculo por issuer/subject;
- emissão da sessão local.

## Próximo problema

Pessoas entram pelo navegador; integrações e rotinas automatizadas não devem
simular uma pessoa nem armazenar senha/refresh token. A próxima aula criará
chaves de API com identidade própria, prefixo público, segredo exibido uma vez,
digest, escopos, expiração opcional, rotação e revogação.
