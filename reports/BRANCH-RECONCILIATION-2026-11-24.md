# Reconciliação de branches auxiliares — 24/11/2026

Comparação de árvores Git completas por SHA de blob e relação de commits com a `main` no commit `b9d5e5812b58e24259943dc63b7290c972957eca`. Nenhuma branch foi excluída.

| Branch | Head | Ahead / behind | Blobs iguais / diferentes / exclusivos | Decisão |
| --- | --- | --- | --- | --- |
| feat/archive-pages-codex-plugin-20261123 | 2feb3f9327fcd2f1fd30254538b7f6079d5eebee | 7 / 143 | 69 / 43 / 2 | Preservar: exportação offsite e SQLite histórico exclusivos |
| feat/chatgpt-native-archive-search-20261123 | 1869d0628426225590845ff226a7c9d7ccafc93a | 3 / 137 | 69 / 46 / 1 | Preservar SQLite histórico; implementação privada atual validada separadamente |
| feat/exams-archive-source-artifact-060 | a5eadb2db8b7b424f45619fdcc2b6686d373c0e6 | 1 / 123 | 80 / 66 / 1 | Preservar versão histórica e SQLite |
| feat/exams-archive-unified-multiagent-060 | 1583bc98024a4d2ce12df4675c665e041dc7fced | 2 / 127 | 79 / 65 / 1 | Preservar versão 0.6.0 e SQLite |
| fix/authenticated-search-plugin-080 | 8578730ee714d18805d1d0dce56c6480d93586fd | 10 / 12 | 234 / 8 / 0 | PR #61 integrada por squash aa52b6ee382b2dce70f67dcbf0aae2fe7445e8c7; plugin 0.8.0 conferido 20/20; preservar ref até autorização |

Arquivos exclusivos no primeiro ramo: `.github/workflows/export-archive-for-offsite.yml` e `reports/archive-index.sqlite`. Nos outros três ramos históricos, somente `reports/archive-index.sqlite` é exclusivo em caminho. O workflow offsite foi inspecionado: prepara artifacts temporários na própria conta, não constitui cópia independente. Não ativá-lo só para satisfazer artificialmente a issue #4; manter sua versão histórica. As árvores diferentes não provam equivalência semântica dos patches. Nenhuma branch histórica será apagada por esta auditoria.

Outras refs observadas:
- `main`: infraestrutura ativa.
- `archive-search-queries` (`d475d53b50b5416555359d7ade55bf0be24f6b13`): fila legada; preservar, não escrever consultas privadas em repositório público.
- `notes-private-import` (`019c67284606c7c47029154d71b27101914a44da`): transferência histórica; bundle posterior verificado, mas branch não autorizada para exclusão.
- A fila autenticada atual reside no Notes privado, com índice e resultados verificados por hash.

O inventário anterior de 75 branches é histórico; este suplemento reconcilia as oito refs do arquivo atualmente observadas. O gate de exclusão deve permanecer bloqueado para dependências externas não confirmadas, cópia independente não verificada e ausência de autorização explícita. O Google Drive foi dispensado pelo proprietário para aceite do acervo, sem eliminar o risco de conta única.

Evidências: [PR #61](https://github.com/ianmaciel7/exams-app-archive/pull/61), [auditoria atual](ARCHIVE-STATUS-2026-11-24.md).
