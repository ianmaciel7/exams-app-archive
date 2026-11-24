# Benchmark e Avaliacao de Extracao de Documentos (Issue #32)

Data da avaliacao: 2026-11-23  
Issue de referencia: `#32` (complementa `#5`, `#7`, `#8` e `#24`)  
Script reproduzivel: `scripts/document_extractor.py` (`EXTRACTOR_VERSION = "1.0.0"`)  
Suite de testes: `tests/test_document_extractor.py`

## 1. Decisao Executiva

| Candidato / Estrategia | Decisao | Papel no `exams-app-archive` |
|---|---|---|
| **Extrator leve integrado (`scripts/document_extractor.py`)** | **ADOTAR (padrao offline)** | Extrator deterministico em Python stdlib para Markdown, texto puro, especificacoes JSON/JSONC e PDFs nativos com hierarquia `h1/h2/h3+`, tabelas, links para diagramas/imagens, proveniencia por pagina/elemento e SHA-256. |
| **Docling (`docling-project/docling`)** | **FERRAMENTA OPCIONAL OFFLINE (build)** | Nao adotar no core nem no plugin. Usar apenas offline em etapa manual/build quando surgirem PDFs escaneados complexos ou layouts multi-coluna densos que exijam OCR/layout deep-learning. |
| **OpenDataLoader PDF (`opendataloader-project/opendataloader-pdf`)** | **FERRAMENTA OPCIONAL OFFLINE (build)** | Alternativa preferencial para PDFs pesados caso o acervo passe a conter PDFs nativos/escaneados extensos com necessidade de `bounding_box` em alta precisao; exige Java 11+ (ou modo hibrido local). |
| **Xberg (`xberg-io/xberg`)** | **REJEITAR no core / opcional futuro** | Binario Rust externo ausente no runner padrao; adiciona distribuicao multi-plataforma ao plugin sem superar o extrator stdlib nos documentos Markdown/JSON reais do acervo. |
| **PageIndex (`VectifyAI/PageIndex`)** | **REJEITAR** | Depende de chamadas a LLM/API (ex.: OpenAI `gpt-4o`) para construir e navegar a arvore hierarquica, gerando custo de tokens e risco de envio de dados privados; substituido localmente pela arvore deterministica de headings + SQLite FTS5 (`doc_elements_fts`). |

**Resumo da decisao:** Manter o extrator leve integrado (`scripts/document_extractor.py`) como padrao para documentos Markdown, texto puro, JSON estruturado e PDFs com texto nativo; tratar motores pesados de PDF/OCR (`Docling` / `OpenDataLoader PDF`) exclusivamente como ferramenta opcional offline de build apenas quando houver PDFs escaneados ou multi-coluna complexos.

---

## 2. Inventario Real de Documentos no Acervo Preservado

Auditoria realizada sobre os inventarios e arquivos versionados no repositorio (`inventory/exams-app-branch-files.json`, `inventory/notes-app/`, `docs/` e `reports/`):

| Fonte / Escopo | PDFs (`.pdf`) | Markdown (`.md`) | Texto (`.txt`) | JSON estruturado (`.json`) | HTML (`.html`) | Observacoes |
|---|---:|---:|---:|---:|---:|---|
| `exams-app` branch `chore/consolidate-legacy-sources-20261123` | **0** | 536 | 23 | 317 | 36 | Maior volume de docs historicos (~17,15 MB totais entre docs/JSON; 4,33 MB em `.md`, maior `.md` = 239,9 KB) |
| `exams-app` branch `dev` | **0** | 85 | 19 | 5 | 26 | ~3,25 MB totais (300,6 KB em `.md`, maior `.md` = 70,7 KB) |
| `exams-app` branch `claude/project-thread-o4dym1` | **0** | 40 | 0 | 3 | 1 | 186,8 KB totais (172,0 KB em `.md`) |
| `exams-app` branch `main` | **0** | 0 | 0 | 0 | 0 | Branch enxuta com 1 arquivo |
| `exams-app-archive` (`docs/` atual) | **0** | 9 | 0 | 1 | 0 | 64.419 bytes auditados diretamente |
| `exams-app-archive` (`reports/` atual) | **0** | 8 | 0 | 8 | 0 | 134.931 bytes auditados diretamente |
| `notes-app` (`inventory/notes-app/platform/pr-file-diffs-batch-*.json`) | **0 arquivos binarios** | - | - | - | - | Apenas mencoes textuais em patches/evals (ex.: `edital-001.pdf`, `prova-tipo-1.pdf`, `gabarito.pdf`, `sample1.pdf`) |

**Constatação empirica:** Ate o snapshot de `2026-11-23`, o acervo preservado possui **0 arquivos `.pdf` binarios** e **661+ documentos Markdown** (somando branches de `exams-app`), alem de `txt` e especificacoes `json`. As referencias a `.pdf` encontradas no `notes-app` sao nomes de fixtures/exemplos em diffs de PRs (testes de importacao/evals). Isso reforca que adotar um stack pesado de PDF/OCR/PyTorch no core violaria a proporcionalidade tecnica.

---

## 3. Medicao Reproduzivel com `scripts/document_extractor.py`

Comando executado no ambiente offline (`Python 3.12.16`, sem `docling`, `pageindex`, `xberg` ou `opendataloader` instalados):

```bash
python3 scripts/document_extractor.py benchmark --docs-dir docs
python3 scripts/document_extractor.py scan reports/ --repo-name exams-app-archive --ref main
```

### 3.1 Resultados nas Fixtures Sinteticas (incluindo PDF nativo, pagina escaneada e PDF criptografado)

Tempo total das 5 fixtures: **23.09 ms** | Pico de RAM (`tracemalloc`): **89.26 KiB**

| Fixture | Tipo | Status | Skip Reason | Bytes | Secoes | Tabelas | Links Diagrama/Img | Paginas nao interpretadas | Tokens Brutos -> Outline |
|---|---|---|---|---:|---:|---:|---:|---|---:|
| `docs/architecture.md` | `markdown` | `ok` | - | 425 | 3 | 1 | 2 (`exam-flow.png`, `mermaid`) | `[]` | 107 -> 72 |
| `specs/screens.json` | `json_spec` | `ok` | - | 325 | 4 | 1 | 2 (`home.png`, `graph.png`) | `[]` | 82 -> 49 |
| `notes/decision.txt` | `text` | `ok` | - | 165 | 3 | 0 | 1 (`old-10-home.png`) | `[]` | 41 -> 52 |
| `archive/legacy-spec.pdf` (2 pags) | `pdf` | `partial` | - | 1295 | 1 | 1 | 1 (`page-2:/Im1`) | `[2]` (`image_only_needs_ocr`) | 303 -> 18 |
| `archive/locked.pdf` | `pdf` | `skipped` | `encrypted_pdf` | 792 | 0 | 0 | 0 | `[]` | 195 -> 1 |

### 3.2 Resultados no Acervo Local (`docs/` e `reports/`)

| Diretorio | Arquivos | `ok` / `partial` / `skipped` | Bytes Totais | Secoes Extraidas | Tabelas | Links Diagrama | Tempo (ms) | Pico RAM (KiB) |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `docs/` | 10 (9 `.md`, 1 `.json`) | 10 / 0 / 0 | 64.419 | 61 | 10 | 0 | 156.89 ms | 221.84 KiB |
| `reports/` | 16 (8 `.md`, 8 `.json`) | 16 / 0 / 0 | 134.931 | 90 | 27 | 19 | 213.39 ms | 379.08 KiB |

Notas tecnicas da medicao:
1. Cada secao, tabela e link de diagrama recebe chave completa de proveniencia `repo/ref/commit_sha/path#page=N&element=E`, `bounding_box` (quando disponivel em PDF), `doc_sha256`, `element_sha256` e `extractor_version`.
2. Links de imagens/diagramas (`markdown_image`, `html_img`, `mermaid_block`, `pdf_image_xobject`) registram explicitamente `"understood": false` para nunca simular compreensao visual apenas por indexacao de metadados.
3. Paginas PDF sem camada de texto nativa ou contendo apenas XObjects de imagem sao marcadas explicitamente como `extraction_mode: "image_only_needs_ocr"` e listadas em `uninterpreted_pages`, enquanto PDFs criptografados ou ilegíveis retornam `status: "skipped"` com `skip_reason`.

---

## 4. Comparativo Tecnico dos Candidatos

| Criterio | Extrator Leve Integrado (`document_extractor.py`) | Docling (`docling-project/docling`) | PageIndex (`VectifyAI/PageIndex`) | Xberg (`xberg-io/xberg`) | OpenDataLoader PDF (`opendataloader-pdf`) |
|---|---|---|---|---|---|
| **Instalacao no ambiente** | Nativo (Python stdlib, 0 deps) | Ausente (requer `pip install docling` + `torch`, `docling-ibm-models`, pesos HF) | Ausente (requer `pageindex` + chave LLM/API) | Ausente (requer binario Rust / `cargo`) | Ausente (requer pacote + Java 11+ ja presente em `/usr/bin/java`) |
| **Suporte a formatos do acervo** | `.md`, `.mdx`, `.txt`, `.rst`, `.json`, `.jsonc`, `.pdf` nativo | PDF, DOCX, PPTX, HTML, MD, imagens (OCR) | PDF e Markdown (via arvore gerada por LLM) | PDF e documentos diversos (parser poliglota Rust) | PDF (nativo + modo hibrido opcional para OCR/tabelas) |
| **Hierarquia (`h1/h2/h3`), secoes e tabelas** | Sim: deterministico para MD/TXT/JSON e PDF nativo (por fonte/numeracao e gaps de coluna) | Excelente para PDF complexo (DocLayNet + TableFormer) | Boa arvore semantica de secoes, porem nao deterministica (LLM) | Boa extracao estrutural e de metadados | Excelente para PDF com JSON estruturado (heading, table, paragraph) |
| **Proveniência (`page`, `element_id`, `bounding_box`, `hash`)** | Completa (`repo/ref/SHA/path/pdf_page/element_id/bounding_box/extractor_version` + SHA-256) | `prov` com `page_no` e `bbox` por elemento | `page_index` / resumo de no (sem `bounding_box` nativo deterministico) | Pagina e metadados estruturais | `page`, `type`, `bounding box` verificavel |
| **PDFs escaneados / OCR** | Detecta e marca `image_only_needs_ocr` + `uninterpreted_pages` (sem OCR embutido) | Sim (RapidOCR / EasyOCR / Tesseract offline apos download de modelos) | Nao nativo para scan sem texto / depende de VLM/API | Limitado ao texto/estrutura ou backends extras | Modo hibrido opcional com OCR |
| **Custo computacional (Tempo / RAM / Disco)** | ~23 ms / <400 KiB RAM / ~35 KB codigo | Alto: ~1.5-4 GB dependencias/modelos, ~1-3 GB RAM, segundos/pagina em CPU | Alto custo de latencia e tokens de LLM por documento | Baixo-medio em runtime (binario compilado ~10-30 MB), build Rust pesado | Medio: JVM + JAR (~50-150 MB), ~300-700 MB RAM em execucao |
| **Operacao 100% offline e privacidade** | Sim, garantido (zero rede, bloqueio de `.env`/segredos) | Sim **apenas apos** pre-download offline de modelos; risco de fetch automatico do HuggingFace se mal configurado | **Nao por padrao** (requer endpoint OpenAI/LLM; exige LLM local pesado para ficar offline) | Sim (execucao local) | Sim (execucao local em JVM, sem rede no modo padrao) |
| **Tokens transferidos para APIs externas** | **0 tokens** | **0 tokens** (modo local) | Alto (envia paginas/arvore inteira ao LLM na indexacao e na busca) | **0 tokens** | **0 tokens** (modo local) |
| **Compatibilidade com plugin stdlib & CI leve** | 100% compativel | Incompativel com runtime leve do plugin e runners GitHub padrao sem cache pesado | Incompativel com requisito offline/sem LLM pago | Exige distribuir binario nativo por SO/arquitetura | Exige JVM + JAR adicional (nao portatil para plugin stdlib) |

---

## 5. Analise Especifica: PageIndex vs Arvore de Titulos + FTS5

A issue `#32` pediu verificar se **PageIndex** acrescenta recall em documentacao longa frente a arvore de titulos + SQLite FTS5:

1. **Dependencia de LLM/API**: O fluxo padrao do `PageIndex` realiza chamadas de inferencia LLM para gerar resumos de nos (`node_summary`), extrair indice hierarquico quando nao ha sumario formal e percorrer a arvore por raciocinio em tempo de consulta (`tree search`). Isso transfere texto privado para APIs externas ou exige servir um LLM local de varios GB de VRAM/RAM.
2. **Ganho sobre arvore deterministica + FTS5**: Os documentos longos reais encontrados no acervo (ate 239 KB em Markdown, ex.: `docs/Documentos/...`) ja possuem estrutura explicita em Markdown (`#`, `##`, `###`), tabelas e listas. O extrator deterministico preserva a hierarquia completa `section_path` (`h1 > h2 > h3`) e indexa `title`, `section_path` e `content` em `doc_elements_fts` (SQLite FTS5 com `unicode61` e `bm25`), permitindo recuperacao sub-milissegundo e retorno de secoes especificas sem custo de tokens.
3. **Conclusao para PageIndex**: **Rejeitado**. A navegacao por arvore de titulos + FTS5 + expansao PT<->EN (`scripts/search_expansion.py`) entrega proveniencia verificavel com 0 tokens de LLM.

---

## 6. Analise de Integracao: Parsing Deterministico vs OCR/PDF Pesado

Seguindo os requisitos da issue `#32`, a arquitetura separa estritamente tres camadas:

1. **Camada 1 — Parsing Deterministico Padrao (`scripts/document_extractor.py`)**:
   - Atua sobre `.md`, `.mdx`, `.txt`, `.rst`, `.json`, `.jsonc` e PDFs nativos nao criptografados.
   - Produz esquema unico com `repo/ref/commit_sha/path/pdf_page/element_id/bounding_box/extractor_version` + `doc_sha256` e `element_sha256`.
   - Mantem o plugin (`plugins/exams-archive-native`) e os testes de CI (`tests.yml`) 100% livres de dependencias pesadas.
2. **Camada 2 — Deteccao Explicita de Lacunas**:
   - Paginas PDF sem texto nativo e com `/Subtype /Image` recebem `extraction_mode = "image_only_needs_ocr"` e entram em `uninterpreted_pages`.
   - Documentos criptografados, corrompidos, binarios mascarados, ausentes ou com caminhos/padroes secretos retornam `status = "skipped"` com `skip_reason` auditavel.
3. **Camada 3 — Ferramenta Opcional Offline de Build (somente sob demanda)**:
   - Se inventario futuro acusar PDFs historicos escaneados ou multi-coluna complexos (`uninterpreted_pages` nao vazio), rodar **offline** em ambiente de build dedicado:
     - **Opcao A (menor footprint para PDFs com `bounding_box`):** `OpenDataLoader PDF` local (aproveitando JVM ja disponivel) ou `Docling` offline com cache local de modelos, gravando o JSON estruturado e mantendo os binarios originais e indices estritamente privados.
     - **Opcao B (OCR puro offline):** `Tesseract` / `Docling` com `do_ocr=True` sem envio a APIs externas, atribuindo `extractor_version` especifico ao artefato derivado para preservar rastreabilidade frente ao parsing deterministico.

---

## 7. Verificacao de Aceite (#32)

- [x] Levantamento dos documentos preservados no acervo (0 PDFs binarios reais ate 2026-11-23; 661+ Markdowns em branches historicos + docs/reports locais).
- [x] Extrator offline deterministico criado em `scripts/document_extractor.py` com suporte a hierarquia, tabelas, links de diagramas/imagens, proveniencia completa (`repo/ref/SHA/path/pdf_page/element_id/bounding_box/extractor_version`) e SHA-256.
- [x] Separacao explicita entre parsing deterministico, skips auditaveis (`encrypted_pdf`, `missing_file`, `secret_*`) e paginas escaneadas (`image_only_needs_ocr` / `understood: false`).
- [x] Benchmark comparando Docling, PageIndex, Xberg e OpenDataLoader PDF versus extrator leve integrado, com decisao fundamentada.
- [x] Politica Zero Emoji respeitada em scripts, relatorios e testes.
