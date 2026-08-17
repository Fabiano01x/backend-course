# Progresso

Estado: piloto preservado e fluxo progressivo configurado

Última aula processada: 03

## Fonte

- Curso e versão confirmados: `3b30bbfd-e48e-4883-8450-8fca5452c8d1`, v3.
- Módulo 4 importado integralmente: 8 JSON, 8 Markdown e manifesto com hashes.
- As oito aulas foram analisadas e rastreadas no mapa curricular.

## Conteúdo autoral

- Ordem pedagógica do Módulo 4 definida.
- Aula piloto produzida: `course/04-fastapi/03-apirouter.md`.
- Aulas 1, 2 e 4–8 ainda não foram escritas.

## Conceitos incorporados

- Baseline do piloto: FastAPI, `async def`, Pydantic v2 e contratos HTTP.
- Introduzido e permanente: `APIRouter`, prefixos, tags e `include_router`.

## Arquitetura atual

- A solução atual foi preservada em `reference/pilot/module-04/lesson-03/`.
- `main.py` cria e compõe a aplicação piloto.
- Livros, usuários e saúde possuem routers separados.
- Persistência continua em memória, de forma deliberadamente temporária.
- Ambiente resolvido registrado no `requirements.lock` do piloto.
- `student/library-api/` está reservado para a implementação manual do aluno.
- Ainda não existem checkpoints sequenciais; o primeiro será criado com a aula 1.

## Pendências

- Submeter o padrão da aula piloto à avaliação.
- Depois da aprovação, produzir as aulas em ordem, começando pela nova aula 1.
- Encerrar cada aula ou mudança relevante com testes, validação e commit.
- Nunca alterar ou incluir a área `student/` em commits do Codex.
- Manter HTML, PDF, SQLAlchemy, autenticação e Docker fora deste marco.

## Próxima etapa

Validar didática, profundidade, tamanho e estrutura do piloto. Não produzir o
restante do módulo antes dessa validação.
