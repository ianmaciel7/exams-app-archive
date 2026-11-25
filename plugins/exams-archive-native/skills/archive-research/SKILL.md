---
name: archive-research
description: Use to research, verify, audit, search or recover historical Exam App/Notes App repositories, commits, Git bundles, screenshot paths, code and original UI sources. Use GitHub connected reads and local FTS5; do not send private queries to public Actions. For a visual preview or sidebar/UI reconstruction also consult ui-fidelity.
---

# Exams Archive — pesquisa histórica via GitHub

Fonte do **backup histórico**: repositório **público desde 24/11/2026** (confirme a visibilidade antes de escrever) `ianmaciel7/exams-app-archive`, branch `main`. O GitHub já está conectado. O plugin não cria ferramenta MCP independente. Para fontes **atuais de protótipos**, consulte também `ianmaciel7/exams-app@dev` e os repos originais quando acessíveis, sem confundir com o backup.

## Roteamento: decidir antes de buscar

- **Salvar/sincronizar pesquisa UI/UX** ("mande tudo memoria,plugin,github" ou variantes): carregar `skills/sync-ux-knowledge/SKILL.md` antes de consultar novamente fontes ou modificar arquivos. O destino plugin é o Especialista em UI/UX; este plugin apenas orquestra.

- **Criação, reprodução ou preview de UI (sidebar, shell, layout, design, HTML, imagem de referência)**: leia a skill **`ui-fidelity`**, `visual-source-catalog.md`, `chat-preview-contract.md` e `source-map.md` **antes** de qualquer FTS5. Primeiro obtenha os arquivos e screenshots originais, não um índice genérico.
- **Auditoria de backup/restauração**: leia `README.md`, `docs/VERIFICATION-2026-11-23.md`, `docs/DELETE-READINESS.md` e `docs/EXTRACTION-GUIDE.md` conforme necessidade. Verifique o status presente; jamais conclua que o Notes privado está 100% restaurado só por histórico.
- **Busca histórica sem caminho conhecido**: relatórios primeiro, busca autenticada privada depois (`references/private-fts5.md`).

## Consulta com menor custo

1. Use `mcp__GitHub__get_repo` para confirmar acesso, privacidade e repositório.
2. Se arquivo/ref/caminho conhecido, use `mcp__GitHub__fetch_file` **diretamente**, com `ref` explícita. Para listar pastas ou inspecionar árvore use `mcp__GitHub__fetch` GET de `https://api.github.com/repos/<owner>/<repo>/contents/<path>?ref=<branch>` (somente se a ferramenta oferecer esse endpoint).
3. Para buscas sem caminho, use `reports/ARCHIVE-STATUS-2026-11-24.md`, `inventory/` e depois a fila autenticada do Notes App descrita em `references/private-fts5.md`. Consulte conteúdo, relações, context packs e evidências no fluxo enriquecido. Não escreva consultas na branch pública do arquivo.
4. Limite a 10–20 resultados, refine por repositório/termo/tipo e apresente origem, ref, SHA, caminho, tipo, release. Diferencie **registro indexado** de **bytes efetivamente recuperados**.
5. Para reconstruir UI, **não transforme** uma lista de arquivos/commits ou resumo em suposta réplica visual. Se houver HTML/CSS/TSX e capturas, são a fonte prioritária; a versão do chat precisa de verificação visual.

## Segurança

Não peça tokens, computador ligado nem clone local se a conexão GitHub já atende. Não faça escrita fora de consulta FTS5 e não modifique repositórios, branches, arquivos de backup, releases, artefatos ou configuração do app sem solicitação. Não execute código legado automaticamente, exponha conteúdo privado publicamente, faça merge da branch de buscas, nem exclua repositórios antigos. Se a execução FTS5 não retornar JSON `ok:true` com ID, `index_release` e `index_checksum` válidos, reporte falha.

Referências: `references/github-connected.md`, `references/private-fts5.md`; para UI usar `skills/ui-fidelity/SKILL.md`.

## Motion retrieval

The historical FTS5 indexes paths and commit subjects. The authenticated advanced index supports source-body lexical search; use it for motion, with `skills/ui-motion/SKILL.md` and `docs/UI-MOTION-EVIDENCE.json` followed by original SHA verification.

## Componentes, grafo e capturas
Para árvore de arquivos, código, React interativo, screenshots, SQLite visual, CLI/MCP e site/llms.txt, carregue `skills/component-explorer/SKILL.md` antes de consultar ou renderizar. Leia `docs/COMPONENT-EXPLORER.md` e verifique as ferramentas realmente disponíveis.
