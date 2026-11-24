# Agent access

All interfaces reuse the existing archive. No second database, hosted service or background daemon is required. The GitHub repository is public; review sensitive historical data separately. The Pages artifact contains only a curated interface and documentation links.

## CLI

Clone the repository, install Python 3.12+ and GitHub CLI, then run from its root:

```sh
python plugins/exams-archive/scripts/archive_query.py sync
python plugins/exams-archive/scripts/archive_query.py search "sidebar" --limit 20
python plugins/exams-archive/scripts/archive_query.py graph --inventory-dir inventory --stats
python plugins/exams-archive/scripts/archive_query.py graph "sidebar" --hops 2
python plugins/exams-archive/scripts/archive_query.py context --inventory-dir inventory --stats
python plugins/exams-archive/scripts/archive_query.py context "sidebar"
```

Sync verifies the release checksum; use authenticated GitHub CLI if required. Graph/context build commands are explicit.

## Local MCP (optional)

With uv installed, configure a stdio MCP client using an absolute local path:

```json
{
  "mcpServers": {
    "exams-archive": {
      "command": "uv",
      "args": ["run", "--no-project", "--with", "mcp>=1.9,<2", "python", "/absolute/path/exams-app-archive/scripts/archive_mcp.py"]
    }
  }
}
```

On Windows use an absolute path with forward slashes or escaped backslashes. Adapt the configuration container to the host (Codex, Claude Code, or another stdio MCP client). Prepare the local indexes using the CLI first. The five MCP tools are search, graph, context, images and stats. There is no remote MCP endpoint on GitHub Pages. Tools do not accept shell commands or arbitrary output paths.

## Website

- Open the Pages URL and search the curated documentation catalog immediately.
- Import the existing historical export or a graph JSON file for deeper local search.
- Export the native graph from the archive root with `python scripts/graph_linker.py build-inventory --export-json ~/archive-graph.json`.
- The graph also accepts nodes/links JSON in Graphify-style format. Relationships are shown as recorded, not guessed.
- `/exams-app-archive/llms.txt` is the proposed Markdown discovery file for agents, not an API or MCP endpoint.

Imported files stay in the current tab. Never commit an unreviewed data export.

## Integration validation

CI runs a real MCP stdio handshake and CLI calls against synthetic fixtures, then Chromium checks search, graph import, node selection, confidence filters and llms.txt. No archive data is uploaded by this test.
