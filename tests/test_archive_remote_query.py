#!/usr/bin/env python3
"""Test GitHub-based private FTS5 request bridge using synthetic data."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import context_linker
import graph_linker

RUNNER = ROOT / "scripts/archive_remote_query.py"
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class RemoteQueryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.requests = self.dir / "requests"
        self.results = self.dir / "results"
        self.requests.mkdir()
        self.db = self.dir / "index.sqlite"

        # Create sample TSX component for AST tests
        self.sample_tsx = self.dir / "SidebarPeek.tsx"
        self.sample_tsx.write_text(
            "import React, { useState } from 'react';\n"
            "export function SidebarPeek() {\n"
            "  const [open, setOpen] = useState(false);\n"
            "  const handleMouseEnter = () => {\n"
            "    setTimeout(() => setOpen(true), 300);\n"
            "  };\n"
            "  return <aside onMouseEnter={handleMouseEnter} className='transition-all duration-200 ease-out'>{String(open)}</aside>;\n"
            "}\n",
            encoding="utf-8",
        )

        with sqlite3.connect(self.db) as c:
            # Legacy tables
            c.executescript("""
            CREATE TABLE repositories(id INTEGER PRIMARY KEY,name TEXT);
            CREATE TABLE commits(repo_id INTEGER,sha TEXT,date TEXT,subject TEXT);
            CREATE TABLE changes(repo_id INTEGER,sha TEXT,status TEXT,path TEXT,previous_path TEXT);
            CREATE TABLE images(repo_id INTEGER,path TEXT,blob TEXT,commit_sha TEXT,kind TEXT,bytes INTEGER);
            CREATE VIRTUAL TABLE commit_fts USING fts5(subject,repo_id UNINDEXED,sha UNINDEXED);
            CREATE VIRTUAL TABLE change_fts USING fts5(path,repo_id UNINDEXED,sha UNINDEXED,status UNINDEXED);

            INSERT INTO repositories VALUES(1,'exams-app-antigo-2');
            INSERT INTO commits VALUES(1,'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','2026-01-01','Grafo antigo');
            INSERT INTO commit_fts VALUES('Grafo antigo','1','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
            INSERT INTO changes VALUES(1,'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','D','docs/grafo.png','');
            INSERT INTO change_fts VALUES('docs/grafo.png','1','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','D');
            INSERT INTO images VALUES(1,'docs/grafo.png','bbbb','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','deleted',42);

            -- Content Index tables
            CREATE TABLE content_occurrences(
                repo TEXT,
                ref TEXT,
                commit_sha TEXT,
                path TEXT,
                extension TEXT,
                language TEXT,
                blob_sha TEXT,
                status TEXT,
                previous_path TEXT,
                commit_author TEXT,
                commit_date TEXT
            );
            CREATE VIRTUAL TABLE content_fts USING fts5(
                blob_sha UNINDEXED,
                start_line UNINDEXED,
                end_line UNINDEXED,
                content
            );
            INSERT INTO content_occurrences VALUES(
                'exams-app', 'refs/heads/main', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                'src/sidebar.tsx', '.tsx', 'tsx', 'cccccccccccccccccccccccccccccccccccccccc', 'A',
                '', 'Ian', '2026-11-20T00:00:00Z'
            );
            INSERT INTO content_fts VALUES(
                'cccccccccccccccccccccccccccccccccccccccc', 1, 10,
                'export function Sidebar() { return <aside>Sidebar navigation panel</aside>; }'
            );
            """)

            # Context Linker tables & data
            c.executescript(context_linker.DB_SCHEMA)
            c.execute(
                "INSERT INTO ctx_sources(source_key, source_type, repo, location, imported_at) "
                "VALUES ('exams-app', 'git', 'exams-app', 'https://github.com/ianmaciel7/exams-app', '2026-11-20')"
            )
            c.execute(
                "INSERT INTO ctx_commit_files(repo, commit_sha, ref, date, path, previous_path, status, blob_sha, patch, blob_url, origin_file) "
                "VALUES ('exams-app', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'main', '2026-11-20', 'src/sidebar.tsx', '', 'A', 'cccccccccccccccccccccccccccccccccccccccc', '@@ -0,0 +1,10 @@\n+export function Sidebar()', 'https://github.com/...', 'commits/1.json')"
            )
            c.execute(
                "INSERT INTO ctx_items(repo, kind, number, title, body, state, author, created_at, updated_at, merged_at, head_ref, head_sha, base_ref, base_sha, merge_commit_sha, html_url, origin_file) "
                "VALUES ('exams-app', 'pull_request', 1, 'Add sidebar navigation', 'Implements collapsible sidebar', 'closed', 'ian', '2026-11-20', '2026-11-20', '2026-11-20', 'feat/sidebar', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'main', '1111111111111111111111111111111111111111', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'https://github.com/ianmaciel7/exams-app/pull/1', 'pulls/1.json')"
            )
            c.execute(
                "INSERT INTO ctx_links(link_uid, repo, pr_number, commit_sha, ref, path, image_path, link_type, origin_url, origin_file) "
                "VALUES ('lnk:1', 'exams-app', 1, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'main', 'src/sidebar.tsx', '', 'modifies', 'https://github.com/...', 'links.json')"
            )

            # Graph Linker tables & data
            c.executescript(graph_linker.DB_SCHEMA)
            c.execute(
                "INSERT OR REPLACE INTO graph_nodes (node_id, node_type, repo, ref, label, path, commit_sha, timestamp, validity_status, metadata_json) "
                "VALUES ('cmp:Sidebar', 'component', 'exams-app', 'main', 'Sidebar', 'src/sidebar.tsx', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '2026-11-20', 'verified', '{}')"
            )
            c.execute(
                "INSERT OR REPLACE INTO graph_nodes (node_id, node_type, repo, ref, label, path, commit_sha, timestamp, validity_status, metadata_json) "
                "VALUES ('file:src/sidebar.tsx', 'file', 'exams-app', 'main', 'src/sidebar.tsx', 'src/sidebar.tsx', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '2026-11-20', 'verified', '{}')"
            )
            c.execute(
                "INSERT OR REPLACE INTO graph_edges (edge_id, src_id, dst_id, edge_type, confidence, repo, ref, commit_sha, timestamp, weight, provenance_json) "
                "VALUES ('e1', 'cmp:Sidebar', 'file:src/sidebar.tsx', 'defined_in', 'EXTRACTED', 'exams-app', 'main', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', '2026-11-20', 1.0, '{}')"
            )

    def write_request(self, identifier="test-grafo-01", **changes):
        obj = {"version": 1, "id": identifier, "operation": "search", "query": "grafo"}
        obj.update(changes)
        path = self.requests / (identifier + ".json")
        path.write_text(json.dumps(obj), encoding="utf-8")
        return path

    def execute(self):
        return subprocess.run([
            sys.executable, str(RUNNER), "--root", str(ROOT),
            "--requests", str(self.requests), "--results", str(self.results),
            "--db", str(self.db), "--offline"
        ], capture_output=True, text=True)

    def test_search_and_idempotent_result(self):
        self.write_request()
        first = self.execute()
        self.assertEqual(first.returncode, 0, first.stderr)
        obj = json.loads((self.results / "test-grafo-01.json").read_text(encoding="utf-8"))
        self.assertTrue(obj["ok"], obj)
        self.assertEqual({r["kind"] for r in obj["results"]}, {"commit", "file", "image"})
        self.assertTrue(all(r["sha"] == "a" * 40 for r in obj["results"]))
        self.assertEqual(obj["index_release"], "offline-test")
        again = self.execute()
        self.assertEqual(json.loads(again.stdout)["processed"], 0)

    def test_deleted_images(self):
        self.write_request(identifier="test-images-01", operation="images",
                           repo="exams-app-antigo-2", deleted_only=True, query=None)
        path = self.requests / "test-images-01.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        del obj["query"]
        path.write_text(json.dumps(obj), encoding="utf-8")
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-images-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)
        self.assertEqual(doc["results"][0]["path"], "docs/grafo.png")

    def test_legacy_stats_operation(self):
        self.write_request(identifier="test-stats-01", operation="stats", query=None)
        path = self.requests / "test-stats-01.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        del obj["query"]
        path.write_text(json.dumps(obj), encoding="utf-8")
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-stats-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)
        self.assertIsInstance(doc["results"], list)
        self.assertEqual(doc["results"][0]["repository"], "exams-app-antigo-2")

    def test_bad_data_yields_error_not_crash(self):
        self.write_request(identifier="test-invalid-01", query="a" * 150)
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-invalid-01.json").read_text(encoding="utf-8"))
        self.assertFalse(doc["ok"])
        self.assertIn("120", doc["error"])

    def test_pending_batch_status_and_retention_pruning(self):
        self.write_request(identifier="test-batch-01")
        self.write_request(identifier="test-batch-02")
        self.write_request(identifier="test-batch-03")
        p1 = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--root",
                str(ROOT),
                "--requests",
                str(self.requests),
                "--results",
                str(self.results),
                "--db",
                str(self.db),
                "--offline",
                "--batch-limit",
                "2",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p1.returncode, 0, p1.stderr)
        meta1 = json.loads(p1.stdout)
        self.assertEqual(meta1["processed"], 2)
        self.assertEqual(meta1["pending_remaining"], 1)
        self.assertEqual(meta1["status"], "pending")

        p2 = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--root",
                str(ROOT),
                "--requests",
                str(self.requests),
                "--results",
                str(self.results),
                "--db",
                str(self.db),
                "--offline",
                "--batch-limit",
                "2",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p2.returncode, 0, p2.stderr)
        meta2 = json.loads(p2.stdout)
        self.assertEqual(meta2["processed"], 1)
        self.assertEqual(meta2["pending_remaining"], 0)
        self.assertEqual(meta2["status"], "complete")

        # Mark test-batch-01 pair older than 14 days and prune
        import os
        import time
        old_ts = time.time() - (20 * 86400)
        for p in (self.requests / "test-batch-01.json", self.results / "test-batch-01.json"):
            os.utime(p, (old_ts, old_ts))
        p3 = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--root",
                str(ROOT),
                "--requests",
                str(self.requests),
                "--results",
                str(self.results),
                "--db",
                str(self.db),
                "--offline",
                "--retention-days",
                "14",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(p3.returncode, 0, p3.stderr)
        meta3 = json.loads(p3.stdout)
        self.assertEqual(meta3["pruned"], 1)
        self.assertFalse((self.requests / "test-batch-01.json").exists())
        self.assertFalse((self.results / "test-batch-01.json").exists())
        self.assertTrue((self.requests / "test-batch-02.json").exists())

    def test_content_search_operation_and_filters(self):
        self.write_request(
            identifier="test-content-01",
            operation="content_search",
            query="sidebar",
            repo="exams-app",
            language="tsx",
            limit=5,
        )
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-content-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)
        self.assertGreater(len(doc["results"]), 0)
        hit = doc["results"][0]
        self.assertEqual(hit["repository"], "exams-app")
        self.assertEqual(hit["language"], "tsx")
        self.assertEqual(hit["path"], "src/sidebar.tsx")
        self.assertIn("Sidebar navigation", hit["snippet"])
        self.assertIn("source_trace", doc)
        self.assertTrue(any("src/sidebar.tsx" in t for t in doc["source_trace"]))

    def test_linked_context_operation(self):
        self.write_request(
            identifier="test-linked-ctx-01",
            operation="linked_context",
            query="sidebar",
            repo="exams-app",
            limit=10,
        )
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-linked-ctx-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)
        self.assertIn("files", doc["results"])
        files = doc["results"]["files"]
        self.assertGreater(len(files), 0)
        self.assertEqual(files[0]["path"], "src/sidebar.tsx")
        self.assertEqual(files[0]["repo"], "exams-app")

    def test_context_pack_operation_with_budget(self):
        self.write_request(
            identifier="test-ctx-pack-01",
            operation="context_pack",
            query="sidebar",
            repo="exams-app",
            token_budget=1500,
            max_lines=50,
            max_bytes=10000,
        )
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-ctx-pack-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)
        pack = doc["results"]
        self.assertIn("items", pack)
        self.assertIn("usage", pack)
        self.assertLessEqual(pack["usage"].get("total_estimated_tokens", 0), 1500)

    def test_get_evidence_operation(self):
        self.write_request(
            identifier="test-evidence-01",
            operation="get_evidence",
            path="src/sidebar.tsx",
            source_sha="cccccccccccccccccccccccccccccccccccccccc",
            query=None,
        )
        path = self.requests / "test-evidence-01.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        del obj["query"]
        path.write_text(json.dumps(obj), encoding="utf-8")

        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-evidence-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)
        evidence = doc["results"]
        self.assertEqual(evidence["path"], "src/sidebar.tsx")
        self.assertIn("Sidebar navigation panel", evidence["content"])
        self.assertEqual(evidence["bytes"], len(evidence["content"].encode("utf-8")))
        self.assertEqual(evidence["sha256"], hashlib.sha256(evidence["content"].encode("utf-8")).hexdigest())

    def test_coverage_operation(self):
        self.write_request(
            identifier="test-coverage-01",
            operation="coverage",
            query=None,
        )
        path = self.requests / "test-coverage-01.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        del obj["query"]
        path.write_text(json.dumps(obj), encoding="utf-8")

        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-coverage-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)
        cov = doc["results"]
        self.assertIn("indexed_refs", cov)
        self.assertIn("inspected_refs", cov)
        self.assertIn("uninspected_gaps", cov)
        self.assertIn("repositories", cov)

    def test_ast_chunks_operation(self):
        self.write_request(
            identifier="test-ast-01",
            operation="ast_chunks",
            path=str(self.sample_tsx),
            language="tsx",
            max_lines=40,
            query=None,
        )
        path = self.requests / "test-ast-01.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        del obj["query"]
        path.write_text(json.dumps(obj), encoding="utf-8")

        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-ast-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)
        ast_res = doc["results"]
        self.assertEqual(ast_res["language"], "tsx")
        self.assertGreater(ast_res["chunk_count"], 0)
        names = {c.get("name") for c in ast_res["chunks"]}
        self.assertIn("SidebarPeek", names)

    def test_graph_neighbors_operation(self):
        self.write_request(
            identifier="test-graph-01",
            operation="graph_neighbors",
            concept_id="cmp:Sidebar",
            hops=2,
            edge_type="defined_in",
            query=None,
        )
        path = self.requests / "test-graph-01.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        del obj["query"]
        path.write_text(json.dumps(obj), encoding="utf-8")

        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-graph-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)
        graph_res = doc["results"]
        self.assertIn("nodes", graph_res)
        self.assertIn("edges", graph_res)
        node_ids = {n.get("node_id") or n.get("id") for n in graph_res["nodes"]}
        self.assertIn("cmp:Sidebar", node_ids)

    def test_security_gate_sanitization(self):
        # Insert a secret into content index
        with sqlite3.connect(self.db) as c:
            c.execute(
                "INSERT INTO content_occurrences VALUES('exams-app', 'refs/heads/main', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'src/auth.ts', '.ts', 'typescript', 'secretblob', 'A', '', 'Ian', '2026-11-20T00:00:00Z')"
            )
            c.execute(
                "INSERT INTO content_fts VALUES('secretblob', 1, 5, 'const AWS_KEY = \"AKIASYNTHETIC1234567\"; const PAT = \"ghp_syntheticTestClassicToken123456789012\";')"
            )

        self.write_request(
            identifier="test-secret-sanitize-01",
            operation="content_search",
            query="AWS_KEY",
        )
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        raw_output = (self.results / "test-secret-sanitize-01.json").read_text(encoding="utf-8")
        doc = json.loads(raw_output)
        self.assertTrue(doc["ok"], doc)

        # Raw secrets must NEVER be present in the output JSON
        self.assertNotIn("AKIASYNTHETIC1234567", raw_output)
        self.assertNotIn("ghp_syntheticTestClassicToken123456789012", raw_output)

        # Redaction marker must be present
        self.assertIn("[REDACTED", raw_output)
        self.assertGreater(doc.get("secrets_sanitized", 0), 0)

    def test_security_gate_sensitive_path_blocking(self):
        self.write_request(
            identifier="test-secret-block-01",
            operation="content_search",
            query="password",
            path=".env",
        )
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-secret-block-01.json").read_text(encoding="utf-8"))
        self.assertFalse(doc["ok"])
        self.assertIn("Blocked by secrets gate", doc["error"])

    def test_metadata_and_checksum_validation(self):
        self.write_request(
            identifier="test-meta-check-01",
            operation="content_search",
            query="sidebar",
        )
        res = self.execute()
        self.assertEqual(res.returncode, 0, res.stderr)
        doc = json.loads((self.results / "test-meta-check-01.json").read_text(encoding="utf-8"))
        self.assertTrue(doc["ok"], doc)

        # 1. extractor_version
        self.assertEqual(doc["extractor_version"], "1.0.0")

        # 2. release_id
        self.assertEqual(doc["release_id"], "offline-test")

        # 3. checksum matches SHA-256 of payload
        computed_checksum = hashlib.sha256(
            json.dumps(doc["results"], sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.assertEqual(doc["checksum"], computed_checksum)

        # 4. coverage (indexed_refs, inspected_refs, uninspected_gaps)
        cov = doc["coverage"]
        self.assertIn("indexed_refs", cov)
        self.assertIn("inspected_refs", cov)
        self.assertIn("uninspected_gaps", cov)
        self.assertIn("refs/heads/main", cov["inspected_refs"])

        # 5. source_trace
        traces = doc["source_trace"]
        self.assertIsInstance(traces, list)
        self.assertGreater(len(traces), 0)
        trace_re = re.compile(r"^.+/.+/[0-9a-fA-F]{7,64}/.*:\d+-\d+$")
        for tr in traces:
            self.assertTrue(trace_re.match(tr), f"Invalid trace format: {tr}")

    def test_zero_emoji_policy(self):
        for script_name in ("scripts/archive_remote_query.py", "tests/test_archive_remote_query.py"):
            target_path = ROOT / script_name
            content = target_path.read_text(encoding="utf-8")
            matches = EMOJI_REGEX.findall(content)
            self.assertEqual(matches, [], f"Found emojis in {script_name}: {matches}")


if __name__ == "__main__":
    unittest.main()
