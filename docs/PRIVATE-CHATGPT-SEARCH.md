# Consulta nativa ao SQLite FTS5 via GitHub privado

Esta ponte permite que o **plugin nativo Exams Archive do ChatGPT** consulte o SQLite histórico hospedado em release privada, sem exigir computador ligado nem criar um servidor MCP.

## Escopo e protocolo

O índice cobre mensagens de commits, caminhos de arquivos e inventário de imagens. **Não** cobre texto integral de todos os blobs. Cada pedido retorna no máximo 40 resultados.

A conexão GitHub autorizada no ChatGPT cria um arquivo pequeno na branch privada `archive-search-queries`, separado do histórico imutável em `main`. Isso é uma **escrita de metadados de busca**, não uma operação somente leitura.

- Enviar usando `mcp__GitHub__create_file`, com `branch: "archive-search-queries"` e caminho `.archive-search/requests/<id>.json`.
- O GitHub Actions `archive-private-search.yml` detecta o push, usa seu token temporário para baixar a release privada e verificar o SHA-256 do índice, e executa `scripts/archive_remote_query.py` com limites.
- Ler `.archive-search/results/<id>.json` pela ferramenta `mcp__GitHub__fetch_file` com `ref: "archive-search-queries"` **apenas depois que a execução terminar**.
- Se `ok: false`, informar a falha; não declarar pesquisa concluída. Conferir `request_sha256`, `index_release` e `index_checksum`.

Busca real já validada: [execução do grafo/sidebar](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45267569005).

## Pedidos permitidos

Busca por commits/caminhos/imagens:

```json
{"version":1,"id":"grafo-sidebar-20261123-01","operation":"search","query":"grafo sidebar","kind":"all","limit":20}
```

Inventário de imagens históricas excluídas:

```json
{"version":1,"id":"imagens-antigas-20261123-01","operation":"images","repo":"exams-app-antigo-2","deleted_only":true,"limit":20}
```

Estatísticas do índice:

```json
{"version":1,"id":"stats-archive-20261123-01","operation":"stats"}
```

Os IDs devem ter 6–64 caracteres alfanuméricos, hífen ou sublinhado. O nome do arquivo JSON deve coincidir com o ID. Os resultados ficam na branch privada; não fazer merge na `main`.

## Segurança e custos

- Nunca publicar requests/results, SQLite ou bundles no Pages.
- A Action lê código confiável da `main`, valida os campos de entrada e não avalia shell de usuário.
- O GitHub Actions consome minutos de CI por busca; prefira relatórios existentes para perguntas triviais.
- A fila processa em lotes de até **30 pedidos** por execução (até 5 lotes por workflow) e informa `pending_remaining` / `status` (`complete` ou `pending`). Pares processados (`requests/` + `results/`) com mais de **14 dias** são podados pela política de retenção, preservando a branch ativa `archive-search-queries`.
- Não remover histórico, releases, repositórios antigos ou indexar credenciais.
- Recuperação efetiva de bytes de imagens ou documentos ainda exige acesso autorizado ao bundle correspondente; os resultados aqui fornecem **referências e SHAs**, não cópias de binários. Para recuperação local verificada com `source_repo`, `ref`, `full_sha`, `path`, `mime`, `sha256` e preview base64/linhas, utilize `scripts/archive_flow.py` (`search`, `fetch`, `preview`, `recover`).
