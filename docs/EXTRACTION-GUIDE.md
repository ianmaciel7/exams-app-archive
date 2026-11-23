# Consultar o arquivo histórico

O `exams-app-archive` é **privado**. Reúne um índice compacto no Git e bundles
históricos em uma [release privada](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-initial).
Não é o código-fonte do aplicativo atual.

## Nível 1 — leitura rápida no GitHub

- [`reports/POC.md`](../reports/POC.md) — resultados reais, latências e exemplos.
- [`reports/POC.json`](../reports/POC.json) — resultados, commits e hashes verificáveis.
- [`manifests/release-2026-11-23.json`](../manifests/release-2026-11-23.json) — backups Git, nomes, SHA-256 e verificação.

Esses arquivos são texto comum: podem ser consultados diretamente pelo plugin
GitHub no ChatGPT sem carregar o índice SQLite completo.

## Nível 2 — busca local no índice SQLite

Clone este repositório privado com `gh repo clone ianmaciel7/exams-app-archive`.
Na raiz do repositório, execute:

```powershell
python scripts/archive_index.py --db reports/archive-index.sqlite search grafo
python scripts/archive_index.py --db reports/archive-index.sqlite search qconcursos
python scripts/archive_index.py --db reports/archive-index.sqlite search capacit
python scripts/archive_index.py --db reports/archive-index.sqlite images --deleted-only
```

As consultas usam FTS5 sobre **mensagens de commit e caminhos de arquivos**.
Não incluem ainda busca semântica sobre todo o texto de cada versão histórica.

## Nível 3 — recuperação comprovável de uma versão antiga

No terminal com `gh` autenticado, baixe o bundle antigo de Notes:

```powershell
gh release download archive-2026-11-23-initial --repo ianmaciel7/exams-app-archive --pattern notes-app-old-10.bundle --dir downloads
git clone --mirror downloads/notes-app-old-10.bundle .cache/notes-app-old-10.git
python scripts/archive_index.py recover --repo .cache/notes-app-old-10.git --sha cabcec2e8227fc7f06aa5c9c5afcc0e8944802c6 --path src/domain/recall.ts --output recovered/recall.ts
```

Essa implementação histórica de `src/domain/recall.ts` foi recuperada na POC.
O resultado inclui seu SHA-256, identificador do commit e caminho original.

Para uma imagem removida em determinado commit, baixe
`exams-app-antigo-2.bundle`, restaure-o com `git clone --mirror` e use:

```powershell
python scripts/archive_index.py recover --repo .cache/exams-app-antigo-2.git --sha 65ce2ab7ac95e8fc4e1be998eb0aa593049bf2c8 --path prototypes/board-exam-app/assets/issue68_graph_toolbar_1366.png --output recovered/issue68_graph_toolbar_1366.png
```

Não use `git show ... > imagem.png` em shells que possam alterar bytes na
redireção. O comando Python grava os bytes binários diretamente.

## Regras importantes

1. Os bundles da release incluem referências históricas *internamente*, sem
   recriar as branches `old-*`, `claude/*` ou `dependabot/*` no repositório atual.
2. A release contém cinco bundles de repositórios públicos e quatro snapshots
   históricos de `notes-app`. O histórico **completo** do `notes-app` privado
   ainda não foi copiado.
3. A integridade foi verificada com `git bundle verify`; o backup
   `exams-app-old.bundle` também foi baixado da release e conferido por SHA-256.
4. Não apague nem arquive repositórios originais antes de comprovar cobertura,
   incluindo branches e referências históricas privadas faltantes.
5. Se precisar de acesso programático MCP a todas as versões, implemente somente
   após comprovar que o GitHub MCP e a CLI não atendem à necessidade.