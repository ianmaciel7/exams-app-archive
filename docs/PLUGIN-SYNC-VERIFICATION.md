# Exams Archive — Plugin Synchronization and Multi-Client Verification (v0.6.0)

## 1. Overview and Synchronization Baseline

The canonical source of truth for the Exams Archive native plugin is:
- **Canonical Repository:** `ianmaciel7/exams-app-archive`
- **Canonical Tree:** `main:plugins/exams-archive-native/`
- **Desired Version:** `0.6.0`
- **Plugin ID:** `plugins_6b04aaa9fd848191a24525011f76e2bb`
- **Target Consumer Release (ChatGPT):** `pluginrel_6b04c63bd96c8191bda2c535f2b62e1b`
- **Status:** `verified-synced` as recorded in `plugins/exams-archive-native/.sync-state.json`

The synchronization state bridges the GitHub repository with the ChatGPT Personal Plugin Creator, while simultaneously serving portable manifests and skills to Codex, Claude Code, and Google Antigravity.

## 2. 19 Canonical Package Files Verification

The native plugin consists of 19 canonical files. All 19 files are validated against the release bundle:
- **18 Byte-Identical Files:** Content matches raw byte-for-byte.
- **1 JSON Semantic Equivalent File:** `.codex-plugin/plugin.json` matches semantically (`json.loads(canonical) == json.loads(release)`). The slight byte variance arises from standard Unicode character escaping (`\\u00e3` vs `ã`) applied by the ChatGPT Personal Plugin Creator during export.

### Canonical File Matrix

| Index | File Path | Category | Equivalence Type | Notes |
|---|---|---|---|---|
| 1 | `agents/openai.yaml` | Agent Config | Byte-identical | OpenAI agent interface and prompt |
| 2 | `.antigravity-plugin/plugin.json` | Manifest | Byte-identical | Google Antigravity v1 schema |
| 3 | `.claude-plugin/plugin.json` | Manifest | Byte-identical | Claude Code private marketplace |
| 4 | `.codex-plugin/plugin.json` | Manifest | Semantic JSON | Unicode character escaping variation |
| 5 | `plugin.json` | Manifest | Byte-identical | Agent-plugins standard 1.0.0 |
| 6 | `README.md` | Documentation | Byte-identical | Plugin instructions and capabilities |
| 7 | `scripts/archive_query.py` | CLI & Engine | Byte-identical | FTS5, AST, graph, context, secrets |
| 8 | `skills/archive-research/references/github-connected.md` | Skill Reference | Byte-identical | GitHub connected search reference |
| 9 | `skills/archive-research/references/private-fts5.md` | Skill Reference | Byte-identical | FTS5 index and query syntax |
| 10 | `skills/archive-research/SKILL.md` | Skill | Byte-identical | Historical research skill |
| 11 | `skills/archive-search/SKILL.md` | Skill | Byte-identical | FTS5 CLI and GitHub search skill |
| 12 | `skills/sync-bridge/SKILL.md` | Skill | Byte-identical | Controlled bidirectional sync contract |
| 13 | `skills/ui-fidelity/references/chat-preview-contract.md` | Skill Reference | Byte-identical | Self-contained HTML preview contract |
| 14 | `skills/ui-fidelity/references/source-map.md` | Skill Reference | Byte-identical | Component to source file mapping |
| 15 | `skills/ui-fidelity/references/visual-qa.md` | Skill Reference | Byte-identical | Visual QA checklist and capture audit |
| 16 | `skills/ui-fidelity/references/visual-source-catalog.md` | Skill Reference | Byte-identical | 213 historical images catalog |
| 17 | `skills/ui-fidelity/SKILL.md` | Skill | Byte-identical | Design fidelity and tokens skill |
| 18 | `skills/ui-motion/references/motion-taxonomy.md` | Skill Reference | Byte-identical | Motion taxonomy and duration metrics |
| 19 | `skills/ui-motion/SKILL.md` | Skill | Byte-identical | UI animations and gestures skill |

### External Sync Tracking

The metadata file `plugins/exams-archive-native/.sync-state.json` tracks external release synchronization state:
```json
{
  "schema": 2,
  "source_of_truth": "ianmaciel7/exams-app-archive@main:plugins/exams-archive-native/",
  "plugin_id": "plugins_6b04aaa9fd848191a24525011f76e2bb",
  "desired_version": "0.6.0",
  "last_published_release_id": "pluginrel_6b04c63bd96c8191bda2c535f2b62e1b",
  "last_published_version": "0.6.0",
  "status": "verified-synced",
  "verified_files": 19,
  "byte_identical_files": 18,
  "json_semantic_equivalent_files": [
    ".codex-plugin/plugin.json"
  ]
}
```

## 3. Automated Smoke Test Runner for CLI Routing

To ensure portable routing integrity across environments, `scripts/validate_plugin_sync.py` provides an automated smoke test runner that exercises all 7 subcommands supported by `scripts/archive_query.py`:

1. **`search`**: Full-text FTS5 search across commits, changed files, and historical images with BM25 ranking and inter-kind quotas.
2. **`images`**: Historical image queries filtering active and deleted images with size and occurrence deduplication.
3. **`stats`**: Repository commit aggregation and high-level index metadata.
4. **`ast`**: Multi-language AST structural chunker and UI motion contract extraction.
5. **`graph`**: Multi-repo temporal knowledge graph query engine and neighborhood traversal.
6. **`context`**: Multi-repo chronological context linker uniting PRs, commits, reviews, and artifacts.
7. **`secrets-check`**: High-entropy token, credential, and private key detection gate.

### Running the Validation Script

```bash
# Validate sync state, manifests, 19 canonical files, and run CLI smoke tests
python3 scripts/validate_plugin_sync.py

# Output JSON report
python3 scripts/validate_plugin_sync.py --json

# Compare with an external release bundle directory or zip
python3 scripts/validate_plugin_sync.py --target-dir /path/to/extracted/release
python3 scripts/validate_plugin_sync.py --target-zip /path/to/plugin-v0.6.0.zip
```

## 4. Multi-Client Consumer Protocols

The plugin tree is structured to provide native installation and discovery across 4 major agent platforms:

### 4.1. OpenAI ChatGPT (Personal Plugin Creator)
- **Plugin Identifier:** `plugins_6b04aaa9fd848191a24525011f76e2bb`
- **Release Channel:** Personal Plugin Creator overlay publication.
- **Protocol:**
  1. Generate release overlay zip directly from canonical `plugins/exams-archive-native/`.
  2. Upload via Plugin Creator targeting `plugins_6b04aaa9fd848191a24525011f76e2bb` with `expected_release_id`.
  3. Validate post-publication release files using `scripts/validate_plugin_sync.py --target-zip <bundle>`.
  4. Record new release ID and status in `.sync-state.json`.
  5. Important: ChatGPT personal plugins do not receive webhooks or auto-redeploy on git commit. Every deployment requires explicit overlay publishing.

### 4.2. Codex
- **Marketplace Manifest:** `.agents/plugins/marketplace.json` references source `./plugins/exams-archive-native`.
- **Plugin Manifest:** `plugins/exams-archive-native/.codex-plugin/plugin.json`.
- **Protocol:**
  ```bash
  # Register repository marketplace
  codex plugin marketplace add ianmaciel7/exams-app-archive

  # Upgrade installed plugin to canonical release
  codex plugin marketplace upgrade exams-archive-native
  ```

### 4.3. Claude Code
- **Marketplace Manifest:** `.claude-plugin/marketplace.json` references source `./plugins/exams-archive-native`.
- **Plugin Manifest:** `plugins/exams-archive-native/.claude-plugin/plugin.json`.
- **Protocol:**
  ```bash
  # Register repository marketplace
  claude plugin marketplace add ianmaciel7/exams-app-archive

  # Install or validate plugin package
  claude plugin install exams-archive-native@exams-archive-private
  claude plugin validate ./plugins/exams-archive-native
  ```

### 4.4. Google Antigravity
- **Plugin Manifest:** `plugins/exams-archive-native/.antigravity-plugin/plugin.json`.
- **Schema:** `https://antigravity.google/schemas/v1/plugin.json`.
- **Protocol:**
  ```bash
  # Validate plugin package definition
  agy plugin validate ./plugins/exams-archive-native

  # Install local plugin into agent environment
  agy plugin install ./plugins/exams-archive-native
  ```

## 5. Security and Operational Guarantees

- **Zero Credential Embedding:** No API tokens, private keys, or session identifiers are stored in the plugin package, manifests, or sync state.
- **Private Repository Boundaries:** The canonical plugin points exclusively to the private GitHub repository `ianmaciel7/exams-app-archive`.
- **Zero Emoji Policy:** All configuration, code, and documentation strictly adhere to zero Unicode emoji characters.
