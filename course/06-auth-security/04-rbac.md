# Autorização explícita com papéis

> **Origem, reorganização e correção:** esta aula adapta *Implementing RBAC
> Systems* à Library API. A fonte propõe a associação muitos-para-muitos entre
> usuários e papéis e uma dependência declarativa, mas recomenda copiar os
> papéis para o JWT para evitar consultas. Aqui o access token continua sendo
> apenas prova de identidade: atribuições persistidas são consultadas em cada
> operação protegida, para que uma remoção tenha efeito imediato. Também
> separamos papel global de propriedade de um recurso.

A M06/A03 consegue responder **quem** apresentou a requisição. Isso ainda não
responde se essa pessoa pode cadastrar livros, listar todas as contas ou
registrar uma devolução.

## O problema

!!! problem "Um token válido não é permissão para tudo"
    Qualquer usuário cadastrado consegue obter um access token legítimo. Se
    apenas `get_current_identity` for aplicado a uma rota administrativa, um
    membro comum e uma pessoa bibliotecária recebem exatamente o mesmo acesso.

O extremo oposto também falha. Codificar `if user_id == 1` espalharia exceções
por routers, não explicaria qual função organizacional está sendo exercida e
seria difícil de revisar.

Precisamos de uma decisão explícita depois da autenticação:

```text
requisição
    |
    v
access token íntegro e válido? -- não --> 401 Unauthorized
    |
   sim
    |
    v
conta atual existe e está ativa? -- não --> 401 Unauthorized
    |
   sim
    |
    v
papel ou propriedade permite a ação? -- não --> 403 Forbidden
    |
   sim
    v
executar o caso de uso
```

## Por que isso importa

Uma autorização omitida em uma única rota pode expor dados ou permitir uma
mudança indevida. O cliente não é a fronteira de segurança: esconder um botão
no frontend não impede uma chamada HTTP construída manualmente.

!!! resource "Referências atuais"
    A [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
    recomenda menor privilégio, negação por padrão e validação de permissão em
    toda requisição. O
    [projeto RBAC do NIST](https://csrc.nist.gov/Projects/Role-Based-Access-Control)
    formaliza usuários, papéis, permissões, operações e objetos, além das
    relações de atribuição entre eles.

RBAC reduz repetição quando uma função estável da organização reúne várias
permissões. Ele não substitui toda regra contextual. “Bibliotecário pode
administrar o acervo” é papel; “membro pode consultar o próprio perfil” é uma
relação entre sujeito e objeto.

## O conceito

### Autenticação e autorização não são sinônimos

| Pergunta | Resultado de falha | Exemplo |
|---|---:|---|
| A credencial prova uma identidade atual? | `401` | token ausente, expirado, conta removida ou inativa |
| A identidade pode executar esta operação? | `403` | membro tenta cadastrar um livro |
| O recurso existe? | `404` | livro ou empréstimo inexistente depois da autorização |
| O estado permite a transição? | `409` | devolver empréstimo já encerrado |

O `WWW-Authenticate: Bearer` acompanha `401`, pois o problema está na
credencial. Ele não acompanha `403`: autenticar novamente com a mesma conta não
cria o papel que falta.

### Um usuário pode exercer mais de um papel

Uma coluna `users.role` permitiria somente um valor. A Library API usa uma
relação muitos-para-muitos normalizada:

```text
users                 user_roles                 roles
-----                 ----------                 -----
id <----------------- user_id
                      role_name ----------------> name
                                               member
                                               librarian
```

`user_roles` possui chave primária composta `(user_id, role_name)`. A mesma
atribuição não pode ser repetida, uma conta pode acumular papéis e cada nome
precisa existir no catálogo `roles`.

A revisão `0004_role_assignments`:

1. cria `roles` e `user_roles`;
2. cadastra os papéis conhecidos `member` e `librarian`;
3. atribui `member` a todos os usuários anteriores;
4. deixa a elevação a `librarian` como operação administrativa de implantação,
   não como endpoint público capaz de elevar a própria conta.

Novos cadastros já incluem `UserRole(role_name="member")` na mesma confirmação
que cria o usuário. Não existe janela com uma identidade local sem seu papel
básico.

### O JWT não é a fonte atual dos papéis

A fonte original inclui `roles` no payload para tornar a autorização
autocontida. Isso economiza uma consulta, mas cria uma janela de obsolescência:

```text
t0: login emite JWT com roles=["librarian"]
t1: administrador remove librarian no banco
t2: JWT ainda vale por 14 minutos
t3: se a claim for autoritativa, a permissão removida continua funcionando
```

O checkpoint mantém o JWT da M06/A02 sem papéis. `sub` identifica o sujeito;
`AuthorizationRepository` lê a conta e todas as atribuições atuais. O custo de
uma consulta explícita compra revogação imediata e uma única fonte de verdade.

!!! correction "Claim assinada pode estar correta e ainda estar velha"
    A assinatura prova que o emissor produziu o conteúdo e que ele não foi
    alterado. Ela não prova que uma decisão mutável permanece verdadeira.
    Cache de autorização exigiria política de invalidação e tolerância a
    obsolescência próprias; não é antecipado nesta aula.

## Modelo mental

!!! mental-model "O token é o crachá; a escala atual diz onde ele abre"
    O crachá identifica a pessoa por pouco tempo. A escala persistida registra
    a função que ela exerce agora. Um crachá legítimo não mantém uma porta
    aberta depois que a função foi removida da escala.

`Principal` é a fotografia pequena produzida para uma requisição:

```python
@dataclass(frozen=True, slots=True)
class Principal:
    user_id: int
    roles: frozenset[str]

    def has_role(self, role: str) -> bool:
        return role in self.roles
```

Ele não é o modelo ORM inteiro e não é serializado para o cliente.

## Exemplo mínimo

O padrão declarativo encadeia identidade, estado persistido e papel:

```python
async def get_current_principal(
    identity: CurrentIdentity,
    session: DatabaseSession,
) -> Principal:
    principal = await AuthorizationRepository(session).find_active_principal(
        identity.user_id
    )
    if principal is None:
        raise invalid_access_credential()
    return principal


async def require_librarian(principal: CurrentPrincipal) -> Principal:
    if not principal.has_role("librarian"):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    return principal
```

Uma rota recebe `LibrarianPrincipal` e publica automaticamente o esquema
Bearer no OpenAPI:

```python
@router.post("")
async def create_book(
    payload: BookCreate,
    session: DatabaseSession,
    _librarian: LibrarianPrincipal,
) -> BookResponse:
    ...
```

Esse exemplo representa o estado atual para CRUDs simples. Ele consulta a
autorização na mesma sessão que a rota depois confirma.

## Aplicando ao projeto

### Matriz explícita de permissões

| Operação | Regra |
|---|---|
| saúde, configuração pública, cadastro e login | pública |
| listar e consultar livros | pública |
| retirar livro | papel atual `member` |
| consultar `/users/{id}` | próprio usuário **ou** `librarian` |
| criar, substituir ou remover livro | `librarian` |
| listar todos os usuários | `librarian` |
| listar todos os empréstimos | `librarian` |
| registrar devolução | `librarian` |

Rotas novas devem nascer negadas até que uma regra justifique sua abertura.
Essa matriz é pequena o bastante para revisão e os testes protegem cada tipo
de decisão.

### Propriedade continua separada de papel

O detalhe de usuário não inventa um papel `self`:

```python
if user_id != principal.user_id and not principal.has_role("librarian"):
    raise insufficient_permission()
```

O membro consulta o próprio histórico. Para consultar outro usuário, precisa
do papel global. Em domínios com relações mais ricas — autor de um documento,
membro de uma equipe, titular de uma conta — essas regras podem evoluir para
ReBAC ou ABAC sem fingir que todo contexto é um papel.

### Autorização dentro da transação composta

`POST /loans` e `POST /loans/{id}/return` já possuem uma fronteira
`session.begin()`. Fazer a dependência consultar a mesma `AsyncSession` antes
dessa fronteira iniciaria uma transação implícita e entraria em conflito com a
transação explícita.

Por isso esses services consultam `AuthorizationRepository` **dentro** da
transação existente, antes de bloquear ou alterar o recurso:

```text
BEGIN
  consultar conta + papéis atuais
  exigir member ou librarian
  SELECT recurso FOR UPDATE
  validar estado
  escrever
COMMIT
```

Não é uma segunda política. É a mesma fonte de autorização posicionada na
fronteira atômica correta.

### Correção da execução CPU-bound no runtime aprovado

M06/A01 deslocou Argon2id para uma worker thread. Durante a validação do
checkpoint atual com Python 3.14.6 e AnyIO 4.14.2, a ponte anterior não
propagou de volta a conclusão do trabalho nesse ambiente. O estado atual isola
hash e verificação em `run_password_operation`, que usa um
`ThreadPoolExecutor` limitado a quatro workers e aguarda o `Future` sem executar
Argon2id no event loop.

Essa correção não muda o conceito nem os parâmetros do hash. Um teste comprova
que a operação roda em uma thread `library-password`, e os testes HTTP continuam
executando Argon2id real.

## Antes e depois

| Antes da M06/A04 | Depois da M06/A04 |
|---|---|
| token válido bastava para a retirada | retirada também exige `member` atual |
| administração do acervo era pública | escrita de livros exige `librarian` |
| usuários e empréstimos podiam ser listados publicamente | listagens administrativas exigem `librarian` |
| detalhe de usuário não distinguia proprietário | próprio usuário ou `librarian` |
| devolver não exigia identidade | devolução exige `librarian` dentro da transação |
| não havia `403` de domínio | `401` e `403` possuem significados distintos |
| schema terminava em `0003` | `0004` cria papéis, atribuições e backfill |

## Como testar

O checkpoint verifica:

- metadata, DDL, chaves estrangeiras e PK composta de `user_roles`;
- upgrade, downgrade e uma única head Alembic;
- cadastro novo com atribuição `member`;
- `401` sem token, com usuário ausente ou inativo;
- `403` para identidade válida sem o papel exigido;
- ausência de `WWW-Authenticate` no `403`;
- o mesmo JWT aceito como `librarian` e recusado após a remoção persistida;
- uma claim extra `roles=["librarian"]` incapaz de sobrepor o banco;
- propriedade do próprio perfil separada do papel global;
- papéis verificados dentro das transações de retirada e devolução;
- contratos Bearer, `401` e `403` publicados no OpenAPI;
- executor CPU-bound fora da thread do event loop;
- ciclo completo contra PostgreSQL real.

## Exercícios

Implemente uma rota `GET /users/me` no seu projeto manual.

Requisitos:

1. não receba `user_id` no path, query ou body;
2. derive a conta do Bearer token;
3. consulte o estado atual no banco;
4. retorne `401` se a conta não existir ou estiver inativa;
5. reutilize o schema de detalhe sem duplicar a regra de propriedade;
6. teste que o identificador de outro usuário enviado como query extra não
   altera a resposta.

<details markdown="1">
<summary>Checkpoint de raciocínio</summary>

A rota `/users/me` precisa do papel `member`?

Não necessariamente. O requisito essencial é identidade atual e propriedade:
o sujeito só acessa o próprio objeto. Exigir `member` também é coerente se a
política declarar que toda conta ativa deve possuir esse papel, mas a decisão
precisa ser explícita e testada. Não crie um papel apenas para substituir a
comparação de propriedade.

</details>

## Checkpoint

Use `reference/checkpoints/module-06/lesson-04/` como solução completa. Compare
somente em leitura com sua área manual e confira:

```bash
pytest -q
alembic upgrade head
alembic downgrade 0003_refresh_token_rotation
alembic upgrade head
```

O checkpoint correto deixa explícito:

- quem autentica;
- onde o estado atual de papéis é lido;
- qual operação exige qual regra;
- quando `401`, `403`, `404` e `409` são usados;
- por que autorização transacional não abre uma segunda fronteira.

## Próximo problema

A Library API agora controla identidades locais. Organizações frequentemente
querem aceitar uma identidade mantida por outro provedor sem receber a senha
desse provedor. “Entrar com Google” não é apenas chamar uma rota OAuth 2.0: a
próxima aula usará OpenID Connect, Authorization Code, `state`, `nonce`, issuer,
audience e assinatura, vinculando a identidade externa por `(issuer, subject)`.
