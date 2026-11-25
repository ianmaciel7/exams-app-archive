# Exams Archive — pacote único multiagente (v0.8.1)

Fonte canônica do plugin privado para **ChatGPT, Codex, Claude Code e Antigravity**: `plugins/exams-archive-native/` na branch `main` deste repositório. Nenhum backup histórico é publicado no pacote.

## Conteúdo
- `skills/archive-research`: GitHub conectado e localização de histórico.
- `skills/archive-search` + `scripts/archive_query.py`: FTS5 autenticado no ambiente local (Python stdlib e `gh`).
- `skills/ui-fidelity`: recuperação de protótipos, capturas e componentes originais.
- `skills/ui-motion`: transições e microinterações com evidência por SHA.
- `skills/sync-bridge`: fluxo GitHub → publicação de releases, com divergência explícita.

## Instalação
- **Codex**: `codex plugin marketplace add ianmaciel7/exams-app-archive`, depois instalar `exams-archive-native` no marketplace privado.
- **Claude Code**: `claude plugin marketplace add ianmaciel7/exams-app-archive` e `claude plugin install exams-archive-native@exams-archive-private`.
- **Antigravity**: após clone do repositório canônico, `agy plugin validate plugins/exams-archive-native` e `agy plugin install ./plugins/exams-archive-native`. Para distribuição direta por URL, verificar suporte da versão do cliente a subdiretórios de repositório.
- **ChatGPT pessoal**: release privada atualizada via Plugin Creator com arquivos da fonte canônica; sync automática GitHub → publicação depende de workspace elegível e **não está habilitada** pela existência deste repositório.

O script `archive_query.py` é mantido em paridade com o legado por teste de hash; para pesquisa local execute `python scripts/archive_query.py sync` dentro da pasta do plugin e então `python scripts/archive_query.py search "sidebar" --limit 10`.

O plugin histórico em `plugins/exams-archive/` foi preservado para recuperação/rollback, mas saiu do marketplace ativo. Ele não é removido automaticamente. Veja `docs/PLUGIN-SYNC.md`.

## Segurança
O repositório foi tornado público em 24/11/2026. Verifique a visibilidade antes de usar Actions; nunca escrever consultas, resultados, índices, bundles, tokens ou imagens privadas em branches/Pages públicas. Toda alteração no pacote entra por GitHub, com CI e review; publicação ChatGPT é uma etapa explícita, não webhook.

## Componentes e capturas (0.7.0)
A skill `component-explorer` orienta árvore de arquivos, grafo, Pages, `llms.txt`, renderização React revisada, captura Playwright e catálogo SQLite. Leia `docs/COMPONENT-EXPLORER.md` no repositório para a CLI `components` e o MCP stdio local. Os comandos novos precisam do checkout canônico e dependências; não são ferramentas MCP remotas instaladas no ChatGPT.

## Sincronização de conhecimento UI/UX

- `skills/sync-ux-knowledge`: comando explícito "mande tudo memoria,plugin,github"; consolida uma única delta e sincroniza Especialista em UI/UX, arquivo GitHub, referência privada da Biblioteca e memória do ChatGPT quando suportada. Verifica os quatro destinos de forma independente; não promete gravação automática na memória.
