# Mapa GitHub — histórico e fontes da UI

## Backup histórico (repositório tornado público em 24/11/2026)
- `ianmaciel7/exams-app-archive@main`: `README.md`, `docs/VERIFICATION-2026-11-23.md`, `docs/DELETE-READINESS.md`.
- Restauração: `docs/EXTRACTION-GUIDE.md`, `docs/EXAMS-APP-COMPLETE.md`.
- Índices e referências: `reports/FULL-INDEX.md`, `reports/FULL-INDEX.json`, `reports/POC.md`, `manifests/ALL-REFS.md`, `inventory/exams-app-branch-files.json`.
- Notes: `inventory/notes-app/README.md`; conferir pendências de branches/tags privadas antes de afirmar completude.
- Consulta remota: `docs/PRIVATE-CHATGPT-SEARCH.md` e `references/private-fts5.md` (branch `archive-search-queries`; não usar para consultas privadas enquanto o repositório estiver público). Índice da release `index-2026-11-23-exams-complete`.

## Fontes de UI diretamente consultáveis (não confundir com backup)
- `ianmaciel7/exams-app@dev`: `docs/Documentos/01-planejamento/revisao/sidebar-prototipo/prototipo-sidebar.html` (HTML standalone), `decisoes.md` e `capturas/` (26 PNGs).
- `ianmaciel7/exams-app@dev`: `docs/Documentos/01-planejamento/revisao/sidebar-comparacao-2026-11-23.md`, `docs/context/memoria/sidebar-referencias-repos.md`, `docs/Documentos/01-planejamento/revisao/app-shell/decisoes.md`.
- `ianmaciel7/notes-app@old-5`: `src/app/globals.css` para tokens visuais de referência (confirmar SHA atual).

Para UI consulte `skills/ui-fidelity/references/source-map.md` e evite FTS5 quando a fonte está acessível por caminho. O `exams-app@dev` já existia: consultas não autorizam criar ou apagar branch.

## Fontes que faltavam na indexação visual anterior
- `ianmaciel7/notes-app@old-5`: pasta `src/app/_components/workspace/` com **56 arquivos** de UI + Ladle stories; `src/components/ui/shared-styles.ts` e `compact-menu.tsx`; `src/app/_components/objects/object-icons.tsx`; `src/app/globals.css`.
- `ianmaciel7/notes-app@old-4`: `docs/DESIGN.md` e `docs/references/capacities-workspace-parity.md` (métricas de layout historicamente medidas).
- `ianmaciel7/exams-app-antigo-2@dev`: `prototype/exam-app-0.1.1__index.html`, `prototype/lowchrome_97_manifest.json` e 48 capturas `lowchrome_97_*.png` do shell.
- `ianmaciel7/exams-app@dev`: `docs/Documentos/02-referencias/inventario-recuperadas.md` com 213 imagens únicas e diretórios `imagens/recuperadas/` por referência (99 Capacities, 70 Readwise, 39 QConcursos, 5 ExamTopics).
Para lista exata, SHAs e QA: `skills/ui-fidelity/references/visual-source-catalog.md`.

## Componentes e ferramentas
`docs/COMPONENT-EXPLORER.md`, `docs/AGENT-ACCESS.md`, `scripts/component_catalog.py`, `scripts/archive_mcp.py`, `site/files.html`, `site/llms.txt`: ver skill `component-explorer`.
