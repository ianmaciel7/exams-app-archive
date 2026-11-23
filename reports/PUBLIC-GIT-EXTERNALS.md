# Auditoria Git LFS, submodulos e wikis

Todos os dados Git foram recuperados **das releases privadas**, não dos repositorios de origem.
Validação: SHA-256 dos bundles, restauração, git fsck --full e inspeção dos objetos.

| Origem | Objetos Git | Ponteiros LFS | Gitlinks | Wiki |
|---|---:|---:|---:|---|
| ianmaciel7/exams-app | 3870 | 0 | 0 | not found / inaccessible / empty |
| ianmaciel7/exams-app-old | 9437 | 0 | 0 | not found / inaccessible / empty |
| ianmaciel7/exams-app-antigo-2 | 5904 | 0 | 0 | not found / inaccessible / empty |
| ianmaciel7/shadcn-template | 1573 | 0 | 0 | not found / inaccessible / empty |
| ianmaciel7/shadcn-firebase-template | 9252 | 0 | 0 | not found / inaccessible / empty |
| ianmaciel7/fcc-responsive-web-design | 35 | 0 | 0 | not found / inaccessible / empty |
| ianmaciel7/ianmaciel7 | 27 | 0 | 0 | not found / inaccessible / empty |

Ponteiros Git LFS indicam conteúdo armazenado fora dos objetos Git; é necessária exportação dos binários.
Gitlinks indicam submodulos cujo repositório deve ser arquivado separadamente.
Wikis são Git separado e exigem exportação se existirem e estiverem acessíveis.

**Esta validação não cobre objetos deletados do upstream, metadados das issues ou
arquivos externos incluídos por URLs em documentos.**
