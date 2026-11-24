---
name: component-explorer
description: Use when asked to browse historical repository trees, inspect React or HTML components, render and interact with previews, capture screenshots, query visual evidence, integrate CLI or MCP, or use the Exams Archive site, graph and llms.txt.
---

# Explorador de componentes e evidências visuais

## Descoberta e roteamento

- Repositório canônico: `ianmaciel7/exams-app-archive@main` (público desde 24/11/2026; verifique a visibilidade real antes de qualquer consulta/escrita). Não confundir repositório público com autorização para publicar arquivos privados do Notes App ou novas capturas.
- Site: https://ianmaciel7.github.io/exams-app-archive/ ; árvore e código: `files.html`; guia de descoberta: `llms.txt`. Se Pages falhar, leia o status do workflow e o código original no GitHub; não invente uma prévia publicada.
- Leia primeiro `docs/COMPONENT-EXPLORER.md`, `docs/AGENT-ACCESS.md`, `scripts/component_catalog.py`, `scripts/archive_mcp.py` e `site/files.html` conforme a tarefa. Para reproduzir um componente existente, aplique também `ui-fidelity`, `ui-motion` e as referências de código, CSS, stories e screenshots. FTS5 isolado não prova aparência nem comportamento.
- O explorador abre árvores Git de revisões públicas e arquivos restaurados localmente. O grafo aceita JSON do grafo nativo e relações estruturais do índice. Não diga que todo o histórico, todos os componentes ou relações semânticas já estão disponíveis automaticamente no site.

## CLI canônica e MCP local

Use a raiz de um checkout revisado do archive, não presuma que as dependências ou o servidor já estejam instalados. O script do plugin é o espelho da CLI, mas os comandos novos importam módulos em `scripts/` da raiz (ou `EXAMS_ARCHIVE_ROOT`). A documentação canônica explica como preparar dependências React/esbuild, Python Playwright e Chromium. Consulte a CLI `--help` e a implementação atual antes de chamar.

```sh
python plugins/exams-archive-native/scripts/archive_query.py components list
python plugins/exams-archive-native/scripts/archive_query.py components render error-boundary
python plugins/exams-archive-native/scripts/archive_query.py components capture error-boundary --state retry --theme dark --width 390 --height 844
python plugins/exams-archive-native/scripts/archive_query.py components screenshots --component error-boundary
python plugins/exams-archive-native/scripts/archive_query.py components export SCREENSHOT_ID --output component.png
```

O MCP `scripts/archive_mcp.py` é local, stdio e opcional. Ferramentas: `components_list`, `component_render`, `component_capture`, `component_screenshots`, `component_screenshot_image` (PNG real), além de `search`, `graph`, `context`, `images`, `stats`. Use ferramentas reais apenas se disponíveis no cliente. GitHub Pages não hospeda um MCP executável; o plugin ChatGPT é de skills e não registra automaticamente esses endpoints locais. Sem executor, use GitHub conectado para inspecionar código/CI e indique o limite; não fabrique imagens, capturas ou respostas MCP.

## Previews e provas

- Comece por `components list`: o catálogo de componentes revisados é a fonte de verdade. O primeiro componente interativo é `error-boundary` de `exams-app-old`, commit `b86b70c304e574022416e8e2ecdc3816f1b386f1`, `src/app/error.tsx`, blob `936e638aa231a2533e866c12e4d97a429c524d6c`. O reset e alternância de tema são fixture; não são integração de produção. Loading é um preview SSR separado.
- Capture com Playwright somente builds revisados, sem credenciais, usando estado, tema e viewport explícitos. Não execute código legado desconhecido nem instale dependências arbitrárias. Para screenshots existentes use `component_screenshots` e depois a imagem real, evitando reexecutar builds desnecessariamente.
- O SQLite local `~/.cache/exams-app-archive/component-previews/components.sqlite` conserva PNG BLOB, caminho, SHA do commit e blob, SHA-256 do build e PNG, estado, tema, viewport e timestamp. O índice histórico e o banco visual são distintos. Não envie o banco, imagens privadas ou tokens para Pages/branches públicas. Para ampliar a cobertura, revise fonte e dependências, adicione fixture e manifeste proveniência, verifique interações e compare screenshots originais; não chame adaptação de réplica fiel.
- Para preview dentro do ChatGPT, siga o contrato autocontido de `ui-fidelity` (sem iframe remoto). A galeria Pages e os artefatos PNG são alternativas, não substitutos automáticos. Reporte resultados efetivamente verificados: build, interação, screenshot e publicação separadamente.
