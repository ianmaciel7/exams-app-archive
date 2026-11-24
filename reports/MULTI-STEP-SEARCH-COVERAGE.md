# Busca Contextual Multi-Etapas e Garantia de Cobertura Historica (Issue #29)

Data da avaliacao: 2026-11-24  
Issue de referencia: `#29` (complementa `#5`, `#6`, `#7`, `#8`, `#9`, `#24`, `#30`, `#31`, `#32`, `#33`)  
Orquestrador reproduzivel: [`scripts/context_coverage.py`](../scripts/context_coverage.py)  
Suite de testes ponta a ponta: [`tests/test_context_coverage.py`](../tests/test_context_coverage.py)

---

## 1. Decisao Executiva

1. **Orquestrador multi-etapas integrado (`scripts/context_coverage.py`)**: **ADOTAR como padrao** para pesquisas historicas entre repositorios, encadeando `search_expansion.py` (PT<->EN) -> `archive_index.py` (FTS5 + BM25 + varredura por repositorio) -> `graph_linker.py` (nos/arestas + supersessao temporal) -> `ast_chunker.py` (AST + contratos de motion) -> `context_linker.py` (PRs/issues/reviews/imagens com citacao literal ou `"sem justificativa citada"`).
2. **Garantia de cobertura `coverage@source`**: Nenhuma consulta com intencao exaustiva (`"todas"`, `"em todos os repositorios"`, `"historico completo"`) pode declarar inventário completo sem enumerar todos os **9 repositorios** de `inventory/source-refs-2026-11-23.json` (8 origens pesquisaveis + `exams-app-archive` excluido de auto-snapshot) e todas as branches candidatas, incluindo branches antigas (`notes-app@old-2`, `old-4`, `old-5`, `old-10`, `old-11`, `exams-app-antigo-2@dev`, `exams-app@dev`).
3. **Comparacao com `grepai` e `XERJ`**: **NAO NECESSARIAS** no core ou como servico permanente. A linha de base integrada stdlib ja atinge **`coverage@source = 1.0000` (100% dos repositorios pesquisaveis) e `1.0000` das branches candidatas** sem servidor de embedding externo (Ollama/vectordb) e sem dependencia Rust/Go adicional.

---

## 2. Arquitetura do Pipeline Multi-Etapas (`scripts/context_coverage.py`)

O orquestrador executa 6 passos deterministicos (Etapa 0 a Etapa 5):

1. **Etapa 0 — Descoberta de fontes e classificacao de intencao (`load_source_catalog`, `classify_query_intent`)**:
   - Le `inventory/source-refs-2026-11-23.json` e enumera os **9 repositorios** (`fcc-responsive-web-design`, `ianmaciel7`, `notes-app`, `shadcn-template`, `shadcn-firebase-template`, `exams-app-old`, `exams-app-antigo-2`, `exams-app`, e `exams-app-archive` marcado como `excluded_self`).
   - Classifica pedidos com termos exaustivos (`todas`, `todos`, `em todos`, `completo`, `historico`) e normaliza termos ruidosos (`todas as caracteristicas das sidebars` -> foco `sidebar`).
2. **Etapa 1 — Expansao bilingue PT<->EN (`scripts/search_expansion.py`)**:
   - Expande termos em portugues e ingles (`barra lateral` <-> `sidebar` <-> `gaveta`; `grafo` <-> `graph`; `captura de tela` <-> `screenshot`).
3. **Etapa 2 — Busca FTS5 + BM25 + cotas + varredura por repositorio (`scripts/archive_index.py`)**:
   - Executa busca global e varredura por repositorio para impedir que commits ruidosos recentes em um repositorio (ex.: `exams-app-old`) sufoquem branches historicas (`notes-app@old-2..old-11`).
4. **Etapa 3 — Grafo relacional e impacto temporal (`scripts/graph_linker.py`)**:
   - Resolve nos canonicos (`Component`, `Decision`, `Image`, `PR`, `File`, `Commit`) com BFS 2-hop, separando `EXTRACTED` vs `INFERRED` e rastreando arestas `SUPERSEDES` (`valid_in_commit` vs `superseded_in_later_branch`).
5. **Etapa 4 — Chunking estrutural AST e contratos de motion (`scripts/ast_chunker.py`)**:
   - Deduplica blobs por `blob_sha` mantendo ocorrencias por `(repo, ref, commit_sha, path)` e extrai blocos coesos + contratos deterministicos (`timer` 300ms/150ms, `css-transition`, `tailwind`, `waapi`, `handler`, `prefers-reduced-motion`).
6. **Etapa 5 — Citacoes, gaps e auditoria de completude (`scripts/context_linker.py`)**:
   - Vincula PRs, reviews e imagens de `inventory/` (ex.: `notes-app` PRs `#33`, `#38`, `#40`), registra `gaps` explicitos e calcula `coverage@source`, `candidate_branch_coverage`, `partial` e `inventory_complete_claim_allowed`.

---

## 3. Resultados Reproduziveis nas Consultas Canonicas

Comando reproduzivel executado em `2026-11-24`:

```bash
python3 scripts/context_coverage.py benchmark
```

### 3.1 Metricas por Consulta Canonica (Baseline Integrado)

| Query ID | Consulta | `coverage@source` | Cobertura Branches Candidatas | Hits FTS5 | Nos no Grafo | Chunks AST | Arquivos `context_linker` | Latencia (ms) | Tokens Resp. | Inventario Completo Permitido |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `q_sidebars_all` | `todas as caracteristicas das sidebars` | **1.0000** (8/8) | **1.0000** | 34 | 160 | 12 | 47 | 1612.98 | 6904 | `true` |
| `q_grafo` | `grafo` | **1.0000** (8/8) | **1.0000** | 6 | 160 | 7 | 68 | 1592.63 | 6502 | `true` |
| `q_hover_peek` | `hover peek` | **1.0000** (8/8) | **1.0000** | 3 | 160 | 3 | 45 | 1384.85 | 6976 | `true` |
| `q_drag_and_drop` | `drag-and-drop` | **1.0000** (8/8) | **1.0000** | 5 | 160 | 6 | 116 | 4837.88 | 7168 | `true` |
| `q_tooltip` | `tooltip` | **1.0000** (8/8) | **1.0000** | 5 | 160 | 0 | 40 | 3096.53 | 4920 | `true` |
| `q_drawer_mobile` | `drawer mobile` | **1.0000** (8/8) | **1.0000** | 4 | 160 | 4 | 50 | 2603.88 | 6193 | `true` |

Pico de RAM medido com `tracemalloc` durante toda a execucao das 6 consultas: **13.88 MiB**.

### 3.2 Regressao Obrigatoria: `"todas as caracteristicas das sidebars"`

Verificacao explicita de todas as 7 fontes minimas exigidas na regressao da issue `#29`:

| Fonte Obrigatoria | Status na Execucao | Evidencia Associada (Exemplo Real / Corpus) |
|---|---|---|
| `notes-app@old-2` | `verified_with_evidence` | `src/components/workspace/sidebar.tsx` (shell inicial colapsavel) |
| `notes-app@old-4` | `verified_with_evidence` | `src/components/sidebar/sidebar-tooltip.tsx` + commit de tooltip/grafo |
| `notes-app@old-5` | `verified_with_evidence` | `src/app/_components/workspace/app-sidebar-overview.tsx` (hover reveal `opacity-0` -> `group-hover:opacity-100`, `duration-200`) |
| `notes-app@old-10` | `verified_with_evidence` | `src/components/space-frame.tsx` (peek `setTimeout` 300ms/150ms, WAAPI `animate` 200ms) + `docs/captures/old-10-sidebar-collapsed-peek.png` |
| `notes-app@old-11` | `verified_with_evidence` | `src/components/layout/mobile-drawer-sidebar.tsx` (drawer mobile responsivo) |
| `exams-app-antigo-2@dev` | `verified_with_evidence` | `src/components/sidebar/unified-sidebar.tsx` + `graph-canvas.tsx` |
| `exams-app@dev` | `verified_with_evidence` | `docs/Documentos/01-planejamento/revisao/insumos-design-system/mapeamento-sidebars.md` + `m-dark-2-gaveta.png` (38 arquivos sidebar/gaveta no `inventory/exams-app-branch-files.json`) |

Alem dessas 7, os PRs `#33`, `#38` e `#40` do `notes-app` (via `inventory/notes-app/source-pulls-2026-11-23.json` e `graph_linker.py`) e os prototipos de `exams-app@chore/consolidate-legacy-sources-20261123` (43 arquivos sidebar/gaveta) e `exams-app@claude/project-thread-o4dym1` (5 capturas sidebar/Capacities) sao vinculados no mesmo resultado.

### 3.3 Cobertura na Consulta `"grafo"`

Na consulta `"grafo"`:
- **Expansao PT<->EN**: gera `("grafo"* OR "graph"*)` mantendo compatibilidade com commits em portugues (`feat(grafo): exporta PNG...`) e codigo/imagens em ingles (`graph-canvas.tsx`, `capacities_live_3pane_local_graph.png`).
- **Inventario real em `exams-app`**: localiza 110 arquivos em `chore/consolidate-legacy-sources-20261123`, 75 arquivos em `dev` (ex.: `docs/05-ferramentas/repo-grafo/grafo.mjs`) e 7 capturas em `claude/project-thread-o4dym1`, alem de `exams-app-antigo-2` (`feat/67-unified-graph-20261115`, `claude/downloads-grafo-png`) e `notes-app@old-4`.
- **AST + Motion**: `ast_chunker.py` extrai `GraphCanvas` (`requestAnimationFrame` + `onClick`) e `GraphForceModel` (`step_layout`, `damping`) com offsets e linhas exatas.

---

## 4. Avaliacao Comparativa: Linha de Base Integrada vs `grepai` e `XERJ`

Estado do ambiente: `grepai=absent`, `xerj=absent`, `qmd=absent`, `picoqmd=absent`, `ollama=absent`, `sentence_transformers=absent`, `torch=absent`.

Comparacao reproduzivel na consulta `"todas as caracteristicas das sidebars"` sobre o corpus multirepositorio (8 repositorios pesquisaveis + 10 commits ruidosos recentes em `exams-app-old`):

| Abordagem | `coverage@source` | Repositorios Alcancados | Servidor / Binario Externo | Proveniencia AST + PR + Imagem | Decisao |
|---|---:|---|---|---|---|
| **Orquestrador Integrado (`context_coverage.py`)** | **1.0000 (8/8)** | Todos os 8 pesquisaveis (9/9 inventariados) | **Nao** (Python 3.12 stdlib) | **Sim** (FTS5 + Grafo + AST + Context Linker) | **ADOTAR (padrao)** |
| **Busca Simples Top-8 (single-pass sem varredura)** | 0.5000 (4/8) | `exams-app`, `exams-app-antigo-2`, `exams-app-old`, `notes-app` | Nao | Parcial | Insuficiente para `"todas"` |
| **`XERJ` (proxy BM25 puro sem PT<->EN / multi-etapa)** | 0.1250 (1/8) | `exams-app` | Binario Rust (`xerj`) | Nao | **Nao necessaria** |
| **`grepai` (proxy semantico / embeddings locais)** | 0.6250 (5/8) | `exams-app`, `exams-app-antigo-2`, `exams-app-old`, `notes-app`, `shadcn-template` | **Sim** (binario Go + Ollama/embeddings) | Nao | **Nao necessaria** |

### Conclusao sobre `grepai` e `XERJ`

1. **`grepai`**: Mesmo com licenca `MIT` e suporte a Ollama offline (`docs/TOOL-LICENSES-PRIVACY.md`), exige servico/modelo de embeddings local e nao resolve por si so a enumeracao obrigatoria de fontes historicas, vinculacao a PRs/issues (`context_linker.py`) nem extracao deterministica de timers/motion (`ast_chunker.py`). Como a linha de base integrada ja atinge **`coverage@source = 1.0000`** sem servidor externo de embeddings, `grepai` e classificado como **nao necessaria**.
2. **`XERJ`**: Engine BM25 em Rust (`Apache-2.0`), redundante frente ao SQLite FTS5 + BM25 + expansao PT<->EN (`archive_index.py` + `search_expansion.py`), e sem garantia nativa de varredura multirepositorio. Classificada como **nao necessaria**.

---

## 5. Garantias de Seguranca, Degradacao Parcial e Privacidade

- **Degradacao explicita (`partial=True`)**: Quando um repositorio esta indisponivel (`simulate_unavailable_repos`) ou ocorre timeout (`timeout_seconds`), o orquestrador registra `omitted_sources`, reduz `coverage@source` abaixo de `1.0` e define `inventory_complete_claim_allowed = False`, impedindo que o agente afirme inventario completo com fontes faltantes.
- **Distincao de nivel de inspecao**: Capturas estaticas de imagem recebem `inspection_level="cataloged_metadata_only"` e `proves_animation_timing=False`, enquanto contratos de codigo AST recebem `evidence_state="verified_in_source"`.
- **Isolamento de privacidade**: `validate_private_output_path` bloqueia qualquer escrita de artefatos privados em `site/` ou publicacao em GitHub Pages.
