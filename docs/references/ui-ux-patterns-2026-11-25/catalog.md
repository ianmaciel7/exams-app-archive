# Pattern catalog

All examples in the last column are proposals for Exams App. Full fields in [patterns.json](patterns.json). Source IDs link to [references](references.md).

| Pattern | Purpose | Anatomy | Behavior | Accessibility | Evidence | Exams App |
|---|---|---|---|---|---|---|
| List / lista | Scan text-heavy objects | Icon, title, metadata | sort, filter, selection, empty | Semantic list; visible focus | official: C1 | Questões, concursos |
| Table / tabela | Compare properties | Headers, rows, property cells | sort, filter, selection, edit | Header associations; keyboard | official: C1 | Questões com metadados |
| Gallery / galeria | Compare visual objects | Uniform image cards, title | resize, select, filter | Alt text; reflow | official: C1 | Capas de provas |
| Wall / mural | Browse variable-size visual objects | Variable-height tiles | select, filter | Logical reading order | official: C1 | Referências visuais |
| Kanban | Group objects by workflow | Columns, cards, group heading | move, reorder, filter | Non-drag move controls | official: C1 | Status de estudo |
| Saved query | Dynamic filtered object set | Filters, sort, saved view | create, update, empty | Label filters and announce results | official: C5 | Questões erradas |
| Collection | Curate one object type | Collection name, members, view | add, remove | Accessible selection | official: C6 | Lista de revisão manual |
| Object-type dashboard | Explore an object type | Sections, view controls, objects | switch, filter, save | Keyboard-accessible tabs | official: C4, C10 | Dashboard de concursos |
| Preview | Inspect without losing context | Object content, close, navigation | open, next, previous, close | Escape; restore focus | official: C2 | Prévia de questão |
| Main tabs | Maintain workspaces | Tab list, active tab, close | open, switch, reorder, close | Tab semantics and focus | official: C2, C7 | Documentos e simulados |
| Right side panel | Work with two objects | Secondary tabs, content | shift-click, open, close | Keyboard access; maintain focus | official: C2, C3, C7 | Questão e material |
| Inspector | Inspect context and navigation | Inspector tabs, outline | toggle, empty | Label regions | official: C3 | Propriedades e relações |
| Bulk actions | Operate on selected objects | Selection, actions | select, apply | Announce count | official: C11 | Mover questões |
| Inline card | Show small structured result | Title, media, details, action | loading, ready, error | Label controls; no nested scroll | official: O1 | Resumo de desempenho |
| Inline carousel | Browse short visual alternatives | Image, title, metadata, CTA | scroll, select | Keyboard; accessible alternatives | official: O1 | Escolher provas |
| Fullscreen | Deep exploration | Expanded app surface, close, composer | expand, stream, collapse | Manage focus; maintain context | official: O1 | Simulado ou leitor |
| Picture-in-picture | Keep small active view alongside chat | Floating surface, controls | open, close | Accessible controls | official: O1 | Timer opcional |
| Interactive chart | Explore quantitative data | Axes, legend, values, controls | filter, inspect, loading | Text summary and data alternative | official: O2, A2 | Evolução de acertos |
| Diagram / flowchart | Explain relationships | Nodes, links, labels | inspect, zoom if applicable | Text equivalent | official: A1, A2 | Mapa de tópicos |
| Artifact | Create persistent deliverable | Dedicated workspace, content, revision actions | create, edit, revisit | Keyboard access; clear save state | official: A1 | Material de estudo |
| Design canvas | Create and edit visual prototypes | Canvas, elements, editing controls | select, edit, preview | Accessible alternatives | official: A3 | Prototipação |
| Whiteboard | Organize ideas spatially | Nodes, groups, connectors | edit, arrange | Equivalent ordered content | official: A4 | Planejamento |
| Interactive form | Gather structured answers | Labels, inputs, submit | idle, invalid, pending, success | Errors associated with inputs | official: O2 | Configurar simulado |
| Map | Explore geography | Pins, controls, optional details | pan, zoom, select | List alternative | official: O1 | Locais de prova |
| Message actions | Operate on messages | Copy, feedback, optional actions | hover, focus, touch | Never hover-only | third-party-example: T1, T2 | Copiar explicação |
| Composer | Input or cancel task | Text field, attachments, primary action | idle, typing, recording, running | Accessible names; live status | third-party-example: T1, T2 | Assistente de estudo |
| Grid | Compare uniform items | Responsive cells, headings | select, resize | Reflow; logical order | proposal: W1 | Catálogo |
| Code block | Read and copy source | Language, code, copy action | focus, copy, error | Selectable text; no trap | proposal: W1 | Questões de programação |
| Dashboard | Combine metrics and charts | Metric cards, chart, context | filter, refresh, empty | Data equivalents | official: A1 | Relatório de estudo |
| Document | Read or edit long-form work | Title, sections, editing surface | edit, save, export | Semantic headings | official: A1 | Resumo de edital |
| Streaming shimmer | Indicate streaming in composer | Animated status cue | thinking, completed | Static alternative; status text | official: O1 | Geração de explicação |
| Layout animation | Maintain spatial continuity | Layout transition, shared identity | enter, exit, reorder | Reduced motion | official: M1, M2 | Abrir painel |
| Reorder animation | Rearrange lists | Draggable items, handles | drag, drop, cancel | Alternative move commands | official: M3, M2 | Ordenar abas |
| Loading / error / empty | Communicate system status | Message, skeleton, retry | loading, error, empty, success | Live status, no color-only cues | proposal: W1 | Busca de questões |
| Modal / drawer | Focused secondary flow | Title, content, close | open, dismiss, confirm | Focus trap only when modal | proposal: W1 | Filtros mobile |
