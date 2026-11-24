# Protocolo FTS5 privado nativo (Actions + GitHub conectado)

## Bloqueio de privacidade

O repositório foi tornado público em 24/11/2026. Uma branch de repositório público não é privada. Antes de qualquer request, verifique visibilidade: se público, NÃO grave consultas ou resultados históricos potencialmente privados em `archive-search-queries`. Prefira a CLI local. As etapas abaixo documentam o protocolo histórico e só são permitidas para um destino efetivamente privado e autorizado.

## Ferramentas e branches

- Repositório: `ianmaciel7/exams-app-archive` (historicamente privado; agora verifique).
- Códigos de busca verificados: `scripts/archive_remote_query.py` e `.github/workflows/archive-private-search.yml` na `main`.
- Branch exclusiva de mensagens: `archive-search-queries` (não modificar backups nem mesclar na `main`).
- Modelo de request: `.archive-search/requests/<ID>.json`.
- Resultado: `.archive-search/results/<ID>.json`.
- Registro de prova: `https://github.com/ianmaciel7/exams-app-archive/actions/runs/45267569005` (12 referências grafo/sidebar e índice SHA-256 conferido).

## Como efetuar consulta

1. Para busca que não pode ser resolvida com relatórios, gere um ID único, por exemplo `grafo-20261123-analise-01` (6–64 caracteres ASCII alfanuméricos, hífens ou sublinhados, iniciando com alfanumérico).
2. Com o GitHub instalado, chame `mcp__GitHub__create_file` com `repository_full_name: "ianmaciel7/exams-app-archive"`, `branch: "archive-search-queries"`, `path: ".archive-search/requests/<ID>.json"` e conteúdo JSON abaixo. A mensagem de commit deve indicar uma consulta privada. Nunca sobrescreva pedido já existente; crie outro ID em colisão.
3. Encontre a execução de `Private historical archive search` pelo commit criado, usando `mcp__GitHub__fetch_commit_workflow_runs` ou o endpoint Actions via conexão GitHub. Aguarde de forma limitada, sem prometer trabalho em segundo plano.
4. Ao concluir com sucesso, chame `mcp__GitHub__fetch_file` com `ref: "archive-search-queries"` e `path: ".archive-search/results/<ID>.json"`.
5. Valide `id` igual, `ok:true`, `request_sha256` com 64 caracteres hexadecimais, `index_release` e `index_checksum`. Se a Action falhar ou o resultado não estiver disponível, reporte sem fingir êxito. Extraia poucos resultados com `repository`, `kind`, `sha`, `path`, `summary`, `blob`, `deleted` conforme presentes.

## Pedidos aceitos

Busca geral (busca lógica OR sobre tokens, limite até 40):

```json
{"version":1,"id":"grafo-20261123-analise-01","operation":"search","query":"grafo sidebar","kind":"all","limit":20}
```

`kind` pode ser `all`, `commit`, `file`, `image`. O campo opcional `repo` restringe a fonte.

Imagens apagadas:

```json
{"version":1,"id":"grafo-imagens-20261123-01","operation":"images","repo":"exams-app-antigo-2","deleted_only":true,"limit":20}
```

Estatísticas:

```json
{"version":1,"id":"estatisticas-20261123-01","operation":"stats"}
```

Todos os requests são JSON simples, até 4096 bytes, e o worker valida operação, tipo, caminho de saída e limite.

## Limites importantes

Cada pedido é um commit privado + execução GitHub Actions; não iniciar se a pergunta pode ser respondida lendo relatório. O worker baixa e verifica a release SQLite FTS5 sem divulgar o índice. Os resultados ficam versionados na branch privada. Isso não cria API de serviço contínuo nem executa busca sem ter disponível uma ferramenta GitHub com permissões de escrita. A execução depende do Actions habilitado e da permissão atual da conexão GitHub. Não transforma o repositório em público, não baixa imagens binárias nem oferece texto integral dos fontes.
