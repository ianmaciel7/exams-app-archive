# Benchmark e Avaliacao Comparativa: Representacao em Grafo Multi-Repo (Issue #30)

Data da avaliacao: 2026-11-24  
Issue de referencia: `#30` (complementa `#29`, `#8`, `#5`, `#24` e `#31`)  
Implementacao PoC: `scripts/graph_linker.py` | Testes: `tests/test_graph_linker.py`

---

## Decisao Executiva

| Candidato | Licenca | Runtime / Banco | Decisao | Justificativa resumida |
|---|---|---|---|---|
| **Grafo relacional leve em SQLite (`scripts/graph_linker.py`)** | Public Domain / PSF (stdlib) | SQLite (`graph_nodes`, `graph_edges`, `graph_nodes_fts`) + JSON inerte opcional | **ADOTAR como padrao** | Zero daemon, zero dependencia externa, multi-repo e multibranch por `(repo, ref, commit_sha)`, latencia 31-145 ms em warm query no corpus real (6.076 nos, 13.724 arestas), 19.04 MiB SQLite, 76.1 MiB RAM pico |
| **Graphify (`Graphify-Labs/graphify`)** | Apache-2.0 (partes MIT) | Python 3.10+ / tree-sitter + `graph.json` / `graph.html` (opcional Neo4j/FalkorDB) | **ADAPTAR IDEIA / OPCIONAL no build** | Ideia valiosa: separacao explicita de confianca `EXTRACTED` vs `INFERRED` e extracao AST deterministica (`--code-only`). Rejeitar como runtime obrigatorio por foco em snapshot unico de working tree e necessidade de LLM para docs/imagens |
| **Graphicle (`Graphicle-AI/graphicle`)** | Apache-2.0 | Binario Rust + SQLite local + MCP/HTTP (`127.0.0.1`) | **ADAPTAR IDEIA / OPCIONAL** | Port Rust rapido do Graphify que ja demonstra viabilidade de armazenar grafo + memoria em **um unico SQLite** com estados de frescor/invalidacao quando o codigo ancora muda. Nao adotar daemon/MCP obrigatorio |
| **Codebase Memory MCP (`DeusData/codebase-memory-mcp`)** | MIT | Binario C/Go + MCP server + UI web (`port 9749`) | **OPCIONAL (somente local/offline) / NAO no core** | Bom call-graph cross-repo e 159 linguagens via tree-sitter, porem exige servidor MCP/binario nativo fora da stdlib Python e nao resolve snapshots historicos apagados nem releases privadas sem PC ligado |
| **GitNexus (`abhigyanpatwari/GitNexus`)** | **PolyForm-Noncommercial-1.0.0** | TypeScript / Node.js + grafo embutido | **REJEITAR** | Licenca nao comercial (`PolyForm-Noncommercial-1.0.0`), dependencia de runtime Node/JS e foco em analise de repositorio ativo unico, sem modelo nativo multibranch/temporal para Git Bundles |
| **CodeGraph (`colbymchenry/codegraph`)** | MIT | Kernel Rust + tree-sitter + SQLite + watcher/MCP via npm | **REJEITAR para o core (opcional local)** | Excelente ergonomia em repositorios ativos via file watcher, porem dependente de binario Rust/npm e focado na arvore corrente; nao modela decisoes, imagens deletadas e refs historicas multi-repo |
| **Trail-Code (`trailhq/Trail-Code`, ex-Graft)** | MIT | TypeScript / Node.js + `.trail/` Markdown + hooks | **ADAPTAR IDEIA / REJEITAR ferramenta** | Modelo de `learnings` em arquivos versionados e util como inspiracao, mas ja temos PRs/issues/reviews/commits indexados em `#8` (`context_linker.py`). Gravar memorias de agentes como fatos sem evidencia de SHA viola o contrato de proveniencia |

---

## 1. Contexto e Criterios da Issue #30

O `exams-app-archive` consolida historicos de **multiplos repositorios e dezenas de refs/branches** (`exams-app`, `exams-app-old`, `exams-app-antigo-2`, `notes-app@old` a `old-11`, templates), com codigo recuperado de Git Bundles, metadados de plataforma em `inventory/` (PRs, issues, diffs, reviews, workflow runs) e catalogos de imagens (`scripts/image_catalog.py`).

Requisitos arquiteturais que restringem a escolha:
1. **Multibranch e multi-repo temporal**: uma mesma entidade (ex.: `Sidebar` / `barra lateral`) aparece em `notes-app@old-5`, `notes-app` PR #40, `exams-app@dev` e `exams-app@chore/consolidate-legacy-sources-20261123` com implementacoes, screenshots e decisoes distintas ao longo do tempo.
2. **Proveniência exata e separacao fato vs inferencia**: toda relacao precisa apontar `(repo, ref, commit_sha, path)` e distinguir `EXTRACTED` (ex.: diff real, import AST/regex deterministico, commit->file) de `INFERRED` (ex.: associacao de diretorio irmao ou decisao por palavra-chave).
3. **Acesso com PC desligado e CI leve**: o indice deve rodar em Python 3.12 stdlib-only dentro de GitHub Actions (`archive-private-search.yml`) e no plugin portatil, sem exigir daemon, Neo4j, FalkorDB ou binario MCP residente.
4. **Seguranca de memoria e licencas**: memorias de agentes nao podem virar fatos automaticos sem ancora + status de frescor (`valid_in_commit`, `superseded_in_later_branch`, `unverified`).

---

## 2. Medicoes Reproduziveis do Prototipo Leve (`scripts/graph_linker.py`)

O modulo `scripts/graph_linker.py` implementa um grafo de propriedades tipado diretamente sobre SQLite (e exportacao JSON inerte opcional):

- **Nos (`graph_nodes`)**: `Repo`, `Ref`, `Commit`, `File`, `Component`, `PR`, `Issue`, `Image`, `Decision`.
- **Arestas (`graph_edges`)**: `MODIFIES`, `DOCUMENTED_IN`, `EVIDENCED_BY`, `SUPERSEDES`, `IMPORTS`, `CO_OCCURS_WITH`.
- **Indice auxiliar**: `graph_nodes_fts` (SQLite FTS5 `unicode61`) + expansao bilingue PT<->EN (`scripts/search_expansion.py`) para resolver consultas como `barra lateral` e `Sidebar` no mesmo no canonico `component:sidebar`.

### Execucao Real sobre `inventory/` do Repositorio

Comando reproduzivel:

```bash
python3 scripts/graph_linker.py benchmark
```

Metricas medidas diretamente sobre `inventory/exams-app-branch-files.json` + `inventory/notes-app/`:

| Metrica | Valor medido |
|---|---:|
| Tempo total de construcao (ingestao + links `SUPERSEDES` + FTS5) | **16.44 s** (16.438 ms) |
| Pico de memoria RAM em Python (`tracemalloc`) | **76.09 MiB** |
| Tamanho do arquivo SQLite (`graph-linker.sqlite`) | **19.04 MiB** (19.968.000 bytes) |
| Tamanho da exportacao JSON inerte (`graph.json`) | **11.06 MiB** (11.599.427 bytes) |
| Total de nos | **6.076** (`File`: 4.349, `Image`: 1.083, `Component`: 405, `Decision`: 129, `Commit`: 52, `PR`: 50, `Ref`: 4, `Issue`: 2, `Repo`: 2) |
| Total de arestas | **13.724** (`MODIFIES`: 7.260, `EVIDENCED_BY`: 5.076, `IMPORTS`: 955, `DOCUMENTED_IN`: 189, `CO_OCCURS_WITH`: 169, `SUPERSEDES`: 75) |
| Distribuicao de confianca | **7.845 `EXTRACTED`** (57.2%) / **5.879 `INFERRED`** (42.8%) |

### Latencia e Cobertura das Consultas de Vizinhanca (2-hop BFS + Impacto Temporal)

| Consulta | Cold/Bench (ms) | Warm mediana (ms) | Repositorios alcancados | Decisoes vinculadas | Imagens vinculadas |
|---|---:|---:|---|---:|---:|
| `Sidebar` (equivale a `barra lateral`) | 851.3 ms | **145.0 ms** (min 142.0 ms) | `exams-app`, `notes-app` | 23 | 71 |
| `GraphCanvas` | 251.4 ms | **53.3 ms** (min 48.1 ms) | `exams-app`, `notes-app` | 0 (codigo/PRs/imagens) | 48 |
| `AppShell` | - | **32.7 ms** (min 31.3 ms) | `exams-app`, `notes-app` | 2-13 | 74 |
| `FSRS` | - | **199.8 ms** (min 195.9 ms) | `exams-app`, `notes-app` | 52 | 39 |

Observacao sobre a pergunta de teste *"quais decisoes e imagens afetam a Sidebar ao longo dos repositorios?"*:
- A consulta `Sidebar` (ou `barra lateral` via expansao PT<->EN) atravessa os dois repositorios simultaneamente, retornando decisoes documentadas em `exams-app` (ex.: `docs/Documentos/01-planejamento/revisao/app-shell/decisoes.md`, `sidebar-comparacao-2026-11-23.md`), decisoes de PRs de `notes-app` (ex.: `PR #38`, `PR #40`, `PR #33` com `add-app-sidebar`), capturas de prototipo (`m-dark-2-gaveta.png`, `d-dark-1.png`), screenshots Capacities (`capacities-sidebar-task-placement-2026-08-24.webp`) e arestas `SUPERSEDES` marcando decisoes antigas como `superseded_in_later_branch`.

---

## 3. Comparativo Tecnico Detalhado

### 3.1 Latencia, Footprint de Armazenamento e RAM

| Solucao | Latencia tipica de consulta | Footprint em disco | RAM em runtime | Daemon / Processo residente |
|---|---|---|---|---|
| **Grafo SQLite (`graph_linker.py`)** | **31 - 199 ms** (warm 2-hop BFS), <5 ms para 1-hop direto | **~19 MiB** SQLite (comprimivel para ~3-4 MiB `.gz` em release) | **~76 MiB** pico na construcao; <20 MiB em consulta | **Nenhum** (CLI / biblioteca Python stdlib) |
| **Graphify** | ~50 - 300 ms em JSON em memoria | `graph.json` + `graph.html` + `GRAPH_REPORT.md` (10-40 MiB em repos grandes; opcional Neo4j/FalkorDB) | ~150 - 400 MiB (Python + NetworkX/tree-sitter; +1 GB se Neo4j) | Opcional (watch / Neo4j se habilitado) |
| **Graphicle** | Sub-10 ms - 50 ms (kernel Rust + SQLite) | SQLite unico em `~/.local/share/graphicle` + `.graphicle/` | ~50 - 150 MiB (Rust) | HTTP/MCP loopback (`127.0.0.1`) |
| **Codebase Memory MCP** | Sub-ms a ~15 ms (grafo em C/SQLite) | Artefato `.codebase-memory/` compactado (zstd) | ~50 - 150 MiB | Servidor MCP (stdio/HTTP UI `9749`) |
| **GitNexus** | ~10 - 100 ms (grafo embutido) | Indice local em disco por workspace | ~200 - 500 MiB (Node.js) | Zero-server CLI/MCP via Node.js |
| **CodeGraph** | ~5 - 40 ms (Rust + SQLite) | SQLite local por projeto | ~60 - 180 MiB (Rust + file watcher) | File watcher + MCP server |
| **Trail-Code** | ~3 - 30 ms (leitura direta de `.md` / `wiring.json`) | Arquivos Markdown em `graft/` + `.trail/` | ~80 - 250 MiB (Node.js) | Hooks por turno + CLI |

### 3.2 Capacidade Multi-Repo, Temporalidade e Proveniencia

| Criterio | SQLite Relacional (`graph_linker.py`) | Graphify | Graphicle | Codebase Memory MCP | GitNexus | CodeGraph | Trail-Code |
|---|---|---|---|---|---|---|---|
| **Multi-repo no mesmo grafo** | **Nativo** (`repo` em todo no/aresta + `Component` canonico cross-repo) | Parcial (1 projeto por execucao; exige merge manual) | Parcial (projetos em store unico, sem modelagem de bundles) | Sim (cross-repo no MCP) | Nao nativo para bundles arquivados | Focado em 1 workspace ativo | Focado em 1 repo Git por `.trail/` |
| **Multibranch / commits deletados** | **Nativo** (`Ref` + `Commit` + `validity_status` por commit) | Nao (le arvore atual; `graphify-out/` diverge entre branches) | Parcial (rastreia mudancas atuais; nao navega Git Bundles antigos) | Nao (indexa working tree; sem multi-ref historico) | Nao (snapshot atual) | Nao (auto-sync no working tree) | Apenas working tree + diffs recentes |
| **Separacao `EXTRACTED` vs `INFERRED`** | **Nativo** (campo `confidence` obrigatorio em `graph_edges`) | **Nativo** (tags `EXTRACTED` / `INFERRED`) | **Nativo** (herdado do Graphify + hash de invalidação) | Extracao AST deterministica | Extracao AST/call-graph | Extracao AST tree-sitter | Nao separa bem sumarizacao LLM de AST sem `graft check` |
| **Vinculo a Imagens / Screenshots** | **Nativo** (`Image` + `EVIDENCED_BY` via diffs, docs e catalogo) | Exige LLM/visao (custo de API e risco de privacidade) | Exige LLM para imagens/docs fora de `--code-only` | Nao focado em screenshots de UI | Nao | Nao | Nao |
| **Funciona com PC desligado (Actions + Release)** | **Sim (100%)** — Python stdlib em workflow privado | Precisa `pip install graphifyy` + pinning de tree-sitter | Precisa baixar binario Rust em runner Linux | Precisa baixar binario nativo em runner | Precisa Node + dependencias npm | Precisa binario Rust/npm | Precisa Node + `node-gyp` |

### 3.3 Avaliacao Especifica das Novas Ferramentas (Atualizacao 23/11/2026)

1. **Graphicle (`Graphicle-AI/graphicle`, Apache-2.0)**:
   - Implementacao em Rust do motor de grafo do Graphify (ate `0.9.103`), armazenando fontes, memorias e grafo em **um unico SQLite local**.
   - **O que aproveitar (adaptar ideia)**: o mecanismo de **ancora de memoria por simbolo/arquivo + invalidacao com recibo quando o codigo ancora muda**. Em `scripts/graph_linker.py`, esse conceito foi prototipado como `Decision -> Component/File -> commit_sha -> validity_status` (`valid_in_commit`, `superseded_in_later_branch`, `unverified`) com arestas `SUPERSEDES`.
   - **Por que nao adotar o binario**: exige distribuicao de binario Rust externo, foca em workspace local ativo (nao Git Bundles historicos) e o fluxo completo de docs/imagens usa chamadas a LLM.

2. **Trail-Code (`trailhq/Trail-Code`, MIT)**:
   - Gera mapa de codigo (`graft` via tree-sitter) e camada de `learnings` em Markdown (`.trail/`).
   - **O que evitar**: importar `learnings` gerados por sessoes de agentes como verdade historica. No `exams-app-archive`, o `context_linker.py` (`#8`) ja indexa PRs, reviews, comentarios inline, issues e commits originais com citacao literal ou retorno explicito de `"sem justificativa citada"`.
   - **Conclusao**: Trail-Code nao acrescenta contexto verificavel alem dos metadados ja preservados em `inventory/` e traz risco de misturar inferencias de sessao com fatos historicos.

3. **Codebase Memory MCP (`DeusData/codebase-memory-mcp`, MIT) e CodeGraph (`colbymchenry/codegraph`, MIT)**:
   - Ambos possuem excelente analise estatica de call-graph via tree-sitter, mas operam como **servidores MCP / indexadores de arvore ativa**.
   - Para codigo historico estatico de bundles (`old-5`, `old-10`, `old-11`, `exams-app@dev`), o ganho de call-graph profundo pode ser obtido pontualmente no build (ou via SCIP em `#31`) sem acoplar o arquivo a um daemon MCP.
   - Nota de seguranca observada no historico do `codebase-memory-mcp`: vulnerabilidade corrigida apenas na v0.9.0 (`CVE-2026-114495` em descompressao zstd de artefatos `.codebase-memory/`), reforcando a vantagem de manter o parser do core em Python stdlib auditavel sobre JSON/SQLite/Git puro.

4. **GitNexus (`abhigyanpatwari/GitNexus`, PolyForm-Noncommercial-1.0.0)**:
   - **Rejeitado** por licenca restritiva (nao comercial) e por nao atender ao requisito de multi-repo/multibranch offline em Python stdlib.

---

## 4. Complexidade de Manutencao e Evolucao Recomendada

Manter um **grafo relacional leve embutido no SQLite existente** (ou em `graph-linker.sqlite` reconstruivel em conjunto com `archive-index.sqlite` / `context-linker.sqlite`) apresenta menor custo total de manutencao porque:

1. **Mesmo stack do repositorio**: 100% Python 3.12 stdlib + SQLite3 (mesma base de `archive_index.py`, `context_linker.py`, `selective_context.py` e `image_catalog.py`).
2. **Schema minimo e portavel**: apenas duas tabelas principais (`graph_nodes`, `graph_edges`) e uma tabela virtual FTS5 (`graph_nodes_fts`), totalmente reconstruiveis a partir dos Git Bundles e `inventory/` versionados no repo.
3. **Sem daemon, sem porta aberta, sem MCP obrigatorio**: funciona em `pytest`, GitHub Actions (`archive-private-search.yml`), plugin portatil e ambientes sem Node/Rust/Docker.
4. **Caminho claro para `#31` (SCIP) e AST pontual**: quando precisarmos de call-graph preciso em TypeScript (`IMPORTS` e chamadas de funcoes em `old-5`/`old-11`/`exams-app@dev`), basta um importador batch offline de indices SCIP que popula `graph_edges` com `edge_type='IMPORTS'` e `confidence='EXTRACTED'`, sem trocar o motor de armazenamento ou consulta.

### Recomendacao Final

1. **MANTER E ADOTAR** o modelo relacional leve em SQLite (`scripts/graph_linker.py`) integrado ao pipeline de indices do `exams-app-archive`, publicavel na release privada junto ao `full-index.sqlite`.
2. **ADAPTAR IDEIAS** do **Graphify** (`EXTRACTED` vs `INFERRED` obrigatorio em cada aresta) e do **Graphicle** (estado de validade temporal `valid_in_commit` / `superseded_in_later_branch` para decisoes ancoradas em `Component` e `commit_sha`).
3. **NAO ADOTAR** daemon, servidor MCP residente, Neo4j/FalkorDB, **GitNexus** (licenca nao comercial) ou **Trail-Code** (nao substitui nem supera os PRs/reviews reais ja indexados em `#8` e introduz risco de memoria nao comprovada).
4. **DEIXAR OPCIONAL** o uso local de **Graphify** (`--code-only`) ou **Codebase Memory MCP** / **CodeGraph** apenas durante desenvolvimento em repositorios ativos, nunca como dependencia do arquivo historico nem de workflows de busca remota.
