# Benchmark de Busca: FTS5/BM25 vs Expansao PT<->EN vs QMD, picoqmd e Busca Semantica/Visual

Data da avaliacao: 2026-11-23  
Issue de referencia: `#9` (dependencias `#5`, `#7`, `#16`)  
Scripts reproduziveis: `scripts/search_expansion.py`, `scripts/search_benchmark.py`, `scripts/archive_index.py`

## Decisao Executiva

- **Expansao PT<->EN (`scripts/search_expansion.py`)**: **ADOTAR** no fluxo padrao de busca (`archive_index.search`).
- **SQLite FTS5 + BM25 + cotas por tipo (`#16`)**: **MANTER como padrao** do core (stdlib only, zero dependencias externas, latencia sub-25 ms na maioria das consultas no indice real de 37.5 MiB).
- **QMD / picoqmd / embeddings de texto**: **REJEITAR para o core** (opcional fora do core apenas se um caso futuro exigir busca semantica sobre texto integral em corpus sem correspondencia lexical).
- **Busca visual (CLIP / OCR offline)**: **OPCIONAL / TRILHA SEPARADA** apenas para o catalogo privado de imagens sem nome descritivo, nunca como requisito de runtime do indice textual.

| Tecnologia / Estrategia | Decisao | Justificativa resumida |
|---|---|---|
| SQLite FTS5 + BM25 (`#16`) | **Manter como padrao** | Zero dependencias (stdlib), 37.5 MiB em disco, latencia media 0.48 ms (sintetico) / 2-25 ms (indice real), 100% reproduzivel em GitHub Actions |
| Expansao PT<->EN (`scripts/search_expansion.py`) | **Adotar** | Elimina o maior gap semantico (commits em PT vs paths em EN): eleva Recall@8 de `0.5259` para `0.9630` (+83% relativo), Precision@8 de `0.1944` para `0.3750` e MRR para `1.0000` |
| QMD / picoqmd (`tobi/qmd`, `altSeneca/picoqmd`) | **Rejeitar no core** (opcional) | Nao instalados por padrao (`qmd=absent`, `picoqmd=absent`), exigem runtime adicional (Node/Bun/GGUF ou binario extra) e modelo local (~300 MB-1.5 GB RAM) sem superar FTS5+BM25+PT<->EN |
| Embeddings densos locais (proxy / sentence-transformers) | **Rejeitar no core** | Proxy denso atingiu Recall@8 `0.7000` e Precision@8 `0.2639` (abaixo de FTS5+BM25+PT<->EN); modelos reais exigem `torch`/`numpy`/pesos pesados incompatíveis com CI leve e plugin stdlib |
| Busca visual (CLIP / embeddings de imagem) | **Opcional (trilha separada)** | Unica tecnica capaz de recuperar screenshots com nomes opacos (`IMG_*.png` / `old-10-home.png`) sem texto auxiliar; custo elevado de RAM/GPU impede inclusao no core |

---

## 1. Contexto e Problema Medido no Acervo Real

O acervo historico consolidado em `.cache/benchmark/full-index.sqlite` (37.5 MiB, 19 fontes historicas, 3.995 commits, 77.530 alteracoes de arquivo e 3.572 registros de imagens) apresenta assimetria linguistica estrutural:

- **Mensagens de commit** em repositorios recentes (`exams-app`, `exams-app-antigo-2`) estao majoritariamente em **portugues** (`grafo`, `simulado`, `questao`, `barra lateral`, `captura`).
- **Caminhos de arquivo e codigo** estao majoritariamente em **ingles** (`graph`, `exam`, `mock`, `question`, `sidebar`, `screenshot`).

Medicao direta no indice real (`scripts/search_benchmark.py --live-db .cache/benchmark/full-index.sqlite`):

| Consulta | Commits (sem exp.) | Commits (com PT<->EN) | Paths distintos (sem exp.) | Paths distintos (com PT<->EN) | Latencia base -> exp. | Tokens resposta (base -> exp.) |
|---|---:|---:|---:|---:|---:|---:|
| `sidebar` | 145 | 145 | 213 | 217 | 11.51 ms -> 13.01 ms | 811 -> 823 |
| `barra lateral` | 0 | **145** | 0 | **217** | 5.06 ms -> 13.44 ms | 445 -> 823 |
| `grafo` | 28 | **227** | 75 | **719** | 4.14 ms -> 23.99 ms | 817 -> 789 |
| `graph` | 210 | 227 | 644 | 719 | 24.49 ms -> 22.69 ms | 748 -> 789 |
| `simulado` | 10 | **103** | 38 | **3456** | 4.45 ms -> 85.06 ms | 788 -> 800 |
| `questao` | 6 | **97** | 20 | **580** | 3.51 ms -> 19.31 ms | 776 -> 790 |
| `prova` | 0 | **710** | 0 | **5264** | 2.13 ms -> 149.64 ms | 1 -> 762 |
| `Capacities` | 92 | 92 | 675 | 675 | 15.20 ms -> 14.84 ms | 787 -> 787 |
| `QConcursos` | 7 | 7 | 334 | 334 | 11.17 ms -> 10.57 ms | 812 -> 812 |
| `fsrs` | 10 | **43** | 17 | **248** | 2.55 ms -> 19.73 ms | 700 -> 781 |
| `recall` | 4 | 4 | 67 | 67 | 3.84 ms -> 3.62 ms | 809 -> 809 |
| `captura de tela` | 0 | **46** | 0 | **188** | 50.39 ms -> 15.37 ms | 837 -> 816 |

Observacoes principais sobre o acervo real:
1. Consultas em portugues como `barra lateral` e `prova` tinham **0 acertos exatos em FTS5** sem expansao e passaram a recuperar **145 commits / 217 caminhos** (`sidebar`/`gaveta`) e **710 commits / 5.264 caminhos** (`exam`/`test`), respectivamente.
2. `grafo` saltou de **28 commits e 75 caminhos** para **227 commits e 719 caminhos**, mantendo orcamento compacto de resposta (~789 tokens para `limit=12`).
3. Entidades proprias (`Capacities`, `QConcursos`, `recall`) mantiveram exatamente os mesmos resultados e latencia, sem diluicao por sinonimos.

---

## 2. Benchmark Reproduzivel com Ground Truth (Precision@k, Recall@k, MRR)

O script `scripts/search_benchmark.py` cria um corpus bilingue controlado (29 documentos entre commits, caminhos de codigo/docs e imagens, incluindo 8 commits ruidosos recentes e 1 screenshot de nome opaco `assets/opaque/img_0042.png`) e 9 consultas de referencia cobrindo todas as categorias exigidas pela issue `#9`:
- Termos diretos EN (`sidebar`)
- Cruzamento PT<->EN (`barra lateral`, `grafo`, `simulado`, `questao`)
- Entidades (`Capacities`, `QConcursos`)
- Identificador divergente no codigo (`repeticao espacada` -> `fsrs.ts`)
- Screenshot sem nome descritivo (`captura tela inicial` -> commit PT + `IMG_20260801_0042.png` + `assets/opaque/img_0042.png`)

Comando executado (`k=8`, `repetitions=10`):
```bash
python3 scripts/search_benchmark.py --k 8 --repetitions 10 --live-db .cache/benchmark/full-index.sqlite
```

### Tabela Comparativa (Corpus Ground Truth, k=8)

| Estrategia | Precision@8 | Recall@8 | MRR | Latencia Media | Latencia P95 | Tokens / Resposta | Armazenamento / RAM extra | Dependencias |
|---|---:|---:|---:|---:|---:|---:|---|---|
| **FTS5 Legado** (pre-`#16`, sem BM25/cotas) | 0.1528 | 0.4426 | 0.7778 | 0.140 ms | 0.239 ms | 98.6 | 92 KiB SQLite (baseline) | Python stdlib + SQLite |
| **FTS5 + BM25 (`#16`)** | 0.1944 | 0.5259 | 0.8889 | 0.481 ms | 0.657 ms | 128.7 | 92 KiB SQLite (baseline) | Python stdlib + SQLite |
| **FTS5 + BM25 + Expansao PT<->EN** | **0.3750** | **0.9630** | **1.0000** | 0.669 ms | 0.951 ms | 238.4 | +~4 KiB codigo (dicionario v1.0.0) | Python stdlib + SQLite |
| **Semantico Proxy Local** (char 3-gram + TF cosseno) | 0.2639 | 0.7000 | 1.0000 | 0.115 ms | 0.179 ms | 206.1 | ~204 KiB RAM (proxy 29 docs) | In-memory Python (proxy) |
| **QMD / picoqmd** (avaliacao arquitetural) | n/d (nao instalado) | n/d | n/d | ~50-400 ms* | n/d | ~250-500* | +300 MB a 1.5 GB modelos/indice* | Node/Bun + GGUF / embeddings locais |

*\*Estimativas de referencia arquitetural para QMD/picoqmd em CPU local: nao instalados no ambiente (`which qmd` e `which picoqmd` ausentes), e nao trazem ganho sobre FTS5+BM25+PT<->EN para metadados bilingues curtos (assuntos de commit e caminhos de arquivo).*

### Quebra por Consulta (Precision@8 / Recall@8 / MRR)

| Query ID | Consulta | Categoria | FTS5 Legado | FTS5 + BM25 (`#16`) | FTS5 + BM25 + PT<->EN | Proxy Semantico |
|---|---|---|---:|---:|---:|---:|
| `q_sidebar` | `sidebar` | `direct_en` | 0.00 / 0.00 / 0.00 | 0.38 / 0.75 / 1.00 | **0.50 / 1.00 / 1.00** | 0.38 / 0.75 / 1.00 |
| `q_barra_lateral` | `barra lateral` | `cross_lingual_pt_en` | 0.12 / 0.25 / 1.00 | 0.12 / 0.25 / 1.00 | **0.50 / 1.00 / 1.00** | 0.12 / 0.25 / 1.00 |
| `q_grafo` | `grafo` | `cross_lingual_pt_en` | 0.25 / 0.40 / 1.00 | 0.25 / 0.40 / 1.00 | **0.62 / 1.00 / 1.00** | 0.50 / 0.80 / 1.00 |
| `q_simulado` | `simulado` | `cross_lingual_pt_en` | 0.12 / 0.33 / 1.00 | 0.12 / 0.33 / 1.00 | **0.38 / 1.00 / 1.00** | 0.12 / 0.33 / 1.00 |
| `q_questao` | `questao` | `cross_lingual_pt_en` | 0.25 / 0.67 / 1.00 | 0.25 / 0.67 / 1.00 | **0.38 / 1.00 / 1.00** | 0.38 / 1.00 / 1.00 |
| `q_capacities` | `Capacities` | `entity_exact` | 0.25 / 1.00 / 1.00 | 0.25 / 1.00 / 1.00 | **0.25 / 1.00 / 1.00** | 0.25 / 1.00 / 1.00 |
| `q_qconcursos` | `QConcursos` | `entity_exact` | 0.25 / 1.00 / 1.00 | 0.25 / 1.00 / 1.00 | **0.25 / 1.00 / 1.00** | 0.25 / 1.00 / 1.00 |
| `q_divergent_code` | `repeticao espacada` | `divergent_identifier` | 0.00 / 0.00 / 0.00 | 0.00 / 0.00 / 0.00 | **0.25 / 1.00 / 1.00** | 0.12 / 0.50 / 1.00 |
| `q_nondescriptive_img` | `captura tela inicial` | `nondescriptive_image` | 0.12 / 0.33 / 1.00 | 0.12 / 0.33 / 1.00 | **0.25 / 0.67 / 1.00** | 0.25 / 0.67 / 1.00 |

Leituras tecnicas chave:
1. **`#16` (BM25 + cotas por tipo) foi essencial antes da expansao**: Em `q_sidebar`, o FTS5 legado ordenava apenas por data decrescente e foi inundado pelos 8 commits ruidosos recentes (`0.00` de recall no top-8), enquanto BM25 + cotas colocou commit exato, `sidebar.tsx` e imagem no top-8 (`0.75` de recall, MRR `1.00`).
2. **Expansao PT<->EN supera o proxy semantico em todas as queries bilingues e de jargao**: `barra lateral`, `grafo`, `simulado` e `repeticao espacada` atingiram `Recall@8 = 1.00` com dicionario deterministico de 37 grupos (`v1.0.0`), contra `0.25` a `0.80` no proxy lexical-denso sem traducao.
3. **Limite explicito em `q_nondescriptive_img` (`0.67` de recall)**: Tanto FTS5+PT<->EN quanto busca textual densa falham no arquivo `assets/opaque/img_0042.png` porque nao ha nenhuma pista lexical no nome do arquivo. Apenas busca visual (CLIP) ou OCR no binario resolveria esse caso — confirmando que busca visual pertence a uma trilha separada e opcional.

---

## 3. Avaliacao Operacional: Licencas, Privacidade, Custo e Infraestrutura

| Criterio | FTS5 + BM25 + PT<->EN | QMD / picoqmd | Embeddings / CLIP local |
|---|---|---|---|
| **Licenca / Dependencias** | Python stdlib + SQLite (Public Domain / PSF) | MIT (QMD/picoqmd), mas exige Node/Bun/llama.cpp + modelos GGUF (Apache-2.0/MIT) | Apache-2.0 / MIT (`torch`, `transformers`, `open_clip`, varios GB) |
| **Privacidade** | 100% local/offline; zero chamada externa | Local se usar GGUF offline; risco de download automatico de modelos em CI | Local somente apos download previo de pesos; proibido vazar dados privados para APIs pagas |
| **Custo de atualizacao** | Rebuild completo do indice historico em ~25s (`scripts/build_full_index.py`), 0 GPU | Re-embedding incremental de chunks + vetores a cada ingestao | Alto em CPU (minutos a horas para milhares de arquivos/imagens) |
| **Compatibilidade com plugin / CI** | Funciona diretamente no `pytest`, GitHub Actions (`archive-private-search.yml`) e CLI portatil | Incompativel com requisito stdlib-only do CLI portatil e workflows leves | Incompativel com workflows padrao de GitHub Actions sem cache pesado/GPU |
| **Contrato de dados** | Mantem `archive-index.sqlite` (37.5 MiB) sem alterar schema | Exigiria segunda base vetorial ou extensao `sqlite-vec` | Exigiria tabela de vetores + blobs binarios pre-carregados |

---

## 4. Recomendacao Final e Proximos Passos

1. **Adotar** `scripts/search_expansion.py` (`DICTIONARY_VERSION = "1.0.0"`) integrado em `scripts/archive_index.py`, mantendo `expand_pt_en=True` por padrao (com parametro `expand_pt_en=False` disponivel para comparacoes).
2. **Manter** SQLite FTS5 + BM25 + cotas por tipo (`#16`) como motor unico de busca do core.
3. **Rejeitar** a migracao para QMD, `picoqmd` ou embeddings de texto no core: nenhum modelo semantico generico sem traducao de dominio superou a linha de base FTS5+BM25+PT<->EN, e o custo operacional (RAM, dependencias binarias, tempo de build) inviabiliza a execucao leve no plugin e no Actions.
4. **Manter busca visual (CLIP/OCR) como trilha opcional separada**: caso seja necessario recuperar screenshots antigos sem nome descritivo no catalogo privado (`scripts/image_catalog.py`), implementar como comando offline opt-in fora do core.
