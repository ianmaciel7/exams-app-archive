# Anti-AI-slop agent skills — 2026-11-27

Evidence class: external public research (repository descriptions and indexed documentation). This is a comparative discovery snapshot, not historical project evidence, an installation audit, or a benchmark. Stars are rounded observations from public GitHub pages and may change. No external code was executed.

| Scope | Source | Observed role |
|---|---|---|
| UI | https://github.com/pbakaus/impeccable | Design vocabulary, critique, audit, automated anti-pattern detection; ~118k stars |
| UI | https://github.com/Leonxlnx/taste-skill | Art direction, reference images and browser verification; ~122k stars |
| UI | https://github.com/Nutlope/hallmark | Design quality gates and browser checks; ~53.5k stars |
| UI | https://github.com/anthropics/skills/tree/main/skills/frontend-design | Official Anthropic frontend design skill |
| UI | https://awesome-copilot.github.com/skill/anti-ui-slop/ | Product-specific UI guidance |
| UI | https://github.com/nyrthoughts/anti-slop-design | Consolidated design rules, lint and checklist |
| Code | https://github.com/anthropics/claude-plugins-official/tree/main/plugins/pr-review-toolkit | Official code-simplifier agent (not a standalone skill) |
| Code | https://github.com/millionco/react-doctor | React diagnostics and cleanup; ~15.2k stars |
| Code | https://github.com/LeonardNJU/code-humanizer | Behavior-preserving structural cleanup |
| Code | https://github.com/MrZoyo/deslop-GPT | Test bloat, speculative fallbacks and verification theater |
| Code | https://github.com/khasky/awesome-agent-skills | Code cleanup and review skills |
| General | https://github.com/miqdadbadjuber/anti-slop | Cross-agent UI, text, accessibility and comments |
| General | https://github.com/muris11/anti-ai-slop | Modular taxonomy including dashboards, mobile, motion and copy |
| General | https://github.com/DevgenX/slop-skills | Engineering and design skills |
| General | https://github.com/ALVZ93/anti-slop | Clarity and maintainability |
| Writing | https://github.com/blader/humanizer | AI writing pattern cleanup; ~74.3k stars |
| Writing | https://github.com/hardikpandya/stop-slop | Prose cleanup; ~19.3k stars |
| Writing | https://github.com/conorbronsdon/avoid-ai-writing | Audit and rewrite; ~6.4k stars |
| Writing | https://github.com/kimhons/humanize | Skill, hook, agent and scorer |
| Review | https://github.com/openai/codex-plugin-cc | Official cross-agent read-only and adversarial review plugin |

## Recommendations (editorial, not measured)

Select one primary skill per responsibility to avoid duplicated context. For app UI, prefer existing design system and requirements over generic aesthetics. Use an automated visual check and screenshot/browser QA, not a prompt alone. For code, inspect the diff, preserve behavior and run meaningful tests; use React Doctor on React changes. Reserve independent adversarial review for risky changes. Review skill instructions, executable scripts, hooks, dependencies, network access and permissions before installing; pin reviewed revisions. Stars are adoption signals, not security or effectiveness evidence. Writing should prioritize factual correctness and voice rather than detector evasion.

Additional discovery sources: https://github.com/phcodesage/anti-slop-atlas ; https://github.com/zhuyansen/awesome-humanizer-skills ; https://github.com/Daguilar0123/ai-writing-skill-field-guide . Their claims were not independently benchmarked.
