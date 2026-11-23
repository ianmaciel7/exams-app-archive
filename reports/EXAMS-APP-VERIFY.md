# Verificação adicional do exams-app

Bundle original e TAR extraídos da release privada; nenhum repositório de origem foi modificado.

| Verificação | Resultado |
|---|---|
| Git Bundle SHA-256 | Passou |
| Snapshot dev SHA-256 | Passou |
| git fsck --full | Passou |
| SHA de todas as refs | Passou |
| Todas as quatro branches: SHA, arquivos e mídia | Passou |
| Arquivos do TAR dev contra árvore Git | Passou |
| Ponteiros Git LFS detectados (todos os objetos do bundle) | 0 |
| Submódulos nos HEADs | 0 |
| .gitattributes nos HEADs | 2 |
| Workflows antigos | 2 |
| Artifacts de CI | 0 |
| Logs de CI recuperados | 0/2 |

## Branches

| Branch | SHA | Arquivos | Mídias |
|---|---|---:|---:|
| chore/consolidate-legacy-sources-20261123 | \`b67c7c1e36e0\` | 2837 | 811 |
| claude/project-thread-o4dym1 | \`c6d50b2096e3\` | 309 | 260 |
| dev | \`dfc277cd9823\` | 509 | 360 |
| main | \`70247f40f149\` | 1 | 0 |

Release: https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-verification

O relatório JSON contém detalhes e limitações.

## Atualização — logs de CI preservados

A primeira execução da auditoria registrou 0/2 logs porque o GitHub CLI bloqueou sequências de escape do terminal. A exportação foi corrigida com `--allow-escape-sequences` e concluída posteriormente.

Os **dois logs originais** foram compactados, publicados e baixados novamente para validação de SHA-256 e descompressão na release privada [exams-app-2026-11-23-ci-logs](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-ci-logs). Os dois workflows não produziram artefatos próprios.

Manifesto: [EXAMS-APP-ACTIONS-LOGS.json](EXAMS-APP-ACTIONS-LOGS.json).
