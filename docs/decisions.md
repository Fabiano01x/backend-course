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

**Decisão:** HSTS é habilitado apenas quando a aplicação está em produção e
HTTPS foi declarado ativo. Uma CSP genérica não foi copiada; `/docs` e `/redoc`
são testados sem ela, pois uma política arbitrária pode bloquear recursos das
interfaces.

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
registrado nos `requirements.lock` dos checkpoints. O checkpoint 05 foi
executado com Python 3.14.6, FastAPI 0.141.1, Pydantic 2.13.4, Pydantic
Settings 2.14.2, python-dotenv 1.2.3, Uvicorn 0.52.3, HTTPX 0.28.1 e pytest
8.4.2.

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

## ADR-015 — Contrato de consulta antes do banco

**Decisão:** filtros, ordenação e paginação são implementados primeiro sobre a
coleção em memória. `GET /books` passa a responder `BookPage`; filtros são
aplicados antes da ordenação, `total` é calculado antes do recorte e campos de
ordenação são enumerados explicitamente.

SQLAlchemy e `fastapi-pagination`, presentes na fonte, não entram no Módulo 4.
O contrato será traduzido para consultas persistentes no Módulo 5, quando for
possível avaliar custo, contagem e estratégia de paginação com um banco real.

## ADR-016 — Configurar somente necessidades existentes

**Decisão:** a aula 5 introduz `pydantic-settings` para nome, versão, ambiente,
debug e limites de paginação. Não declara URL de banco, JWT ou origens CORS
antes que esses consumidores existam. `.env` é local e ignorado; o arquivo
versionado é `.env.example`, sem segredos.

Uma instância global e congelada de `Settings` foi aceita temporariamente para
tornar visível o custo de substituição em testes. A aula 6 a trocou por uma
dependência cacheada. O endpoint `/info` nunca deve serializar segredos.

## ADR-017 — DI respeita as fases da aplicação

**Decisão:** `load_settings()` é síncrona e cacheada; `get_settings()` é um
adaptador assíncrono usado por `Depends`. Endpoints podem receber overrides sem
reimportar módulos. Metadados e middleware, necessários durante a construção da
aplicação, chamam o carregador diretamente e não fingem ser request-scoped.

O padrão de setup/teardown com `yield` é ensinado, mas nenhum recurso artificial
é incorporado à Library API. Uma sessão real ocupará essa fronteira somente
quando engine, transações e persistência existirem.

## ADR-018 — Políticas de startup usam uma fábrica de aplicação

**Decisão:** `create_app(settings)` compõe middlewares e routers; `app` continua
sendo a instância pronta para o servidor. CORS e HSTS são políticas decididas
na inicialização, portanto recebem `Settings` diretamente em vez de usar
`Depends`, que pertence ao ciclo de requisição.

O middleware de headers defensivos envolve o middleware CORS para que também
as respostas de preflight recebam esses headers. Origens, métodos e headers
permitidos permanecem explícitos; wildcard é rejeitado com credenciais.

## ADR-019 — OpenAPI é contrato testado, não decoração

**Decisão:** a Aula 8 audita `/openapi.json` diretamente. Operações recebem
`operationId` explícito para preservar nomes consumidos por ferramentas mesmo
quando uma função Python for renomeada. Metadados, tags, exemplos, respostas de
sucesso e erros reais são protegidos por testes.

Informações fictícias de contato ou licença e uma rota artificial marcada como
obsoleta não foram copiadas da fonte. `deprecated=True` será usado somente
quando existir uma substituição e um plano real de migração.

## ADR-020 — Módulo 5 introduz persistência em sete problemas

**Decisão:** as sete aulas originais foram preservadas na cobertura, mas
adaptadas à Library API. A sequência parte do esquema, passa pelos modelos,
conexão, CRUD e migrações, e somente então introduz fronteiras de serviço e
repository no caso de uso atômico de empréstimo. Otimização de relacionamentos
encerra o módulo quando as consultas relacionadas realmente existirem.

O curso usará a API tipada do SQLAlchemy 2 (`DeclarativeBase`, `Mapped`,
`mapped_column`, `async_sessionmaker` e `select`). Senhas com caracteres
especiais não serão interpoladas ingenuamente em URLs. `create_all` não será
tratado como migração, autogenerate sempre exigirá revisão e I/O implícito de
relacionamentos não será assumido seguro com `AsyncSession`.

## ADR-021 — Disponibilidade é derivada do histórico

**Decisão:** o esquema relacional não persiste `books.available`. Um livro está
indisponível quando existe um `loan` com o mesmo `book_id` e `returned_at` nulo.
Um índice único parcial garante no banco que apenas um empréstimo ativo exista
por livro.

O campo `available` permanece no contrato HTTP e será calculado pela consulta.
Isso evita duas fontes de verdade. `Loan` é uma entidade associativa, e não uma
tabela `secondary` simples, porque possui datas e histórico próprios.
