# Progresso

Estado: Módulo 6 / aula 03 concluída

Última aula concluída: M06/A03

## Fonte

- Curso e versão confirmados: `3b30bbfd-e48e-4883-8450-8fca5452c8d1`, v3.
- Módulo 4 importado integralmente: 8 JSON, 8 Markdown e manifesto com hashes.
- As oito aulas foram analisadas e rastreadas no mapa curricular.
- Módulo 5 importado integralmente: 7 JSON, 7 Markdown e manifesto com hashes.
- As sete novas aulas foram analisadas e rastreadas no mapa curricular.
- Módulo 6 importado integralmente: 6 JSON, 6 Markdown e manifesto com hashes.
- As seis aulas de autenticação e segurança foram auditadas e rastreadas no
  mapa curricular.

## Conteúdo autoral

- Ordem pedagógica do Módulo 4 definida.
- Aula piloto preservada como registro metodológico em `reference/pilot/`.
- Tema contínuo inspirado no Grasp e gerador HTML responsivo concluídos.
- Manifesto de apresentação registra as oito aulas e sua proveniência.
- Aulas 1–8 e seus checkpoints executáveis concluídos.
- Módulo 4 concluído e verificável a partir do Git.
- Sequência autoral do Módulo 5 e seus sete checkpoints concluídos.
- Sequência autoral do Módulo 6 definida em seis problemas; nenhuma aula foi
  iniciada antes da conclusão do planejamento e da importação.
- M06/A01–A03, com seus checkpoints executáveis, concluídas.

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
- Introduzidos na aula 8: OpenAPI como contrato, metadados, descrições de tags,
  `operationId` estáveis, exemplos de schemas e respostas adicionais.
- Introduzidos em M05/A01: esquema relacional, normalização prática, chaves,
  integridade referencial, constraints e índice único parcial.
- Introduzidos em M05/A02: `DeclarativeBase`, `Mapped`, `mapped_column`, modelos
  tipados, chaves estrangeiras, relacionamentos e association object.
- Introduzidos em M05/A03: `AsyncEngine`, `async_sessionmaker`, `AsyncSession`,
  driver `asyncpg`, uma sessão por requisição, lifespan e PostgreSQL com
  Docker Compose.
- Introduzidos em M05/A04: `select`, `add`, `commit`, `refresh`, `delete`,
  rollback após `IntegrityError`, `EXISTS`, contagem e paginação em SQL,
  `PUT`, `DELETE`, `204` e `409`.
- Introduzidos em M05/A05: Alembic, grafo de revisões, `upgrade`, `downgrade`,
  `target_metadata`, autogenerate revisado, baseline e migração assíncrona.
- Introduzidos em M05/A06: ACID, `session.begin`, `flush`, fronteira
  transacional no service, repository sem commit, `SELECT FOR UPDATE`,
  retirada e devolução concorrentes.
- Introduzidos em M05/A07: N+1, I/O implícito, `joinedload`, `selectinload`,
  loaders encadeados, `lazy="raise"` e testes de orçamento de consultas.
- Introduzidos em M06/A01: hash versus criptografia, Argon2id, salt, parâmetros
  de custo, `pwdlib`, hash fictício, enumeração temporal, normalização de
  identificador e execução CPU-bound em worker thread.
- Introduzidos em M06/A02: JWT assinado versus criptografado, Bearer token,
  algoritmo fixo, `typ`, `iss`, `aud`, `sub`, `iat`, `nbf`, `exp`, `jti`,
  claims obrigatórias, chave simétrica validada e identidade derivada.
- Introduzidos em M06/A03: refresh token opaco, digest SHA-256 de segredo
  aleatório, família, rotação de uso único, replay, revogação, validade
  absoluta, cookie `HttpOnly`, `Secure`, `SameSite`, CSRF, `Origin` e limites
  dessas defesas diante de XSS.

## Arquitetura atual

- A solução piloto foi preservada em `reference/pilot/module-04/lesson-03/`.
- `main.py` expõe uma fábrica e compõe a aplicação do checkpoint M06/A03.
- Livros, usuários, empréstimos e rotas operacionais possuem routers separados.
- Livros e usuários usam persistência PostgreSQL; `app/data.py` foi removido.
- Ambiente resolvido registrado no `requirements.lock` do checkpoint M06/A03.
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
- O checkpoint 08 audita `/openapi.json`, estabiliza identificadores de
  operação e documenta metadados, exemplos, sucessos e erros reais.
- O checkpoint M05/A01 preserva a API e acrescenta `schema.sql` com `users`,
  `books`, `loans` e invariantes testadas, ainda sem instalar ORM.
- O checkpoint M05/A02 adiciona modelos SQLAlchemy 2 que compilam o mesmo DDL
  PostgreSQL, sem criar engine ou abrir conexão.
- O checkpoint M05/A03 adiciona configuração segura de URL, engine e fábrica
  assíncronas, sessão por requisição, lifecycle do pool, PostgreSQL local e
  `GET /health/database` com uma consulta real.
- O checkpoint M05/A04 move livros e usuários para o banco. A listagem traduz
  filtros, disponibilidade derivada, contagem, ordem e recorte para SQL; livros
  ganham `PUT` e `DELETE`, e escritas convertem constraints em `409` com
  rollback.
- O checkpoint M05/A05 adiciona a baseline `0001_library_schema`, reutiliza a
  configuração validada no ambiente assíncrono do Alembic e remove todo DDL
  do startup. Upgrade, downgrade, inspeção do esquema e CRUD foram validados
  em PostgreSQL 18.4 efêmero.
- O checkpoint M05/A06 adiciona retirada, listagem e devolução. Um service
  controla `session.begin`; um repository focado não confirma transações; lock
  de livro e índice parcial garantem uma retirada ativa sob concorrência.
- O checkpoint M05/A07 enriquece o histórico com usuário e livro em uma
  consulta, carrega a coleção do detalhe de usuário em duas consultas fixas e
  usa `lazy="raise"` para recusar qualquer I/O relacional não planejado.
- O checkpoint M06/A01 substitui o cadastro público sem credencial por
  `/auth/register`, persiste somente Argon2id e usa `/auth/login` para verificar
  senha com erro genérico. A revisão `0002` preserva usuários anteriores com
  `password_hash` nulo.
- O checkpoint M06/A02 troca o sucesso vazio do login por um access JWT de 15
  minutos. Algoritmo, tipo, emissor, audience, sujeito, datas e `jti` são
  validados; `POST /loans` exige Bearer token e remove `user_id` da entrada.
  A conta atual é revalidada dentro da transação, sem nova migração.
- O checkpoint M06/A03 adiciona `refresh_tokens` pela revisão `0003`, persiste
  somente digest e estado de uma família com expiração absoluta. Login entrega
  o valor bruto em cookie restrito; refresh rotaciona sob lock; replay revoga a
  família; logout é idempotente. Header customizado, CORS e `Origin` protegem
  as operações por cookie contra CSRF.

## Pendências

- Encerrar cada aula ou mudança relevante com testes, validação e commit.
- Nunca alterar ou incluir a área `student/` em commits do Codex.
- Manter PDF fora dos módulos já concluídos.
- Preservar explicitamente as correções de segurança registradas para JWT,
  refresh, RBAC, OIDC, chaves de API, XSS e CSRF.
- Manter validador, retomada e gerador independentes do nome temático dos
  diretórios de módulo.

## Próxima etapa

Produzir M06/A04 adicionando autorização explícita com papéis persistidos. A
API deverá consultar permissões atuais, diferenciar `401` de `403` e manter
regras de propriedade separadas de papéis globais.
