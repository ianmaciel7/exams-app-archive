# Catálogo de fontes visuais verificadas via GitHub (23/11/2026)

Este arquivo **não duplica** os binários de capturas nem todo o código histórico. Fornece caminhos precisos/SHAs dos arquivos-chave e uma ordem de recuperação. Confirmar ref e SHA se o repo mudar.

## 1. Principal salto de qualidade: Notes App old-5 — implementação real

Repo `ianmaciel7/notes-app`, branch `old-5`.

**Pasta verificada:** `src/app/_components/workspace/` — 56 arquivos/entradas, contendo implementações e `.stories.tsx` (Ladle), inclusive:

| Elemento | Caminho sob `src/app/_components/workspace/` | Blob SHA na auditoria |
| --- | --- | --- |
| Sidebar estrutural e seletor de espaços | `app-sidebar.tsx` | `3a0b57cfbe907c6ea6779880273d61ba02c96bdd` |
| Seções, tipos e objetos (grande) | `app-sidebar-overview.tsx` | `a020d635de368b755992e1282e18af9fdc2b8a03` |
| Ações Novo/Buscar/Explorar etc. | `app-sidebar-primary-actions.tsx` | `20f22641f60ee6069c1f8d3f164595d7155bbdda` |
| Estrutura de três painéis e resize | `app-shell.tsx` | `c8149bad08ee026dec049371d3814c29aec8b89a` |
| Definição de stories e cenários | `app-sidebar.stories.tsx`, `app-sidebar-overview.stories.tsx`, `app-shell.stories.tsx`, `app-header-tabs.stories.tsx` | consultar `fetch_file` |
| Criação/edição de tipo e permissões | `app-sidebar-object-type-studio.tsx` | consultar `fetch_file` |
| Command dialog para criar/buscar | `app-sidebar-primary-actions-command-dialog.tsx` | consultar `fetch_file` |
| Abas e controles do header | `app-header-tabs.tsx` | consultar `fetch_file` |
| Ícones da sidebar | `app-sidebar-icons.tsx`, `app-sidebar-source-icon.tsx` | consultar `fetch_file` |

Complementos em `ianmaciel7/notes-app@old-5`:

| Arquivo | SHA | Relevância |
| --- | --- | --- |
| `src/app/globals.css` | `2c7eb589786097652ceb4b468fe36ee8b6ae1fd8` | Tokens OKLCH claro/escuro e `--app-*` sem inventar paleta |
| `src/components/ui/shared-styles.ts` | `d0d3bda4590a5bf142dd6a0eac7403026eb88332` | Sombras, popovers, focus/overlay, motion |
| `src/components/ui/compact-menu.tsx` | `fbd4634ecb030f9b95fadc7178207fc0a43a0ad8` | Menus compactos com tipografia e largura consistentes |
| `src/app/_components/objects/object-icons.tsx` | `44c000c7cab4370bc1df42864d19a6e2062aee67` | Ícones e tons por tipo, sem emoji |
| `docs/ladle.md` | `6f09c3c8caf23eeaa3da89f029aa11637ff4062c` | Catálogo de componentes reais e stories, não mock paralelo |

**Cuidado:** o screenshot `exams-app-antigo-2@dev/prototype/notes-app-old-5.png` é histórico e exibe `Implementation pending` na área principal; não é exemplo de produto final pronto. HTML/CSS original, testes e stories descrevem mais que uma captura isolada.

## 2. Notes old-4 — contrato de fidelidade medido

Repo `ianmaciel7/notes-app`, branch `old-4`:

- `docs/DESIGN.md` SHA `8e219bca31fcef21d67939405dc1f718724c4efb`: no estado aceito de 28/08/2026 rail **46 px**, gutter **10 px**, editor card raio **12 px**, sidebars **288 px**; fundo `oklch(0.9856 0.0016 67)` e borda `oklch(0.9163 0.0017 67.07)`; menus com 12 px radius, linhas **32 px**, labels **14 px**, raio de item **8 px**, menu contextual **269 px**. **Valores históricos e contextuais, não presets universais.**
- `docs/references/capacities-workspace-parity.md` SHA `44495323fb66ac78b68ca21055bf97ba9452dbe1`: contrato com medições de referência autenticada datadas; identificar estado, viewport, painel e fonte.
- `docs/references/reference-evidence-workflow.md` SHA `a4af1b29e8fa3d2e5282bf417a9dcd36102b53de`: capturas reutilizáveis com manifest e DOM/geometry/computed CSS sanitizados.
- `src/components/app-sidebar.tsx`, `app-sidebar-overview.tsx`, `app-sidebar-primary-actions.tsx`, `app-shell.tsx` também existem em `old-4`, com organização diferente de `old-5`. Não misturar diretórios entre branches.

## 3. Capacities: **99 imagens recuperadas** do projeto (prioridade visual)

Repo `ianmaciel7/exams-app`, branch `dev`, diretório:

`docs/Documentos/02-referencias/capacities/imagens/recuperadas/`

Listagem GitHub confirmou **99 arquivos** PNG/WebP/SVG, entre os quais:

- `capacities_live_type_context_menu.png` — menu de tipo em sidebar (blob `99940667189bc991cd7fda6ae84b51a8ab31b42d`); **imagem realmente inspecionada** nesta auditoria.
- `reference-space-switcher-open.png` — seletor com busca e item marcado (blob `1f4e2a7906dfff243fb93636e160bdce5d9e7fb0`); imagem realmente inspecionada.
- `capacities_live_new_popover.png`, `capacities_live_collapsed_sidebar.png`, `capacities_live_object_page_anatomy.png` e `capacities_live_right_panel_related.png` — estados nominados; bytes não inspecionados nesta auditoria.
- `reference-global-new-open.png`, `reference-type-picker-open.png`, `reference-personalize-open-full.png`, `reference-primary-nav-idle.png`, `reference-plus-hover-tooltip.png` — criação, navegação e estados hover; verificar bytes antes de descrever aparência.
- `reference-mobile-390-navigation-open.png`, `reference-compact-idle-495x638.png`, `reference-trash-surface-header.png` — estados mobile, compacto e lixeira.
- `reference-related-header-hover.png`, `reference-collections-hover.png`, `reference-collection-hover-current-full.png` — estados relacionados e coleções.

Inventário completo e proveniência: `docs/Documentos/02-referencias/inventario-recuperadas.md` SHA `70dda051525ab3c5802c46681b050fb21a2d4b5b`.
Esse inventário registra **213 arquivos únicos recuperados**: 99 Capacities, 70 Readwise Reader, 39 QConcursos e 5 ExamTopics; **293 outros caminhos duplicados registrados**, não necessariamente 293 fotos diferentes. Não interpretar isso como 506 imagens.

**Evidência histórica:** as capturas Capacities são do passado e dependem de tema, espaço, UI autenticada e versão. Não afirmar que representam a UI atual do produto sem verificação.

## 4. Exams App antigo — shell de três painéis e protótipos visuais

Repo `ianmaciel7/exams-app-antigo-2`, branch `dev`:

- A listagem de `prototype/` retornou **765 entradas** (não são todas imagens nem recursos relevantes a sidebar).
- `prototype/exam-app-0.1.1__index.html` (~821 KB), protótipo standalone do produto; consultar por linhas e estado, não tentar colar tudo em um componente do chat.
- **48 capturas** `prototype/lowchrome_97_{before|after}_{light|dark}_{768|1024|1366}_{sideopen|sideclosed}_{rightopen|rightclosed}.png`:
  matriz 2 etapas × 2 temas × 3 larguras × 2 estados da sidebar × 2 estados do painel direito.
- `prototype/lowchrome_97_manifest.json` guarda metadados/estado das capturas; verificar manifest antes de comparar.
- `prototype/lowchrome_97_after_light_1366_sideopen_rightopen.png` (blob `b70ab17e09200b7f6fc3bd1ec0d444982e87daa3`) e `prototype/lowchrome_97_after_dark_1366_sideopen_rightopen.png` (blob `360f11fe8659cf3b33ed3b6123c0fd73fe1f29f5`) **inspecionados de fato** nesta revisão. Eles mostram sidebar de concursos, barra de abas, cartões centrais e painel direito contextual — mais completos que o mock de sidebar isolado.
- `prototype/archive_notes_app_old_4_capacities_shell.png` blob `d550a3adaabe674ca83c44ca55bb06567046b912` inspecionado; painel esquerdo, objeto e painel direito.
- `prototype/notes-app-old-5.png` blob `765983de3115184499a2bdab0f0d672ea3208895` inspecionado: tela parcialmente pendente; não prometer UI pronta.
- `prototype/02-workspace-e-ux.md` SHA `2c508eb857ee78e5e21a87ba82f4f40c183d96c2`, `prototype/arquitetura-informacao-navegacao.md` SHA `fa17151018ec2589fa296d5baf194b0685cb9643`: modelo de três regiões e distinção entre jornadas (Questões, Simulados) e tipos de objeto.
- `prototype/board-exam-app__index.html` e `prototype/board.json`: fontes de inventário e decisões, não renderizar tudo cegamente.

## 5. Sidebar standalone mais recente — **protótipo, não o benchmark de qualidade**

Repo `ianmaciel7/exams-app@dev`, HTML `docs/Documentos/01-planejamento/revisao/sidebar-prototipo/prototipo-sidebar.html` SHA `783b7041913a8ddc01c7bd2aa1ee6bbf6eeb7e1a` (~62 KB); pasta `capturas/` com **26 PNGs** (menu, context, tema, mobile, vazio, erro etc.). Para nomes exatos consultar `source-map.md`.

Não trate esses 26 PNGs como o conjunto total de referência de estilo. São suficientes para reproduzir **aquele protótipo específico**, mas **insuficientes sozinhos** quando o usuário pede qualidade de Capacities, Claude ou ChatGPT.

## 6. Sequência de recuperação enxuta, sem downloads maciços

1. Confirmar nome/branch com `mcp__GitHub__get_repo`/`search_branches`.
2. Se o caminho exato for conhecido, usar `mcp__GitHub__fetch_file({repository_full_name, ref, path})`; para diretórios `mcp__GitHub__fetch` GET Contents com `?ref=old-5` ou `?ref=dev`.
3. Para imagens de arquivo, `fetch_file` com `encoding:"base64"` retorna bytes base64 no campo `content` (pode incluir newlines). Remover somente quebras de linha antes de visualizá-los; os dados binários não precisam ser disponibilizados publicamente.
4. Para arquivos grandes como `app-sidebar-overview.tsx` 108 KB, ler faixas (start_line/end_line), não se limitar a resumo/commits; extrair tokens, JSX, menus, affordances.
5. Fazer matriz elemento → arquivo código → imagem real → estado → SHA → verificado/inferido → adaptação planejada.
6. Só depois criar novo design ou preview. Se usuário quer dentro do ChatGPT, aplicar `chat-preview-contract.md`.

## 7. Limites de benchmark ChatGPT/Claude

A auditoria verificou capturas de Capacities no GitHub, mas **não verificou telas autenticadas atuais de ChatGPT ou Claude**. Uma imagem ilustrativa exibida numa conversa anterior não cria uma fonte validada neste repositório. Só usar capturas reais quando acessíveis/autorizadas; não alegar paridade pixel a pixel com apps não inspecionados.

## Motion catalog

`ianmaciel7/exams-app-archive@main:docs/UI-MOTION-EVIDENCE.json` tracks 13 source-verified motion declarations/events, delays, durations, easing, states, code path/ref/line/SHA. `skills/ui-motion/SKILL.md` defines source validation; this is curated, not exhaustive or vector-based.
