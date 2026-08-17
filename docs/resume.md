# Como encerrar e retomar o trabalho

O estado do curso não depende de um terminal aberto nem da memória da conversa.
Ele é preservado por quatro fontes versionadas:

1. o histórico Git registra cada aula e mudança relevante;
2. os manifestos `course/*/module.json` registram aulas concluídas e a próxima
   etapa;
3. `docs/progress.md` explica o estado pedagógico e arquitetural;
4. cada checkpoint concluído é uma cópia executável e testada.

## Antes de desligar

Execute:

```bash
.venv/bin/python scripts/resume_status.py --verify
```

O comando reexecuta os testes das ferramentas, a validação curricular, os
testes do checkpoint mais recente e a geração HTML das aulas concluídas. No
final, ele deve informar:

```text
Curso limpo: todo o trabalho do Codex está persistido em commits.
```

Se houver arquivos em `student/library-api/`, eles são apresentados em um grupo
separado. O Codex nunca os prepara nem cria commits por você.

## Ao retornar

Na raiz do projeto, execute:

```bash
.venv/bin/python scripts/resume_status.py
```

O resumo mostra branch, último commit, aulas concluídas, próxima aula e
alterações pendentes. Depois, basta pedir ao Codex para continuar a próxima
etapa informada pelo comando.

Não é necessário manter o editor, terminal, servidor local ou esta tarefa
abertos. A pasta `dist/` pode ser recriada e não contém a fonte das aulas.
