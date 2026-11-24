"""Integration smoke tests: run explicitly with MCP SDK and Playwright installed."""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


async def check_mcp():
    with tempfile.TemporaryDirectory() as folder:
        cache = Path(folder) / ".cache" / "exams-app-archive"
        cache.mkdir(parents=True)
        with sqlite3.connect(cache / "full-index.sqlite") as db:
            db.executescript("""
            CREATE TABLE repositories(id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE commits(repo_id INTEGER, sha TEXT);
            CREATE TABLE images(repo_id INTEGER, commit_sha TEXT, path TEXT, kind TEXT, blob TEXT, bytes INTEGER);
            INSERT INTO repositories VALUES (1, 'fixture');
            INSERT INTO commits VALUES (1, 'test-sha');
            INSERT INTO images VALUES (1, 'test-sha', 'sidebar.png', 'deleted', 'blob', 42);
            """)
        params = StdioServerParameters(command=sys.executable,
            args=[str(ROOT / "scripts/archive_mcp.py")],
            env={**os.environ, "HOME": folder, "USERPROFILE": folder})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
                assert names == {"search", "graph", "context", "images", "stats"}, names
                stats = await session.call_tool("stats", {})
                assert not stats.isError, stats
                assert "fixture" in str(stats.content), stats
                images = await session.call_tool("images", {"repo": "fixture", "deleted_only": True})
                assert not images.isError and "sidebar.png" in str(images.content), images
                invalid = await session.call_tool("search", {"query": "--help"})
                assert invalid.isError, invalid
        print("MCP: handshake, five tool registrations, real CLI stats/images, invalid query rejection passed")


def check_browser():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "site")))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 390, "height": 844})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/")
            assert page.locator("#query").is_enabled()
            page.locator("#query").fill("MCP")
            assert page.locator("#results article").count() >= 1
            page.locator("#clear").click()
            graph = {"nodes":[{"id":"a","label":"Sidebar","type":"Component"},{"id":"b","label":"Design","type":"File"}],
                     "edges":[{"source":"a","target":"b","type":"REFERENCES","confidence":"INFERRED"}]}
            page.locator("#file").set_input_files({"name":"graph.json","mimeType":"application/json","buffer":json.dumps(graph).encode()})
            page.locator("#graph .graph-node").first.wait_for()
            assert page.locator("#graph .graph-node").count() == 2
            page.locator("#graph .graph-node").first.click()
            assert "Sidebar" in page.locator("#graph-detail").inner_text()
            page.locator("#confidence").select_option("EXTRACTED")
            assert page.locator("#graph line").count() == 0
            page.locator("#confidence").select_option("INFERRED")
            assert page.locator("#graph line").count() == 1
            assert not errors, errors
            response = page.request.get(f"http://127.0.0.1:{server.server_port}/llms.txt")
            assert response.ok and "# Exams Archive" in response.text()
            browser.close()
        print("Browser: mobile search, graph import, node navigation, confidence filter and llms.txt passed")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    asyncio.run(check_mcp())
    check_browser()
