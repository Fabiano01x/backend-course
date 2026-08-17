# AGENTS.md

## Objetivo

Transformar o curso original em um curso de backend orientado a projeto,
progressivo, didático e executável. O projeto cumulativo é a **Library API**.

## Regra central

Todo conceito novo deve responder a um problema visível e ser integrado ao
projeto principal. Uma abstração adotada não deve desaparecer nas etapas
seguintes sem justificativa explícita.

## Fonte imutável

- `source/` contém material original importado do Grasp.
- Nunca editar manualmente, traduzir, formatar ou normalizar arquivos em
  `source/`.
- O importador deve recusar sobrescritas e o validador deve conferir os hashes
  registrados no manifesto.

## Curso autoral

- O conteúdo novo fica em `course/` e deve ser escrito em português do Brasil.
- Diferenciar claramente conteúdo original, reorganização pedagógica,
  complementação técnica e correção técnica.
- Não atribuir ao curso original algo que não esteja na fonte.
- Toda aula relevante da fonte deve aparecer em `docs/curriculum-map.md`.

## Metodologia

Cada aula deve seguir, quando aplicável:

```text
problema → por que importa → conceito → modelo mental → exemplo mínimo
→ aplicação no projeto → antes/depois → testes → exercício
→ checkpoint → próximo problema
```

## Arquitetura evolutiva

- Evitar overengineering.
- Não introduzir services, repositories, banco de dados, autenticação ou
  outras camadas antes de uma necessidade concreta.
- Depois da aula piloto do Módulo 4, todas as rotas de domínio devem usar
  `APIRouter`.
- Exemplos mínimos que simplificarem a arquitetura devem declarar que não
  representam o estado atual do projeto.

## Código e testes

- O código executável fica em `project/backend/`.
- Código apresentado como funcional deve executar e corresponder ao projeto.
- Pseudocódigo deve ser identificado explicitamente.
- Executar testes e `scripts/validate_course.py` após mudanças relevantes.

## Contexto obrigatório

Antes de alterar aulas ou arquitetura, consultar conforme a tarefa:

- `AGENTS.md`;
- `docs/progress.md`;
- `docs/curriculum-map.md`;
- `docs/concepts.md`;
- `docs/decisions.md`;
- aula anterior;
- estado atual de `project/backend/`.

## Encerramento de etapa

1. Atualizar o projeto executável.
2. Executar testes.
3. Atualizar os documentos afetados.
4. Atualizar `docs/progress.md`.
5. Atualizar o mapa curricular quando a cobertura mudar.

