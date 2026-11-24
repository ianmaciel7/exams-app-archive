# Archive acceptance audit — 2026-11-24

Owner decision: keep the archive public; a Google Drive copy is not required. No source repository or branch has been deleted. Do not treat archive acceptance as permission to delete sources.

## Verified preservation

- Six original Git bundles: 593 original refs (69 branches, 5 tags, 519 PR refs), restored with SHA-256 and Git fsck.
- CI evidence: 2,883 artifact ZIPs checked across 16 partitions; six metadata ZIPs and historical index verified. [29/29 integrity jobs](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45432868764).
- PR metadata: public PRs 100, 101, 102 supplemented; all 161 exams-app-old PRs covered. [Reconciliation](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45437089169).
- Historical Notes worktrees: two missing commit objects preserved at exact SHAs in a private supplemental bundle, with verified restoration and download hash. [Manifest](../manifests/notes-worktrees-2026-11-24.json). This supplement is in the private Notes source, not in the public archive.
- Complete historical-path/commit-subject FTS5 index: six original sources and two supplemental worktree refs (seven indexed sources, 595 refs), SQLite integrity and download hashes verified. [Authenticated release](https://github.com/ianmaciel7/notes-app/releases/tag/archive-index-private-2026-11-24), [build](https://github.com/ianmaciel7/notes-app/actions/runs/45438877532). This is not a full content/semantic index; the public catalog remains limited to explicitly public source repositories.
- Original CI logs: 1,149/10,156 distinct run-log ZIPs retrieved and verified so far (12 pilot, 500 second batch, 637 completed remaining shards). [Pilot](https://github.com/ianmaciel7/notes-app/actions/runs/45439025607), [second batch](https://github.com/ianmaciel7/notes-app/actions/runs/45439865377), [remaining shards](https://github.com/ianmaciel7/notes-app/actions/runs/45442975086). Remaining shard jobs are still running/queued; successful manifests, not scheduling, determine coverage.
- GitHub-hosted attachment inventory: six metadata ZIPs scanned; no matching GitHub attachment URLs detected by the allowlist scanner. [Run](https://github.com/ianmaciel7/notes-app/actions/runs/45439149339). This is not proof that all external attachments, signed URLs or private attachments are absent. The three later PR supplements and links outside the scanned metadata ZIPs require separate checks.

## Remaining limitations

- Original run-log export beyond the pilot: bounded batches via `scripts/archive_ci_log_batch.py`; expired/deleted or inaccessible logs may be unrecoverable. Do not claim completion from workflow success alone.
- Secret candidate triage: [run](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45438524406). Candidate patterns are not proof of active credentials. Binary blobs and large blobs not scanned, and no online credential validation. Confirm/rotate actual credentials through their provider before declaring security clearance.
- Private source data is not replicated into new public artifacts; authenticated index and supplemental bundle are available from Notes.
- No independent off-GitHub copy. The owner waived Google Drive, not the risks of a single hosting account. Keep original repositories available; any destructive action requires separate authorization.
- Authenticated advanced content and evidence release published and round-trip verified: [build](https://github.com/ianmaciel7/notes-app/actions/runs/45442812970), [release](https://github.com/ianmaciel7/notes-app/releases/tag/archive-content-private-2026-11-24). 23,508 unique indexed text blobs, 193,003 chunks, 366,053 occurrences; supported text only, not vector semantic coverage. Real authenticated search, exact text recovery, content search, bounded context pack and linked history passed. Graph and targeted pin tests are pending. The public archive remains unchanged in visibility; private queue and indexes stay in Notes.
- Security triage completed for six sources: no complete PEM private-key blocks in scanned text; candidate tokens/URLs and generic assignments still require provider-specific review. Four oversized and 1,901 binary blobs were excluded; counts refer to scanned Git objects, not credential validity.
- External integrations and independent copy remain deletion blockers; Google Drive was waived. No source deletion authorized.
