# Media evidence policy: extract knowledge, retain source provenance

Date: 2026-11-25. Applies to new external UI/UX research, not immutable historical backups. Follow-up to #67, #75 and #64. Default: do not import complete third-party videos. Prioritize useful evidence per interaction, not raw byte count.

## Comparative references

| Project | Useful practice |
|---|---|
| [Google Screen Annotation](https://github.com/google-research-datasets/screen_annotation) | Stable screenshot ID, structured element type, location, text and description; retrieve images separately. |
| [ActivityNet](https://activity-net.org/download.html) | JSON annotations for temporal segments, separate from video distribution. |
| [Storybook](https://storybook.js.org/docs/writing-tests/interaction-testing) and [visual tests](https://storybook.js.org/docs/writing-tests/visual-testing/) | Executable stories, interaction steps and visual baselines. |
| [Motion](https://motion.dev/examples) | Pattern-specific demos and source code when authorized; do not extract premium content. |
| [Mobbin](https://mobbin.com/) | Organize by product, screen, flow and UI element; no bulk copying. |
| [Awesome Web Design References](https://github.com/jays0606/awesome-web-design-references) | Curated links, design observations and agent-oriented catalog. |
| [GitHub large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) | Separate large binaries from normal Git when durable storage is justified. |

## Evidence tiers

1. Source record (required): canonical URL, product, version/date if known, author, access and license status. Preserve links even when redistribution is not permitted.
2. Interaction record (required for a studied behavior): stable ID, task/pattern/component, initial state, input/trigger, intermediate and final states, constraints, visual observations, confidence, source segment and exact start/end seconds only when actually inspected; use null for unknown.
3. Lightweight evidence (optional, only if rights permit): optimized keyframes for the meaningful states, a short silent loop or clip when static frames cannot show motion, accessible captions. Suggested default 2–8 seconds per clip and 2–5 useful keyframes, not a hard limit. Never claim measured production timing from a reconstruction.
4. Reproducible example (preferred when available): pinned open-source story or original isolated demo, code, dependencies, fixtures, test steps and screenshots. Clearly label reconstruction versus original source.
5. Full source media (exception only): when necessary for preservation, rights verified and justified. Keep large originals in separately managed storage or releases with checksums, not normal main history. Historical backups remain immutable. Existing small archived examples are not removed or reclassified without review.

## Suggested machine-readable record

```json
{
  "id": "product-pattern-interaction",
  "source_url": "https://example.com/documentation",
  "product": "Example",
  "pattern": "side-panel",
  "component": "workspace",
  "evidence_class": "illustrative-schema-not-observed",
  "segment": {"start_seconds": null, "end_seconds": null},
  "states": ["initial", "triggered", "final"],
  "observations": [],
  "keyframes": [],
  "clip": null,
  "demo": null,
  "redistribution": "unknown",
  "verification": "not-inspected"
}
```

Use a shared schema for source, segment, frames, clip, motion contract and demo. Reference original IDs, immutable revisions, asset SHA-256/Git blob and rights. Index descriptions, synonyms, state transitions, timestamps and citations; do not put binary contents into FTS. Agent context packs should return a concise summary and relevant frames on demand.

## Acceptance and migration

- [ ] Audit existing media: distinguish full source, short upstream demo, original reconstruction, keyframe and link-only; playback and durations must be measured, not guessed.
- [ ] Add segment-level annotations, links to exact moments, descriptions and permitted keyframes; derive short clips only where useful and authorized.
- [ ] Deduplicate by blob hash; avoid unnecessary duplicate paths, preserve stable existing links or provide redirects.
- [ ] Integrate the structured records into the visual gallery, public research index and private context packs as appropriate; add schema, rights and coverage tests.
- [ ] Track counts by pattern/state/evidence completeness, not total downloaded videos.
- [ ] No automatic deletion or history rewrite; no copying restricted product media or private account captures to public Git.

This is a proposed operational policy based on comparative research, not a claim that the migration or playback review has been completed.
