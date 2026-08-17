# Decisões arquiteturais e pedagógicas

## ADR-001 — Markdown como fonte autoral e HTML derivado

**Decisão:** aulas novas são mantidas em Markdown semântico. O HTML contínuo é
um artefato local reproduzível, gerado por `scripts/build_course.py`, e não é
versionado. PDF permanece fora do escopo.

O tema adapta a linguagem visual da fonte — fundo bege, títulos serifados,
cartões e código escuro — para a identidade própria Backend Course / Library
API. Não copia marca, controles ou identidade do proprietário da plataforma.
Cada aula gera um único documento de rolagem vertical, sem divisão em páginas.

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

## ADR-005 — APIRouter como mudança permanente

**Decisão:** a aula 3 foi inicialmente usada para validar a metodologia porque
possui dor concreta, refatoração visível e efeito arquitetural permanente. Seu
checkpoint definitivo parte da aula 2 e preserva os contratos HTTP. Depois
dela, todas as rotas do projeto usam `APIRouter`.

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

## ADR-009 — Git e commits são obrigatórios

**Contexto:** o marcador inicial não era um repositório funcional. O usuário
inicializou Git na raiz e o estado anterior à reorganização foi preservado no
commit `chore: initialize progressive backend course`.

**Decisão:** toda aula e toda mudança relevante de arquitetura, contrato,
dependência, ferramenta ou correção técnica recebe commit próprio após testes e
validação. Commits do Codex usam staging por caminhos e nunca incluem
`student/`. O aluno cria pessoalmente seus commits de prática.

## ADR-010 — Dependências resolvidas dos checkpoints

**Decisão:** `pyproject.toml` declara faixas compatíveis; o ambiente aprovado é
registrado nos `requirements.lock` dos checkpoints. O checkpoint 03 foi
executado com Python 3.14.6, FastAPI 0.141.1, Pydantic 2.13.4, Uvicorn
0.52.3, HTTPX 0.28.1 e pytest 8.4.2.

Os testes HTTP usam `httpx.AsyncClient` com transporte ASGI. Isso testa as rotas
assíncronas diretamente e evita depender da ponte síncrona de `TestClient`.

## ADR-011 — Prática e soluções ficam separadas

**Decisão:** `student/library-api/` é a área manual e protegida do aluno. O Codex
produz soluções somente em `reference/checkpoints/`, com um snapshot completo e
executável por aula. As aulas mostram mudanças guiadas; arquivos completos ficam
nos checkpoints para consulta posterior. O commit de reorganização pode criar
somente o `README.md` inicial que estabelece essa fronteira; depois dele, o
Codex não inclui `student/` em seus commits.

## ADR-012 — Piloto não é checkpoint sequencial

**Decisão:** a implementação inicial da aula 3 fica preservada em
`reference/pilot/` como registro metodológico. O checkpoint definitivo foi
reconstruído a partir do checkpoint 02, sem promover o piloto diretamente à
sequência cumulativa.

## ADR-013 — Componentes visuais continuam legíveis no Markdown

**Decisão:** problema, conceito, modelo mental, correção, recurso, orientação
e checkpoint usam a sintaxe de admonitions do Python-Markdown. Exercícios podem
usar `<details markdown="1">`. O tema converte esses elementos em componentes
visuais sem inserir CSS particular dentro das aulas.

O manifesto `course/04-fastapi/module.json` é a fonte de verdade para ordem,
metadados, proveniência, checkpoint e estado de cada aula.

## ADR-014 — Retomada não depende da sessão aberta

**Decisão:** Git, o manifesto do módulo, `progress.md` e os checkpoints são o
estado durável do trabalho. `scripts/resume_status.py` deriva dessas fontes um
resumo de retomada e pode reexecutar todas as verificações necessárias antes de
uma pausa. Servidores locais e `dist/` são descartáveis.
