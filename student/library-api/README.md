# Sua Library API

Esta pasta é a sua área de prática. Ela começa sem uma solução pronta porque
você construirá a aplicação manualmente enquanto acompanha as aulas.

## Regra de proteção

O Codex não deve criar, alterar, formatar, testar com modificação nem remover
arquivos dentro desta pasta sem um pedido seu que mencione explicitamente a
área do aluno.

## Fluxo recomendado

1. Leia a aula atual em `course/`.
2. Digite as mudanças nesta pasta, sem copiar antecipadamente a solução.
3. Execute os testes indicados na aula.
4. Revise `git diff -- student/library-api`.
5. Crie pessoalmente o commit sugerido pela aula.
6. Somente depois, compare sua versão com o checkpoint de referência.

Exemplo de comparação quando o checkpoint estiver disponível:

```bash
python3 scripts/compare_checkpoint.py --module 4 --lesson 1
```

O comparador é somente leitura. Diferenças são exibidas no terminal e nenhum
arquivo seu é substituído.

## Commits do aluno

Você é responsável pelos commits desta pasta. Exemplos:

```text
student(m04-l01): implement the first Library API
student(m04-l02): add Pydantic contracts
student(m04-l03): organize routes with APIRouter
```

