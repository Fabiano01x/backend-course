# Identidade local sem armazenar senhas

> **Origem, complementação e correção:** a fonte *JWT Authentication with
> Access and Refresh Tokens* começa por um `authenticate_user` que a Library API
> ainda não possui. Esta aula torna essa dependência real antes de emitir JWT.
> Preservamos a ideia de hash e verificação, mas adotamos Argon2id, migração
> compatível com usuários existentes, erro genérico, hash fictício contra
> enumeração temporal e execução fora do event loop.

A API já cadastra usuários, mas armazena apenas nome, e-mail e estado. Qualquer
cliente pode criar uma linha em `users`; nenhuma informação permite que essa
pessoa prove depois que controla a conta.

## O problema

!!! problem "Um usuário persistido ainda não é uma identidade"
    `POST /users` aceita nome e e-mail, mas não cria credencial. Implementar JWT
    agora exigiria confiar em um `user_id` informado pelo cliente ou inventar um
    `authenticate_user` sem base no banco.

Adicionar uma coluna `password` resolveria a verificação, mas criaria um risco
maior: uma leitura indevida do banco revelaria imediatamente as senhas e
possivelmente outras contas nas quais elas foram reutilizadas.

O objetivo desta aula é construir somente a primeira fronteira:

```text
cadastro: senha original -> hash lento -> banco
login:    senha candidata + hash do banco -> confere ou recusa
```

Nenhum token será emitido ainda. A próxima aula terá uma identidade verificável
sobre a qual construir o access token.

## Por que isso importa

Senha não deve ser criptografada para posterior recuperação. A aplicação só
precisa responder se uma tentativa corresponde à credencial cadastrada. Hash é
unidirecional; criptografia pressupõe uma chave capaz de recuperar o original.

Também não basta aplicar SHA-256 uma vez. Algoritmos rápidos ajudam atacantes a
testar bilhões de candidatos depois de obter hashes. Um algoritmo de senha deve
ser deliberadamente caro e ajustar CPU e memória.

!!! resource "Referências oficiais"
    A [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
    recomenda Argon2id e publica parâmetros mínimos. O
    [tutorial de segurança do FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
    usa `pwdlib`, Argon2 e um hash fictício para reduzir enumeração temporal.
    Consulte também a [referência do pwdlib](https://frankie567.github.io/pwdlib/reference/pwdlib/).

### Parâmetros são parte da política

O checkpoint registra explicitamente:

```python
Argon2Hasher(memory_cost=19_456, time_cost=2, parallelism=1)
```

São 19 MiB, duas iterações e uma via de paralelismo. O resultado codificado
guarda algoritmo, versão, parâmetros, salt e digest:

```text
$argon2id$v=19$m=19456,t=2,p=1$<salt>$<digest>
```

O salt é aleatório e gerado pela biblioteca. Duas contas com a mesma senha
produzem hashes diferentes; não criamos nem armazenamos uma coluna de salt.

## O conceito

`pwdlib` separa duas operações:

```python
encoded = password_hash.hash(password)
matches = password_hash.verify(password, encoded)
```

O primeiro argumento de `verify` continua sendo a senha original apresentada
naquela tentativa; o segundo é somente o valor codificado do banco. A senha
original não aparece em modelo ORM, log, resposta ou evento de migração.

### Um limite sem regras ornamentais

O cadastro aceita entre 12 e 128 caracteres. Não exigimos arbitrariamente uma
maiúscula, um número e um símbolo: essas regras induzem padrões previsíveis. O
limite superior contém o custo de uma entrada hostil.

A senha não é convertida para minúsculas, normalizada nem recebe `strip()`.
Espaços podem fazer parte dela. O e-mail, que funciona como identificador, é
normalizado com `strip().casefold()` antes da consulta e da persistência.

### Trabalho de CPU não bloqueia o event loop

Argon2id é propositalmente caro e CPU/memory-bound. Chamá-lo diretamente dentro
de `async def` impediria outras tasks de avançar durante o cálculo. Cadastro e
login usam `run_in_threadpool` para manter a fronteira HTTP responsiva.

Isso não remove a necessidade de rate limit, métricas e dimensionamento. Apenas
evita transformar uma operação síncrona cara em bloqueio do event loop.

## Modelo mental

!!! mental-model "O banco guarda um verificador, não um segredo recuperável"
    Pense no hash como uma fechadura construída para uma senha. A tentativa
    futura é testada nessa fechadura; ninguém precisa reconstruir a chave
    original a partir dela.

    ```text
    POST /auth/register
      password ── worker Argon2id ──> $argon2id$... ──> users.password_hash
          |                                      |
          +------ nunca chega à resposta --------+

    POST /auth/login
      email ──> SELECT user ─┐
      password ── worker ────┴─> verify ──> 204 ou 401 genérico
    ```

O endpoint conhece a senha somente durante a requisição. O modelo `User`
conhece apenas `password_hash`.

## Exemplo mínimo

Este exemplo isola a primitiva e não representa sozinho a rota nem a migração:

```python
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

passwords = PasswordHash(
    (Argon2Hasher(memory_cost=19_456, time_cost=2, parallelism=1),)
)

encoded = passwords.hash("correct horse battery staple")
assert passwords.verify("correct horse battery staple", encoded)
assert not passwords.verify("outra tentativa", encoded)
```

Não compare hashes recém-gerados: o salt faz dois resultados corretos serem
diferentes. Use sempre `verify`.

## Aplicando ao projeto

### A migração preserva contas anteriores

A revisão `0002_user_password_hash` adiciona:

```sql
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
```

A coluna começa anulável. Preencher contas existentes com uma senha comum, um
hash conhecido ou um valor aleatório fingiria que elas possuem credencial. Em
vez disso, `NULL` significa explicitamente: esta conta ainda não pode fazer
login local.

Quando recuperação de senha ou identidade social existir, essas contas poderão
ganhar um método legítimo. A reversão remove apenas a nova coluna; a baseline
continua intacta.

### Cadastro muda de fronteira

`POST /users` desaparece. Permitir criação pública de um perfil sem credencial
contradiz o problema agora visível. Seu substituto é `POST /auth/register`:

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "password": "correct horse battery staple"
}
```

O sucesso ainda devolve apenas `UserResponse`. Duplicidade continua protegida
pela constraint e vira `409`, mas a mensagem não repete o e-mail nem afirma
que aquela conta existe.

### Verificação sem enumerar contas

`POST /auth/login` compara credenciais e responde `204` no sucesso. Essa
resposta vazia é uma ponte declarada: M06/A02 manterá a rota e substituirá o
sucesso pela emissão do access token.

Todos estes casos respondem o mesmo `401 {"detail": "Credenciais inválidas"}`:

- e-mail ausente;
- senha incorreta;
- usuário inativo;
- conta anterior sem `password_hash`;
- formato de hash desconhecido.

Quando usuário ou hash não existe, a aplicação ainda verifica a senha contra
`DUMMY_PASSWORD_HASH`. Sem isso, a ausência evitaria o custo do Argon2 e poderia
ser distinguida por tempo. O objetivo não é prometer duração idêntica em toda
rede, mas remover o atalho mais evidente de enumeração.

### Nenhum JWT por antecipação

Ainda não há secret de assinatura, algoritmo JWT, claim, `Authorization` nem
dependência de usuário atual. Adicioná-los nesta aula esconderia se a base de
credenciais funciona. A única nova dependência é `pwdlib[argon2]`.

## Antes e depois

| Antes: M05/A07 | Depois: M06/A01 |
|---|---|
| `POST /users` cria perfil sem credencial | `POST /auth/register` cria identidade local |
| `users` não possui verificador | `password_hash` guarda Argon2id ou `NULL` legado |
| não existe verificação de senha | `/auth/login` diferencia apenas sucesso de falha genérica |
| senha poderia bloquear o event loop | hash e verify executam em worker thread |
| só existe baseline do banco | revisão `0002` preserva dados existentes |
| JWT dependeria de função fictícia | próxima aula parte de autenticação executável |

## Como testar

No checkpoint:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Os testes comprovam:

- Argon2id, parâmetros, salt diferente e verificação positiva/negativa;
- senha ausente do modelo de resposta e do valor persistido;
- normalização do e-mail;
- rollback e mensagem genérica em cadastro duplicado;
- mesma resposta para conta ausente, senha errada, legado e inativo;
- execução do hash fictício quando não há credencial real;
- limites de entrada antes do trabalho caro;
- grafo Alembic `0001 -> 0002`, upgrade e downgrade;
- remoção de `POST /users` e publicação dos contratos de autenticação no
  OpenAPI.

O teste opcional de PostgreSQL também executa migrações, cadastro e login:

```bash
docker compose up -d --wait
LIBRARY_TEST_POSTGRES=1 pytest -q tests/test_postgres_integration.py
docker compose down -v
```

## Exercícios

<details markdown="1">
<summary>Exercício guiado — siga a senha</summary>

Parta de `RegistrationCreate.password` e marque todos os pontos que recebem o
valor original. Confirme que `User`, `UserResponse`, Alembic e logs não precisam
dele depois de `hash_password`.

</details>

<details markdown="1">
<summary>Teste seu entendimento — por que não SHA-256?</summary>

Compare o objetivo de um checksum rápido com o de um hash de senha. Explique
por que uma função rápida é útil para integridade de arquivos e ruim para
resistir a tentativas offline.

</details>

<details markdown="1">
<summary>Desafio — atualização de parâmetros</summary>

Pesquise `verify_and_update` no `pwdlib`. Desenhe como um login futuro poderia
recalcular hashes antigos depois de uma verificação válida, sem exigir troca de
senha nem criar um segundo commit fora da regra do caso de uso.

</details>

## Checkpoint

Você concluiu a etapa quando consegue:

- distinguir hash de senha, criptografia e hash rápido;
- explicar salt, parâmetros e formato codificado do Argon2id;
- justificar por que contas legadas recebem `NULL`, não senha inventada;
- impedir que senha original atravesse o contrato de persistência ou resposta;
- evitar o atalho temporal para usuário inexistente;
- manter trabalho CPU-bound fora do event loop;
- demonstrar upgrade e downgrade da revisão `0002`.

O estado executável está em
`reference/checkpoints/module-06/lesson-01/`.

## Próximo problema

O servidor já sabe verificar uma identidade, mas o `204` do login não permite
que o cliente prove essa identidade em outra requisição. Na M06/A02, o sucesso
emitirá um access token curto, e rotas deixarão de aceitar `user_id` como prova
de quem está agindo.
