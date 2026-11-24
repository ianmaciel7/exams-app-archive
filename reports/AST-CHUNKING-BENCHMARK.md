# Benchmark de Chunking Estrutural por AST vs Janela Fixa de Linhas (Issue #31)

Data da avaliacao: 2026-11-23  
Issue de referencia: `#31` (complementa `#5`, `#9`, `#10`, `#16`, `#24`, `#29`)  
Script reproduzivel: [`scripts/ast_chunker.py`](../scripts/ast_chunker.py)  
Suite de testes: [`tests/test_ast_chunker.py`](../tests/test_ast_chunker.py)

---

## 1. Decisao Executiva

1. **Adotar extracao e chunking estrutural por AST nativo (Python stdlib `ast` + parser deterministico TS/TSX/JS/CSS/HTML em `scripts/ast_chunker.py`)** como evolucao incremental opcional/complementar sobre os blobs ja deduplicados em `scripts/content_index.py`, mantendo **SQLite FTS5 + Git Bundles** como fonte autoritativa.
2. **Manter chunking fixo de 40 linhas como fallback explicito** para linguagens sem parser estrutural, arquivos com sintaxe invalida (`syntax_error_fallback`) ou arquivos de documentacao/configuracao (`md`, `json`, `yaml`), garantindo zero perda de cobertura no FTS5.
3. **Rejeitar adocao obrigatoria no runtime de CocoIndex Code, Probe, sqry e SCIP (`scip-typescript`)**; reaproveitar seus formatos e ideias no schema (`symbol_id`, `node_type`, `parent_context`, `extractor_version`, deduplicacao por `blob_sha` e contratos de motion).
4. **Adotar `ast-grep` apenas como ferramenta auxiliar opcional de auditoria offline/CI** (regras declarativas pontuais sobre arvores extraidas), sem dependencia de runtime no plugin stdlib-only.

| Ferramenta / Estrategia | Decisao | Custo de Dependencias | Adequacao ao Acervo Historico |
|---|---|---|---|
| **Chunking AST nativo (`scripts/ast_chunker.py`)** | **Adotar (evolucao incremental)** | Zero (100% Python stdlib) | Alta: suporta Python, TS/TSX/JS/JSX, CSS, Tailwind, WAAPI e HTML `<style>`/`<script>`, com fallback para sintaxe quebrada |
| **Chunking fixo de 40 linhas (`scripts/content_index.py`)** | **Manter como baseline e fallback** | Zero (100% Python stdlib) | Alta cobertura lexical, porem quebra componentes/funcoes/keyframes acima de 40 linhas e perde contexto pai |
| **ast-grep (`sg`)** | **Auxiliar opcional (CI/auditoria)** | Binario Rust (`ast-grep`) | Boa para regras YAML pontuais (`onMouseEnter`, `setTimeout`), mas nao resolve Python+CSS+Tailwind+WAAPI em formato unificado sem binario extra |
| **CocoIndex Code** | **Rejeitar dependencia; adotar modelo de cache incremental** | Python + Tree-sitter + runtime/indice auxiliar | Excelente referencia de cache incremental por hash de blob; desnecessario trazer pipeline de embeddings/daemon |
| **Probe (`probelabs/probe`)** | **Rejeitar no runtime** | Binario Rust + Tree-sitter | Rapido para busca em checkout plano, mas nao opera nativamente sobre Git Bundles bare deduplicados por `blob_sha` nem extrai contratos de motion |
| **sqry (`verivus-oss/sqry`)** | **Rejeitar no runtime** | Binario Rust + grafo proprio | Util para call-graphs em checkouts compilaveis; redundante com `ast-grep` e pesado para plugin portatil |
| **SCIP (`scip-typescript`)** | **Rejeitar para codigo legado historico** | Node + TypeScript compiler (`tsconfig.json` + `node_modules`) | Fracassa ou degrada em branches historicas antigas (`old-1..old-11`) sem `node_modules` nem `tsconfig` integro |

---

## 2. Benchmark Reproduzivel: 40 Linhas Fixas vs Chunking Estrutural AST

Comando reproduzivel (100% deterministico, stdlib-only):

```bash
python3 scripts/ast_chunker.py benchmark
```

### 2.1 Corpus Avaliado (Sidebar, Grafo e Contratos de Motion)

O benchmark utiliza um corpus controlado cobrindo 5 arquivos representativos do historico (`notes-app`, `exams-app`, `exams-app-antigo-2`), com componentes maiores que 40 linhas para exercitar fronteiras reais de corte:

1. **Sidebar v1 (`notes-app@old-10`, `src/components/space-frame.tsx`, TSX)**: componente `WorkspaceSidebar` com `useState`/`useRef`, `handleMouseEnter` (`setTimeout` 300ms peek open), `handleMouseLeave` (`setTimeout` 150ms peek close), `handleReorderFlip` (WAAPI `el.animate` 200ms `ease-out` `translateY`) e classes Tailwind `transition-all duration-200 ease-out motion-reduce:transition-none`.
2. **Sidebar v2 (`notes-app@old-5`, `src/app/_components/workspace/app-sidebar-overview.tsx`, TSX)**: componente `AppSidebarOverview` com reveal de acoes no hover (`opacity-0 invisible pointer-events-none group-hover:opacity-100`) e `transition-opacity duration-200 ease-out`.
3. **Sidebar prototipo (`exams-app@dev`, `docs/sidebar-prototipo/prototipo-sidebar.css`, CSS)**: regras `.shell` (`transition: margin-left 200ms ease, width 200ms ease`), `.section-chevron` (`150ms ease`), `.mobile-drawer` (`translateX(-105%)`, `200ms ease`), `@keyframes skeletonPulse` (`1200ms ease-in-out infinite`) e `@media (prefers-reduced-motion: reduce)`.
4. **Grafo canvas (`exams-app-antigo-2@feat/67-unified-graph-20261115`, `src/components/graph/graph-canvas.tsx`, TSX)**: componente `GraphCanvas` com `useEffect`, `requestAnimationFrame`, `handleNodeClick` e handler `onClick`.
5. **Modelo de fisica em Python (`exams-app@main`, `src/domain/graph_force.py`, Python)**: classe `GraphForceModel` (`__init__`, `step_layout`) e funcao `compute_peek_dwell_contract`.

### 2.2 Resultados Medidos (FTS5 + BM25 sobre Chunks)

| Metrica | Chunking Fixo (40 linhas, overlap 5) | Chunking Estrutural AST (`ast_chunker.py`) | Variacao |
|---|---:|---:|---|
| **Chunks gerados (5 arquivos)** | 10 | 22 | +120% granularidade semantica (inclui nos pai e filhos) |
| **Recall@3 (queries multi-termo coesas)** | `0.1667` (1/6) | **`1.0000` (6/6)** | **+500% relativo (+0.8333)** |
| **Cohesive Structure Rate@3** | `0.0000` (0/6) | **`1.0000` (6/6)** | **+1.0000** (chunk unico retem assinatura + handler/motion) |
| **Tokens medios no top-1** | 21.83 (5 misses retornaram 0) | 302.67 | Entrega componente/classe/keyframe completo sem truncar corpo |
| **Tempo de ingestao (corpus sintetico)** | 0.476 ms | 72.819 ms | ~15 ms/arquivo (inclui extracao de motion e offsets) |
| **Pico de RAM (`tracemalloc`)** | 15.28 KiB | 193.10 KiB | < 0.2 MiB |
| **Contratos de motion extraidos** | 0 (nao estruturado) | **28 contratos tipados** | Distingue `delay_ms`, `duration_ms`, `easing`, `reduced_motion` |

### 2.3 Quebra por Consulta: Por Que o Chunk Fixo de 40 Linhas Falha

| Query ID | Consulta FTS5 (`AND`) | Fixo 40 Linhas (Top-3) | AST Estrutural (Top-3) | Diagnostico |
|---|---|---|---|---|
| `q_peek_hover_contract` | `WorkspaceSidebar AND onMouseEnter AND setTimeout` | **Miss** (0 hits) | **Hit (`component`)** | A assinatura `WorkspaceSidebar` fica no bloco 1-40 e `setTimeout`/`onMouseEnter` ficam apos a linha 41. O FTS5 por chunk com `AND` nao encontra os termos no mesmo chunk fixo. |
| `q_flip_waapi_sidebar` | `WorkspaceSidebar AND animate AND translateY` | **Miss** (0 hits) | **Hit (`component`)** | `WorkspaceSidebar` e `el.animate(...)` ficam separados pela janela de 40 linhas. O chunk `component` do AST preserva o componente inteiro e tambem extrai o filho `handleReorderFlip` (`parent_context="WorkspaceSidebar"`). |
| `q_overflow_reveal` | `AppSidebarOverview AND opacity AND duration` | **Miss** (0 hits) | **Hit (`component`)** | Nome do componente na linha 19 e classes Tailwind de hover na linha 49 ficam em janelas distintas. |
| `q_skeleton_keyframes` | `skeletonPulse AND opacity` | Parcial (hit quebrado ao meio) | **Hit (`keyframes`)** | `@keyframes skeletonPulse` foi cortado entre chunks no modelo fixo (`0%, 100%` separado de `50%`). O chunk `keyframes` entrega o bloco inteiro em 95 tokens. |
| `q_graph_canvas_hook` | `GraphCanvas AND requestAnimationFrame AND onClick` | **Miss** (0 hits) | **Hit (`component`)** | Componente `GraphCanvas`, hook `useEffect` e JSX `onClick` atravessam a fronteira de 40 linhas. |
| `q_python_force_model` | `GraphForceModel AND step_layout AND damping` | **Miss** (0 hits) | **Hit (`class`)** | `class GraphForceModel` e `self.damping` ficam na janela 1-40, enquanto `def step_layout` fica na janela seguinte. O `ast.parse` preserva a classe completa e o metodo filho. |

---

## 3. Relacao com `docs/UI-MOTION-EVIDENCE.json` e Contratos de Motion

Conforme exigido pela politica de evidencias em `docs/UI-MOTION-EVIDENCE.json`, o extrator `extract_motion_contracts` distingue explicitamente:

1. **Propriedade declarada vs timing vs reducao de movimento**:
   - **Timers de dwell (`timer`)**: `setTimeout(..., 300)` e `setTimeout(..., 150)` sao classificados como `delay_ms` (nunca `duration_ms`), preservando a distincao critica de `peek-open` (300 ms) e `peek-close` (150 ms).
   - **CSS transitions / animations (`css-transition`, `css-animation`)**: capturam `properties` (`margin-left`, `width`, `transform`, `opacity`), `duration_ms` (ex.: `200.0`, `150.0`, `1200.0`), `delay_ms`, `easing` (`ease`, `ease-in-out`) e `reduced_motion` via `@media (prefers-reduced-motion: reduce)`.
   - **Tailwind utility tokens (`tailwind`)**: interpretam `duration-200`, `delay-150`, `ease-out`, `transition-opacity`, `motion-reduce:transition-none`.
   - **WAAPI (`waapi`)**: extraem `element.animate(keyframes, { duration, delay, easing })` como `duration_ms=200.0`, `easing="ease-out"`, `properties=["transform", "translateY"]`.
   - **Handlers (`handler`)**: registram `onMouseEnter`, `onMouseLeave`, `onClick`, `onPointerDown`, `onDrop`, `addEventListener("pointermove")` sem inventar duracao onde nao ha animacao CSS/WAAPI.
2. **Garantia de veracidade**: codigo estatico e screenshots nao constituem medicao em navegador; o campo `confidence` permanece `verified-in-source` ate validacao em browser real.

---

## 4. Avaliacao Detalhada das Ferramentas Externas

### 4.1 CocoIndex Code (`cocoindex-io/cocoindex-code`)
- **O que resolve bem**: indexacao incremental orientada a AST com chunking semantico e cache por hash de conteudo.
- **Limitacoes no nosso contexto**: orienta-se a checkouts locais com runtime proprio e foco em busca vetorial/embedding. No acervo `exams-app-archive`, o armazenamento primario sao **Git Bundles bare** e historicos multibranch deduplicados por `blob_sha`.
- **Decisao**: **Nao adotar como dependencia de runtime**. Adotamos o principio arquitetural de **cache incremental por `blob_sha` + `extractor_version`**, implementando em Python puro `deduplicate_chunks_by_blob` para reutilizar chunks entre branches e repositorios mantendo intacto o mapa de ocorrencias `(repo, ref, commit_sha, path, blob_sha)`.

### 4.2 ast-grep (`ast-grep/ast-grep`)
- **O que resolve bem**: correspondencia estrutural declarativa via YAML sobre Tree-sitter (ex.: `onMouseEnter={$HANDLER}`, `setTimeout($CB, $MS)`, `$EL.animate($KF, $OPTS)`).
- **Limitacoes no ambiente**: nao esta preinstalado no ambiente padrao (`/usr/bin/sg` aponta para `newgrp` do sistema Linux, nao para `ast-grep`) e exige binario nativo por arquitetura; alem disso, regras separadas por linguagem nao unificam facilmente Tailwind em atributos JSX + CSS `@keyframes` + Python `ast` num unico indice SQLite.
- **Exemplo de regra equivalente para auditoria pontual** (referencia se `ast-grep` for usado em CI):
  ```yaml
  id: react-hover-dwell-timer
  language: tsx
  rule:
    pattern: setTimeout($FN, $MS)
    inside:
      kind: arrow_function
      stopBy: end
  ```
- **Decisao**: **Opcional apenas para auditorias offline**, substituido no core pelo parser deterministico em `scripts/ast_chunker.py`.

### 4.3 Probe (`probelabs/probe`) e sqry (`verivus-oss/sqry`)
- **Analise comparativa**:
  - **Probe**: usa Tree-sitter para buscar e expandir blocos inteiros de funcoes/classes em disco, evitando o problema de corte por linhas. Contudo, seu fluxo principal assume arquivos extraidos em working tree (nao le `git cat-file --batch` de Git Bundles bare sem extrair tudo para disco) e parte do ecossistema incentiva agentes LLM sobre o codigo.
  - **sqry**: oferece consultas ricas de definicoes, referencias e grafos de chamada via AST, mas cria um indice binario separado e sobrepoe-se ao `ast-grep` em dependencias nativas.
- **Decisao**: **Rejeitar ambos no runtime do plugin e nos workflows padrao**. O ganho de "retornar o componente/funcao/regra CSS inteiro" e obtido integralmente com **0 dependencias externas** em `scripts/ast_chunker.py`.

### 4.4 SCIP (`scip-code/scip` + `scip-typescript`)
- **Analise tecnica**: SCIP e excelente para navegacao precisa de definicoes/referencias cross-file quando o projeto compila com TypeScript (`tsc`) e possui `node_modules` resolvido.
- **Por que falha no acervo historico**: as branches `notes-app@old`..`old-11`, `exams-app-old` e prototipos antigos nao possuem `node_modules` instalados, tem dependencias descontinuadas e mistura de snippets HTML/JS/TSX sem `tsconfig.json` consistente. Rodar `scip-typescript` nesses snapshots gera erros de resolucao de tipos ou indices parciais frageis.
- **Decisao**: **Rejeitar como indexador do acervo historico**. Aproveitamos apenas o formato de identificador estavel (`symbol_id`, ex.: `tsx:WorkspaceSidebar.handleMouseEnter`) em `ASTChunk`, emitindo `status="partial_unbalanced_braces"` ou `"syntax_error_fallback"` explicitamente quando codigo antigo estiver incompleto, sem perder o texto no FTS5.

---

## 5. Seguranca, Edge Cases e Proposta Minima de Evolucao

1. **Zero execucao de codigo legado**: tanto `ast.parse` (Python) quanto o lexer/parser deterministico (TS/TSX/JS/CSS/HTML) operam estritamente por analise estatica sobre strings normalizadas, sem `eval`, `import`, `tsc` ou runtime JS.
2. **Invalidez sintatica e linguagens nao suportadas**:
   - Python com `SyntaxError` cai automaticamente para `_line_fallback_spans` com `status="syntax_error_fallback"`.
   - TS/CSS com chaves desbalanceadas preservam o que foi possivel extrair (`partial_unbalanced_braces`) ou fazem fallback para blocos de 40 linhas, nunca descartando o blob.
   - Linguagens sem parser AST (`.md`, `.json`, `.yaml`) usam fallback de linhas (`unsupported_language_fallback`).
3. **Deduplicacao e invalidacao de cache**:
   - Chave de reuso: `(blob_sha, extractor_version)`. Quando `EXTRACTOR_VERSION` mudar, apenas os chunks derivados precisam ser recalculados mantendo os objetos Git originais intactos.
   - Cada `ASTChunk` registra `blob_sha`, `chunk_sha`, `start_offset`, `end_offset`, `start_line`, `end_line`, `node_type`, `name` e `parent_context`.
4. **Proposta minima para `scripts/content_index.py` (sem migracao obrigatoria)**:
   - Manter `scripts/content_index.py` inalterado para estabilidade dos testes atuais.
   - Em etapa futura opcional, adicionar `--chunk-mode ast` em `content_index.py` chamando `ast_chunker.chunk_code` para `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.css`, `.html`, adicionando colunas opcionais (`node_type`, `symbol_name`, `parent_context`, `extractor_version`) na tabela `content_chunks` e mantendo `chunk_text` (40 linhas) como fallback automatico.
