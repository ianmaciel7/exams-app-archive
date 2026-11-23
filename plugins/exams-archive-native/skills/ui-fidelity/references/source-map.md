# Mapa verificado das fontes para sidebar e app-shell

**Atualização v0.4.0:** este mapa da sidebar standalone é insuficiente sozinho. Para as fontes visuais mais completas, ler `visual-source-catalog.md`. Para render no chat, ler `chat-preview-contract.md`.

**Observado em 23/11/2026.** Todos os caminhos e SHAs devem ser reconfirmados antes de aplicar alterações. Distinguir documentos atuais do repo de backup privado.

## Fonte primária de preview sidebar — HTML realmente recuperável

- Repo: `ianmaciel7/exams-app` (público), **branch preexistente** `dev`.
- HTML standalone: `docs/Documentos/01-planejamento/revisao/sidebar-prototipo/prototipo-sidebar.html`; blob SHA observado `783b7041913a8ddc01c7bd2aa1ee6bbf6eeb7e1a` (~62 KB). É HTML único com `<!doctype>`, `<style>`, `<svg>` e `<script>`; não requer build de Next/Firebase. Não copiar somente a navegação: HTML também contém menus, dados e eventos.
- Decisões de implementação: `docs/Documentos/01-planejamento/revisao/sidebar-prototipo/decisoes.md` (SHA `5a6b72be94ccfe4316e65dcd9fafaba9fa9accf1`). O documento relata testes Playwright históricos; isso **não substitui** testes atuais.
- Comparação e lacunas: `docs/Documentos/01-planejamento/revisao/sidebar-comparacao-2026-11-23.md` (SHA `7e24cf89d6ca147b44f118c7725c058f04a6ea0e`). Distingue o que vinha de old-5 (objetos) e old-10 (mecânica), além de diagnóstico de preview que perdeu paridade.
- Mapeamento histórico: `docs/context/memoria/sidebar-referencias-repos.md` (SHA `6db7a556a60b2d426b52717a04058ab227d009f9`). **É um mapa para fontes, não o código das fontes**.
- Prefixo REST para listagem: `https://api.github.com/repos/ianmaciel7/exams-app/contents/docs/Documentos/01-planejamento/revisao/sidebar-prototipo?ref=dev`.

## 26 screenshots existentes: NÃO perder

Pasta: `docs/Documentos/01-planejamento/revisao/sidebar-prototipo/capturas/` em `ianmaciel7/exams-app@dev`.

- Desktop claro: `d-light-1.png`, `d-light-2-menu-tipo.png`, `d-light-3-ctx.png`, `d-light-4-novo.png`, `d-light-5-switcher.png`, `d-light-6-renomear.png`, `d-light-7-usuario.png`, `d-light-8-peek.png`.
- Desktop escuro: `d-dark-1.png`, `d-dark-2-menu-tipo.png`, `d-dark-3-ctx.png`, `d-dark-4-novo.png`, `d-dark-5-switcher.png`, `d-dark-6-renomear.png`, `d-dark-7-usuario.png`, `d-dark-8-peek.png`.
- Estados especiais desktop: `d-estado-loading.png`, `d-estado-empty.png`, `d-estado-error.png`, `d-lixeira.png`.
- Mobile claro: `m-light-1.png`, `m-light-2-gaveta.png`, `m-light-3-menu.png`.
- Mobile escuro: `m-dark-1.png`, `m-dark-2-gaveta.png`, `m-dark-3-menu.png`.

Total: **26 arquivos listados**, não necessariamente todos visualizados. Recuperar bytes com ferramenta autenticada ou URLs públicas verificadas antes de comentar cor, densidade ou pixel matching. Não usar `image_query` genérico para substituí-los.

## App-shell: base de tokens de design anterior

- Decisões: `ianmaciel7/exams-app@dev` → `docs/Documentos/01-planejamento/revisao/app-shell/decisoes.md` (SHA `d811241f0a0f694694d35e4636ed46d2e38478c9`). Refeito com tokens `notes-app@old-5` e moldura neutra; menciona screenshot `notes-old-5-home.png` e artifact `https://claude.ai/artifact/6q6XbLy2SFxbwq61wgetrH`.
- **Importante**: em 23/11/2026, `app-shell/prototipo-app-shell.html` **não estava presente** na árvore de `exams-app@dev`; não declare que esse arquivo foi recuperado só porque está citado no documento. Se necessário, verificar Claude Gateway autorizado/artifact ou release/bundle correspondente.
- Tokens verificados no repo privado conectado: `ianmaciel7/notes-app@old-5` → `src/app/globals.css` (SHA `2c7eb589786097652ceb4b468fe36ee8b6ae1fd8` visto neste levantamento). Recuperar conteúdo integral, não inferir valores OKLCH de uma descrição.
- Cuidado: os docs dão informação divergente sobre chips coloridos: sidebar-prototipo usa chips por tipo; app-shell v1.0 declara ícones monocromáticos. **É uma divergência real de alvos, não licença para misturar os dois**. Escolher a fonte visual solicitada e explicitá-la.

## Origens históricas e proveniência

- `notes-app@old-4/old-5`: criação/renomeação de objetos, menus de contexto, tipos, dnd-kit; a referência de fidelidade deve vir de código e capturas reais, não de texto aproximativo.
- `notes-app@old-10`: mecânica de sidebar colapsada, peek, resize; documentos mencionam `space-frame.tsx` e `domain/sidebar.ts` mas o caminho exato no repo precisa verificação na branch. Não inventar um path.
- `notes-app@old-11`: space switcher, usuário, skeleton/vazio/erro.
- `exams-app-antigo-2@dev`: `prototype/exam-app-0.1.1__index.html` mencionado na comparação; confirmar caminho real (nome e branch) antes de citar SHA.
- `exams-app-archive@main`: backup privado com bundles; para extração por commit usar `docs/EXTRACTION-GUIDE.md`. A indexação FTS5 contém caminhos e mensagens, não CSS/HTML integral.

## Contrato para qualquer solicitação de visualização

Sempre declarar (a) artefato e ref consultados; (b) screenshots efetivamente inspecionados; (c) se visual é **original / reprodução verificada / proposta nova**; (d) limites do formato; (e) partes sem comportamento comprovado. Se usuário pediu preview aqui, preservar a aparência do original ou mostrar evidência original. Mock reduzido sem aviso falha no objetivo.

## Correção de localização que faltava no v0.3.0

O Notes App old-5 **não** concentra sua sidebar em `src/components/layout`. A pasta confirmada pelo GitHub é:

`ianmaciel7/notes-app@old-5/src/app/_components/workspace/` (56 entradas na listagem)

Inclui `app-sidebar.tsx`, `app-sidebar-overview.tsx`, `app-sidebar-primary-actions.tsx`, `app-sidebar-object-type-studio.tsx`, `app-sidebar-primary-actions-command-dialog.tsx`, `app-shell.tsx`, `app-header-tabs.tsx` e `*.stories.tsx`. Os primitivos globais ficam em `src/components/ui/shared-styles.ts`, `compact-menu.tsx`, e os ícones de objeto em `src/app/_components/objects/object-icons.tsx`.

A mecânica antiga old-10 está em `src/components/space-frame.tsx` (caminho validado), não `src/components/layout/space-frame.tsx`.

Não se limitar a ler `docs/context/memoria/sidebar-referencias-repos.md`: é somente um mapa resumido e não o código CSS/React usado na tela.
