# Exams Archive — GitHub as canonical source, four clients

**Canonical path:** `plugins/exams-archive-native/` (`main`).
**Consumers:** ChatGPT Personal Plugin Creator, Codex repository marketplace, Claude Code private Git marketplace, Google Antigravity local/Git installation.

## Update protocol

1. Each agent reads GitHub `main` and its own installed version before editing.
2. Propose changes to the canonical plugin folder using a branch/PR. CI checks manifests, skills, marketplaces, Python syntax and legacy FTS5 regression tests.
3. Merge only when checks pass. Plugins installed on machines require marketplace refresh or reinstall/update; git commits do not instantly update local plugin caches.
4. For ChatGPT personal plugin, publish an overlay ZIP through Plugin Creator with `expected_release_id`. Compare contents against GitHub file-by-file, then update `.sync-state.json` with the returned release ID. If publication fails, do not claim the clients are synchronized.
5. For ChatGPT → GitHub improvements, create a PR *first* from the plugin changes, to prevent two independent sources and version conflicts. Reconcile against `main` before publishing again.
6. Keep `plugins/exams-archive/` as a read-only legacy fallback until consumers are confirmed migrated; never alter backup bundles/releases or `archive-search-queries` during plugin synchronization.
7. Avoid force pushes, overwriting diverged files or publishing source/assets outside the private repo.

## Validation

CI only runs portable static and CLI regression tests. It does not verify runtime installation inside ChatGPT, Claude Code, Codex or Antigravity. Manual smoke tests:

```bash
codex plugin marketplace add ianmaciel7/exams-app-archive
codex plugin marketplace upgrade exams-archive-private
claude plugin marketplace add ianmaciel7/exams-app-archive
claude plugin install exams-archive-native@exams-archive-private
claude plugin validate ./plugins/exams-archive-native
agy plugin validate ./plugins/exams-archive-native
agy plugin install ./plugins/exams-archive-native
```

No authentication token should ever be embedded in a file or printed to logs. `gh auth login` is needed only for the local/private FTS5 release, not in ChatGPT.

**Known limitation:** ChatGPT Personal Plugin Creator cannot be assumed to receive a GitHub webhook or scheduled redeploy automatically. Github-managed plugin sync is available only in supported workspace configurations.
