#!/usr/bin/env python3
"""Tests for scripts/ast_chunker.py covering TSX, Python, CSS, motion contracts, deduplication, and Zero Emoji."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ast_chunker  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class AstChunkerTests(unittest.TestCase):
    def test_python_ast_extraction_classes_methods_functions_and_offsets(self):
        source = (
            '"""Sidebar engine module."""\n\n'
            "class SidebarState:\n"
            "    def __init__(self, width: int = 240) -> None:\n"
            "        self.width = width\n\n"
            "    async def sync_layout(self) -> int:\n"
            "        return self.width\n\n"
            "def compute_dwell_delay(open_ms: int = 300) -> int:\n"
            "    return open_ms\n"
        )
        chunks = ast_chunker.chunk_code(source, language="python")
        by_name = {(c.node_type, c.name, c.parent_context): c for c in chunks}

        self.assertIn(("class", "SidebarState", "module"), by_name)
        self.assertIn(("method", "__init__", "SidebarState"), by_name)
        self.assertIn(("method", "sync_layout", "SidebarState"), by_name)
        self.assertIn(("function", "compute_dwell_delay", "module"), by_name)

        cls_chunk = by_name[("class", "SidebarState", "module")]
        self.assertEqual(cls_chunk.start_line, 3)
        self.assertEqual(cls_chunk.end_line, 8)
        self.assertEqual(source[cls_chunk.start_offset : cls_chunk.end_offset], cls_chunk.content)
        self.assertEqual(cls_chunk.symbol_id, "py:SidebarState")
        self.assertEqual(cls_chunk.status, "parsed")

        fn_chunk = by_name[("function", "compute_dwell_delay", "module")]
        self.assertEqual(fn_chunk.start_line, 10)
        self.assertEqual(fn_chunk.end_line, 11)
        self.assertEqual(source[fn_chunk.start_offset : fn_chunk.end_offset], fn_chunk.content)

    def test_tsx_component_hooks_handlers_timers_waapi_and_tailwind(self):
        source = (
            "import React, { useEffect, useState } from 'react';\n\n"
            "export function usePeekTimer(delayMs: number) {\n"
            "  const [open, setOpen] = useState(false);\n"
            "  return { open, setOpen, delayMs };\n"
            "}\n\n"
            "export function SpaceSidebar({ collapsed }: { collapsed: boolean }) {\n"
            "  const { open, setOpen } = usePeekTimer(300);\n\n"
            "  useEffect(() => {\n"
            "    const id = window.setTimeout(() => setOpen(true), 300);\n"
            "    return () => clearTimeout(id);\n"
            "  }, [setOpen]);\n\n"
            "  const handleMouseEnter = () => {\n"
            "    window.setTimeout(() => setOpen(true), 300);\n"
            "  };\n\n"
            "  const handleMouseLeave = () => {\n"
            "    window.setTimeout(() => setOpen(false), 150);\n"
            "  };\n\n"
            "  const handleReorderFlip = (el: HTMLElement) => {\n"
            "    el.animate([{ transform: 'translateY(12px)' }, { transform: 'translateY(0)' }], {\n"
            "      duration: 200,\n"
            "      easing: 'ease-out',\n"
            "    });\n"
            "  };\n\n"
            "  return (\n"
            "    <aside\n"
            "      onMouseEnter={handleMouseEnter}\n"
            "      onMouseLeave={handleMouseLeave}\n"
            '      onClick={() => handleReorderFlip(document.body)}\n'
            '      className="transition-all duration-200 delay-150 ease-out motion-reduce:transition-none"\n'
            "    >\n"
            "      {collapsed && open ? 'peek' : 'docked'}\n"
            "    </aside>\n"
            "  );\n"
            "}\n"
        )
        chunks = ast_chunker.chunk_code(source, language="tsx")
        names = {(c.node_type, c.name, c.parent_context) for c in chunks}

        self.assertIn(("hook", "usePeekTimer", "module"), names)
        self.assertIn(("component", "SpaceSidebar", "module"), names)
        self.assertIn(("hook", "useEffect", "SpaceSidebar"), names)
        self.assertIn(("handler", "handleMouseEnter", "SpaceSidebar"), names)
        self.assertIn(("handler", "handleMouseLeave", "SpaceSidebar"), names)
        self.assertIn(("handler", "handleReorderFlip", "SpaceSidebar"), names)

        comp = next(c for c in chunks if c.node_type == "component" and c.name == "SpaceSidebar")
        self.assertEqual(source[comp.start_offset : comp.end_offset], comp.content)
        self.assertEqual(comp.start_line, 8)
        self.assertEqual(comp.end_line, 41)

        kinds = {m.kind for m in comp.motion_contracts}
        self.assertTrue({"timer", "handler", "waapi", "tailwind"}.issubset(kinds))

        timers = [m for m in comp.motion_contracts if m.kind == "timer"]
        delays = {m.delay_ms for m in timers if m.delay_ms is not None}
        self.assertIn(300.0, delays)
        self.assertIn(150.0, delays)
        self.assertTrue(all(m.duration_ms is None for m in timers))

        waapi = [m for m in comp.motion_contracts if m.kind == "waapi"]
        self.assertEqual(len(waapi), 1)
        self.assertEqual(waapi[0].duration_ms, 200.0)
        self.assertEqual(waapi[0].easing, "ease-out")

        tw = [m for m in comp.motion_contracts if m.kind == "tailwind"]
        self.assertTrue(any(m.duration_ms == 200.0 and m.delay_ms == 150.0 and m.reduced_motion for m in tw))

        handlers = {m.trigger for m in comp.motion_contracts if m.kind == "handler"}
        self.assertTrue({"onMouseEnter", "onMouseLeave", "onClick"}.issubset(handlers))

    def test_css_rules_keyframes_and_reduced_motion(self):
        source = (
            ".shell {\n"
            "  width: 240px;\n"
            "  transition: margin-left 200ms ease;\n"
            "}\n"
            "@keyframes skeletonPulse {\n"
            "  0%, 100% { opacity: 1; }\n"
            "  50% { opacity: 0.5; }\n"
            "}\n"
            ".skeleton-row {\n"
            "  animation: skeletonPulse 1.2s ease-in-out infinite;\n"
            "}\n"
            "@media (prefers-reduced-motion: reduce) {\n"
            "  .shell { transition: none; }\n"
            "}\n"
        )
        chunks = ast_chunker.chunk_code(source, language="css")
        by_name = {(c.node_type, c.name, c.parent_context): c for c in chunks}

        self.assertIn(("css_rule", ".shell", "stylesheet"), by_name)
        self.assertIn(("keyframes", "skeletonPulse", "stylesheet"), by_name)
        self.assertIn(("css_rule", ".skeleton-row", "stylesheet"), by_name)
        self.assertIn(("media_rule", "@media (prefers-reduced-motion: reduce)", "stylesheet"), by_name)
        self.assertIn(("css_rule", ".shell", "@media (prefers-reduced-motion: reduce)"), by_name)

        shell_chunk = by_name[("css_rule", ".shell", "stylesheet")]
        self.assertEqual(source[shell_chunk.start_offset : shell_chunk.end_offset], shell_chunk.content)
        self.assertEqual(shell_chunk.motion_contracts[0].kind, "css-transition")
        self.assertEqual(shell_chunk.motion_contracts[0].duration_ms, 200.0)
        self.assertEqual(shell_chunk.motion_contracts[0].easing, "ease")

        skel_chunk = by_name[("css_rule", ".skeleton-row", "stylesheet")]
        self.assertEqual(skel_chunk.motion_contracts[0].kind, "css-animation")
        self.assertEqual(skel_chunk.motion_contracts[0].duration_ms, 1200.0)
        self.assertEqual(skel_chunk.motion_contracts[0].easing, "ease-in-out")

        media_chunk = by_name[("media_rule", "@media (prefers-reduced-motion: reduce)", "stylesheet")]
        self.assertTrue(media_chunk.motion_contracts[0].reduced_motion)

    def test_blob_deduplication_preserves_lineage_and_deterministic_hashes(self):
        shared_tsx = "export function SharedSidebar() {\n  return <aside className='transition-all duration-200' />;\n}\n"
        other_py = "def helper() -> int:\n    return 42\n"

        occurrences = [
            {
                "repo": "ianmaciel7/notes-app",
                "ref": "refs/heads/old-5",
                "commit_sha": "a" * 40,
                "path": "src/components/sidebar.tsx",
                "language": "tsx",
                "content": shared_tsx,
            },
            {
                "repo": "ianmaciel7/notes-app",
                "ref": "refs/heads/old-10",
                "commit_sha": "b" * 40,
                "path": "src/components/workspace/sidebar.tsx",
                "language": "tsx",
                "content": shared_tsx,
            },
            {
                "repo": "ianmaciel7/exams-app",
                "ref": "refs/heads/main",
                "commit_sha": "c" * 40,
                "path": "scripts/helper.py",
                "language": "python",
                "content": other_py,
            },
        ]
        dedup1 = ast_chunker.deduplicate_chunks_by_blob(occurrences)
        dedup2 = ast_chunker.deduplicate_chunks_by_blob(occurrences)

        self.assertEqual(dedup1, dedup2)
        self.assertEqual(dedup1["unique_blobs"], 2)
        self.assertEqual(dedup1["total_occurrences"], 3)
        self.assertEqual(dedup1["dedup_hits"], 1)

        occ_refs = {(o["ref"], o["path"]) for o in dedup1["occurrences"]}
        self.assertEqual(
            occ_refs,
            {
                ("refs/heads/old-5", "src/components/sidebar.tsx"),
                ("refs/heads/old-10", "src/components/workspace/sidebar.tsx"),
                ("refs/heads/main", "scripts/helper.py"),
            },
        )

    def test_invalid_syntax_fallback_and_unsupported_language(self):
        broken_py = "def broken_fn(:\n    return 1\n"
        chunks_py = ast_chunker.chunk_code(broken_py, language="python")
        self.assertEqual(len(chunks_py), 1)
        self.assertEqual(chunks_py[0].node_type, "fallback_block")
        self.assertEqual(chunks_py[0].status, "syntax_error_fallback")

        broken_ts = "export function UnclosedSidebar() {\n  return <div />;\n"
        chunks_ts = ast_chunker.chunk_code(broken_ts, language="tsx")
        self.assertGreaterEqual(len(chunks_ts), 1)
        self.assertEqual(chunks_ts[0].status, "partial_unbalanced_braces")

        md_chunks = ast_chunker.chunk_code("# Title\n\nSome markdown.\n", language="markdown")
        self.assertEqual(len(md_chunks), 1)
        self.assertEqual(md_chunks[0].status, "unsupported_language_fallback")

    def test_benchmark_and_cli_and_zero_emoji_policy(self):
        result = ast_chunker.run_benchmark()
        self.assertGreater(result["ast_structural"]["recall_at_3"], result["fixed_40_lines"]["recall_at_3"])
        self.assertGreater(
            result["ast_structural"]["cohesive_structure_rate"],
            result["fixed_40_lines"]["cohesive_structure_rate"],
        )
        self.assertEqual(result["ast_structural"]["recall_at_3"], 1.0)
        self.assertEqual(result["ast_structural"]["cohesive_structure_rate"], 1.0)
        self.assertGreaterEqual(result["ast_structural"]["motion_contracts_extracted"], 5)

        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "ast_chunker.py"), "benchmark"],
            capture_output=True,
            text=True,
            check=True,
        )
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["extractor_version"], ast_chunker.EXTRACTOR_VERSION)

        report_path = ROOT / "reports" / "AST-CHUNKING-BENCHMARK.md"
        self.assertTrue(report_path.is_file())
        report_text = report_path.read_text(encoding="utf-8")
        for keyword in ("CocoIndex", "ast-grep", "Probe", "sqry", "SCIP", "UI-MOTION-EVIDENCE"):
            self.assertIn(keyword, report_text)

        for path in (SCRIPTS_DIR / "ast_chunker.py", report_path, Path(__file__)):
            content = path.read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(content), [], f"Found disallowed emoji in {path}")


if __name__ == "__main__":
    unittest.main()
