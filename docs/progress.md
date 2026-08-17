# Progresso

Estado: aula 07 concluída

Última aula processada: 07

## Fonte

- Curso e versão confirmados: `3b30bbfd-e48e-4883-8450-8fca5452c8d1`, v3.
- Módulo 4 importado integralmente: 8 JSON, 8 Markdown e manifesto com hashes.
- As oito aulas foram analisadas e rastreadas no mapa curricular.

## Conteúdo autoral

- Ordem pedagógica do Módulo 4 definida.
- Aula piloto preservada como registro metodológico em `reference/pilot/`.
- Tema contínuo inspirado no Grasp e gerador HTML responsivo concluídos.
- Manifesto de apresentação registra as oito aulas e sua proveniência.
- Aulas 1–7 e seus checkpoints executáveis concluídos.
- Aula 8 ainda não foi escrita.

## Conceitos incorporados

- Introduzidos na aula 1: FastAPI mínimo, endpoints GET, `async def`, coroutine,
  task, event loop e `await`.
- Correção técnica de coroutine versus task incorporada.
- Introduzidos na aula 2: schemas Pydantic v2, contratos separados de entrada e
  saída, validação estrita e respostas `201`, `404` e `422`.
- Introduzido e permanente: `APIRouter`, prefixos, tags e `include_router`.
- Introduzidos na aula 4: query parameters validados, filtros opcionais,
  ordenação enumerada, paginação limit-offset e resposta `BookPage`.
- Introduzidos na aula 5: `BaseSettings`, fontes de configuração, `.env`,
  precedência, validação cruzada e configuração pública em `AppInfo`.
- Introduzidos na aula 6: `Depends`, providers, `Annotated`, `lru_cache`,
  overrides em testes e ciclo setup/teardown com `yield`.
- Introduzidos na aula 7: same-origin policy, CORS, preflight, allowlists,
  headers defensivos, HSTS condicional e fábrica de aplicação.

## Arquitetura atual

- A solução piloto foi preservada em `reference/pilot/module-04/lesson-03/`.
- `main.py` expõe uma fábrica e compõe a aplicação do checkpoint 07.
- Livros, usuários e rotas operacionais possuem routers separados.
- Persistência continua em memória, de forma deliberadamente temporária.
- Ambiente resolvido registrado no `requirements.lock` do checkpoint 07.
- `student/library-api/` está reservado para a implementação manual do aluno.
- O checkpoint sequencial 01 usa rotas diretas em `main.py` e dados somente de
  leitura em memória.
- O checkpoint 02 mantém rotas diretas, adiciona `schemas.py`, estado
  reinicializável e operações de criação/detalhe.
- O checkpoint 03 preserva esses contratos e move saúde, livros e usuários
  para routers próprios, registrados explicitamente em `main.py`.
- O checkpoint 04 mantém os routers e transforma `GET /books` em uma consulta
  filtrável, ordenável e paginada, ainda executada em memória.
- O checkpoint 05 adiciona `config.py`; metadados, `/info` e limites de página
  consomem uma instância global e validada de `Settings`.
- O checkpoint 06 remove a instância global; endpoints recebem `AppSettings` e
  testes substituem `get_settings` sem recarregar a aplicação.
- O checkpoint 07 cria `create_app(settings)`, configura CORS com allowlists e
  adiciona headers defensivos. HSTS exige produção e HTTPS; Swagger e ReDoc
  permanecem funcionais sem uma CSP genérica.

## Pendências

- Produzir a aula 8 e seu checkpoint a partir do estado da aula 7.
- Encerrar cada aula ou mudança relevante com testes, validação e commit.
- Nunca alterar ou incluir a área `student/` em commits do Codex.
- Manter PDF, SQLAlchemy, autenticação e Docker fora deste marco.

## Próxima etapa

Produzir a aula 8 a partir do checkpoint 07. Auditar e refinar o contrato
OpenAPI exposto por schemas, routers e metadados, encerrando o Módulo 4.
