# Critérios de exclusão dos repositórios antigos

> **Retificação de 24/11/2026:** este documento é um snapshot histórico. A conferência mais recente de cobertura, segurança e lacunas está no [README](../README.md). O backup Git posterior de Notes já possui manifesto verificado; isso não implica que o índice antigo foi reconstruído, que a privacidade esteja garantida ou que a exclusão esteja autorizada.


Data de referência: 2026-11-23. **Não excluir automaticamente repositórios de origem.**

## Escopo

| Repositório | Histórico Git / SHA dos heads | Issues/PRs/revisões | Actions artifacts | Situação de exclusão |
|---|---|---|---|---|
| `exams-app-old` | 6/6 branches restauradas e conferidas | ZIP de metadados verificado | Nenhum artifact ativo no inventário | Depende de cópia externa e conferência de integrações |
| `exams-app-antigo-2` | 28/28 branches restauradas e conferidas | 200 PRs e 88 issues; erro de reviews do PR #248 resolvido em complemento | 2.844 ZIPs, aproximadamente 1,09 GB; preservados em release privada e validados | Etapa técnica aprovada; confirmar dependências e cópia independente |
| `shadcn-template` | 7/7 branches restauradas e conferidas | ZIP de metadados verificado | 15 artifacts, aproximadamente 2,60 MB; todos preservados | Etapa técnica aprovada; confirmar dependências e cópia independente |
| `shadcn-firebase-template` | 7/7 branches restauradas e conferidas | ZIP de metadados verificado | 24 artifacts, aproximadamente 19,47 MB; todos preservados, 0 Discussions | Etapa técnica aprovada; confirmar dependências e cópia independente |

O `exams-app` e o `notes-app` **não são alvos** de exclusão: são projetos correntes. Para o Notes privado ainda faltam 4 branches e 3 tags no arquivo (o workflow requer `NOTES_READ_TOKEN`).

## Backups e evidência

- Histórico Git público (bundles completos e refs de PR): [archive-2026-11-23-all-refs](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-all-refs).
- Histórico completo de `exams-app`: [exams-app-2026-11-23-complete](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-complete).
- JSON dos metadados de issues/PRs/CI: [public-metadata-2026-11-23](https://github.com/ianmaciel7/exams-app-archive/releases/tag/public-metadata-2026-11-23).
- Suplemento do PR #248: [inventory/exams-app-antigo-2/pr-248-reviews-supplement.json](../inventory/exams-app-antigo-2/pr-248-reviews-supplement.json).
- Prova de recuperação de mídia de CI: [legacy-ci-evidence-sample-2026-11-23](https://github.com/ianmaciel7/exams-app-archive/releases/tag/legacy-ci-evidence-sample-2026-11-23).
- Preservação integral dos artifacts recuperáveis: [workflow aprovado](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45250235125) e [release completa e verificada](https://github.com/ianmaciel7/exams-app-archive/releases/tag/legacy-ci-artifacts-2026-11-23-bulk).
- Validador: [.github/workflows/verify-legacy-archive.yml](../.github/workflows/verify-legacy-archive.yml), com [execução final aprovada](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45251774013).
- Inventário GraphQL de Discussions e Projects V2: [legacy-github-extras-2026-11-23](https://github.com/ianmaciel7/exams-app-archive/releases/tag/legacy-github-extras-2026-11-23), 0 registros nos quatro repositórios.

## Resultado técnico confirmado em 23/11/2026

- **4/4 repositórios antigos aprovados** no auditor de restauração, com **0 impedimentos técnicos** dentro do escopo verificado.
- **2.883/2.883 GitHub Actions artifacts preservados**, em 16 TARs acompanhados por 16 manifestos, mais manifesto global `complete=true`. **0 arquivos faltantes, 0 downloads falhos e 0 IDs duplicados**.
- A release contém aproximadamente **1,11 GB**, incluindo os dados binários dos artifacts e seus manifestos; SHA-256 da release conferido e um ZIP real extraído e validado.
- O erro HTTP 500 ao exportar reviews do PR #248 foi resolvido por consulta REST e GraphQL: **0 revisões**.
- **0 Discussions e 0 Projects V2** na consulta GraphQL aos quatro repositórios.
- O resultado não prova recuperação de logs/artefatos que já haviam expirado, dados apagados do GitHub ou serviços externos.

**Ainda não excluir originais:** falta a cópia independente fora desta conta GitHub e a confirmação de dependências externas (deploy, webhooks, links e ferramentas). A exclusão exige autorização explícita.

## Condições cumulativas para permitir a exclusão

1. Confirmar que todos os lotes binários estão presentes na release, com manifestos e SHA-256, e que `BULK-MANIFEST.json` registra `complete=true`, sem nenhum artifact pendente.
2. Restaurar ao menos um arquivo histórico real, imagem e ZIP de evidência a partir do arquivo **sem depender da origem**, além das verificações Git já concluídas.
3. Conferir Projects/Discussions, anexos fora do Git, links externos e qualquer arquivo de release não coberto. A API registrou zero URLs diretas de anexos e zero release assets nos quatro arquivos públicos; isso não comprova cobertura de todos os recursos externos.
4. Identificar dependências de repositórios originais: deployments, serviços externos, webhooks, secrets, Actions, forks, colaboradores e links utilizados por outros projetos.
5. Guardar uma segunda cópia dos bundles, manifestos e releases **fora da mesma conta GitHub**, conferida por hash.
6. Preferir arquivar os repositórios originais em modo somente leitura e acompanhar antes da exclusão permanente. Solicitar aprovação explícita do proprietário para excluir cada repo.

**Aviso:** o inventário de CI é um snapshot dos artifacts acessíveis em 23/11/2026; GitHub pode expirar logs/artifacts e dados externos. Não afirmar que 100% de todos os dados históricos já foi capturado.

Nenhum repositório de origem foi alterado ou excluído nesta auditoria.
