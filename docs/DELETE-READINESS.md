# Critérios de exclusão dos repositórios antigos

Data de referência: 2026-11-23. **Não excluir automaticamente repositórios de origem.**

## Escopo

| Repositório | Histórico Git / SHA dos heads | Issues/PRs/revisões | Actions artifacts | Situação de exclusão |
|---|---|---|---|---|
| `exams-app-old` | 6/6 branches restauradas e conferidas | ZIP de metadados verificado | Nenhum artifact ativo no inventário | Depende de cópia externa e conferência de integrações |
| `exams-app-antigo-2` | 28/28 branches restauradas e conferidas | 200 PRs e 88 issues; erro de reviews do PR #248 resolvido em complemento | 2.844 ZIPs, aproximadamente 1,09 GB; exportação em lotes iniciada | **Bloqueado** até auditoria e backup binário concluídos |
| `shadcn-template` | 7/7 branches restauradas e conferidas | ZIP de metadados verificado | 15 artifacts, aproximadamente 2,60 MB | **Bloqueado** até backup dos artifacts |
| `shadcn-firebase-template` | 7/7 branches restauradas e conferidas | ZIP de metadados verificado | 24 artifacts, aproximadamente 19,47 MB | **Bloqueado** até backup dos artifacts e verificação de Discussions |

O `exams-app` e o `notes-app` **não são alvos** de exclusão: são projetos correntes. Para o Notes privado ainda faltam 4 branches e 3 tags no arquivo (o workflow requer `NOTES_READ_TOKEN`).

## Backups e evidência

- Histórico Git público (bundles completos e refs de PR): [archive-2026-11-23-all-refs](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-all-refs).
- Histórico completo de `exams-app`: [exams-app-2026-11-23-complete](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-complete).
- JSON dos metadados de issues/PRs/CI: [public-metadata-2026-11-23](https://github.com/ianmaciel7/exams-app-archive/releases/tag/public-metadata-2026-11-23).
- Suplemento do PR #248: [inventory/exams-app-antigo-2/pr-248-reviews-supplement.json](../inventory/exams-app-antigo-2/pr-248-reviews-supplement.json).
- Prova de recuperação de mídia de CI: [legacy-ci-evidence-sample-2026-11-23](https://github.com/ianmaciel7/exams-app-archive/releases/tag/legacy-ci-evidence-sample-2026-11-23).
- Preservação integral dos artifacts recuperáveis: [workflow](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45250235125) e [release dos lotes](https://github.com/ianmaciel7/exams-app-archive/releases/tag/legacy-ci-artifacts-2026-11-23-bulk).
- Validador: [.github/workflows/verify-legacy-archive.yml](../.github/workflows/verify-legacy-archive.yml).

## Condições cumulativas para permitir a exclusão

1. Confirmar que todos os lotes binários estão presentes na release, com manifestos e SHA-256, e que `BULK-MANIFEST.json` registra `complete=true`, sem nenhum artifact pendente.
2. Restaurar ao menos um arquivo histórico real, imagem e ZIP de evidência a partir do arquivo **sem depender da origem**, além das verificações Git já concluídas.
3. Conferir Projects/Discussions, anexos fora do Git, links externos e qualquer arquivo de release não coberto. A API registrou zero URLs diretas de anexos e zero release assets nos quatro arquivos públicos; isso não comprova cobertura de todos os recursos externos.
4. Identificar dependências de repositórios originais: deployments, serviços externos, webhooks, secrets, Actions, forks, colaboradores e links utilizados por outros projetos.
5. Guardar uma segunda cópia dos bundles, manifestos e releases **fora da mesma conta GitHub**, conferida por hash.
6. Preferir arquivar os repositórios originais em modo somente leitura e acompanhar antes da exclusão permanente. Solicitar aprovação explícita do proprietário para excluir cada repo.

**Aviso:** o inventário de CI é um snapshot dos artifacts acessíveis em 23/11/2026; GitHub pode expirar logs/artifacts e dados externos. Não afirmar que 100% de todos os dados históricos já foi capturado.

Nenhum repositório de origem foi alterado ou excluído nesta auditoria.
