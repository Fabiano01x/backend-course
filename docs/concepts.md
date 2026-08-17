# Registro de conceitos

Este arquivo registra o que já faz parte do estado cumulativo das aulas
concluídas.

## FastAPI

- Introduzido: Módulo 4 / aula 1.
- Estado: incorporado.
- Papel: receber requisições HTTP, validar contratos e produzir respostas.
- Regra: `app/main.py` é o ponto de composição, não um catálogo de regras de
  domínio.

## Async e await

- Introduzido: Módulo 4 / aula 1.
- Estado: incorporado.
- `async def` cria uma função coroutine; sua chamada produz uma coroutine.
- `await` suspende a task atual quando a operação aguardada precisa esperar,
  permitindo que o event loop execute outras tasks prontas.
- Correção registrada: aguardar uma coroutine diretamente não impede, por si
  só, que outras tasks executem quando ela alcança um ponto de suspensão.
- `create_task()` agenda trabalho independente; não deve envolver toda
  coroutine apenas para que `await` seja cooperativo.

## Pydantic v2

- Introduzido: Módulo 4 / aula 2.
- Estado: incorporado.
- `BookCreate`/`UserCreate` controlam entrada; `BookResponse`/`UserResponse`
  controlam saída.
- Campos extras são recusados para tornar o contrato explícito.
- A partir daqui, endpoints de criação não recebem `dict` cru.
- `StrictSchema` recusa campos extras; campos obrigatórios são anotados sem
  valor padrão e serializados com `model_dump()`.

## Contratos HTTP

- Introduzido: Módulo 4 / aula 2.
- Criação responde `201`; recurso ausente responde `404`; falhas de tipos,
  limites ou campos extras respondem `422`.
- Os modelos de entrada não aceitam identificadores nem estado controlado pelo
  servidor.
- Na aula 4, `GET /books` passa intencionalmente de um array solto para
  `BookPage`, com `items`, `total`, `limit` e `offset`.

## APIRouter

- Introduzido: Módulo 4 / aula 3.
- Estado: incorporado permanentemente.
- Rotas de livros ficam em `books.router`, usuários em `users.router` e rotas
  operacionais em `system.router`.
- Prefixos e tags comuns pertencem ao construtor de `APIRouter`.
- `app.include_router()` é o ponto explícito de montagem.
- Exceção: um exemplo mínimo pode usar `app.get()` se declarar que serve
  apenas para isolar um conceito. O projeto principal continuará com routers.

## Armazenamento em memória

- Estado: temporário e deliberadamente simples.
- Não é repository nem simula durabilidade.
- Será substituído quando SQLAlchemy e PostgreSQL forem introduzidos.

## Query parameters

- Introduzido: Módulo 4 / aula 4.
- Estado: incorporado na listagem de livros.
- `available` distingue ausência (`None`) de filtro explícito por `false`.
- `author` faz busca parcial sem diferença entre maiúsculas e minúsculas.
- `sort_by` aceita somente `id`, `title` e `author`; `order` aceita `asc` e
  `desc`.
- Valores fora do contrato respondem `422` antes do endpoint.

## Paginação limit-offset

- Introduzido: Módulo 4 / aula 4.
- Pipeline permanente: filtrar → ordenar → contar → recortar.
- `limit` aceita de 1 a 100 e `offset` deve ser maior ou igual a zero.
- `total` representa a quantidade depois dos filtros e antes do recorte.
- O limite de consistência do offset em coleções mutáveis foi declarado; cursor
  será considerado com persistência real.

## Pydantic Settings

- Introduzido: Módulo 4 / aula 5.
- `Settings` centraliza nome, versão, ambiente, debug e limites de paginação.
- O prefixo externo é `LIBRARY_`; argumentos explícitos prevalecem sobre
  variáveis do processo, que prevalecem sobre `.env` e defaults.
- `.env` é ignorado pelo Git; `.env.example` contém apenas exemplos seguros.
- Campos isolados usam `Field`; `model_validator` garante que o tamanho padrão
  não supere o máximo.
- A configuração é congelada depois de validada e uma inconsistência impede a
  inicialização.
- O objeto global `settings` é temporário e será substituído por dependência
  cacheada na aula 6.

## Configuração pública

- `GET /info` expõe somente nome, versão, ambiente e debug por meio de
  `AppInfo`.
- Variáveis de ambiente não são tratadas como cofre de segredos.
- Banco, JWT e outras configurações sem consumidor real continuam adiados.
