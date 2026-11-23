# Notes App — arquivo parcial de metadados privados

Fonte: [ianmaciel7/notes-app](https://github.com/ianmaciel7/notes-app) (privado)
Destino: [ianmaciel7/exams-app-archive](https://github.com/ianmaciel7/exams-app-archive) (privado)

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

## Pendências para arquivamento privado integral

- Os objetos Git das branches `main`, `dev`, `stag` e `firebase/file`.
- Os objetos Git e referências das tags `v0.1.0`, `v0.2.0`, `v0.3.0`. SHAs e descrições **não equivalem** a backup de objetos Git.
- `refs/pull/*` privadas, inclusive commits não alcançáveis pelas 12 branches históricas.
- Logs completos e artifacts das 1.130 execuções de CI quando ainda recuperáveis. A pasta `actions/` salva metadados dos runs, **não os logs/binários**.
- Links para anexos fora de GitHub Git e demais metadados com acesso restrito.

## Como finalizar

O workflow [Archive 100% accessible private Notes history](https://github.com/ianmaciel7/exams-app-archive/actions/workflows/archive-private-notes.yml) já está configurado. Requer o secret de repositório `NOTES_READ_TOKEN` com token **somente leitura** e acesso exclusivamente a `notes-app`, com permissões Contents, Pull requests, Issues e Actions.

Depois de adicionar o secret, execute o workflow manualmente. Ele tentará criar uma release **privada**, validar refs, blobs e checksums, e registrar explicitamente as limitações de API.

**Não descarte `notes-app` original** até a release passar e os dados externos prioritários serem conferidos.
