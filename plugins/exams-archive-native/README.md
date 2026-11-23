# Exams Archive — pacote único multiagente (v0.6.0)

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
- **Antigravity**: após clone autenticado do repositório privado, `agy plugin validate plugins/exams-archive-native` e `agy plugin install ./plugins/exams-archive-native`. Para distribuição direta por URL, verificar suporte da versão do cliente a subdiretórios de repositório privado.
- **ChatGPT pessoal**: release privada atualizada via Plugin Creator com arquivos da fonte canônica; sync automática GitHub → publicação depende de workspace elegível e **não está habilitada** pela existência deste repositório.

O script `archive_query.py` é **idêntico ao legado**, verificado por teste de hash; para pesquisa local execute `python scripts/archive_query.py sync` dentro da pasta do plugin e então `python scripts/archive_query.py search "sidebar" --limit 10`.

O plugin histórico em `plugins/exams-archive/` foi preservado para recuperação/rollback, mas saiu do marketplace ativo. Ele não é removido automaticamente. Veja `docs/PLUGIN-SYNC.md`.

## Segurança
Nunca compartilhar o índice FTS5, bundles, tokens ou imagens privadas via GitHub Pages. Toda alteração no pacote entra por GitHub, com CI e review; publicação ChatGPT é uma etapa explícita, não webhook.
