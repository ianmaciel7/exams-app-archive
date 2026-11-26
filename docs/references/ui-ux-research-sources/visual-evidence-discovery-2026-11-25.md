# Visual evidence discovery — 2026-11-25

Reference intake for research on real product UIs, including paid products with legitimately public demonstrations or gallery entries. This list is not a claim of unrestricted access or media reuse. Free tiers, counts, prices, MCP/API capabilities and terms change; confirm on the original source before acting. No subscription bypass, account sharing, paywall evasion or restricted scraping.

| Source | Category | Use |
|---|---|---|
| [Pixlpin](https://pixlpin.com/) | gallery | Capturas de apps reais e fluxos; priorizar pesquisa gratuita; conferir limites atuais de downloads. |
| [Screenrove](https://screenrove.com/) | gallery | SaaS e interfaces reais; investigar MCP/API e condições de uso antes de integrar. |
| [The UI Index](https://theuiindex.com/) | gallery | Capturas web por elementos, estados e contexto. |
| [Interface Index](https://interface-index.com/) | gallery | Interfaces desktop, SaaS e B2B. |
| [UXSnaps](https://www.uxsnaps.com/) | gallery | Capturas e análises; distinguir observação de interpretação. |
| [Mobbin](https://mobbin.com/) | freemium-gallery | Telas, fluxos e histórico visual; acesso gratuito limitado. |
| [Refero](https://refero.design/) | freemium-gallery | Interfaces web e apps; conferir acesso. |
| [Refcat](https://refcat.app/) | freemium-gallery | Telas e fluxos; conferir acesso. |
| [Nicelydone](https://nicelydone.club/) | freemium-gallery | Interfaces internas SaaS. |
| [SaaSFrame](https://www.saasframe.io/) | freemium-gallery | Produtos SaaS e fluxos. |
| [Framebin](https://framebin.co/) | freemium-gallery | Capturas de aplicações. |
| [YouTube](https://www.youtube.com/) | discovery | Demonstrações oficiais, mudanças de estado e motion; registrar timestamps e direitos. |
| [App Store](https://apps.apple.com/) | discovery | Capturas promocionais oficiais; não confundir com estado real observado. |
| [Google Play](https://play.google.com/store/apps) | discovery | Capturas oficiais e vídeos de lançamento. |
| [Product Hunt](https://www.producthunt.com/) | discovery | Lançamentos e demonstrações. |
| [G2](https://www.g2.com/) | discovery | Capturas e demonstrações de produtos; verificar autoria. |
| [Capterra](https://www.capterra.com/) | discovery | Diretório e evidências de produto; verificar autoria. |
| [Wayback Machine](https://web.archive.org/) | discovery | Versões históricas de páginas públicas; não garante assets, login ou comportamento. |
| [GitHub](https://github.com/) | discovery | Capturas, GIFs, vídeos e código público com provenance e licença. |
| [Playwright](https://playwright.dev/) | tool | Capturar e testar estados e transições em interfaces com acesso autorizado. |
| [ShareX](https://getsharex.com/) | tool | Capturas e gravações no Windows. |
| [FFmpeg](https://ffmpeg.org/) | tool | Extrair frames de vídeo autorizado, mantendo timestamps. |
| [Eagle](https://eagle.cool/) | tool | Organização de referências visuais; não presumir gratuidade. |
| [SQLite FTS5](https://www.sqlite.org/fts5.html) | tool | Indexação local de metadados e descrições. |
| [Docling](https://docling-project.github.io/docling/) | tool | Extração estruturada de documentos; validar qualidade de resultados. |

Official product documentation, help centers, changelogs and release notes are preferred for specific feature claims. Search product + component + state + platform + version. Prioritize Screenrove, Pixlpin and The UI Index for discovery; use other galleries and original product sources to fill gaps. Verify Screenrove MCP/API availability, credentials and access before claiming integration. Galleries are evidence of appearance at capture time, not conformance or efficacy.

## Evidence collection contract

Record product, platform, version/date if known, source page and direct media link if public, author, component, interaction state, event/trigger, context, before/during/after and timestamps for video, rights/license, access status, inspection status, limitations, retrieval date and checksum only when a permitted file is actually recovered. Distinguish screenshot from motion, official documentation from third-party capture, visual observation from inference. Preserve links when rights are unclear; no copying restricted media into the public archive. Do not imply access to paid private screens. Index descriptions and source IDs, deduplicate by canonical URL and evidence identity; cross-link with components, patterns, states and ADRs. Use Playwright only on authorized surfaces; no credentials or private screenshots in public repositories. Treat a Visual Evidence Collector as a proposed capability, not an installed integration. Related #102, #104, #105 and #94.

## Product-specific evidence: Claude Projects, ChatGPT Projects and Claude Code Projects

These direct URLs complement the gallery homepages. They are discovery leads from the preceding research, not proof that every screen is available for free or that the documented UI is the latest version. Distinguish Claude Projects (chat workspace), Claude Code Projects (coding workspace) and ChatGPT Projects. Prefer official documentation for feature claims, screenshots/video for observed interface and transitions. Do not infer animation from stills; confirm version, platform, specific screen, timestamp and rights before collecting media. The Portuguese OpenAI help article is a localized companion to the existing English record.

| Source | Product | Category | Evidence to investigate |
|---|---|---|---|
| [ScreensDesign — Claude by Anthropic](https://screensdesign.com/apps/claude-by-anthropic/) | Claude | gallery | Project listing, creation, knowledge/files, custom instructions, conversation history and empty states. Some captures may require a paid plan. |
| [Wikidocs — Claude Projects](https://wikidocs.net/340428) | Claude | third-party-guide | Web project creation, instructions and knowledge; source language and version may differ. |
| [Framebin — ChatGPT](https://framebin.co/apps/chatgpt) | ChatGPT | gallery | Project empty state and app screenshots; verify individual availability. |
| [Pixlpin — ChatGPT](https://pixlpin.com/apps/chatgpt?type=browse-and-discover) | ChatGPT | gallery | Sidebar, project discovery/listing and creation flows; verify per-screen access. |
| [Pixlpin — Claude Web](https://pixlpin.com/apps/claude-web?type=browse-and-discover) | Claude | gallery | Web workspace, projects, files, artifacts and split-pane examples; verify exact state in captures. |
| [AI Toolbox — Claude Projects guide](https://www.ai-toolbox.co/claude-management-and-productivity/how-to-use-claude-projects-guide-2026) | Claude | third-party-guide | Project setup and management; validate guide publication and access. |
| [Hello LLM — Claude Projects and Tools](https://amecoder.github.io/hello-llm/en/guide/10-claude/07-projects-tools.html) | Claude | third-party-guide | Projects, connectors and skills; distinguish documented from observed behaviors. |
| [OpenAI Help — Projetos no ChatGPT (pt-BR)](https://help.openai.com/pt-br/articles/10169521-projects-in-chatgpt) | ChatGPT | official-documentation | Official project help in Brazilian Portuguese; localized companion to existing English article, not independent corroboration. |
| [Pixlpin — Claude mobile](https://pixlpin.com/apps/claude-drs5?type=browse-and-discover) | Claude | gallery | Mobile screens and flows; verify project-specific coverage. |
| [YouTube — Claude Code Projects](https://www.youtube.com/watch?v=omihvjf0A2k) | Claude Code | video | Project/workspace demonstration candidate; verify publisher, date, timestamps and relevant behavior before claiming official status. |

Research targets: project list/create/open/rename, empty and populated states, files and knowledge, instructions, history, navigation and split panels, loading/error/permission states, and desktop/mobile differences. Keep links only until inspection and rights are confirmed; no media copied.
