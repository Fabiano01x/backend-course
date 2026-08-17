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

- Soluções executáveis ficam em `reference/checkpoints/`, uma cópia completa
  por aula.
- A solução anterior à sequência definitiva fica em `reference/pilot/`.
- Código apresentado como funcional deve executar e corresponder ao projeto.
- Pseudocódigo deve ser identificado explicitamente.
- Executar testes e `scripts/validate_course.py` após mudanças relevantes.

## Área do aluno

- `student/library-api/` pertence ao aluno.
- Exceção de bootstrap: o commit que cria esta fronteira pode incluir somente
  o `README.md` inicial da área. Depois dele, a proteção é integral.
- Nunca criar, alterar, formatar, remover ou incluir arquivos dessa pasta em
  commits do Codex sem um pedido do usuário que mencione explicitamente a área
  do aluno.
- O comparador de checkpoints deve operar somente em leitura.
- O aluno cria pessoalmente os commits de sua implementação.

## Git e commits obrigatórios

- Inspecionar `git status` e `git diff` antes de preparar qualquer commit.
- Usar `git add` com caminhos explícitos. Não usar `git add .` quando houver
  qualquer trabalho do aluno.
- Conclusão de aula, mudança arquitetural, contrato HTTP, dependência,
  importador, validador ou correção técnica relevante exige commit próprio.
- Não criar commit com testes ou validação falhando.
- Não usar `commit --amend`, rebase ou squash em checkpoints concluídos.
- Não iniciar uma nova aula antes de documentação, checkpoint, testes,
  validação e commit da aula anterior estarem concluídos.

## Contexto obrigatório

Antes de alterar aulas ou arquitetura, consultar conforme a tarefa:

- `AGENTS.md`;
- `docs/progress.md`;
- `docs/curriculum-map.md`;
- `docs/concepts.md`;
- `docs/decisions.md`;
- aula anterior;
- checkpoint anterior em `reference/checkpoints/`;
- `student/library-api/` somente quando o usuário pedir explicitamente.

## Encerramento de etapa

1. Atualizar o projeto executável.
2. Executar testes.
3. Atualizar os documentos afetados.
4. Atualizar `docs/progress.md`.
5. Atualizar o mapa curricular quando a cobertura mudar.
6. Conferir o diff, preparar somente caminhos do escopo e criar o commit
   obrigatório.
