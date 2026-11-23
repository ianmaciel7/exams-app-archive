# Prova de conceito real — Git histórico + SQLite FTS5

Gerada em 2026-11-23T23:26:16.490912+00:00 (UTC). Fonte: Git, sem LLM/embeddings.

| Fonte | Refs | Commits | Alterações | Imagens | Tempo |
|---|---:|---:|---:|---:|---:|
| exams-app-old | 167 | 780 | 13676 | 14 | 1.02 s |
| exams-app-antigo-2 | 234 | 1051 | 18279 | 1563 | 11.21 s |
| notes-app-old-10 | 1 | 110 | 711 | 7 | 0.02 s |

## Recuperação de evidências

- Bundle histórico validado: **True** — `prototype/notes-app-old-10.bundle`
- Imagem removida recuperada e hash Git verificado: **True**
- Código histórico `src/domain/recall.ts` recuperado: **True**
- Tempo total: **12.65 s**; índice SQLite: **14.16 MiB** (`archive-index.sqlite.gz`: **2.39 MiB**)
- SHA-256 `archive-index.sqlite`: `7f3dd76cd7ff116948bf8593cf5faab35f5d960c78175fbe72dc20d6227fc6fc`
- SHA-256 `archive-index.sqlite.gz`: `9ac4c54b46c9987be3eede9ec68dbe57115f0fdedcf1018dadf20b21d180cc7c`
- Release privada do índice POC: `poc-archive-index` (publicado: **True**)

- Evidência de imagem: `exams-app-antigo-2` / `prototypes/board-exam-app/assets/issue68_graph_toolbar_1366.png` / commit `65ce2ab7ac95e8fc4e1be998eb0aa593049bf2c8` / blob `216b4d240c7a05ff2656745f9dd28ccb1d117f6f`

- Evidência de código: `notes-app-old-10` / `src/domain/recall.ts` / commit `cabcec2e8227fc7f06aa5c9c5afcc0e8944802c6`

## Buscas reais

| Busca | Resultados | Latência | Exemplo |
|---|---:|---:|---|
| firebase | 8 | 0.45 ms | `feat(tooling): configure MDX, bundle analyzer, codemod,` |
| grafo | 8 | 0.1 ms | `feat(capacities-graph-engine): painel direito do grafo ` |
| qconcursos | 8 | 0.09 ms | `Add QConcursos inventory for issue #31` |
| recall | 8 | 0.06 ms | `feat: close remaining Recall punch-list items (accessib` |
| capacit | 8 | 0.07 ms | `feat(capacities-graph-engine): painel direito do grafo ` |

## Limitações e próximos passos

- Não é migração completa: esta prova indexa duas fontes públicas e um bundle histórico.
- Sem cópia dos objetos Git para este repositório, a recuperação ainda depende da disponibilidade das fontes originais.
- Não indexa automaticamente todo o `notes-app` privado; exige autorização de acesso entre repositórios ou importação controlada de bundles.
- Próximo passo: verificar demais bundles, integrar históricos aprovados e ampliar a cobertura de consultas/contratos.

Os dados estruturados, SHAs e hashes estão em `POC.json`. O SQLite é publicado como asset comprimido na release privada e pode ser regenerado usando `scripts/run_poc.py`.
