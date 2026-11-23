# Selective Context Export & Repomix Benchmark (Issue #10)

Este documento apresenta a avaliacao do pipeline seletivo de contexto (`scripts/selective_context.py`), comparando deduplicacao por caminho/blob (#16), modos de entrega com orcamento de tokens, formato agrupado por arquivo (#8) e compactacao estruturada opcional via Repomix (`--compress` Tree-sitter) versus compactacao estrutural nativa em Python.

## 1. Pipeline e Modos de Entrega

Pipeline implementado em `scripts/selective_context.py`:

1. `search` (`search_stage`): consulta FTS5 via `scripts/content_index.py` (com fallback `AND` -> `OR` e bloqueio imediato de caminhos/padroes secretos).
2. `selecao de SHA/path` (`select_candidates`): agrupa ocorrencias por `(repository, path)` preservando `commits_matched`, `first_sha`, `last_sha` e linha do tempo com datas de commit (#8), e colapsa copias com mesmo `blob_sha` em `duplicate_paths` (#16).
3. `recuperacao` (`recover_stage`): valida e extrai objetos Git via `scripts/archive_flow.py` / `git cat-file`, revalidando binarios e bloqueando segredos por caminho e conteudo (`.env`, `.pem`, chaves privadas, tokens de API, JWTs).
4. `preparo de contexto com orcamento` (`prepare_context`): aplica `ContextBudget` (`max_files`, `max_bytes`, `max_lines`, `max_tokens`) com truncamento seguro por fronteira de linha/UTF-8 e guarda rigida do envelope JSON final.

Modos suportados:
- `metadata-only`: apenas proveniencia, datas, contagem de commits e intervalos de linhas.
- `snippet`: trechos focalizados ao redor dos termos encontrados (sem corpo integral).
- `exact-file`: conteudo integral verificado limitado pelo orcamento configurado.
- `context-pack`: unidade agrupada por arquivo (data, ref, SHA, resumo de commits, estrutura compactada + snippet principal).

## 2. Resultado do Benchmark Sintetico

Comando reproduzivel:

```bash
python3 scripts/selective_context.py benchmark
```

Corpus sintetico utilizado pelo benchmark (`_build_synthetic_benchmark_repo`):
- Componente TypeScript (`src/components/ui/sidebar.tsx`) com 7 revisoes historicas entre `main` e `feature/sidebar-compact`.
- Copia duplicada do mesmo blob em `src/components/ui/sidebar.legacy.tsx` (testa deduplicacao por `blob_sha`).
- Modulo Python (`src/domain/sidebar_state.py`) e especificacao Markdown (`docs/SIDEBAR-SPEC.md`).
- 7 modulos nao relacionados (`src/unrelated/module_1..7.ts`, 5.278 tokens no repositorio bruto).
- Arquivo `.env` com token sintetico (obrigatoriamente bloqueado).

| Cenario | Arquivos entregues | Linhas | Bytes de conteudo | Tokens de conteudo | Tokens totais (JSON) | Tempo (ms) | Repomix usado |
|---|---:|---:|---:|---:|---:|---:|---|
| `exact_no_dedup` | 33 | 2566 | 74788 | 18714 | 25517 | ~377 | nao |
| `exact_with_dedup` | 4 | 264 | 8145 | 2038 | 3022 | ~117 | nao |
| `metadata_only` | 4 | 0 | 0 | 0 | 1741 | ~40 | nao |
| `snippet` | 4 | 100 | 3158 | 790 | 1733 | ~119 | nao |
| `context_pack_builtin` | 4 | 85 | 3173 | 795 | 1762 | ~117 | nao |
| `context_pack_repomix` | 4 | 189 | 5586 | 1391 | 2389 | ~2579 | sim |

Referencias de repositorio inteiro no mesmo corpus:
- Repositorio bruto sem segredos: **5.278 tokens** de conteudo.
- Repomix `--compress` sobre o repositorio inteiro (snapshot unico, sem historico): **1.072 tokens** (~2.738 ms).

## 3. Comparacoes de Economia de Tokens

- **Deduplicacao por path + blob (`exact_with_dedup` vs `exact_no_dedup`)**: **88.16%** de reducao no volume total (25.517 -> 3.022 tokens) e reducao de 33 para 4 unidades de arquivo, sem perda de proveniencia.
- **Modo `snippet` com deduplicacao vs `exact_no_dedup`**: **93.21%** de reducao (25.517 -> 1.733 tokens); frente ao Repomix do repositorio inteiro, entrega apenas **790 tokens** de conteudo relevante (**26.31%** menor) preservando historico de commits deletados e branches antigas.
- **Modo `context-pack` nativo (`builtin-outline`) vs `exact_with_dedup`**: **60.99%** de economia em tokens de conteudo (2.038 -> 795 tokens) e **93.09%** frente ao baseline sem deduplicacao, em ~117 ms e zero dependencias externas.
- **Modo `context-pack` com Repomix (`repomix --compress`) vs `exact_with_dedup`**: **31.75%** de economia em tokens de conteudo (2.038 -> 1.391 tokens) e **90.64%** frente ao baseline sem deduplicacao, com latencia ~22x maior (~2.579 ms) devido a inicializacao Node/Tree-sitter.

## 4. Qualidade da Compactacao (TS / Python / Markdown)

Analise qualitativa observada na compactacao:
- **TypeScript/TSX**: `repomix --compress` (Tree-sitter) preserva interfaces (`SidebarConfig`, `SidebarItem`), assinaturas de funcoes e JSX principal, enquanto reduz corpos longos; porem adiciona delimitadores `⋮----` e preserva blocos JSX/comentarios que superam o outline nativo (`builtin-outline`) em arquivos medios.
- **Python**: Tree-sitter preserva `@dataclass`, assinaturas `def` e linhas iniciais do corpo; em funcoes curtas, retem parte do miolo (ex.: `retrievability`, `delta`), enquanto o outline nativo extrai exclusivamente assinaturas + docstrings de 1 linha, ficando mais compacto e delegando o detalhe ao `snippet` focalizado.
- **Markdown**: ambos preservam integralmente cabecalhos e notas curtas; em documentos longos, o `context-pack` nativo extrai apenas headings (`#`..`######`) + primeira linha de cada secao, evitando enviar listas repetitivas.

## 5. Seguranca e Conclusao de Arquitetura

1. **Preservacao de segredos**: `.env`, `.env.*`, chaves privadas (`BEGIN ... PRIVATE KEY`), tokens (`ghp_`, `sk_`, `AIza`, `AKIA`, `Bearer`, JWT) e pastas sensiveis (`.ssh`, `.aws`, `.gnupg`) sao bloqueados em tres pontos (busca, recuperacao de blob e antes de gravar qualquer arquivo temporario para o Repomix). Nenhuma integracao externa recebe segredos.
2. **Repomix permanece estritamente opcional**:
   - O maior ganho de tokens (**88.16%**) vem da **deduplicacao por path/blob (#16)** combinada ao **formato agrupado (#8)** e ao **modo `snippet`/`context-pack` nativo (93.1%-93.2%** de corte, ~117 ms, 100% Python stdlib).
   - O Repomix (`--use-repomix`) nao traz ganho de custo-beneficio como padrao obrigatorio porque exige runtime Node/npx (~2.1s de overhead por chamada) e produz saida maior que o `builtin-outline + snippet` para arquivos historicos individuais. Fica disponivel como flag opcional (`--use-repomix`) quando um agente precisar explicitamente de extracao AST Tree-sitter em arquivos TS/Python extensos.
