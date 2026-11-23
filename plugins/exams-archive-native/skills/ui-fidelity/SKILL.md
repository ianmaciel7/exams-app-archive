---
name: ui-fidelity
description: Use when asked to create, show, preview, compare, rebuild, migrate, improve or audit a sidebar, app-shell, navigation, component, interaction or visual design based on historic Exams App, Notes App, Capacities, ChatGPT, Claude or other references in the Exams Archive. Retrieve the original HTML/CSS/TSX, screenshots and design decisions before authoring any preview, mockup or code.
---

# Exams Archive — fidelidade UI/UX (não apenas busca de commits)

## Missão e erro a evitar

O usuário quer **fidelidade a interfaces existentes**, não uma sidebar genérica inventada a partir de uma lista de funcionalidades. O erro registrado em 23/11/2026 foi mostrar uma prévia simplificada no chat ignorando o HTML standalone e as **26 capturas de estados** já presentes em `exams-app@dev`. Não chamar um mock redesenhado de "a sidebar do arquivo".

**Qual fonte vem primeiro?** Leia `references/source-map.md` e valide a ref. O arquivo é importante, mas não é sinônimo de preview. Há três saídas distintas:

1. **"Quero ver o preview aqui"**: procurar HTML standalone **e seus PNGs originais**. Preferir reproduzir o documento original integral quando o ambiente suportar, sem refazer CSS/JS arbitrariamente. Se uma renderização exata não puder ser integrada no chat, mostrar/abrir as capturas reais ou entregar HTML original para visualização e **dizer a limitação**. Não criar réplica inferior por conveniência. A prévia é rotulada "original" só se for o código original de fato; se for adaptação, discriminar diferenças, recursos e estados.
2. **"Crie uma sidebar nova baseada nas antigas"**: recuperar primeiro tokens, estrutura e screenshots; documentar quais decisões vieram de qual branch. Produzir design novo somente se o usuário pediu criação; nunca dizer que nova UI é cópia fiel. Tratar qualidade visual, densidade, estados e interações como critérios objetivos (`references/visual-qa.md`).
3. **"Onde está a sidebar / quais diferenças?"**: fonte + caminho exato + SHA + principais evidências, sem inventar funcionalidade ou render.

## Roteamento visual obrigatório — novas fontes recuperadas

A versão 0.3.0 conhecia sobretudo a sidebar standalone de `exams-app@dev`. O levantamento do GitHub de 23/11/2026 encontrou evidências **mais completas**. Ler antes do preview:

1. `references/visual-source-catalog.md`: diretório exato do Notes App old-5, contratos mensuráveis old-4, inventário das 213 imagens, 48 capturas lowchrome, screenshots e arquivo original antigo.
2. `references/source-map.md`: navegação rápida para o HTML e 26 capturas do protótipo `exams-app@dev` (o design deste protótipo é **mais simples**, não é o teto de qualidade).
3. `references/chat-preview-contract.md`: regras para quando o pedido é "ver aqui no próprio ChatGPT". **Sem fetch remoto, sem iframe para GitHub, sem assets CDN ou código externo**. A implementação do preview deve ser autocontida e precisa de QA visual/funcional antes da resposta.
4. `references/visual-qa.md`: estados a testar e classificação honesta de original vs adaptação.

**Escolha por objetivo, não por conveniência:**
- Para **reproduzir o protótipo específico de sidebar**: HTML de `exams-app@dev` + 26 imagens como fonte, sem chamar adaptação de original.
- Para **aparência premium** inspirada em Capacities/Claude/ChatGPT: priorizar telas de referência identificáveis, `notes-app@old-4` (contrato de medidas) e `notes-app@old-5` (componentes reais + CSS + stories). O HTML standalone de 62 KB é um **protótipo histórico**, não um design system premium.
- Para **Exams App com três regiões**: consultar matriz `lowchrome_97` e as telas de navegação (tabs, painel contextual, cards, estados), em vez de mostrar uma sidebar isolada num grande painel vazio.

## Pipeline obrigatório para pedidos de UI

1. **Localizar**: verificar `ianmaciel7/exams-app@dev` pelo GitHub conectado, listar pasta do protótipo e capturas. Ler `sidebar-prototipo/decisoes.md`, `sidebar-comparacao-2026-11-23.md`, `app-shell/decisoes.md` e, quando necessário, `notes-app@old-5/src/app/globals.css`. Fonte histórica privada `exams-app-archive` fica para casos não acessíveis diretamente.
2. **Recuperar (não resumir)**: obter HTML/CSS/JS **completos** (o `prototipo-sidebar.html` tem aproximadamente 62 KB); se `fetch_file` parcial, continuar todas as faixas de linhas, ou baixar o raw somente se autorizado/acessível. Verificar `<style>`, `<script>`, `<svg>` e assets. **Não interromper leitura após 200 linhas e não recriar do zero em 200 linhas**. Se ferramenta bloquear parte, sinalizar explicitamente.
3. **Evidência visual**: listar os PNGs de `capturas/` e comparar visual claro/escuro, desktop/celular e menus. Para imagens originais privadas, usar somente acesso autenticado; não substituí-las por imagens geradas ou resultados da web. Se não conseguir visualizar os bytes, registrar "inventário encontrado, imagem não inspecionada".
4. **Priorizar os tokens e componentes existentes**: o HTML de sidebar usa seus próprios tokens; o app-shell de referência foi deliberadamente reconstruído em cima de `notes-app@old-5` OKLCH e componentes de moldura. Não trocar por paleta inventada, gradientes, grandes ícones Unicode/emoji, tipografia aleatória ou cards desnecessários. Evitar cores de chip por tipo quando o alvo for app-shell monocromático: **há decisões diferentes nos dois protótipos**; registrar e escolher conscientemente.
5. **Implementar / exibir**: para prévias dentro do próprio ChatGPT, seguir integralmente `references/chat-preview-contract.md` antes de qualquer código. Escolher o meio apropriado: (a) original standalone e PNGs, (b) preview renderizado com fontes reais, ou (c) adaptação claramente identificada. Se mostrar dentro do chat (AppBlock ou equivalente disponível), preservar código original tanto quanto tecnicamente possível; se o ambiente não suporta injetar/rodar os arquivos, não alegar fidelidade. Não gravar alterações em `dev` sem pedido explícito.
6. **Verificar**: aplicar `references/visual-qa.md` (estados, largura e responsividade, menus, foco, teclado, acessibilidade, scroll, dark). Idealmente renderizar e comparar lado a lado as capturas já existentes. Relatar testes **executados agora** separadamente dos testes **descritos pela documentação histórica**. Não afirmar Playwright executado se só leu documentação.
7. **Entregar**: preview ou arquivo/artefato com fonte e SHA consultados; dizer o que é original, adaptado e não verificado. Não usar GitHub Pages para conteúdos privados.

## Regras de experiência

- Relevância primeiro: "sidebar" significa **lateral visual**; não interpretar como pedido genérico de pesquisa de commits.
- Densidade profissional ao estilo Capacities/Linear/Claude/ChatGPT depende de alinhamento, espaços, ícones, hierarquia, estados e feedback, não de copiar marca. Benchmarks externos **não são templates autorizados**; não prometer paridade visual com UI autenticada não vista.
- Preservar comportamento: switcher de space, Novo e busca, árvore de Concursos, triagem Leituras, Tipos de objeto, Fixados, seções customizadas, menus ⋯ e clique direito, renomear inline, teclado, drag and drop, lixeira/restauração, rodapé, resize, collapsed/peek e gaveta mobile. **Não afirmar que a reconstrução tem essas interações sem testar cada uma**.
- Garantir que saída visual seja utilizável no layout em que é exibida. O shell completo não cabe em uma sidebar de 220px; não escalar texto ou remover controles para "caber" sem explicar.
- Se usuário disser "apague o que criou", auditar **o que foi efetivamente gravado nesta sessão**. Não remover a branch `dev` preexistente, repositórios antigos, backups ou capturas só porque foram consultados.

Fontes: `references/source-map.md`, `references/visual-source-catalog.md`, `references/chat-preview-contract.md` e checklist `references/visual-qa.md`. Para buscas históricas sem caminho conhecido, encaminhar à skill `archive-research`.

## Motion-aware recovery

For animations, transitions, peek, drag, hover, focus, opening/closing menus or reduced-motion, **also read `skills/ui-motion/SKILL.md`** and the private catalog `ianmaciel7/exams-app-archive@main:docs/UI-MOTION-EVIDENCE.json`. Static images do not prove transition timing; recover code and validate.
