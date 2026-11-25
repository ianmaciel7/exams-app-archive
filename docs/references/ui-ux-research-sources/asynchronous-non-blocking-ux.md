# Asynchronous & Non-blocking UX

Research date: 2026-11-25. General UI/UX; product-independent. This is a descriptive taxonomy, not a formal standardized list. Evidence: independent UX research, practitioner guidance, platform examples, accessibility and technical architecture. Links only; no third-party media copied.

## Core distinction
Non-blocking UX is the perceived availability of unrelated interactions. Async execution is a technical mechanism, not a guarantee of a usable interface. Background execution does not necessarily survive closing a browser, logout or offline mode; state persistence and job ownership must be explicitly supported. Modeless presentation describes interaction freedom, not backend durability. Streaming is incremental delivery and may or may not run independently.

## Pattern family

### Non-blocking Interaction (`non-blocking-interaction`)
- Definition: Manter ações independentes disponíveis enquanto outra operação executa.
- Limits and selection: Não permitir ações conflitantes sobre o mesmo recurso; explicar bloqueio local.
- Sources: [nng-waits](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/), [logrocket-async](https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines)

### Background Task Execution (`background-execution`)
- Definition: Separar a execução da tela que iniciou a tarefa.
- Limits and selection: Só prometer persistência fora da tela, aba ou sessão quando o backend a garantir.
- Sources: [nng-waits](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/), [azure-bg-jobs](https://learn.microsoft.com/en-us/azure/architecture/best-practices/background-jobs)

### Concurrent Task Management (`concurrent-task-management`)
- Definition: Gerenciar tarefas em paralelo ou fila, com identidade e escopo próprios.
- Limits and selection: Exibir limites reais, dependências e motivo da espera; não confundir fila com execução.
- Sources: [logrocket-async](https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines), [azure-bg-jobs](https://learn.microsoft.com/en-us/azure/architecture/best-practices/background-jobs)

### Task Tray / Task Center (`task-tray`)
- Definition: Área global acessível com tarefas ativas, pendentes, finalizadas e falhas.
- Limits and selection: Permitir voltar à origem e detalhes; não depender apenas de toast efêmero.
- Sources: [stepikin-background](https://stepikin.com/llm-ux-patterns/background-tasks/), [vscode-notifications](https://code.visualstudio.com/api/ux-guidelines/notifications), [nng-waits](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/)

### Persistent Task State (`persistent-task-state`)
- Definition: Restaurar status, resultados e contexto ao retornar ou reconectar.
- Limits and selection: Distinguir status desconhecido de falha; reconciliar com estado autoritativo.
- Sources: [azure-bg-jobs](https://learn.microsoft.com/en-us/azure/architecture/best-practices/background-jobs), [logrocket-async](https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines)

### Modeless Progress (`modeless-progress`)
- Definition: Feedback de progresso que não impede outras ações.
- Limits and selection: Preferir inline para operação local; barra de status ou painel global para tarefas persistentes.
- Sources: [ms-progress](https://learn.microsoft.com/en-us/windows/win32/uxguide/progress-bars), [vscode-status](https://code.visualstudio.com/api/ux-guidelines/status-bar)

### Determinate Progress (`determinate-progress`)
- Definition: Mostrar unidades concluídas, total ou percentual quando mensurável.
- Limits and selection: Não inventar percentuais ou ETA; 100% somente quando confirmado.
- Sources: [nng-progress](https://www.nngroup.com/articles/progress-indicators/), [ms-vs-progress](https://learn.microsoft.com/en-us/visualstudio/extensibility/ux-guidelines/notifications-and-progress-for-visual-studio?view=visualstudio)

### Indeterminate Progress (`indeterminate-progress`)
- Definition: Indicar atividade real quando o total não é conhecido.
- Limits and selection: Spinner não prova avanço; fornecer etapa conhecida, última atualização e recuperação.
- Sources: [ms-progress](https://learn.microsoft.com/en-us/windows/win32/uxguide/progress-bars), [logrocket-async](https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines)

### Task Completion Notification (`completion-notification`)
- Definition: Avisar conclusão sem interromper tarefas independentes.
- Limits and selection: Incluir tarefa, resultado e link; respeitar preferências e evitar notificações repetidas.
- Sources: [ms-vs-progress](https://learn.microsoft.com/en-us/visualstudio/extensibility/ux-guidelines/notifications-and-progress-for-visual-studio?view=visualstudio), [vscode-notifications](https://code.visualstudio.com/api/ux-guidelines/notifications)

### Task Reentrance (`task-reentrance`)
- Definition: Retomar atividade de origem preservando contexto, histórico e anotações.
- Limits and selection: Não roubar foco ou substituir tela atual; oferecer retorno explícito.
- Sources: [nng-waits](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/)

### Cancellation, Retry & Recovery (`cancel-retry-recovery`)
- Definition: Permitir interromper, repetir ou recuperar uma tarefa conforme capacidade real.
- Limits and selection: Cancelamento solicitado não equivale a cancelado; explicar efeitos parciais e evitar duplicação.
- Sources: [logrocket-async](https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines), [azure-bg-jobs](https://learn.microsoft.com/en-us/azure/architecture/best-practices/background-jobs)

### Partial Results & Partial Failure (`partial-results`)
- Definition: Mostrar saídas já disponíveis e itens com falha separadamente.
- Limits and selection: Sinalizar incompletude e repetir apenas itens seguros; preservar sucessos.
- Sources: [logrocket-async](https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines)

### Human-in-the-loop / Awaiting Input (`async-approval`)
- Definition: A tarefa aguarda decisão humana sem travar toda a aplicação.
- Limits and selection: Mostrar decisão, consequência, prazo real e retomada; não simular autorização.
- Sources: [logrocket-async](https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines), [nng-waits](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/)

## Lifecycle and presentation
Proposed state model (not a universal standard): submitted → queued → running → succeeded / partially succeeded / failed / canceled. Running can transition to waiting for input, paused (if supported), retrying, or cancellation requested. A lost connection is a client observation, not a definitive job failure. Reconnect and obtain authoritative status. Terminal outcomes include timestamp, result link, errors and next action. Do not promise pause/resume, background survival, or exact ETA without actual support.

Use local inline progress for a scoped operation, global tray/status bar for background work, a detail view for history/logs, and a nonintrusive completion notification for results. Use blocking UI only where action on the same resource would be unsafe or a necessary decision genuinely prevents continuation. Avoid app-wide overlays, perpetual spinners, fake progress, duplicate submissions, ambiguous cancel behavior, hidden errors, notification spam, and destructive automatic retries.

## Suggested task record (architecture-neutral)
Stable task ID, human-readable label, owner and originating resource, lifecycle state, submitted/started/updated/finished timestamps, measured units and total when available, current stage, result links, recoverable error, permitted actions, cancellation scope and retry lineage. Keep state separate from view lifecycle. Prefer safe retries, checkpoints and deduplication where relevant. Backend implementation choices are not UX patterns.

## Accessibility and acceptance tests
Expose progress through accessible names/values; use status/live regions for significant changes without moving focus; avoid repeated announcements of every tick; honor reduced motion; avoid color-only status. Keyboard access to tray, task details and actions. Test navigation to another workspace, parallel jobs, refresh, reconnect, tab close only if supported, unknown duration, queued state, partial success, failure, cancel races, stale state, duplicate submission, notification preferences, and return to originating context. Verify an unrelated action stays usable throughout. Test with real users and assistive technology; these are design acceptance proposals, not completed product tests.

## Evidence and scope
NN/g and LogRocket articles opened; remaining sources were inspected via public search index; Stepikin direct fetch failed. Microsoft legacy Windows guidance is historical, not a current universal rule. UI examples like editors and AI research are illustrative, not proof of any product's persistence guarantee. No product-specific implementation or statistical adoption claim.

## Source register
- [NN/g — Designing for Long Waits and Interruptions](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/) — independent-ux-research; Opened article; 2021-09-05. Background execution, task resumption, history, notes and contextual completion.
- [LogRocket — UI patterns for async workflows](https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines) — practitioner-article; Opened article; 2026-02-13. Lifecycle, queue, progress, partial outcomes, refresh and disconnect tests.
- [NN/g — Progress Indicators](https://www.nngroup.com/articles/progress-indicators/) — independent-ux-research; Search-index evidence. Progress feedback and perceived waiting.
- [Stepikin — Background AI Tasks](https://stepikin.com/llm-ux-patterns/background-tasks/) — independent-pattern-library; Search-index only; direct fetch failed. Handoff, task tray and completion notification; revalidate.
- [Microsoft — Progress Bars](https://learn.microsoft.com/en-us/windows/win32/uxguide/progress-bars) — historical-platform-guidance; Search-index; Windows 7 era guidance. Modeless, determinate and indeterminate progress; not current universal rules.
- [Microsoft — Notifications and Progress for Visual Studio](https://learn.microsoft.com/en-us/visualstudio/extensibility/ux-guidelines/notifications-and-progress-for-visual-studio?view=visualstudio) — primary-platform; Search-index evidence. Ambient completion, scope and honest progress.
- [VS Code — Notifications](https://code.visualstudio.com/api/ux-guidelines/notifications) — primary-platform; Search-index evidence. Progress notifications and notification placement.
- [VS Code — Status Bar](https://code.visualstudio.com/api/ux-guidelines/status-bar) — primary-platform; Search-index evidence. Discreet background activity; escalate when attention needed.
- [W3C — Understanding Status Messages](https://www.w3.org/WAI/WCAG21/Understanding/status-messages) — accessibility-standard-guidance; Search-index evidence. Expose meaningful status changes without stealing focus.
- [W3C — ARIA25 Progress Status](https://www.w3.org/WAI/WCAG22/Techniques/aria/ARIA25) — accessibility-technique; Search-index evidence. Announce meaningful progress via live region.
- [Azure Architecture — Background Jobs](https://learn.microsoft.com/en-us/azure/architecture/best-practices/background-jobs) — technical-architecture; Search-index evidence. Persistent checkpoints, retries, idempotency; technical enabling mechanism.
- [W3C — WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria/) — accessibility-standard; Search-index evidence. Progressbar, busy and live status semantics.
