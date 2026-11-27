# Pesquisa independente de UI/UX: fontes e ferramentas contextuais

Data: 2026-11-25. Conhecimento geral, sem vinculação automática a projeto. Sites de inspiração são evidência de existência, não de eficácia ou popularidade. Preferir fontes de padrões, pesquisa, livros e galerias independentes; design systems são validação complementar. Não confundir descrição estética, padrão, técnica de implementação e norma.

## Roteiro de pesquisa

1. Nome e sinônimos: UI Patterns, UX Patterns for Developers, UXologist e Component Gallery. Buscar por problema, não apenas por nome visual. Comparar taxonomias e identificar sinônimos; não chamar toda denominação de termo oficial.
2. Produtos reais: Mobbin, Refero, Nicelydone e Pttrns. Registrar produto, plataforma, versão/data quando disponível, tela, contexto e ação; não deduzir hover de screenshot estático.
3. Fluxos e motion: Page Flows, ScreensDesign, 60fps e Design Spells. Observar antes/durante/depois, entrada/saída, interrupção e relação espacial; medir duração apenas se houver vídeo ou instrumentação; não inventar easing.
4. Evidência de usabilidade: NN/g, Baymard, IxDF, livros e estudos originais. Diferenciar estudo, orientação profissional, exemplo e hipótese; respeitar domínio e método.
5. Implementação: UX Patterns, Smashing, APG/WCAG, documentação da plataforma; verificar suporte, teclado, touch, reduced motion, estado e licenças. Não copiar mídias de galerias sem autorização.

## Ferramentas contextuais: taxonomia e decisões

Scott e Neil (Designing Web Interfaces, 2009, capítulo Contextual Tools; sumário consultado, não capítulo integral) distinguem Always-Visible Tools, Hover-Reveal Tools, Toggle-Reveal Tools, Multi-Level Tools e Secondary Menu; contextual toolbar e radial menu aparecem no detalhamento. A classificação é histórica. Hover-to-reveal, focus-to-reveal e swipe-to-reveal descrevem mecanismos de ativação, não famílias incompatíveis. Low-chrome é uma estratégia visual; progressive disclosure é mais ampla que hover.

| Padrão | Quando considerar | Limite / alternativa |
|---|---|---|
| Always-visible tools | Ação primária, frequente, essencial ou que precisa ser descoberta | Agrupar secundárias em overflow; não ocultar navegação principal por estética |
| Hover-reveal tools | Muitas linhas repetidas com ações secundárias | Foco equivalente, toque por menu persistente, não depender só do mouse |
| Focus-reveal tools | Navegação por teclado e foco dentro do objeto | Não esconder botão ao mover foco para descendente; foco visível |
| Toggle-reveal tools | Usuário quer abrir explicitamente controles | Indicar estado expandido; permitir fechar/retornar foco |
| Selection-based toolbar | Seleção única ou múltipla | Mostrar contagem, alcance e limpar seleção; confirmar ações irreversíveis |
| Contextual menu | Agrupar operações de um objeto | Gatilho próximo, rótulo acessível; alternativa a clique direito |
| Multi-level tools | Muitos comandos relacionados | Hierarquia rasa, sem submenu exclusivamente por hover |
| Radial menu | Comandos espaciais especializados | Não é padrão universal; oferecer alternativa linear e de teclado |
| Swipe-to-reveal | Ações secundárias em listas touch | Alternativa explícita visível; gesto não é único meio |
| Ghost controls | Controles discretos mas perceptíveis | Contraste, foco e affordance; não confundir botão ghost com invisibilidade |

## Comportamento e acessibilidade

- Estados: repouso, pointer hover, focus-visible/focus-within, menu aberto, selecionado, touch/no-hover, desabilitado, pending, erro. Reservar área quando necessário para evitar salto de layout; overlay não deve encobrir informação essencial.
- Revelar ações do objeto sob hover e foco; manter enquanto cursor/foco passa para as ações. Ações essenciais visíveis. Para touchscreen e dispositivos híbridos, botão de overflow acessível sempre disponível; usar media queries de capacidade de entrada como melhoria, não detecção infalível do dispositivo.
- Não usar opacity:0 isoladamente para elementos interativos: podem continuar capturando clique e foco invisível. Testar ordem de tabulação, foco, leitor de tela, pointer events e semântica. Menu real requer comportamento de menu; grupo simples pode usar botões nativos.
- WCAG 1.4.13 trata de conteúdo adicional mostrado por hover/foco, quando aplicável; não é regra universal para todos os controles ocultos. Para popovers/tooltip relevantes, assegurar possibilidade de dispensar, mover cursor até conteúdo e manter aberto conforme aplicável. Validar teclado e alvos conforme critérios WCAG pertinentes.
- Timing: feedback de alvo imediato; revelar conteúdo após intenção quando disparos acidentais forem problema; evitar desaparecer ao cruzar espaço até a superfície. NN/g discute timing de conteúdo oculto; não transferir um número universal para qualquer hover. Testar delay, interrupção, touch, teclado, reduced motion.
- Antipadrões históricos: Hover and Cover, Mystery Meat Activation, Tiny Targets. Outros riscos de implementação: hover-only, layout shift, foco perdido, overflow ambíguo, seleção que desaparece, menus encobertos/clipped, ações destrutivas sem confirmação adequada.
- Medir encontrabilidade, tempo, erro de acionamento, sucesso com teclado/touch e recuperação. Estudo NN/g sobre navegação principal oculta não é evidência direta para toda ação secundária de linha.

## Como preservar evidência

Registrar URLs originais e redirects, datas de consulta, fonte e status (verificada, parcial, bloqueada, candidata, histórica), licença, tipo de evidência e contexto. Não apagar URL desatualizada: preservar com status. Para vídeo/GIF/screenshot incluir fonte, hash, data, direitos de reprodução e descrição do comportamento. Links são preservados mesmo quando não é possível copiar mídia. Nunca guardar URLs privadas, credenciais ou contornar paywalls. Ao reutilizar, revalidar fonte. Não fazer alegações de cobertura completa, ranking 2026 ou testes de produto sem evidência.

## Diretório das fontes

- [UI Patterns](https://ui-patterns.com/patterns) — pattern-library; verified. Named problem/solution patterns; start here for vocabulary.
- [UX Patterns for Developers](https://uxpatterns.dev/) — pattern-library; verified. Specimens, comparison guides, glossary and implementation trade-offs.
- [The UXologist](https://theuxologist.com/patterns) — pattern-library; verified. Problem-led pattern discovery.
- [The Component Gallery](https://component.gallery/components/) — cross-system-catalog; verified. Compare component names, aliases and variants; not a single design system.
- [Critical Web Design Pattern Library](https://criticalwebdesign.github.io/pattern-library/about/) — pattern-library; verified. Tagged interface patterns from websites, apps and games; curated evidence.
- [Interaction Design Foundation](https://www.interaction-design.org/) — education; redirect to https://ixdf.org/. Concepts and education; follow original studies for empirical claims.
- [Mobbin](https://mobbin.com/) — product-gallery; verified. Shipped app and web screens; search by component, flow and product; access may be gated.
- [Refero](https://refero.design/) — product-gallery; page title retrieved; body unavailable. Web/iOS references by pattern, element and flow; revalidate direct content.
- [Page Flows](https://pageflows.com/) — flow-gallery; 403 on direct fetch; secondary confirmation. Recorded journeys; keep URL and verify access separately.
- [UI Sources](https://www.uisources.com/) — flow-gallery; legacy; reported merged into ScreensDesign. Keep historical URL; do not count as independent current service.
- [ScreensDesign](https://screensdesign.com/) — flow-motion-gallery; verified. App recordings, tagged screens, animation explorer; access varies.
- [Pttrns](https://pttrns.com/) — mobile-gallery; verified; redirects to www.pttrns.com. Curated mobile screenshots and patterns.
- [Nicelydone](https://nicelydone.club/) — web-app-gallery; verified. Production web-app screens, components and flows.
- [60fps](https://60fps.design/) — motion-gallery; verified. Real interaction recordings; useful for continuity and timing observation.
- [Design Spells](https://designspells.com/) — microinteraction-gallery; verified. Small delightful product interactions; examples are not universal recommendations.
- [DesignMotionHQ](https://designmotionhq.com/patterns) — motion-pattern-library; verified. Motion and interface breakdowns with text; editorial advice.
- [Nielsen Norman Group](https://www.nngroup.com/articles/) — usability-research; individual articles verified. Research and applied guidance; inspect methods and scope.
- [Baymard Institute](https://baymard.com/research) — usability-research; verified. Research and annotated examples, especially ecommerce; domain limits.
- [Smashing Magazine UX](https://www.smashingmagazine.com/category/ux/) — technical-editorial; verified. Technical and UX articles; evaluate author evidence.
- [UX Collective](https://uxdesign.cc/) — editorial; verified. Practitioner case studies and commentary, not automatically research evidence.
- [Laws of UX](https://lawsofux.com/) — education; verified. Psychology and design concepts; distinguish laws from heuristics.
- [Designing Web Interfaces — Contextual Tools](https://www.oreilly.com/library/view/designing-web-interfaces/9780596155353/ch04.html) — book; table of contents verified; full chapter not read. Scott and Neil taxonomy and antipattern names; historical, not a new 2026 invention.
- [Mobile Design Pattern Gallery — Tools](https://www.oreilly.com/library/view/mobile-design-pattern/9781449336455/ch05.html) — book; chapter listing verified. Touch-oriented contextual tools, inline and bulk actions.
- [Principles and Patterns for Rich Interaction](https://principles.design/examples/principles-and-patterns-for-rich-interaction) — secondary-catalog; verified. Historical framework summary: manipulation, context, lightweight interactions.
- [NN/g Contextual Menus](https://www.nngroup.com/articles/contextual-menus/) — usability-guidance; verified. Relevant local tools and alternative activation routes.
- [NN/g Contextual Menu Guidelines](https://www.nngroup.com/articles/contextual-menus-guidelines/) — usability-guidance; verified. Placement, grouping, recognizability, labels and discoverability.
- [NN/g Timing Guidelines for Exposing Hidden Content](https://www.nngroup.com/articles/timing-exposing-content/) — usability-guidance; verified. Separate immediate target feedback, intentional reveal and dismissal.
- [NN/g Hidden Navigation](https://www.nngroup.com/articles/hamburger-menus/) — usability-study; verified. Hidden primary navigation can harm discoverability; not a direct test of row actions.
- [Smashing — Accessible Components](https://www.smashingmagazine.com/2021/06/css-javascript-requirements-accessible-components/) — technical-editorial; verified. CSS visibility alone does not implement full accessible interactions.
- [Designing Web Interfaces historical gallery](https://www.flickr.com/photos/designingwebinterfaces/collections/72157606817815788/) — historical-gallery; carried forward; not revalidated in this batch. Historical visual examples; verify individual media rights.
- [Creative Bloq — Web Design Patterns](https://www.creativebloq.com/ux/web-design-patterns-81412535) — editorial; carried forward; not revalidated in this batch. Historical contextual-tool examples.
- [Carbon data table](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) — supporting-design-system; carried forward; not revalidated in this batch. Reference implementation, not the main research catalog.
- [ServiceNow Invisible Controls](https://horizon.servicenow.com/guidelines/accessibility/invisible-controls) — supporting-design-system; carried forward; not revalidated in this batch. Invisible controls guidance.
- [GitLab Affordance](https://design.gitlab.com/patterns/affordance/) — supporting-design-system; carried forward; not revalidated in this batch. Affordance and discoverability reference.
- [WCAG 2.2 Content on Hover or Focus](https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus) — normative-support; carried forward; not revalidated in this batch. SC 1.4.13 understanding; dismissible, hoverable, persistent as applicable to additional content.
- [Chrome Natural Interactions](https://developer.chrome.com/docs/modern-web-guidance/guides/user-experience/natural-interactions) — technical-guidance; carried forward; already cataloged. Hover/focus and touch fallback; retain source once.
- [Mobbin alternatives 2026](https://mobbin.com/blog/best-mobbin-alternatives) — commercial-secondary; verified. Competitor overview and reported historical mergers; not independent ranking.
- [Cupertino reference directory](https://cupertino.design/) — secondary-directory; verified. Discovery of platform and motion sources; follow original links.

## Behavioral quality research — 2026-11-25

- [Catalog and criteria](./behavioral-ux-quality-2026.md)
- [Structured index](./behavioral-ux-quality-2026.json)
- [Canonical source register](../interface-pattern-library/sources.json)

## Component interaction and behavior patterns

- [Catalog and capability matrix](./component-interaction-behavior-patterns.md)
- [Structured records](./component-interaction-behavior-patterns.json)

## Microinteraction states and polish

- [Catalog and interaction contract](./microinteraction-state-and-polish.md)
- [Structured records](./microinteraction-state-and-polish.json)

## Agent-ready design system completeness

- [Catalog and source reviews](./agent-ready-design-system-completeness.md)
- [Structured index](./agent-ready-design-system-completeness.json)

## Getdesign.md public corpus (2026-11-25)

- [Corpus review and 84-document inventory](./getdesign-public-corpus-2026-11-25.md)
- [Structured corpus](./getdesign-public-corpus-2026-11-25.json)
- [Canonical source register](../interface-pattern-library/sources.json)

## AI-native product design and Beyond Chat

- [Synthesis and acceptance criteria](./ai-native-product-design.md)
- [Structured cross-index](./ai-native-product-design.json)
- 10 families, 163 cross-indexed labels, 14 source links; 10 added to the canonical register (387 retained). Partial public documentation, not exhaustive audit.

## Component registry discovery

- [Shoogle](https://shoogle.dev/) — search shadcn/ui registries for components, blocks, templates, AI elements, charts and themes; directory and MCP available. Verify upstream license, dependencies, accessibility and compatibility. Reviewed 2026-11-25; discovery, not a design standard.


## Iterative UI/UX design activities — 2026-11-25

- [Guia de dez atividades, checklists e catálogo visual](./ux-design-activities-2026-11-25.md)
- [Registro estruturado](./ux-design-activities-2026-11-25.json)
- [Comparação visual original](./ux-design-activities-2026-11-25.svg)
- 10 atividades de método/entregável; 36 fontes revisadas, 35 URLs novas no registro canônico e 1 reutilizadas. Exemplos hipotéticos, mídias externas link-only. Não altera padrões de interface nem produto.

## Design foundations, states and transitions (2026-11-25)

- [Decision guide](./design-foundations-and-state-transitions-2026-11-25.md) and [structured cross-index](./design-foundations-and-state-transitions-2026-11-25.json): 11 decision frameworks covering color, motion, focus, layout, interaction/async states and logical/visual transitions; not 11 novel patterns. Candidate sources and untested claims labeled. Further research #103–#105.

## Visual evidence discovery (2026-11-25)

- [Source directory and evidence protocol](./visual-evidence-discovery-2026-11-25.md) / [structured records](./visual-evidence-discovery-2026-11-25.json). 25 links, 19 new URLs in the canonical register, others reused. Access limits and rights require revalidation.

- Product-specific addition: 10 direct Claude/ChatGPT Projects references in the visual evidence directory; 10 new canonical URLs, with the official English OpenAI article retained alongside the localized variant.

## ChatGPT Space — views and composable pages (2026-11-26)

- [Research and visual examples](chatgpt-space-views-and-composable-pages-2026-11-26.md)
- [Machine-readable catalog](chatgpt-space-views-and-composable-pages-2026-11-26.json)
- 14 view/filter/navigation concepts, 11 patterns, 6 inspected official image links, 21 documentation/video references (9 documentation URLs rechecked; remaining leads marked for revalidation). No third-party image bytes redistributed.

## Claude, Grok Bot, Gemini and Gemini Notebook (2026-11-26)

- [Benchmark](ai-product-views-and-artifacts-2026-11-26.md) · [JSON catalog](ai-product-views-and-artifacts-2026-11-26.json)
- 42 official documentation references, 23 product patterns, 12 publisher-page visual leads, 4 direct image URLs (not pixel-verified). New sources: 42. Companion to ChatGPT Space.

## AI product gap research and cross-index (2026-11-26)

- [Gap delta](ai-product-gap-delta-2026-11-26.md) · [JSON](ai-product-gap-delta-2026-11-26.json)
- [Graph and backlog](../interface-pattern-library/ai-product-knowledge-graph.md)

## Documented product flows

- [Interaction sequences and persistence boundaries](ai-product-documented-flows-2026-11-26.md) · [JSON](ai-product-documented-flows-2026-11-26.json)

## Product availability and state boundaries

- [Comparison and evidence](ai-product-availability-and-state-boundaries-2026-11-26.md) · [Structured matrix](ai-product-availability-and-state-boundaries-2026-11-26.json)

## Editor contracts and state sequences

[Research](ai-product-editor-contracts-2026-11-26.md) · [JSON](ai-product-editor-contracts-2026-11-26.json)

## Visual and learning evidence

[Research](ai-product-visual-and-learning-evidence-2026-11-26.md) · [JSON](ai-product-visual-and-learning-evidence-2026-11-26.json)

## Creation inventory

[Research](ai-product-creation-inventory-2026-11-26.md) · [JSON](ai-product-creation-inventory-2026-11-26.json)

## Data visualization and evidence coverage

[Matrix and coverage report](ai-product-dataviz-and-evidence-coverage-2026-11-26.md) · [JSON](ai-product-dataviz-and-evidence-coverage-2026-11-26.json)

## Visual verification follow-up

[Report](ai-product-visual-verification-2026-11-26.md) · [JSON](ai-product-visual-verification-2026-11-26.json)

## Generative UI research examples

[Google Research reference](google-research-generative-ui-evidence-2026-11-26.md) · [JSON](google-research-generative-ui-evidence-2026-11-26.json)

## Product-specific research: ClickUp

- [Initial coverage audit](clickup-coverage-audit-2026-11-27.md)
- [Expanded ClickUp interaction inventory](clickup/README.md) — official-source summaries, visual links, and explicit runtime gaps.
- [Machine-readable ClickUp inventory](clickup/inventory.json)

## Laws of UX — 30 concepts (2026-11-27)

[Applied catalog](laws-of-ux-2026-11-27.md) · [Structured inventory](laws-of-ux-2026-11-27.json). All 30 concept pages reviewed; external full-text research and plugin publication are separate verification steps.

## Brand identity and color systems

- [Decision guide](brand-identity-color-systems-2026-11-27.md) and [structured records](brand-identity-color-systems-2026-11-27.json): 17 structured records and 34 sources bridging brand strategy, harmony, psychology, science, engineering, accessibility, governance and visual perception, including Stroop interference, opponent processing, constancy, CIECAM16, color discrimination and Feature Congestion. Public abstracts and excerpts reviewed; no full-book/standard audit or product tests.

## Award-backed art direction — 2025–2026

[Research catalog](award-backed-art-direction-2025-2026.md) · [Structured evidence](award-backed-art-direction-2025-2026.json). Nine award directories, six studios, award cases and task-fit evaluation protocol. Distinguish awards from demonstrated usability.
