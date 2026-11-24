# Matriz de Integracao de Melhorias Aprovadas (Issue #36)

Data da integracao: 2026-11-24  
Issue de implementacao: `#36`  
Issues consolidadas: `#9`, `#10`, `#30`, `#31`, `#32`, `#33` (alinhado com `#5`, `#6`, `#7`, `#8`, `#16`, `#24`, `#29`)

---

## 1. Principios Arquiteturais Inegociaveis

1. **Zero novos daemons obrigatorios:** nenhuma funcionalidade integrada requer servidor MCP residente, banco de grafos externo (Neo4j/FalkorDB), file watcher ou processo Node/Rust em background.
2. **Zero quebra de bundles imutaveis:** os Git Bundles em releases privadas permanecem fontes historicas imutaveis verificadas por SHA-256 e manifesto; todos os indices SQLite derivados sao reconstruiveis a partir dos bundles e de `inventory/`.
3. **Zero egress e Zero Emoji:** operacao 100% offline/local em Python 3.12 stdlib, sem envio de codigo privado a APIs externas, sem execucao automatica de codigo legado e sem emojis em scripts, relatorios ou testes.
4. **Compatibilidade retroativa estrita:** a CLI do plugin (`plugins/exams-archive-native/scripts/archive_query.py` e `plugins/exams-archive/scripts/archive_query.py`) preserva integralmente `sync`, `search`, `images`, `stats`, `export-pages` e `recover`, mantendo a identidade byte-a-byte verificada por `tests/test_multiagent_plugin.py`.

---

## 2. Matriz de Decisao Tecnica (Candidato x Feature x Baseline x Decisao)

| Issue | Candidate | Feature | Baseline | Ganho | RAM | Storage | Latencia | Tokens | Licenca | Telemetria / Egress | Decisao |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **#9** | Expansao PT<->EN (`scripts/search_expansion.py`) + BM25 (`#16`) | Dicionario bilingue `v1.0.0` (37 grupos) + cotas por tipo | FTS5 legado + BM25 sem sinonimos | Recall@8 `0.5259 -> 0.9630` (+83% rel.), Precision@8 `0.1944 -> 0.3750`, MRR `1.0000` | +~4 KiB codigo | 0 bytes extras no SQLite (`37.5 MiB` mantido) | 0.48 ms -> 0.67 ms (sintetico); 13-24 ms (live) | 128.7 -> 238.4 tokens/resposta | PSF / stdlib | Zero (offline) | **ADOTAR (Core)** — integrado em `scripts/archive_index.py` |
| **#9** | `QMD` / `picoqmd` / embeddings densos locais | Busca vetorial / hibrida com GGUF ou `sentence-transformers` | FTS5 + BM25 + PT<->EN | Inferior ao baseline PT<->EN no proxy (`0.7000` recall vs `0.9630`) | ~300 MiB - 1.5 GiB | +300 MiB - 2.2 GiB modelos | ~50 - 400 ms | ~250 - 500 | MIT / Apache-2.0 | Risco de download HF no 1o uso | **REJEITAR no Core** (opcional fora do core) |
| **#9** | Busca visual (`CLIP` / OCR offline em imagens) | Recuperacao de screenshots com nomes opacos (`img_0042.png`) | Busca lexical em `images.path` | Resolve 1/3 misses opacos (`q_nondescriptive_img`) | ~1 - 3 GiB | Pesos CLIP/OCR | Segundos/imagem | N/A | Apache-2.0 / MIT | Requer pre-cache offline | **FERRAMENTA OPCIONAL (trilha separada)** |
| **#10** | Contexto seletivo com orcamento (`scripts/selective_context.py`) | `metadata-only`, `snippet`, `exact-file`, `context-pack` + dedup por `blob_sha` | `exact_no_dedup` (33 unidades, 25.517 tokens) | **-88.16%** com dedup (`3.022` tokens) e **-93.09% / -93.21%** em `context-pack` / `snippet` | < 10 MiB | 0 bytes extras | ~40 - 119 ms | 25.517 -> 1.733 / 1.762 | PSF / stdlib | Zero (offline + filtro triplo de segredos) | **ADOTAR (Core)** |
| **#10** | `Repomix` (`--compress` Tree-sitter) | Compactacao AST via CLI `--use-repomix` | `builtin-outline` (`context-pack`) | -31.75% vs `exact_with_dedup`, porem pior que `builtin-outline` (-60.99%) | Overhead Node | Temp isolado | ~2.579 ms (~22x mais lento) | 1.391 (vs 795 nativo) | MIT | Offline apenas sem `--remote` | **FERRAMENTA OPCIONAL DE BUILD** (`--use-repomix`) |
| **#30** | Grafo relacional SQLite (`scripts/graph_linker.py`) | Nos tipados + arestas `EXTRACTED`/`INFERRED` + `SUPERSEDES` temporal + FTS5 | Busca plana sem vinculo cross-repo | Atravessa `exams-app` + `notes-app`, vincula 23 decisoes e 71 imagens para `Sidebar` | 76.09 MiB pico build (<20 MiB query) | 19.04 MiB SQLite (6.076 nos, 13.724 arestas) | 31 - 199 ms warm 2-hop BFS | Compacto por vizinhanca | PSF / stdlib | Zero (offline, zero daemon) | **ADOTAR (Core)** — integrado na CLI como `archive_query.py graph` |
| **#30** | `Graphify` & `Graphicle` | Separacao `EXTRACTED` vs `INFERRED` e invalidacao temporal por ancora | Grafo sem status de obsolescencia | Conceitos incorporados em `graph_edges.confidence` e `validity_status` | 50 - 400 MiB | SQLite / JSON local | 10 - 300 ms | 0 em `--code-only`; alto em LLM | Apache-2.0 | Graphify Cloud / LLM docs; Graphicle update notifier | **ADAPTAR CONCEITO** (runtime opcional `--code-only`) |
| **#30** | `Codebase Memory MCP` / `CodeGraph` | Call-graph via Tree-sitter em working tree ativa | Ingestao batch de bundles/inventarios | Call-graph local ativo, mas nao le Git Bundles nem imagens deletadas | 50 - 180 MiB | Indice local separado | < 40 ms | N/A | MIT (`colbymchenry`; `AGPL` em homonimo) | Servidor MCP / watcher local | **FERRAMENTA OPCIONAL LOCAL / REJEITAR no Core** |
| **#30** | `GitNexus` / `Trail-Code` | Grafo Node/JS (`GitNexus`) e `learnings` de agentes (`Trail-Code`) | `context_linker.py` (`#8`) com citacoes reais | Sem ganho verificavel sobre PRs/reviews reais; `Trail-Code` mistura sessao com fatos | 80 - 500 MiB | `.trail/` / workspace | 3 - 100 ms | N/A | **PolyForm-Noncommercial** (`GitNexus`) / MIT | Risco `--pair`/`--connect` no Trail | **REJEITAR** (`GitNexus` por licenca; `Trail-Code` por contrato de proveniencia) |
| **#31** | Chunker AST estrutural (`scripts/ast_chunker.py`) | AST Python (`ast`) + lexer/parser TS/TSX/JS/CSS/HTML + `MotionContract` | Janela fixa de 40 linhas (`content_index.py`) | Recall@3 `0.1667 -> 1.0000`, Cohesive Structure `0.0000 -> 1.0000`, 28 contratos de motion | 193.10 KiB pico | Chunks sob demanda / dedup por `blob_sha` | 72.8 ms (corpus 5 arqs) | 302.67 tokens top-1 sem truncar | PSF / stdlib | Zero (analise estatica pura) | **ADOTAR (Core)** — integrado na CLI como `archive_query.py ast` |
| **#31** | `ast-grep` / `CocoIndex Code` / `Probe` / `sqry` / `SCIP` | Regras Tree-sitter, cache por hash, `symbol_id` | `ast_chunker.py` stdlib + fallback 40 linhas | Cache por `(blob_sha, extractor_version)` e `symbol_id` adaptados; `scip-typescript` falha em `old-1..11` sem `node_modules` | Binarios Rust / Node / Postgres | Indices paralelos | Variavel | N/A | MIT / Apache-2.0 | CocoIndex tem telemetria opt-out | **ADAPTAR CONCEITO** (`CocoIndex`/`SCIP`); `ast-grep` **OPCIONAL**; rejeitar no runtime |
| **#32** | Extrator documental deterministico (`scripts/document_extractor.py`) | Hierarquia `h1..h6`, tabelas, links de diagramas (`understood: false`), PDF nativo + FTS5 | Leitura bruta / grep sem hierarquia | 100% deterministico em 661+ `.md` e PDFs nativos; marca `image_only_needs_ocr` explicitamente | < 400 KiB (`docs/`/`reports/`) | SQLite opcional (`doc_elements_fts`) | 23 ms (fixtures) / 157-213 ms (acervo) | Reduz outline (ex.: 107 -> 72) | PSF / stdlib | Zero (offline) | **ADOTAR (Core)** |
| **#32** | `Docling` / `OpenDataLoader PDF` | OCR e layout deep-learning/JVM para PDFs escaneados complexos | `document_extractor.py` (0 PDFs binarios no snapshot 2026-11-23) | Necessario apenas se surgirem PDFs escaneados (`uninterpreted_pages`) | 300 MiB - 3 GiB | 50 MiB - 4 GiB modelos/JAR | Segundos/pag | N/A | MIT / Apache-2.0 (`>=2.0`) | Docling exige `HF_HUB_OFFLINE=1` | **FERRAMENTA OPCIONAL OFFLINE DE BUILD** |
| **#32** | `Xberg` / `PageIndex` | Parser Rust (`Xberg`) e arvore via LLM (`PageIndex`) | Arvore deterministica + `doc_elements_fts` | `PageIndex` envia PDFs privados a LLM e tem custo alto; `Xberg` exige binario Rust | Binario Rust / API LLM | N/A | Alto em `PageIndex` | Alto em `PageIndex` (0 no core) | MIT | `PageIndex` envia docs a LLM externo | **REJEITAR** (`PageIndex` por egress/tokens; `Xberg` nao supera stdlib no acervo atual) |
| **#33** | Gate local de segredos (`scripts/secrets_gate.py`) | Scan em arquivos, JSON, SQLite, logs e bundles Git + `sanitize` | Filtros individuais em `content_index.py` | Bloqueia 14 classes de segredos + `.env`/`.pem` sem nunca vazar valor bruto (`sha256:` truncado) | < 15 MiB | 0 bytes (report JSON opcional) | < 50 ms por artefato | N/A | PSF / stdlib | Zero (offline) | **ADOTAR (Core)** — integrado na CLI como `archive_query.py secrets-check` |
| **#33** | `Gitleaks` (CLI MIT) & `Playwright` / `DevTools MCP` / `rrweb` | Segunda linha SAST (`--redact`) e observabilidade UI isolada | `secrets_gate.py` + QA estatico | Reforca SAST local quando instalado; browser/DOM exigem flags estritas e sanitizacao | Binario Go / Chromium | Efemero | ~100 ms - segundos | N/A | MIT / Apache-2.0 | Clearcut/CrUX no DevTools MCP sem opt-out; `rrweb` captura DOM | **OPCIONAL COM ISOLAMENTO ESTRITO** (`--no-usage-statistics --no-performance-crux --isolated`, masking `rrweb`) |
| **#8 / #29** | Context Linker (`scripts/context_linker.py`) | Timeline cronologica por `(repo, path)` unindo commits, PRs, reviews, issues, imagens e gaps | Busca isolada em `archive_index` | Separa fatos (`objective_links`) de `"sem justificativa citada"` | < 30 MiB | SQLite reconstruivel | Sub-50 ms | Compacto por arquivo | PSF / stdlib | Zero (offline) | **ADOTAR (Core)** — integrado na CLI como `archive_query.py context` |

---

## 3. Pontos de Integracao na CLI do Plugin

A CLI canonica em `plugins/exams-archive-native/scripts/archive_query.py` (espelhada em `plugins/exams-archive/scripts/archive_query.py`) integra agora as capacidades consolidadas mantendo 100% de compatibilidade com os comandos legados (`sync`, `search`, `images`, `stats`, `export-pages`, `recover`):

1. `archive_query.py ast <path> [--lang ...] [--summary-only]`: executa `scripts/ast_chunker.py` para extrair chunks estruturais, `symbol_id`, `blob_sha` e `motion_contracts` sem executar codigo legado.
2. `archive_query.py graph [entity] [--graph-db ...] [--inventory-dir ...] [--archive-db ...] [--hops 2] [--repo ...] [--since ...] [--until ...] [--confidence EXTRACTED|INFERRED] [--stats]`: consulta ou constroi o grafo multi-repo via `scripts/graph_linker.py`, preservando proveniencia (`EXTRACTED` vs `INFERRED`) e `validity_status`.
3. `archive_query.py context [query] [--context-db ...] [--inventory-dir ...] [--git-source ...] [--repo ...] [--limit 20] [--stats]`: consulta ou indexa a linha do tempo cronologica de arquivos, PRs, reviews, imagens e lacunas via `scripts/context_linker.py`.
4. `archive_query.py secrets-check <target> [--allowlist ...] [--use-gitleaks]`: executa o gate independente `scripts/secrets_gate.py` sobre arquivos, diretorios, JSON, SQLite ou bundles Git (exit code `2` em bloqueio, zero vazamento de segredos).

Todos os novos subcomandos operam **sob demanda** via resolucao deterministica da pasta `scripts/` (`EXAMS_ARCHIVE_ROOT` ou ancestrais do repositorio), sem quebrar o funcionamento portatil standalone de `sync`/`search`/`images`/`stats`/`export-pages`/`recover` quando executado isoladamente com o cache local `~/.cache/exams-app-archive/full-index.sqlite`.

---

## 4. Lacunas Conhecidas e Limites Preservados

- O backup integral das 4 branches privadas ativas (`main`, `dev`, `stag`, `firebase/file`) e 3 tags de `notes-app` permanece pendente de autorizacao no repositorio de origem e e reportado explicitamente sem falsas afirmacoes de 100%.
- O catalogo `docs/UI-MOTION-EVIDENCE.json` e o `ast_chunker.py` entregam evidencias verificadas em codigo-fonte (`verified-in-source`), distintas de medicoes em navegador real.
- Nenhum bundle historico, manifest ou release privada foi alterado ou reempacotado nesta integracao.
