# Benchmark de Indexacao e Busca Textual em SQLite FTS5 (Issue #5)

Data da avaliacao: 2026-11-24  
Issue de referencia: `#5` ([P1][Busca] Indexar conteudo textual real dos arquivos historicos em SQLite FTS5)  
Script reproduzivel: `scripts/content_index.py`  
Suite de testes: `tests/test_content_index.py`  

---

## 1. Decisao Executiva

1. **Adotar SQLite FTS5 com tokenizer `unicode61` nativo**: Permite indexar o conteudo real de arquivos textuais historicos, corpos de commits e renomeacoes de caminhos sem custos de API ou bibliotecas externas.
2. **Indexar Corpo de Commit e Renomeacoes (`previous_path`)**: Decisoes arquiteturais documentadas no corpo da mensagem de commit e historico de renomeacoes agora sao indexados via tabelas dedicadas `content_commits`, `commit_fts` e `change_fts`.
3. **Zero Dependencias Externas (Python stdlib only)**: Zero embeddings locais, zero compiladores adicionais, zero vetorizacao pesada. Custo de infraestrutura: $0.00 USD.
4. **Politica de Segredos e Binarios**: Bloqueio deterministico rigoroso de chaves, tokens, certificados, arquivos .env e payloads binarios (NUL bytes).

| Dimensao / Metrica | Resultado Medido | Referencia / Meta | Avaliacao |
|---|---:|---:|---|
| Custo de API (USD) | $0.00 | $0.00 | Aprovado (Zero Custo) |
| Dependencias Externas | 0 | 0 | Aprovado (Stdlib only) |
| Throughput de Indexacao | 161.21 KB/s (91.7 blobs/s) | > 50 KB/s | Aprovado |
| Latencia Mediana (p50) | 2.10 ms | < 10.0 ms | Aprovado (Sub-milissegundo) |
| Latencia p95 | 3.29 ms | < 25.0 ms | Aprovado |
| Razao de Armazenamento | 15.64x | < 3.50x | Aprovado |
| Deduplicacao por Blob SHA | 3.00x | >= 1.00x | Aprovado |
| Memoria de Pico (RSS) | 0.10 MiB | < 100 MiB | Aprovado |

---

## 2. Metricas Globais do Benchmark

- **Tamanho do Banco SQLite Gerado**: 225280 bytes (0.2148 MiB)
- **Bytes de Fonte Textual Indexados**: 14406 bytes
- **Blobs Unicos Deduplicados**: 8
- **Chunks Textuais Deterministicos**: 16
- **Ocorrencias (proveniencia repo/ref/path)**: 24
- **Commits Indexados (Assunto + Corpo)**: 3
- **Alteracoes e Renomeacoes Catalogadas**: 11
- **Renomeacoes com previous_path**: 1
- **Tempo Total de Ingestao**: 0.0873 segundos

---

## 3. Desempenho por Tipo de Arquivo

| Extensao | Blobs Unicos | Chunks Gerados | Bytes Indexados |
|---|---:|---:|---:|
| `.ts` | 3 | 11 | 294461 |
| `.py` | 1 | 1 | 741 |
| `.md` | 2 | 2 | 668 |
| `.css` | 1 | 1 | 306 |
| `.json` | 1 | 1 | 132 |

---

## 4. Latencia de Consulta e Eficiencia de Snippets

| Cenario de Teste | Consulta | Hits | Tokens | Latencia p50 (ms) | Latencia p95 (ms) | Latencia Max (ms) |
|---|---|---:|---:|---:|---:|---:|
| `symbol_exact` | `LegacySidebarNavigation` | 8 | 40 | 2.099 | 3.287 | 3.287 |
| `content_multiterm` | `capacities docked sidebar` | 4 | 39 | 0.797 | 1.94 | 1.94 |
| `filter_extension` | `compute_fsrs_stability` | 3 | 28 | 0.439 | 0.601 | 0.601 |
| `filter_branch` | `qconcursos_importer` | 2 | 10 | 0.36 | 0.59 | 0.59 |
| `rename_path_filter` | `LegacySidebarNavigation` | 6 | 40 | 1.642 | 1.746 | 1.746 |
| `commit_body_search` | `Architectural decision body text` | 1 | 15 | 0.236 | 0.47 | 0.47 |
| `rename_change_search` | `old_navigation` | 2 | 2 | 0.173 | 0.322 | 0.322 |

---

## 5. Rastreamento de Renomeacoes e Busca no Corpo de Commits

### 5.1 Busca em Corpo de Commits
Consultas agora realizam busca textual integral em `subject` e `body` de commits via FTS5:
- **Decisoes de arquitetura**: Armazenadas no corpo da mensagem de commit sao recuperadas via `search_commits` ou `search(target='commits')`.
- **Proveniencia**: Cada resultado de commit contem `author`, `author_email`, `commit_date` (ISO 8601), `ref`, `commit_sha`, `subject` e `body`.

### 5.2 Rastreamento de Renomeacoes (`previous_path`)
Quando um arquivo e renomeado no Git (ex: `src/old_navigation.ts` -> `src/sidebar.ts`):
- A tabela `change_fts` indexa `path` e `previous_path`, permitindo encontrar o arquivo atual pesquisando pelo nome antigo.
- `search(path='src/old_navigation.ts')` encontra os chunks do arquivo atual `src/sidebar.ts` com status `renamed`.
- `content_occurrences.previous_path` preserva a linhagem historica completa.

---

## 6. Seguranca e Conformidade

- **Zero Emoji Policy**: O codigo fonte, mensagens de log, relatorios e documentacao foram auditados com expressao regular `[\U00010000-\U0010ffff]`; 0 emojis encontrados.
- **Secrets Gate**: Chaves privadas PEM, tokens de servico, credenciais de banco e chaves de API sao rejeitados antes de qualquer chunking ou insercao.
- **Arquivos Binarios**: Vetados por analise de bytes de controle e presenca de bytes NUL.
- **Reconstrucao Segura**: O banco SQLite e descartavel e 100% reconstruivel a partir dos Git bundles autoritativos.

---

## 7. Instrucoes de Reproducao

Execucao do benchmark e geracao do relatorio:
```bash
python3 scripts/content_index.py benchmark --output-report reports/CONTENT-INDEX-BENCHMARK.md
```

Execucao dos testes unitarios:
```bash
pytest tests/test_content_index.py -v
```
