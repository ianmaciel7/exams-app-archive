"""Optional local MCP adapter for the canonical archive CLI."""
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "plugins" / "exams-archive" / "scripts" / "archive_query.py"
mcp = FastMCP("exams-archive")


def checked(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 500 or value.startswith("-"):
        raise ValueError("Expected a nonempty query, at most 500 characters")
    return value


def invoke(*args: str):
    proc = subprocess.run(
        [sys.executable, str(CLI), *args], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    if proc.returncode:
        raise RuntimeError("Archive query failed. Check the local index and CLI setup.")
    if len(proc.stdout) > 2_000_000:
        raise RuntimeError("Result too large; reduce limit or narrow query.")
    return json.loads(proc.stdout)


def repository_arg(repo: str | None) -> list[str]:
    return ["--repo=" + checked(repo)] if repo else []


@mcp.tool()
def search(query: str, repo: str | None = None,
           kind: Literal["all", "file", "commit", "image"] = "all", limit: int = 20):
    """Find indexed historical records, not full source text."""
    return invoke("search", checked(query), "--kind", kind,
                  "--limit", str(max(1, min(limit, 50))), *repository_arg(repo))


@mcp.tool()
def graph(entity: str, repo: str | None = None, hops: int = 2,
          confidence: Literal["EXTRACTED", "INFERRED"] | None = None, limit: int = 30):
    """Explore typed relations from a prebuilt local graph; preserve provenance."""
    args = ["graph", checked(entity), "--hops", str(max(1, min(hops, 3))),
            "--limit", str(max(1, min(limit, 50))), *repository_arg(repo)]
    if confidence:
        args += ["--confidence", confidence]
    return invoke(*args)


@mcp.tool()
def context(query: str, repo: str | None = None, limit: int = 20):
    """Find chronological context in the prebuilt local context index."""
    return invoke("context", checked(query), "--limit",
                  str(max(1, min(limit, 50))), *repository_arg(repo))


@mcp.tool()
def images(repo: str | None = None, deleted_only: bool = False, limit: int = 20):
    """Find indexed historical image references."""
    args = ["images", "--limit", str(max(1, min(limit, 50))), *repository_arg(repo)]
    if deleted_only:
        args.append("--deleted-only")
    return invoke(*args)


@mcp.tool()
def stats():
    """Return counts for the locally synchronized archive."""
    return invoke("stats")


if __name__ == "__main__":
    mcp.run(transport="stdio")
