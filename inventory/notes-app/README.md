# Notes App — inventário histórico e backup Git verificado

Fonte: [ianmaciel7/notes-app](https://github.com/ianmaciel7/notes-app) (privado)
Destino: [ianmaciel7/exams-app-archive](https://github.com/ianmaciel7/exams-app-archive) (público desde 24/11/2026; não adicionar dados privados sem revisão).

## Estado verificado em 24/11/2026

O bundle integral do Notes App foi restaurado e conferido: 17 heads, 5 tags e 50 refs de PR, total 72 refs originais. Ver [manifesto](../../manifests/notes-app-private-full.json) e [auditoria binária](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45432868764). O ZIP posterior contém 1.135 runs. Dois commits de worktrees ausentes foram preservados em [suplemento autenticado](https://github.com/ianmaciel7/notes-app/releases/tag/notes-worktrees-2026-11-24), com restore e hash verificados; ver [manifesto](../../manifests/notes-worktrees-2026-11-24.json). As origens permanecem intactas. Os dados abaixo são o inventário parcial anterior, preservado como evidência histórica.

## Dados preservados nesta pasta — 23/11/2026

Tudo abaixo foi copiado diretamente pela conexão GitHub autenticada, sem copiar credenciais e sem tornar o repositório público.

| Tipo de informação | Quantidade | Arquivos |
|---|---:|---|
| Pull requests com títulos e descrições | 50 | `source-pulls-2026-11-23.json` |
| Registros de issues/PRs | 50 | `source-issues-2026-11-23.json` |
| Revisões formais de PR | 37 | `platform/pr-reviews-batch-01..05.json` |
| Comentários de revisão inline | 100 | `platform/pr-inline-review-comments-page-001.json` |
| Comentários de conversa | 10 | `platform/issue-conversation-comments-page-001.json` |
| Eventos de issues/PRs | 153 | `platform/issue-events-page-001..002.json` |
| Registros de arquivos alterados em PRs | 1.889 | `platform/pr-file-diffs-batch-01..05.json` |
| Workflow runs — dados do GitHub | 1.130 | `actions/workflow-runs-page-001..012.json` |
| Descrições de releases | 3 | `source-releases-2026-11-23.json` |
| Referências das tags | 3 | `source-tags-2026-11-23.json` |

Essas contagens representam **registros**, não necessariamente entidades distintas de código ou versões.

## Conteúdo Git preservado em outros backups

As 12 branches históricas `old`, `old-1` a `old-11` foram preservadas em 12 Git Bundles dentro de um backup completo de `exams-app-antigo-2`. Seus commits de ponta coincidiram com o repositório original em [verificação de 15 bundles](../../reports/embedded-bundles-audit.md).

## Limitações atuais

- Os objetos Git de main, dev, stag, firebase/file, tags originais e refs de PR estão preservados no bundle verificado.
- O índice histórico autenticado e o índice de conteúdo foram publicados em releases privadas no Notes App. O arquivo público não deve receber novos dados privados.
- Logs originais de CI são recuperados separadamente dos metadados de runs; ver [auditoria atual](../../reports/ARCHIVE-STATUS-2026-11-24.md).
- Transferências temporárias e origens não devem ser excluídas sem análise de dependências e autorização específica.
