# Mapa curricular

## Escopo analisado

- Curso: **Python full stack for MNCs**
- Course ID: `3b30bbfd-e48e-4883-8450-8fca5452c8d1`
- Versão: `3`
- Módulo original: **Modern Python Backend with FastAPI**
- Total: 8 aulas

Os títulos e conceitos abaixo vieram da fonte. Os novos títulos, a ordem e
as decisões de implementação são reorganização pedagógica deste projeto.

## Cobertura e reorganização

| Ordem original | Aula original | Fonte | Conceitos identificados | Nova posição | Nova aula | Status | Justificativa |
|---:|---|---|---|---:|---|---|---|
| 1 | Asynchronous Python: Coroutines and Async/Await | `source/module-04/01.md` | I/O-bound, coroutine, `async`, `await`, event loop, task, `gather` | 1 | Primeira Library API e programação assíncrona | Concluído e corrigido | O FastAPI mínimo dá contexto ao async. A explicação incorreta sobre aguardar uma coroutine foi corrigida e comprovada por exemplo. |
| 2 | Building Modular FastAPI Apps with Routers | `source/module-04/02.md` | `APIRouter`, prefix, tags, packages, `include_router`, organização por domínio | 3 | Crescendo sem um `main.py` monolítico | Concluído | Primeiro tornamos a dor visível com rotas de livros e usuários; depois adotamos routers permanentemente. |
| 3 | Pydantic Data Models for Request/Response Validation | `source/module-04/03.md` | `BaseModel`, request body, `response_model`, `Field`, validadores | 2 | Contratos de entrada e saída com Pydantic v2 | Concluído e reordenado | Os contratos aparecem antes da refatoração estrutural, permitindo comprovar depois que mover uma rota não muda seu contrato HTTP. |
| 4 | Dependency Injection for Resource Management | `source/module-04/04.md` | `Depends`, `yield`, setup/teardown, substituição em testes, sessão de banco | 6 | Dependências e ciclo de vida de recursos | Reordenado e dividido | A DI será aplicada primeiro a configurações. `AsyncSession` ficará como ponte conceitual para o Módulo 5, sem banco fictício no projeto atual. |
| 5 | Advanced RESTful API Design | `source/module-04/05.md` | query parameters, filtros, ordenação, limit/offset, paginação, SQLAlchemy | 4 | Filtros, ordenação e paginação | Reordenado e dividido | O contrato REST será aprendido com a coleção em memória. Queries SQLAlchemy e bibliotecas de paginação serão retomadas quando houver banco. |
| 6 | Securing FastAPI: CORS and Essential Headers | `source/module-04/06.md` | same-origin policy, preflight, `CORSMiddleware`, headers, middleware | 7 | Integração segura com o frontend | Reordenado e complementado | CORS depende da configuração por ambiente. HSTS será condicionado a HTTPS/produção e CSP não será copiada sem considerar Swagger/ReDoc. |
| 7 | Environment Variables for Configuration and Secrets | `source/module-04/07.md` | variáveis de ambiente, `.env`, `BaseSettings`, `lru_cache`, settings como dependência | 5 | Configuração por ambiente | Reordenado e dividido | Primeiro externalizamos a configuração; a refatoração para `Depends` e cache motiva a aula seguinte. |
| 8 | Interactive API Docs with Swagger UI & ReDoc | `source/module-04/08.md` | OpenAPI, Swagger UI, ReDoc, metadados, tags, descrições | 8 | OpenAPI como contrato executável | Mantido e complementado | Encerra o módulo auditando tudo que routers, schemas e tipos expõem aos consumidores. |

## Sequência aprovada

1. Primeira Library API e programação assíncrona.
2. Contratos de entrada e saída com Pydantic v2.
3. Crescendo sem um `main.py` monolítico.
4. Filtros, ordenação e paginação.
5. Configuração por ambiente.
6. Dependências e ciclo de vida de recursos.
7. Integração segura com o frontend.
8. OpenAPI como contrato executável.

As aulas são concluídas sequencialmente. O status de cada linha distingue
conteúdo produzido de planejamento aprovado.
