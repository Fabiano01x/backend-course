# Registro de conceitos

Este arquivo registra o que já faz parte do estado cumulativo. Os conceitos das
aulas 1 e 2 aparecem como **baseline do piloto**; suas aulas completas ainda não
foram produzidas.

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

## APIRouter

- Introduzido: Módulo 4 / nova aula 3.
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
