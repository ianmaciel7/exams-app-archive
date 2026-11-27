# Open Artifact release evolution — 2026-11-27

Scope: public upstream release notes, not private package contents or verified runtime behavior. Complements the existing artifact-portal-qa skill.

- v0.14.6 (2026-11-23): eight built-in artifact types; baseline for comparing older integrations.
- v0.15.0 (2026-11-25, 64f2b56): ninth type Page, custom type lifecycle, native desktop library, improved PDF export and Docs recovery, Windows browser discovery.
- v0.16.0 (2026-11-25): Pi adapter and desktop per-artifact applications.
- v0.16.1 (2026-11-26): optional workspace confinement and explicit non-executed write conflicts.
- v0.16.2 (2026-11-26): undelivered message recovery, signed macOS desktop updates.
- v0.16.3 (2026-11-26): project-aware artifact storage, configuration and library filters.
- v0.17.0 (2026-11-26, 0f60798): editable SVG layers and stylus/touch improvements in Whiteboard, Motion video trimming, improved request/comment handling, OMP adapter, official static browser playground.

Implication: absence of Page in a 0.14.6 bundle is expected, not evidence of an import omission. A package version bump does not update its runtime. Upgrade using the official release bundle and digest, compare manifests/skills/editor assets, preserve local adaptations, test migration, all nine types, storage restrictions and native editor features. Do not conflate static Playground with a persistent host or assume live MCP is configured.

Sources (accessed 2026-11-27):
- https://github.com/JimLiu/open-artifact/releases
- https://github.com/JimLiu/open-artifact/releases/tag/v0.15.0
- https://github.com/JimLiu/open-artifact/releases/tag/v0.17.0
- https://github.com/JimLiu/open-artifact
