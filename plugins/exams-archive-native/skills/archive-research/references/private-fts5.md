# Pesquisa autenticada (Actions + GitHub conectado)

## Privacidade obrigatória

O arquivo principal `ianmaciel7/exams-app-archive` permanece público. Nunca grave consultas, resultados, índices de conteúdo ou dados privados em branches desse repositório. A fila autorizada é `ianmaciel7/notes-app`, branch `archive-authenticated-queries-20261124`. Antes de escrever, confirme que o Notes continua privado. Se não for privado ou não houver acesso, falhe explicitamente.

## Consultar sem computador local

1. Use o GitHub conectado para ler o arquivo/commit conhecido diretamente; use a fila somente se a pesquisa histórica exigir contexto.
2. Crie um ID único de 6–64 caracteres ASCII (letras, números, hífen e sublinhado). Em `ianmaciel7/notes-app`, branch `archive-authenticated-queries-20261124`, crie `archive-query/requests/<ID>.json` com no máximo 4096 bytes. Exemplo:

```json
{"version":1,"id":"sidebar-motion-20261124-01","operation":"content_search","query":"togglePin","limit":10}
```

3. Consulte a execução `Authenticated archive queries` pelo commit criado. Leia `archive-query/results/<ID>.json` com a branch explícita. Se ainda não existir, reconsulte de modo limitado. Não confunda sucesso da Action com sucesso da consulta.
4. Exija `ok:true`, ID correspondente, `index_release`, `index_checksum` SHA-256 e `result_checksum`. Confira a release e os hashes quando necessário. Retorne caminhos, ref, commit SHA, blob SHA e linhas presentes; nunca invente proveniência. Resultados são commits privados persistentes; não envie informações sensíveis desnecessárias à fila.
5. Se a operação falhar, reporte a categoria; reduza limite ou restrinja repo/path. Para imagem/binário que exceda limite, use recuperação local autorizada do bundle, não uma réplica inventada.

## Operações

- `search`, `images`, `stats`, `coverage`: índice histórico de 595 refs. `search` aceita `kind` all/commit/file/image.
- `content_search`: texto e código indexados; filtros `repo`, `ref`, `path`, `language`, `source_sha`. Use termos literais de implementação, depois amplie sinônimos e caminhos.
- `linked_context`: relações e timeline por caminho/termo; commits recentes limitados, omissões explícitas.
- `context_pack`: snippets deduplicados, limite 1–20 e `token_budget` opcional (heurística, não contagem exata). Não confundir snippet com recuperação integral.
- `get_evidence`: `repo`, SHA completo no campo `sha`, `path`, `start_line`, `end_line` (até 100 linhas). Confirme bytes e SHA do blob; não execute código histórico.
- `graph_neighbors`: vizinhança derivada de Git histórico, caminhos e imagens; `query` ou `concept_id`, `hops` 1–2, `edge_type`, `entity_type`, `repo`. Distinga arestas inferidas das extraídas. Operação nova: confirme resultado real antes de afirmar que funcionou.

## Fontes e evidências

- `archive-index-private-2026-11-24` e `archive-content-private-2026-11-24`, releases autenticadas de Notes; SHA-256 e SQLite conferidos.
- Busca de texto, conteúdo, context pack e timeline foram testados no corpus real. A recuperação exata de código do complemento de worktrees foi conferida por blob SHA.
- O índice de conteúdo é FTS5 lexical, não embedding semântico. Tipos de arquivo, tamanhos e caminhos sensíveis têm exclusões. Use o bundle original para verificar lacunas. Não presuma que todos os ADRs, testes ou links estão indexados.
- CLI local com autenticação `gh` continua disponível. Não use a fila pública histórica `archive-search-queries`.
