# Progresso

Estado: aula 02 concluída

Última aula processada: 02

## Fonte

- Curso e versão confirmados: `3b30bbfd-e48e-4883-8450-8fca5452c8d1`, v3.
- Módulo 4 importado integralmente: 8 JSON, 8 Markdown e manifesto com hashes.
- As oito aulas foram analisadas e rastreadas no mapa curricular.

## Conteúdo autoral

- Ordem pedagógica do Módulo 4 definida.
- Aula piloto produzida: `course/04-fastapi/03-apirouter.md`.
- Tema contínuo inspirado no Grasp e gerador HTML responsivo concluídos.
- Manifesto de apresentação registra as oito aulas e sua proveniência.
- Aulas 1 e 2 e seus checkpoints executáveis concluídos.
- Aulas 4–8 ainda não foram escritas; aula 3 permanece como piloto.

## Conceitos incorporados

- Introduzidos na aula 1: FastAPI mínimo, endpoints GET, `async def`, coroutine,
  task, event loop e `await`.
- Correção técnica de coroutine versus task incorporada.
- Introduzidos na aula 2: schemas Pydantic v2, contratos separados de entrada e
  saída, validação estrita e respostas `201`, `404` e `422`.
- Introduzido e permanente: `APIRouter`, prefixos, tags e `include_router`.

## Arquitetura atual

- A solução atual foi preservada em `reference/pilot/module-04/lesson-03/`.
- `main.py` cria e compõe a aplicação piloto.
- Livros, usuários e saúde possuem routers separados.
- Persistência continua em memória, de forma deliberadamente temporária.
- Ambiente resolvido registrado no `requirements.lock` do piloto.
- `student/library-api/` está reservado para a implementação manual do aluno.
- O checkpoint sequencial 01 usa rotas diretas em `main.py` e dados somente de
  leitura em memória.
- O checkpoint 02 mantém rotas diretas, adiciona `schemas.py`, estado
  reinicializável e operações de criação/detalhe.

## Pendências

- Produzir as aulas em ordem, começando pela nova aula 1.
- Encerrar cada aula ou mudança relevante com testes, validação e commit.
- Nunca alterar ou incluir a área `student/` em commits do Codex.
- Manter PDF, SQLAlchemy, autenticação e Docker fora deste marco.

## Próxima etapa

Reconstruir a aula 3 a partir do checkpoint 02. Mover rotas para `APIRouter`,
preservar os contratos HTTP e substituir o piloto pelo checkpoint definitivo.
