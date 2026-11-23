# Exams Archive — plugin privado ChatGPT (v0.5.1)

Pesquisa Git/FTS5, recuperação visual e motion-aware baseada em evidências reais do histórico, mais um protocolo de sincronização bidirecional de **código-fonte do plugin** com o GitHub privado.

## Duas implementações — não sobrescrever

- **ChatGPT** `exams-archive-native` (esta release): espelho em `plugins/exams-archive-native/` no repositório `ianmaciel7/exams-app-archive`.
- **Codex legado** `exams-archive` em `plugins/exams-archive/`: preservado, com Python/FTS5 e seu manifesto próprio.

O espelho do GitHub é uma fonte versionada dos arquivos do plugin ChatGPT; não é a cópia de bundles, releases, índice FTS5 ou artefatos históricos.

## Fluxos

1. Histórico privado e backups: `skills/archive-research/SKILL.md` e referência FTS5. Buscas FTS5 podem criar writes na branch `archive-search-queries`.
2. Sidebar, shell, design e preview: `skills/ui-fidelity/SKILL.md`, `references/visual-source-catalog.md` e `references/source-map.md`; checar código, imagens e estados.
3. Animações, hover e drag: `skills/ui-motion/SKILL.md` e catálogo privado com fontes/SHA.
4. **Sincronização ChatGPT ↔ GitHub:** `skills/sync-bridge/SKILL.md`. Antes e depois de qualquer alteração relevante do plugin, comparar versões, arquivos e SHA. Criar mudanças verificáveis nos dois lados e relatar conflitos.

## Limitação da automação

Não existe webhook ou daemon neste plugin de skills que publique automaticamente releases do ChatGPT a cada commit GitHub. A sincronização é executada com ferramentas GitHub + Plugin Creator conectadas durante uma solicitação. Um commit no GitHub, sozinho, não atualiza a instalação ChatGPT. Não afirmar que os lados estão sincronizados enquanto houver PR não mesclada ou diferença de conteúdo.

## Segurança

O repositório e o histórico são privados. Não publicar arquivos, índices, capturas ou segredos em Pages; não alterar bundles/release, backups históricos, `exams-app@dev` ou plugin Codex ao sincronizar a fonte desta release.
