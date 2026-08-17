# Decisões arquiteturais e pedagógicas

## ADR-001 — Markdown como fonte autoral

**Decisão:** aulas novas serão mantidas somente em Markdown. HTML e PDF serão
artefatos derivados em uma etapa posterior.

## ADR-002 — Fonte original imutável

**Decisão:** respostas do Grasp ficam em `source/` como JSON e como o campo
`content` original em Markdown. O manifesto registra hashes. O importador recusa
sobrescritas.

**Proveniência:** a seleção de versão e a navegação da API foram adaptadas do
exportador existente em `AutomçãoCurso/grasp_export_ajustado.py`. Tradução,
HTML e PDF daquele projeto não foram copiados, e o projeto vizinho não foi
alterado.

## ADR-003 — Idioma do novo curso

**Decisão:** fonte em inglês; curso e documentação autoral em português do
Brasil. Tradução não substitui nem altera a fonte.

## ADR-004 — Library API cumulativa

**Decisão:** `User`, `Book` e posteriormente `Loan` formarão o domínio. O
primeiro piloto usa livros e usuários; empréstimos aguardam persistência.

## ADR-005 — APIRouter como piloto

**Decisão:** a nova aula 3 valida a metodologia porque possui dor concreta,
refatoração visível e efeito arquitetural permanente. Depois dela, todas as
rotas do projeto usam `APIRouter`.

## ADR-006 — Banco adiado para o Módulo 5

**Decisão:** exemplos SQLAlchemy encontrados nas aulas originais 4 e 5 não
serão incorporados ao projeto no Módulo 4. DI e contratos de consulta serão
ensinados sem fingir que já existe uma sessão de banco.

## ADR-007 — Correção da explicação assíncrona

**Problema:** a aula original 1 afirma que `await coro_c()` faz outra task
esperar até `coro_a` terminar, mesmo quando `coro_c` executa
`await asyncio.sleep(...)`.

**Decisão:** corrigir o modelo mental. O `await` mantém a relação sequencial
dentro da task atual, mas um ponto de suspensão permite ao event loop executar
outras tasks prontas. `create_task()` cria concorrência independente; não é
necessário envolver toda coroutine aguardada em uma task.

## ADR-008 — Segurança compatível com o ambiente

**Decisão:** HSTS será habilitado apenas quando a aplicação estiver em produção
sob HTTPS. Uma CSP genérica não será copiada sem testar `/docs` e `/redoc`, pois
pode bloquear os recursos das interfaces.

## ADR-009 — Git não é requisito do piloto

**Contexto:** o diretório atual possui um `.git` vazio e somente leitura, não um
repositório funcional.

**Decisão:** não executar commits nem alterar esse marcador. Mudanças serão
mantidas em unidades prontas para commit quando o versionamento estiver
disponível.

## ADR-010 — Dependências resolvidas do piloto

**Decisão:** `pyproject.toml` declara faixas compatíveis; o ambiente aprovado é
registrado em `project/backend/requirements.lock`. O checkpoint foi executado
com Python 3.14.6, FastAPI 0.141.1, Pydantic 2.13.4, Uvicorn 0.52.3, HTTPX
0.28.1 e pytest 8.4.2.

Os testes HTTP usam `httpx.AsyncClient` com transporte ASGI. Isso testa as rotas
assíncronas diretamente e evita depender da ponte síncrona de `TestClient`.
