# Prova de conceito real — Git histórico + SQLite FTS5

Gerada em 2026-11-23T17:58:11.650630+00:00 (UTC). Fonte: Git, sem LLM/embeddings.

| Fonte | Refs | Commits | Alterações | Imagens | Tempo |
|---|---:|---:|---:|---:|---:|
| exams-app-old | 167 | 780 | 13676 | 14 | 1.16 s |
| exams-app-antigo-2 | 234 | 1051 | 18279 | 1563 | 13.36 s |
| notes-app-old-10 | 1 | 110 | 711 | 7 | 0.02 s |

## Recuperação de evidências

- Bundle histórico validado: **True** — `prototype/notes-app-old-10.bundle`
- Imagem removida recuperada e hash Git verificado: **True**
- Código histórico `src/domain/recall.ts` recuperado: **True**
- Tempo total: **14.94 s**; índice SQLite: **14.16 MiB**

- Evidência de imagem: `exams-app-antigo-2` / `prototypes/board-exam-app/assets/issue68_graph_toolbar_1366.png` / commit `65ce2ab7ac95e8fc4e1be998eb0aa593049bf2c8` / blob `216b4d240c7a05ff2656745f9dd28ccb1d117f6f`

- Evidência de código: `notes-app-old-10` / `src/domain/recall.ts` / commit `cabcec2e8227fc7f06aa5c9c5afcc0e8944802c6`

## Buscas reais

| Busca | Resultados | Latência | Exemplo |
|---|---:|---:|---|
| firebase | 8 | 0.41 ms | `feat(tooling): configure MDX, bundle analyzer, codemod,` |
| grafo | 8 | 0.1 ms | `feat(capacities-graph-engine): painel direito do grafo ` |
| qconcursos | 8 | 0.09 ms | `Add QConcursos inventory for issue #31` |
| recall | 8 | 0.07 ms | `feat: close remaining Recall punch-list items (accessib` |
| capacit | 8 | 0.07 ms | `feat(capacities-graph-engine): painel direito do grafo ` |

## Limitações e próximos passos

- Não é migração completa: esta prova indexa duas fontes públicas e um bundle histórico.
- Sem cópia dos objetos Git para este repositório, a recuperação ainda depende da disponibilidade das fontes originais.
- Não indexa automaticamente todo o `notes-app` privado; exige autorização de acesso entre repositórios ou importação controlada de bundles.
- Próximo passo: verificar demais bundles, integrar históricos aprovados e ampliar a cobertura de consultas/contratos.

Os dados estruturados, SHAs e hashes estão em `POC.json`. O SQLite pode ser regenerado usando `scripts/run_poc.py`.
