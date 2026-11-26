#!/usr/bin/env python3
"""Tests for federated multidomain retrieval (#81)."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ast_chunker  # noqa: E402
import concept_packs  # noqa: E402
import domain_ontology  # noqa: E402
import evidence_graph  # noqa: E402
import federated_retrieval as fr  # noqa: E402
import knowledge_indexer  # noqa: E402
import research_index  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


def _build_authenticated_fixtures() -> tuple[sqlite3.Connection, sqlite3.Connection, list[dict], list[dict], list[dict]]:
    # 1. Knowledge index (ADRs + glossary)
    k_conn = sqlite3.connect(":memory:")
    k_conn.row_factory = sqlite3.Row
    k_conn.executescript(knowledge_indexer.SCHEMA_SQL)
    knowledge_indexer.seed_canonical_knowledge(k_conn)

    # 2. Evidence graph
    e_conn = evidence_graph.open_db(Path(":memory:"))
    tsx_src = (
        "export function AppHeaderTabs() {\n"
        "  const [pinnedTabs, setPinnedTabs] = useState([]);\n"
        "  const togglePin = () => setPinnedTabs(prev => prev);\n"
        "  return <button onClick={togglePin} data-pinned='true'>Fixar</button>;\n"
        "}\n"
    )
    evidence_graph.ingest_tsx_file(
        e_conn,
        "src/app/_components/workspace/app-header-tabs.tsx",
        tsx_src,
        repo="notes-app",
        ref="refs/heads/old-5",
        commit_sha="4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
    )
    evidence_graph.build_canonical_notes_evidence(e_conn)

    # 3. AST chunks (code + test)
    code_bsha = ast_chunker.compute_git_blob_sha(tsx_src)
    chunks = ast_chunker.chunk_code(tsx_src, language="tsx", blob_sha=code_bsha)
    ast_items = [
        {
            **c.to_dict(),
            "repo": "notes-app",
            "ref": "refs/heads/old-5",
            "commit_sha": "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
            "path": "src/app/_components/workspace/app-header-tabs.tsx",
            "provenance_status": "verified",
        }
        for c in chunks
    ]
    test_src = "def test_pin_tab_toggle():\n    assert togglePin('tab-1')['pinned'] is True\n"
    ast_items.append(
        {
            "node_type": "function",
            "name": "test_pin_tab_toggle",
            "parent_context": "module",
            "content": test_src,
            "blob_sha": ast_chunker.compute_git_blob_sha(test_src),
            "chunk_sha": fr.sha256_text(test_src),
            "symbol_id": "py:test_pin_tab_toggle",
            "repo": "notes-app",
            "ref": "refs/heads/old-5",
            "commit_sha": "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
            "path": "tests/test_app_header_tabs.py",
            "provenance_status": "verified",
        }
    )

    # 4. Image catalog records
    images = [
        {
            "repo": "notes-app",
            "ref": "refs/heads/old-5",
            "commit": "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
            "path": "docs/captures/app-header-tabs-pin.png",
            "screen": "app-header-tabs",
            "blob_sha": "a" * 40,
            "sha256": "11" * 32,
            "format": "png",
            "bytes": 42000,
            "dimensions": {"width": 1280, "height": 720},
            "status": "present",
            "deleted": False,
        }
    ]

    # 5. Requirement/spec documents
    docs = [
        {
            "repo": "notes-app",
            "ref": "refs/heads/old-5",
            "commit_sha": "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
            "path": "openspec/specs/ui/app-header/spec.md",
            "element_id": "req-pin-tab",
            "title": "REQ-01: Pin Tab in Header",
            "content": "Requirement: Users can pin tab with togglePin and keep pinned tabs visible in AppHeaderTabs.",
            "evidence_type": "requirement",
            "domain": "workspace",
            "blob_sha": "cc44dd55ee66ff77889900112233445566778899",
            "doc_sha256": "22" * 32,
            "version": "1.0.0",
            "provenance_status": "verified",
        }
    ]

    return k_conn, e_conn, ast_items, images, docs


class FederatedRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = research_index.load_records()
        cls.taxonomy = concept_packs.load_taxonomy()
        cls.ontology = domain_ontology.DomainOntology()

    def test_strict_scope_isolation_public_never_touches_private(self) -> None:
        k_conn, e_conn, ast_items, images, docs = _build_authenticated_fixtures()
        try:
            # Even if an authenticated context is erroneously passed, scope='public' MUST NOT read it
            poisoned_auth = fr.AuthenticatedArchiveContext(
                authorized=True,
                provenance_verified=True,
                knowledge_conn=k_conn,
                evidence_conn=e_conn,
                ast_chunks=ast_items,
                image_records=images,
                documents=docs,
            )
            res = fr.federated_search(
                "pin tab",
                scope="public",
                budget_tokens=3000,
                auth_context=poisoned_auth,
                public_records=self.records,
                public_taxonomy=self.taxonomy,
                ontology=self.ontology,
            )
            self.assertEqual(res["scope"], "public")
            self.assertEqual(res["status"], "ok")
            for item in res["results"]:
                self.assertEqual(item["scope"], "public")
                self.assertNotIn(
                    item["source_channel"],
                    {"knowledge_decisions", "evidence_graph", "ast_code", "image_catalog", "content_archive"},
                )
            omitted_ids = {o["source_id"] for o in res["sources_omitted"]}
            self.assertIn("authenticated_archive", omitted_ids)
            self.assertIn("knowledge_decisions", omitted_ids)
        finally:
            k_conn.close()
            e_conn.close()

    def test_authenticated_archive_requires_authorization_and_valid_pins(self) -> None:
        # Missing auth context -> fail closed
        denied_missing = fr.federated_search("pin tab", scope="authenticated_archive", budget_tokens=2000)
        self.assertEqual(denied_missing["status"], "authorization-denied")
        self.assertEqual(denied_missing["results"], [])

        # authorized=False -> fail closed
        denied_unauth = fr.federated_search(
            "pin tab",
            scope="authenticated_archive",
            auth_context=fr.AuthenticatedArchiveContext(authorized=False, provenance_verified=True),
        )
        self.assertEqual(denied_unauth["status"], "authorization-denied")

        # Bad checksum pin -> fail closed
        bad_pin = fr.federated_search(
            "pin tab",
            scope="authenticated_archive",
            auth_context=fr.AuthenticatedArchiveContext(
                authorized=True,
                provenance_verified=True,
                expected_index_checksum="a" * 64,
                actual_index_checksum="b" * 64,
            ),
        )
        self.assertEqual(bad_pin["status"], "authorization-denied")
        self.assertTrue(any("index_digest_mismatch" in g for g in bad_pin["gaps"]))

    def test_authenticated_multidomain_fusion_and_evidence_diversity(self) -> None:
        k_conn, e_conn, ast_items, images, docs = _build_authenticated_fixtures()
        try:
            auth_ctx = fr.AuthenticatedArchiveContext(
                authorized=True,
                provenance_verified=True,
                pinned_repo="notes-app",
                pinned_source_sha="4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
                expected_index_checksum="c" * 64,
                actual_index_checksum="c" * 64,
                knowledge_conn=k_conn,
                evidence_conn=e_conn,
                ast_chunks=ast_items,
                image_records=images,
                documents=docs,
            )
            res = fr.federated_search(
                "pin tab togglePin",
                scope="authenticated_archive",
                budget_tokens=6000,
                intent="mixed",
                limit=20,
                auth_context=auth_ctx,
                ontology=self.ontology,
            )
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["ranking_method"], "rrf_bm25_diversity")
            returned_types = set(res["returned_by_type"].keys())
            # Must cover diverse modalities across decisions, code, requirements, tests, media, concepts
            self.assertTrue({"decision", "code", "requirement", "test", "media"}.issubset(returned_types), returned_types)

            # Every result must have RRF and BM25 scores and provenance
            for item in res["results"]:
                self.assertIn("rrf_score", item)
                self.assertIn("bm25_score", item)
                self.assertIn("fused_score", item)
                self.assertTrue(item["occurrences"])
                self.assertTrue(item["dedup_key"])
        finally:
            k_conn.close()
            e_conn.close()

    def test_rrf_and_bm25_deterministic_scoring(self) -> None:
        scores = fr.compute_bm25_scores(
            ["sidebar", "toggle"],
            ["sidebar toggle pin component", "unrelated document about weather", "sidebar"],
        )
        self.assertGreater(scores[0], scores[2])
        self.assertEqual(scores[1], 0.0)

        fused = fr.reciprocal_rank_fusion({
            "bm25": ["docA", "docB", "docC"],
            "graph": ["docB", "docA"],
        })
        # docA and docB appear in both lists so they outrank docC
        self.assertGreater(fused["docA"], fused["docC"])
        self.assertGreater(fused["docB"], fused["docC"])

    def test_exact_blob_deduplication_retains_all_occurrences(self) -> None:
        k_conn, e_conn, ast_items, images, docs = _build_authenticated_fixtures()
        try:
            shared_blob = "deadbeef" * 5
            dup_docs = [
                {
                    "repo": "notes-app",
                    "ref": "refs/heads/old-5",
                    "commit_sha": "1" * 40,
                    "path": "docs/a.md",
                    "element_id": "e1",
                    "title": "Pin Tab Spec A",
                    "content": "Requirement pin tab behavior identical blob",
                    "evidence_type": "requirement",
                    "blob_sha": shared_blob,
                    "doc_sha256": "33" * 32,
                    "provenance_status": "verified",
                },
                {
                    "repo": "notes-app",
                    "ref": "refs/heads/main",
                    "commit_sha": "2" * 40,
                    "path": "docs/b.md",
                    "element_id": "e2",
                    "title": "Pin Tab Spec B",
                    "content": "Requirement pin tab behavior identical blob",
                    "evidence_type": "requirement",
                    "blob_sha": shared_blob,
                    "doc_sha256": "33" * 32,
                    "provenance_status": "verified",
                },
            ]
            auth_ctx = fr.AuthenticatedArchiveContext(
                authorized=True,
                provenance_verified=True,
                knowledge_conn=k_conn,
                documents=dup_docs,
            )
            res = fr.federated_search(
                "identical blob requirement",
                scope="authenticated_archive",
                intent="requirement",
                budget_tokens=4000,
                auth_context=auth_ctx,
                ontology=self.ontology,
            )
            self.assertGreaterEqual(res["deduplicated_occurrences"], 1)
            matching = [r for r in res["results"] if r["provenance"].get("blob_sha") == shared_blob]
            self.assertEqual(len(matching), 1)
            self.assertEqual(len(matching[0]["occurrences"]), 2)
            paths = {occ["path"] for occ in matching[0]["occurrences"]}
            self.assertEqual(paths, {"docs/a.md", "docs/b.md"})
        finally:
            k_conn.close()
            e_conn.close()

    def test_strict_token_budget_and_audit_ledger(self) -> None:
        res = fr.federated_search(
            "barra lateral",
            scope="public",
            budget_tokens=700,
            limit=20,
            public_records=self.records,
            public_taxonomy=self.taxonomy,
            ontology=self.ontology,
        )
        self.assertLessEqual(res["budget"]["total_tokens"], 700)
        self.assertTrue(res["sources_consulted"])
        self.assertTrue(res["sources_omitted"])
        if res["omitted_for_budget"]:
            self.assertTrue(any(g.startswith("budget_truncated:") for g in res["gaps"]))

    def test_intent_routing_and_cli(self) -> None:
        self.assertEqual(fr.detect_intent("Qual ADR decidiu o app shell?")["primary"], "decision")
        self.assertEqual(fr.detect_intent("Show me the screenshot GIF of motion")["primary"], "media")
        self.assertEqual(fr.detect_intent("Which tests verify regression?")["primary"], "test")

        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "federated_retrieval.py"), "sortable list", "--scope", "public", "--budget-tokens", "1800"],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["scope"], "public")
        self.assertLessEqual(payload["budget"]["total_tokens"], 1800)

    def test_zero_emoji_compliance(self) -> None:
        for p in (SCRIPTS_DIR / "federated_retrieval.py", Path(__file__).resolve()):
            text = p.read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(text), [], f"Emoji found in {p}")


if __name__ == "__main__":
    unittest.main()
