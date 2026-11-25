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
from playwright.sync_api import sync_playwright, expect

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
                assert names == {"search", "graph", "context", "images", "stats", "components_list", "component_render", "component_capture", "component_screenshots", "component_screenshot_image", "research_search", "research_audit", "resolve_concept", "query_concept_context"}, names
                stats = await session.call_tool("stats", {})
                assert not stats.isError, stats
                assert "fixture" in str(stats.content), stats
                images = await session.call_tool("images", {"repo": "fixture", "deleted_only": True})
                assert not images.isError and "sidebar.png" in str(images.content), images
                components = await session.call_tool("components_list", {})
                assert not components.isError and "error-boundary" in str(components.content), components
                research = await session.call_tool("research_search", {"query": "sortable", "product": "dnd-kit"})
                assert not research.isError and "dnd-kit" in str(research.content), research
                audit = await session.call_tool("research_audit", {})
                assert not audit.isError and "visual_matrix" in str(audit.content), audit
                resolved = await session.call_tool("resolve_concept", {"query": "painel lateral"})
                assert not resolved.isError, resolved
                result = getattr(resolved, "structuredContent", None)
                if not result:
                    result = json.loads(resolved.content[0].text)
                assert result["matches"][0]["id"] == "ui.navigation.side-panel", result
                context_result = await session.call_tool("query_concept_context", {
                    "concept_id": "ui.navigation.side-panel", "query": "side panel redesign",
                    "snapshot": result["snapshot"], "product": "Capacities", "max_bytes": 5000})
                assert not context_result.isError and "official-capacities-1" in str(context_result.content), context_result
                invalid = await session.call_tool("search", {"query": "--help"})
                assert invalid.isError, invalid
        print("MCP: handshake, fourteen tool registrations, real CLI stats/images, invalid query rejection passed")


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
            fixture = json.loads((ROOT / "tests/fixtures/public-catalog.json").read_text(encoding="utf-8"))
            page.route("**/catalog.json", lambda route: route.fulfill(json=fixture))
            page.goto(f"http://127.0.0.1:{server.server_port}/")
            expect(page.locator("#query")).to_be_enabled()
            assert page.locator("#query").is_enabled()
            expect(page.locator("#view-files")).to_be_visible()
            page.locator("#tab-graph").click()
            assert page.locator("#graph .graph-node").count() > 2
            assert page.locator("#graph-groups button").count() >= 2
            page.locator("#zoom-in").click()
            expect(page.locator(".graph-world")).to_have_attribute("transform", "translate(-112.5 -70) scale(1.25)")
            page.locator("#graph-fit").click()
            page.locator("#query").fill("sidebar")
            expect(page.locator("#results article").filter(has_text="prototipo-sidebar.html").first).to_be_visible()
            assert page.locator("#results article").count() >= 30
            page.locator("#results article").filter(has_text="prototipo-sidebar.html").first.get_by_role("button", name="＋ Contexto").click()
            page.locator("#toggle-context").click()
            expect(page.locator("#context-count")).to_have_text("1/30")
            assert page.locator("#context-export").is_enabled()
            page.locator("#tab-preview").click()
            expect(page.locator("#workspace-preview")).to_have_attribute("src", "./preview-error.html")
            page.locator("#preview-choice").select_option("loading")
            expect(page.locator("#workspace-preview")).to_have_attribute("src", "./preview-loading.html")
            page.locator("#tab-graph").click()
            page.locator("#context-clear").click()
            expect(page.locator("#context-count")).to_have_text("0/30")
            page.locator("#close-context").click()
            page.locator("#kind").select_option("image")
            expect(page.locator("#results article").filter(has_text="capturas/").first).to_be_visible()
            page.locator("#clear").click()
            page.locator("#query").fill("MCP")
            assert page.locator("#results article").count() >= 1
            page.locator("#clear").click()
            graph = {"nodes":[{"id":"a","label":"Sidebar","type":"Component","community":1},{"id":"b","label":"Design","type":"File","community":2}],
                     "edges":[{"source":"a","target":"b","type":"REFERENCES","confidence":"INFERRED"}]}
            page.locator("#file").set_input_files({"name":"graph.json","mimeType":"application/json","buffer":json.dumps(graph).encode()})
            page.get_by_role("button", name="Sidebar", exact=True).wait_for()
            assert page.locator("#graph .graph-node").count() == 2
            expect(page.locator("#graph")).to_have_attribute("data-layout", "settled")
            node = page.get_by_role("button", name="Sidebar", exact=True).locator("circle").last
            node.hover()
            expect(page.locator("#graph line")).to_have_class("graph-edge graph-dashed highlighted")
            before = page.get_by_role("button", name="Sidebar", exact=True).get_attribute("transform")
            rect = node.bounding_box()
            assert rect
            page.mouse.move(rect["x"]+rect["width"]/2, rect["y"]+rect["height"]/2)
            page.mouse.down()
            page.mouse.move(rect["x"]+rect["width"]/2+24, rect["y"]+rect["height"]/2+20, steps=5)
            page.mouse.up()
            assert page.get_by_role("button", name="Sidebar", exact=True).get_attribute("transform") != before
            page.locator("#graph-motion").uncheck()
            expect(page.locator("#graph")).to_have_attribute("data-layout", "settled")
            assert page.locator("#group-title").inner_text() == "Comunidades"
            page.get_by_role("button", name="Sidebar", exact=True).locator("circle").last.click()
            page.locator("#toggle-context").click()
            assert "Sidebar" in page.locator("#graph-detail").inner_text()
            page.locator("#close-context").click()
            page.locator("#confidence").select_option("EXTRACTED")
            assert page.locator("#graph line").count() == 0
            page.locator("#confidence").select_option("INFERRED")
            assert page.locator("#graph line").count() == 1
            assert not errors, errors
            response = page.request.get(f"http://127.0.0.1:{server.server_port}/llms.txt")
            assert response.ok and "# Exams Archive" in response.text()
            page.goto(f"http://127.0.0.1:{server.server_port}/files.html")
            page.locator("#local-files").set_input_files([{"name":"Button.tsx","mimeType":"text/plain","buffer":b"export const Button = () => <button>OK</button>"},{"name":"example.html","mimeType":"text/html","buffer":b"<h1>Original HTML</h1><script>document.body.dataset.ran=1</script>"}])
            page.get_by_role("button", name="Button.tsx", exact=False).click()
            expect(page.locator("#source-code")).to_contain_text("export const Button")
            assert page.locator("#component-help").is_visible()
            page.locator("#components-only").check()
            assert page.get_by_role("button", name="example.html", exact=False).count() == 0
            page.locator("#components-only").uncheck()
            page.get_by_role("button", name="example.html", exact=False).click()
            expect(page.locator("#preview-tab")).to_be_enabled()
            page.locator("#preview-tab").click()
            page.locator("#render-preview").click()
            assert page.frame_locator("#preview-frame").locator("h1").inner_text() == "Original HTML"
            assert page.frame_locator("#preview-frame").locator("body").get_attribute("data-ran") is None
            assert not errors, errors
            browser.close()
        print("Browser: mobile search, graph import, node navigation, confidence filter and llms.txt passed")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    asyncio.run(check_mcp())
    check_browser()
