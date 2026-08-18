# Sessões renováveis sob um navegador hostil

> **Origem, integração e correção:** esta aula combina *Secure Refresh Token
> Management* com *Preventing XSS and CSRF Attacks*. A primeira fonte ensina
> rotação e detecção de reutilização, mas aceita token bruto no banco apenas
> por clareza; aqui persistimos somente digest. A segunda usa exemplos
> Flask/Jinja e apresenta `SameSite` como defesa principal; na Library API,
> analisamos o navegador React/FastAPI e combinamos cookie restrito, header não
> simples, allowlist CORS e validação de `Origin`.

O access token da M06/A02 expira em 15 minutos. Essa janela curta limita o uso
de uma credencial roubada, mas cria outro problema: sem renovação, uma pessoa
precisaria reenviar e-mail e senha quatro vezes por hora.

## O problema

!!! problem "Conveniência longa pode recriar uma credencial longa"
    Um refresh token estático válido por sete dias permite obter novos access
    tokens durante sete dias. Se for copiado, trocar apenas o access token a
    cada 15 minutos não contém o invasor.

Guardar o refresh token em `localStorage` facilitaria o uso pelo frontend, mas
também permitiria que um XSS o extraísse para uso fora do navegador. Colocá-lo
em cookie `HttpOnly` reduz essa exposição, porém faz o browser enviá-lo
automaticamente e abre a pergunta de CSRF.

O objetivo é equilibrar três fronteiras:

```text
renovar sem reenviar senha
        +
um token bruto roubado não pode ser reutilizado silenciosamente
        +
o navegador não pode enviar o cookie em uma operação forjada
```

## Por que isso importa

Refresh token é uma credencial de alto valor: ele não chama diretamente as
rotas de domínio, mas fabrica novas credenciais de acesso. Sua duração maior
exige estado no servidor, ao contrário do access JWT autocontido.

A rotação também transforma uma falha silenciosa em sinal. Depois que `R1` é
usado, somente `R2` deve continuar. Uma nova apresentação de `R1` significa
retry inseguro, cópia ou disputa entre cliente legítimo e invasor. Não sabemos
qual lado usou primeiro; por isso toda a família é revogada.

!!! resource "Referências atuais"
    O [OAuth 2.0 Security Best Current Practice, RFC 9700](https://www.rfc-editor.org/info/rfc9700/)
    exige, para clientes públicos, refresh token vinculado ao emissor ou
    rotação com retenção do relacionamento para detectar replay. A
    [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
    recomenda headers customizados para APIs e trata `SameSite` como defesa em
    profundidade. A
    [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
    esclarece que `HttpOnly` impede leitura pelo JavaScript, mas não impede um
    XSS de fazer requisições no navegador.

## O conceito

### Refresh opaco, access estruturado

O access token continua sendo JWT porque diferentes requisições precisam
validar suas claims sem consultar uma sessão. O refresh token tem outro uso:
identificar um registro de uso único no servidor. Ele pode ser opaco:

```text
access:  header.payload.signature   -> claims verificadas
refresh: rt_<32 bytes aleatórios>   -> SHA-256 -> busca no banco
```

SHA-256 seria inadequado para senha humana, mas é apropriado para um valor
aleatório com 256 bits de entropia. Não há dicionário viável de candidatos. O
banco recebe somente 64 caracteres hexadecimais; uma leitura indevida não
entrega cookies utilizáveis.

!!! correction "Uma tabela de tokens válidos não é uma blocklist"
    A fonte chama o modelo de `TokenBlocklist`, embora ele registre tokens
    ativos e revogados. O checkpoint usa `refresh_tokens`: cada linha descreve
    um elo de uma família, sem nome contraditório.

### O estado de uma família

```text
família F

R1: used_at=t1, replaced_by=R2
                       |
                       v
R2: used_at=t2, replaced_by=R3
                       |
                       v
R3: ativo até expires_at absoluto
```

Cada linha de `refresh_tokens` possui:

| Campo | Função |
|---|---|
| `id` | UUID interno do elo |
| `family_id` | agrupa uma sessão iniciada por um login |
| `user_id` | vincula a família à conta |
| `token_digest` | localiza o valor bruto sem armazená-lo |
| `created_at` | instante de criação do elo |
| `expires_at` | limite absoluto herdado do primeiro elo |
| `used_at` | prova que o elo já foi consumido |
| `revoked_at` | encerra o elo ou a família |
| `replaced_by_id` | retém a relação exigida para rotação |

A rotação não estende indefinidamente a sessão. Todos os substitutos
herdam a expiração de sete dias definida no login. Essa é uma validade
absoluta, não uma janela deslizante eterna.

### Rotação é uma transação

O service executa:

```text
BEGIN
  SELECT token_digest = hash(cookie) FOR UPDATE
  validar estado, expiração e usuário atual
  INSERT substituto
  UPDATE anterior SET used_at, replaced_by_id
COMMIT
```

O lock serializa duas tentativas com o mesmo token. A primeira insere o
substituto e consome o anterior. A segunda acorda, encontra `used_at` e revoga
todos os elos da família antes de responder `401`.

Dois `flush()` explícitos preservam a FK autorreferente: o substituto precisa
existir no banco antes de `replaced_by_id` apontar para ele. Ambos acontecem na
mesma transação; não existe commit intermediário.

## Modelo mental

!!! mental-model "Access token é um crachá curto; refresh token é um canhoto de troca"
    O crachá circula nas operações e expira logo. O canhoto fica guardado pelo
    navegador, só pode ser trocado uma vez e deixa um rastro no servidor. Se
    alguém apresenta um canhoto já carimbado, toda aquela sequência de trocas é
    encerrada.

    ```text
    senha -> login -> access A1 + cookie R1
    R1 -> refresh -> access A2 + cookie R2
    R1 novamente -> replay -> revoga família F
    R2 depois disso -> 401
    ```

Revogar a família não apaga access tokens já emitidos. A1 ou A2 ainda podem
valer até completar seus 15 minutos. Revogação instantânea exigiria consulta a
estado, token version, blocklist ou outra decisão que não faz parte desta aula.

## Exemplo mínimo

Este exemplo mostra somente o digest. Ele **não representa o estado completo
do projeto**, que também usa família, lock, transação e cookie:

```python
from hashlib import sha256
import secrets


def issue_refresh_token() -> tuple[str, str]:
    raw = "rt_" + secrets.token_urlsafe(32)
    digest = sha256(raw.encode("utf-8")).hexdigest()
    return raw, digest
```

O valor `raw` atravessa somente a resposta `Set-Cookie`. O `digest` é o valor
persistido e consultado.

## Aplicando ao projeto

### 1. Login inicia a família

`POST /auth/login` continua devolvendo apenas o access token no JSON:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

A resposta também possui:

```http
Set-Cookie: library_refresh=rt_...; Max-Age=604800; Path=/auth;
  HttpOnly; SameSite=strict
```

Em produção, `Secure` é sempre aplicado. Em desenvolvimento HTTP ele é
omitido para que o laboratório local funcione. Não há atributo `Domain`, e
`Path=/auth` evita enviar a credencial a livros, usuários e empréstimos.

### 2. Refresh exige cookie e prova contra CSRF

```http
POST /auth/refresh
Cookie: library_refresh=rt_...
X-CSRF-Protection: 1
```

O header customizado torna a chamada não simples no navegador. Uma origem
diferente precisa passar pelo preflight CORS, cuja allowlist é explícita. Se o
browser enviar `Origin`, a dependência exige a origem da própria API ou uma
origem nessa lista. Clientes não navegador podem omitir `Origin`, mas ainda
precisam do header.

Ausência de cookie, digest desconhecido, expiração, revogação, conta inativa
ou replay produzem a mesma resposta:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer
Set-Cookie: library_refresh=""; Max-Age=0; Path=/auth; ...

{"detail":"Sessão renovável inválida"}
```

Falha da defesa CSRF usa `403`, pois a sessão nem chega a ser processada.

### 3. Logout é idempotente

`POST /auth/logout` exige a mesma defesa CSRF, revoga a família quando reconhece
o cookie, sempre o remove e responde `204`. Cookie ausente ou desconhecido não
revela se uma sessão existia.

### 4. XSS e CSRF não são a mesma ameaça

| Ameaça | O que o atacante explora | Defesa desta etapa |
|---|---|---|
| CSRF | envio automático do cookie por outro site | `SameSite=Strict`, header customizado, CORS e `Origin` |
| roubo por XSS | leitura do token por script injetado | refresh cookie `HttpOnly`; access token deve ficar em memória |
| ação por XSS | script executa dentro da origem confiável | não resolvida por cookie ou CSRF; exige prevenir XSS |

`HttpOnly` limita extração, mas o navegador ainda anexa o cookie a uma chamada
feita por um XSS na aplicação confiável. O script também consegue adicionar o
header CSRF. Prevenção de XSS depende de tratar dados como dados, fazer encoding
por contexto, evitar sinks inseguros e sanitizar HTML quando ele for realmente
permitido. Uma CSP pode complementar, mas a API não inventa uma política que
quebraria Swagger/ReDoc nem controla o build do frontend.

!!! warning "SameSite é site, não origin"
    Portas diferentes em `localhost` continuam same-site. Subdomínios também
    podem ser same-site, embora sejam origins diferentes. Esta configuração
    presume frontend same-site. Um frontend realmente cross-site exigiria
    `SameSite=None; Secure` e uma reavaliação explícita do modelo de ameaça.

## Antes e depois

| Aspecto | M06/A02 | M06/A03 |
|---|---|---|
| Access token | JWT de 15 minutos | preservado |
| Refresh token | inexistente | opaco, uso único e cookie `HttpOnly` |
| Estado de sessão | nenhum | digest, família, uso, revogação e substituição |
| Expiração | novo login após 15 min | família absoluta de sete dias |
| Replay | não se aplica | detecta e revoga a família |
| CSRF | access em header não automático | cookie protegido por camadas |
| Logout | inexistente | `204`, revoga família e limpa cookie |
| Esquema | revisão `0002` | revisão `0003` cria `refresh_tokens` |

## Como testar

No checkpoint:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Os testes comprovam:

- aleatoriedade, prefixo e digest do refresh token;
- ausência do valor bruto no banco e no JSON;
- atributos `HttpOnly`, `SameSite`, `Path`, `Max-Age` e `Secure` em produção;
- grafo Alembic `0001 -> 0002 -> 0003` nas duas direções;
- constraints, índices e FK autorreferente;
- rotação com validade absoluta e dois flushes ordenados;
- revogação da família depois de reutilização;
- recusa de cookie ausente, expirado, revogado ou ligado a conta inativa;
- header CSRF ausente, incorreto e `Origin` fora da allowlist;
- logout idempotente e remoção do cookie;
- preservação de todos os contratos anteriores.

O teste PostgreSQL cria o esquema, executa duas rotações simultâneas com o
mesmo token, confirma uma resposta `200` e uma `401`, prova que o substituto foi
revogado e percorre login, empréstimo e logout:

```bash
docker compose up -d --wait
LIBRARY_TEST_POSTGRES=1 pytest -q tests/test_postgres_integration.py
docker compose down -v
```

## Exercícios

<details markdown="1">
<summary>Exercício guiado — siga uma família</summary>

Desenhe os estados de R1, R2 e R3 depois de duas rotações. Em seguida,
apresente R1 novamente e marque quais linhas recebem `revoked_at`.

</details>

<details markdown="1">
<summary>Teste seu entendimento — por que SHA-256 agora?</summary>

Compare uma senha de 12 caracteres escolhida por pessoa com 32 bytes gerados
por `secrets`. Explique por que Argon2id é necessário para a primeira e um digest
rápido é adequado para localizar o segundo.

</details>

<details markdown="1">
<summary>Desafio — falha de rede depois da rotação</summary>

O servidor confirma R2, mas a resposta se perde e o cliente repete R1. Explique
por que a família é revogada e proponha, sem implementar, como uma pequena
janela de idempotência mudaria segurança, estado e complexidade.

</details>

## Checkpoint

Você concluiu a etapa quando consegue:

- justificar estado no servidor para refresh e statelessness para access;
- explicar por que o banco recebe digest, não o valor bruto;
- rotacionar um elo atomicamente e reter sua relação;
- detectar replay sob concorrência e revogar a família;
- limitar a sessão por expiração absoluta;
- configurar cookie com escopo e flags coerentes por ambiente;
- distinguir CSRF, roubo por XSS e ação por XSS;
- explicar por que logout não invalida imediatamente um access JWT;
- demonstrar upgrade, downgrade e fluxo HTTP em PostgreSQL real.

O estado executável está em
`reference/checkpoints/module-06/lesson-03/`.

## Próximo problema

Agora a API sabe quem age e consegue renovar essa identidade, mas toda pessoa
autenticada ainda é tratada da mesma forma. Na M06/A04, papéis persistidos e
dependências de autorização separarão `401` de `403`, sem transformar claims
potencialmente antigas na fonte atual de permissão.
