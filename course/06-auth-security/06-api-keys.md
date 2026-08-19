# Chaves de API com ciclo de vida

> **Origem, reorganização e correção:** esta aula adapta *API Key
> Authentication for Service-to-Service Communication*. A fonte distingue
> pessoas de sistemas, recomenda header, prefixo, hash e comparação segura,
> mas o exemplo executável usa uma constante global e chega a devolver a chave
> apresentada. A Library API modela identidade de máquina, menor privilégio e
> todo o ciclo de criação, uso, expiração, rotação e revogação.

Até a M06/A05, toda operação protegida começa com uma pessoa: senha ou OpenID
Connect inicia uma sessão local; o access JWT identifica um usuário; papéis e
propriedade decidem o que ele pode fazer.

Uma rotina de catálogo ou um serviço de relatórios não é uma pessoa. Inventar
um usuário, guardar sua senha e renovar sua sessão esconderia quem realmente
fez a chamada e ampliaria a superfície de ataque.

## O problema

!!! problem "Uma constante compartilhada autentica um segredo, não um cliente"
    Se todos os sistemas usam o mesmo `API_KEY`, o banco não consegue responder
    qual integração chamou, qual capacidade ela precisava, quando sua
    credencial expirava ou qual chave deve ser revogada após um vazamento.

Também não podemos armazenar o valor bruto para mostrá-lo novamente. Uma
leitura indevida do banco transformaria metadados de autenticação em
credenciais imediatamente utilizáveis.

Precisamos de uma credencial que seja simples para máquinas e ainda tenha:

- identidade própria, separada de `users`;
- segredo criptograficamente aleatório e irreversível no banco;
- permissões mínimas por escopo;
- expiração opcional e estado de uso;
- rotação e revogação isoladas;
- resposta uniforme para chave ausente, malformada, expirada ou revogada.

## Por que isso importa

Uma API key é um bearer secret: quem possui o valor consegue apresentá-lo. Ela
não prova posse por assinatura e pode ser repetida até expirar ou ser revogada.
Por isso TLS, menor privilégio e resposta rápida a vazamentos pertencem ao
contrato, não à operação futura.

```text
serviço de catálogo       Library API                 PostgreSQL
        |                      |                           |
        | X-API-Key: lka_...   |                           |
        |--------------------->| separar prefixo público   |
        |                      |-------------------------->|
        |                      | ApiKey + ApiClient atuais |
        |                      |<--------------------------|
        |                      | SHA-256 + compare_digest  |
        |                      | expiração/revogação/scope |
        |                      | registrar last_used_at    |
        | livros permitidos    |                           |
        |<---------------------|                           |
```

!!! resource "Referências atuais"
    O [OWASP Secrets Management Cheat
    Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
    descreve criação, rotação, revogação e expiração como partes do ciclo de
    vida, recomenda geração robusta, menor privilégio e capacidade de revogar
    rapidamente. O [OWASP REST Security Cheat
    Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
    exige HTTPS, recomenda revogação e alerta que API keys sozinhas não devem
    proteger recursos críticos de alto valor. Prefixos previsíveis também
    permitem criar padrões de detecção conforme a documentação de [custom
    patterns do GitHub Secret
    Scanning](https://docs.github.com/en/code-security/reference/secret-security/custom-patterns).

## O conceito

### A identidade e a credencial são entidades diferentes

`ApiClient` responde **quem é o sistema**. `ApiKey` responde **qual credencial
desse sistema foi apresentada**.

```text
ApiClient "catalog-sync"
    |
    +-- chave A: books:read, revogada
    +-- chave B: books:read, ativa até 2030-01-01
```

Separar as duas entidades permite emitir uma substituta sem renomear o cliente,
preservar histórico e desativar a identidade inteira no futuro. Nenhuma delas
possui `user_id`: chamadas de máquina não simulam ações humanas.

### O valor possui uma parte pública e outra secreta

O formato do checkpoint é:

```text
lka_<prefixo hexadecimal de 12 caracteres>_<segredo base64url de 256 bits>
```

`lka_` torna o tipo reconhecível para pessoas e secret scanners. O prefixo
aleatório não é segredo; ele seleciona uma única linha antes da comparação. O
segmento final é o bearer secret e só aparece na emissão ou rotação.

O banco guarda:

```text
prefix = 7b1b402ec719
secret_digest = SHA256(chave completa)
```

SHA-256 não seria adequado para uma senha escolhida por uma pessoa, que exige
Argon2id e custo deliberado. Aqui a entrada possui 256 bits aleatórios, portanto
não existe um dicionário humano economicamente útil. O digest permite
verificação sem tornar o segredo recuperável.

### Comparação segura continua necessária

Depois da busca pelo prefixo, a API calcula o digest do valor apresentado e
usa `secrets.compare_digest`. Quando a linha não existe, compara contra um
digest fictício do mesmo tamanho. Todos os estados inválidos recebem o mesmo
`401` e o desafio `WWW-Authenticate: ApiKey`.

Isso não torna o tempo total matematicamente idêntico — a busca no banco ainda
tem custo próprio —, mas evita comparação parcial do material sensível e não
revela na resposta se prefixo, digest ou estado falhou.

### Escopo é capacidade, não papel humano

Papéis atuais respondem o que uma pessoa pode fazer na Library API. Escopos
respondem para qual integração uma chave foi emitida:

| Escopo | Rota de máquina | Capacidade |
|---|---|---|
| `books:read` | `GET /integrations/books` | exportar o acervo |
| `loans:read` | `GET /integrations/loans` | exportar empréstimos |

Chave válida sem o escopo exigido recebe `403`. O valor não é aceito nas rotas
humanas `/books` e `/loans`; access JWT não substitui chave nas rotas
`/integrations`. Essa separação evita uma credencial ganhar poderes por
acidente.

### Estado atual decide a cada requisição

A autenticação lê a linha sob lock e verifica:

1. formato e prefixo válidos;
2. digest em tempo constante;
3. `ApiClient.active` atual;
4. ausência de `revoked_at`;
5. `expires_at` ausente ou no futuro;
6. escopo requerido pela rota.

Uma chave revogada deixa de funcionar na requisição seguinte. `last_used_at` é
atualizado na mesma transação, criando um sinal operacional mínimo. Em tráfego
muito alto, escrever a cada chamada causaria contenção; agregação assíncrona de
auditoria só deve entrar quando esse custo aparecer.

## Modelo mental

!!! mental-model "Crachá de prestador com número visível e tarja secreta"
    O cliente é a empresa prestadora; cada chave é um crachá. O prefixo é o
    número visível usado para localizar o cadastro. A tarja secreta prova que o
    portador recebeu o crachá. Os escopos abrem somente salas determinadas; a
    validade e a revogação são conferidas na catraca a cada entrada. Trocar o
    crachá não cria outra empresa.

## Exemplo mínimo

Geração e persistência são etapas diferentes:

```python
def generate_api_key() -> GeneratedApiKey:
    prefix = secrets.token_hex(6)
    secret = secrets.token_urlsafe(32)
    raw = f"lka_{prefix}_{secret}"
    return GeneratedApiKey(
        raw=raw,
        prefix=prefix,
        digest=hashlib.sha256(raw.encode("ascii")).hexdigest(),
    )
```

Somente `prefix` e `digest` entram em `ApiKey`. `raw` pertence ao contrato de
resposta da emissão e não é atributo do modelo persistente.

Na autenticação, o prefixo reduz a busca e o digest confirma o segredo:

```python
key = await repository.lock_key_by_prefix(prefix)
expected = key.secret_digest if key else "0" * 64

if key is None or not secrets.compare_digest(
    hashlib.sha256(raw.encode("ascii")).hexdigest(), expected
):
    raise invalid_api_key()
```

O exemplo omite expiração, revogação, cliente ativo e escopo apenas para isolar
a comparação. Ele não representa sozinho o estado atual do projeto.

## Aplicando ao projeto

### Revisão `0006_api_keys`

A migração adiciona:

| Tabela | Campos centrais | Responsabilidade |
|---|---|---|
| `api_clients` | `id`, `name`, `active`, `created_at` | identidade estável da integração |
| `api_keys` | prefixo, digest, escopos e datas | credencial e seu ciclo de vida |

`api_keys` possui FK para o cliente e uma autorreferência
`replaced_by_id`. Prefixo e substituta são únicos. Constraints impedem digest
ou prefixo com tamanho incorreto e datas anteriores à criação.

Os dois escopos ficam em um array JSON validado pela aplicação. Ainda não há
consulta SQL por escopo nem metadados próprios para cada capacidade; uma tabela
associativa agora adicionaria estrutura sem resolver outro problema visível.

### Administração continua humana

Somente um principal atual com papel `librarian` pode chamar:

```text
POST   /api-clients
POST   /api-clients/{client_id}/keys
POST   /api-keys/{key_id}/rotate
DELETE /api-keys/{key_id}
```

Essas rotas usam access JWT. A emissão recebe escopos e expiração opcional. A
resposta contém `api_key` uma única vez; consultas futuras, logs e OpenAPI não
expõem `secret_digest` nem permitem recuperar o valor bruto.

### Rotação é uma transação

`POST /api-keys/{id}/rotate` bloqueia a credencial anterior, cria outra com os
mesmos escopos, faz flush, liga `replaced_by_id`, marca `revoked_at` e confirma
tudo junto.

```text
lock antiga → inserir nova → revogar antiga → commit
                       falha → rollback de tudo
```

O endpoint faz troca imediata. Quando uma integração precisar de sobreposição,
o operador pode emitir uma segunda chave, instalar e testar no consumidor, e
só então revogar a primeira. O modelo permite múltiplas chaves ativas por
cliente sem antecipar um orquestrador de deploy.

### A autenticação encerra sua transação antes do domínio

A chave é bloqueada, validada e recebe `last_used_at`. Só depois do commit a
rota consulta livros ou empréstimos. Assim a leitura de domínio não mantém o
lock da credencial.

O `joinedload` entre chave e cliente usa `INNER JOIN`, pois a FK é obrigatória,
e `FOR UPDATE OF api_keys` bloqueia somente a credencial. Isso evita o erro do
PostgreSQL ao aplicar `FOR UPDATE` ao lado anulável de um `LEFT JOIN`.

### Header não substitui HTTPS nem vira query string

Clientes enviam:

```http
X-API-Key: lka_7b1b402ec719_<segredo>
```

O header não protege o tráfego; produção precisa de HTTPS. Chaves não entram em
URL, pois URLs aparecem com frequência em histórico, métricas, proxies e logs.
CORS é uma política de navegador e não protege chamadas serviço-a-serviço.

## Antes e depois

| Antes da M06/A06 | Depois da M06/A06 |
|---|---|
| somente identidades humanas | usuários e clientes de máquina separados |
| exemplo original com constante global | identidade e chaves persistidas |
| segredo recuperável/configurado | bruto mostrado uma vez; somente digest no banco |
| qualquer chave teria o mesmo poder | `books:read` e `loans:read` explícitos |
| sem vencimento individual | expiração opcional verificada por chamada |
| vazamento exigiria trocar tudo | revogação isolada e imediata |
| troca sem histórico | rotação atômica com elo de substituição |
| schema terminava em `0005` | `0006` cria clientes e credenciais |

## Como testar

O checkpoint cobre:

- formato `lka_`, 256 bits aleatórios, extração estrita do prefixo e digest;
- valor bruto diferente do armazenamento e ausente no modelo;
- emissão com escopos ordenados e expiração futura;
- resposta única contendo o segredo;
- chave ausente, malformada, incorreta, expirada ou revogada como `401`;
- cliente inativo como credencial inválida;
- identidade válida sem escopo como `403`;
- atualização de `last_used_at` após autenticação;
- exportações separadas de livros e empréstimos;
- rotação atômica, elo de substituição e rejeição imediata da antiga;
- revogação idempotente;
- OpenAPI com `MachineApiKey` separado de `AccessToken`;
- upgrade, downgrade, autogenerate limpo e ciclo HTTP em PostgreSQL real.

## Exercícios

Implemente manualmente a desativação de um cliente inteiro:

```text
DELETE /api-clients/{client_id}
```

Requisitos:

1. exigir `librarian` atual;
2. não apagar cliente, chaves ou histórico;
3. trocar `active` para falso sob lock;
4. fazer todas as chaves atuais falharem com o mesmo `401` genérico;
5. manter revogação individual idempotente;
6. testar duas desativações concorrentes;
7. documentar como reativação seria auditada antes de implementá-la.

<details markdown="1">
<summary>Checkpoint de raciocínio</summary>

Por que não devolver `403` quando o cliente está inativo?

Porque a identidade apresentada não é mais aceita como atual. `403` confirmaria
que a chave foi reconhecida e apenas perdeu permissão; a política uniforme trata
digest incorreto, expiração, revogação e cliente inativo como falha da
credencial e responde `401`.

</details>

## Checkpoint

Compare somente em leitura com
`reference/checkpoints/module-06/lesson-06/`. Execute:

```bash
pytest -q
alembic upgrade head
alembic downgrade 0005_oidc_identities
alembic upgrade head
```

Ao revisar, localize separadamente:

- formato e digest em `app/security/api_keys.py`;
- persistência e locks no repository;
- ciclo de vida no service;
- autenticação e escopo nas dependências;
- administração humana e rotas de integração;
- migração, constraints e testes contra PostgreSQL.

## Próximo problema

O Módulo 6 termina com pessoas, sessões, autorização, identidade externa e
clientes de máquina protegidos por fronteiras explícitas. O próximo módulo
tratará trabalho que não deve manter uma requisição HTTP aberta: tarefas
assíncronas, filas, repetição segura e observabilidade de processamento.
