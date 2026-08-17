# Progresso

Estado: piloto concluído

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

- `main.py` cria e compõe a aplicação.
- Livros, usuários e saúde possuem routers separados.
- Persistência continua em memória, de forma deliberadamente temporária.
- Ambiente resolvido registrado em `project/backend/requirements.lock`.

## Pendências

- Submeter o padrão da aula piloto à avaliação.
- Depois da aprovação, produzir as aulas em ordem, começando pela nova aula 1.
- Configurar um repositório Git funcional antes de depender de checkpoints por
  commit.
- Manter HTML, PDF, SQLAlchemy, autenticação e Docker fora deste marco.

## Próxima etapa

Validar didática, profundidade, tamanho e estrutura do piloto. Não produzir o
restante do módulo antes dessa validação.
