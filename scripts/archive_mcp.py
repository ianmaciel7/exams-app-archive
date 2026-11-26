"""Optional local MCP adapter for the canonical archive CLI."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP, Image

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
        capture_output=True, text=True, encoding="utf-8", timeout=120,
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


@mcp.tool()
def components_list():
    """List reviewed historical component previews and capture counts."""
    return invoke("components", "list")


@mcp.tool()
def component_render(component: str):
    """Build an allowlisted interactive component using preinstalled local dependencies."""
    return invoke("components", "render", checked(component))


@mcp.tool()
def component_capture(component: str, state: Literal["default","retry"] = "default",
                      theme: Literal["light","dark"] = "light", width: int = 1280, height: int = 800):
    """Capture a reviewed build with Playwright and save PNG plus provenance in SQLite."""
    return invoke("components","capture",checked(component),"--state",state,"--theme",theme,
                  "--width",str(width),"--height",str(height))


@mcp.tool()
def component_screenshots(component: str | None = None, limit: int = 20):
    """List saved component screenshots and their immutable source/build checksums."""
    args=["components","screenshots","--limit",str(max(1,min(limit,50)))]
    if component: args+=["--component",checked(component)]
    return invoke(*args)


@mcp.tool()
def component_screenshot_image(screenshot_id: str) -> Image:
    """Return the actual stored PNG image by id, not just a path."""
    from component_catalog import screenshot_bytes
    return Image(data=screenshot_bytes(screenshot_id),format="png")


@mcp.tool()
def research_search(query: str, kind: Literal["pattern", "source", "visual", "view", "output", "flow", "contract", "availability"] | None = None,
                    product: str | None = None, availability: str | None = None,
                    limit: int = 20):
    """Search approved public research catalogs; independent from private history."""
    import research_index
    with sqlite3.connect(":memory:") as db:
        research_index.build(db, research_index.load_records())
        return research_index.search(db, checked(query), kind, max(1, min(limit, 50)),
                                     product=product, availability=availability)


@mcp.tool()
def research_audit():
    """Return public catalog coverage, declared visual availability and explicit gaps."""
    import research_index
    records = research_index.load_records()
    result = research_index.audit(records)
    result["record_provenance"] = research_index.verify_record_provenance(records)
    return result


@mcp.tool()
def resolve_concept(query: str):
    """Resolve a public research concept to canonical ID and catalog snapshot before querying."""
    import archive_context
    import concept_packs
    import research_index
    return archive_context.discover(checked(query), research_index.load_records(),
                                    concept_packs.load_taxonomy())


@mcp.tool()
def query_concept_context(concept_id: str, query: str, snapshot: str,
                          product: str | None = None, limit: int = 12,
                          max_bytes: int = 12000):
    """Retrieve public catalog excerpts only, pinned to the resolved snapshot; no private history."""
    import archive_context
    import concept_packs
    import research_index
    return archive_context.retrieve(checked(concept_id), checked(query),
                                    research_index.load_records(), concept_packs.load_taxonomy(),
                                    revision=checked(snapshot), product=product,
                                    limit=limit, max_bytes=max_bytes)


if __name__ == "__main__":
    mcp.run(transport="stdio")
