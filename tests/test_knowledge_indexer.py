#!/usr/bin/env python3
"""Unit tests for scripts/knowledge_indexer.py.

Validates:
  - ADR parsing from markdown, sections, tables, and commit bodies.
  - Decision status mapping, temporal validity, and 'not-recovered' tracking.
  - Multilingual PT/EN glossary concept extraction, relationship tagging,
    and explicit UI/domain disambiguation (pin tab vs pinned sidebar entity).
  - Ambiguous query expansion into candidate groups partitioned by concept_id.
  - CLI invocations and JSON exports.
  - Zero Emoji Policy: Absolutely NO Unicode emojis [\\U00010000-\\U0010ffff].
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import knowledge_indexer as ki  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


class KnowledgeIndexerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test_knowledge.sqlite"
        self.conn = ki.open_knowledge_db(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_canonical_concepts_and_relationships(self):
        """Verify that all core concepts and semantic relationships are seeded."""
        concepts = ki.list_glossary(self.conn)
        concept_ids = {c["concept_id"] for c in concepts}

        expected_concepts = {
            "ui.tabs.pin_tab",
            "ui.sidebar.pinned_entity",
            "domain.object.pin_type",
            "ui.favorites",
            "domain.space",
            "domain.workspace",
            "domain.question",
            "domain.flashcard",
            "domain.simulado",
            "ui.graph",
            "domain.grafo",
            "ui.sidebar.peek",
            "ui.sidebar.collapse",
        }
        self.assertTrue(expected_concepts.issubset(concept_ids))

        # Verify semantic relationship types exist in glossary
        all_relationships = set()
        for c in concepts:
            for t in c["terms"]:
                all_relationships.add(t["relationship"])

        self.assertIn("same-as", all_relationships)
        self.assertIn("alias", all_relationships)
        self.assertIn("related", all_relationships)
        self.assertIn("conflicts-with", all_relationships)
        self.assertIn("ambiguous-with", all_relationships)

    def test_disambiguation_pin_tab_vs_pinned_sidebar(self):
        """Acceptance Criteria 1: 'fixar uma aba', 'pin tab', 'fixar objeto', 'fixados sidebar'

        Recovers and distinguishes implementations and applicable decisions.
        """
        # 1. 'fixar uma aba' -> ui.tabs.pin_tab (app-header-tabs.tsx)
        res_fixar_aba = ki.query_knowledge(self.conn, "fixar uma aba")
        self.assertFalse(res_fixar_aba["is_ambiguous"])
        self.assertEqual(res_fixar_aba["concept"]["concept_id"], "ui.tabs.pin_tab")
        self.assertIn("app-header-tabs.tsx", res_fixar_aba["concept"]["implementation_file"])
        self.assertEqual(res_fixar_aba["concept"]["implementation_sha"], "4eb93c5013c27ba6724b4f116cc9fe5846398eb8")
        dec_ids_aba = [d["decision_id"] for d in res_fixar_aba["concept"]["applicable_decisions"]]
        self.assertIn("DEC-APP-SHELL-01", dec_ids_aba)

        # 2. 'pin tab' -> ui.tabs.pin_tab
        res_pin_tab = ki.query_knowledge(self.conn, "pin tab")
        self.assertFalse(res_pin_tab["is_ambiguous"])
        self.assertEqual(res_pin_tab["concept"]["concept_id"], "ui.tabs.pin_tab")

        # 3. 'fixados sidebar' -> ui.sidebar.pinned_entity (app-sidebar-overview.tsx)
        res_fixados_sidebar = ki.query_knowledge(self.conn, "fixados sidebar")
        self.assertFalse(res_fixados_sidebar["is_ambiguous"])
        self.assertEqual(res_fixados_sidebar["concept"]["concept_id"], "ui.sidebar.pinned_entity")
        self.assertIn("app-sidebar-overview.tsx", res_fixados_sidebar["concept"]["implementation_file"])
        self.assertEqual(res_fixados_sidebar["concept"]["implementation_sha"], "a020d635de368b755992e1282e18af9fdc2b8a03")
        dec_ids_sidebar = [d["decision_id"] for d in res_fixados_sidebar["concept"]["applicable_decisions"]]
        self.assertIn("DEC-SIDEBAR-PROTOTIPO-01", dec_ids_sidebar)

        # 4. 'fixar objeto' -> domain.object.pin_type
        res_fixar_obj = ki.query_knowledge(self.conn, "fixar objeto")
        self.assertFalse(res_fixar_obj["is_ambiguous"])
        self.assertEqual(res_fixar_obj["concept"]["concept_id"], "domain.object.pin_type")

        # 5. Ambiguous query 'fixar' -> returns candidate groups partitioned by concept_id
        res_ambiguous_fixar = ki.query_knowledge(self.conn, "fixar")
        self.assertTrue(res_ambiguous_fixar["is_ambiguous"])
        cg_ids = [cg["concept_id"] for cg in res_ambiguous_fixar["candidate_groups"]]
        self.assertIn("ui.tabs.pin_tab", cg_ids)
        self.assertIn("ui.sidebar.pinned_entity", cg_ids)
        self.assertIn("domain.object.pin_type", cg_ids)

        # 6. Ambiguous query 'pin' -> returns candidate groups partitioned by concept_id
        res_ambiguous_pin = ki.query_knowledge(self.conn, "pin")
        self.assertTrue(res_ambiguous_pin["is_ambiguous"])
        cg_ids_pin = [cg["concept_id"] for cg in res_ambiguous_pin["candidate_groups"]]
        self.assertIn("ui.tabs.pin_tab", cg_ids_pin)
        self.assertIn("ui.sidebar.pinned_entity", cg_ids_pin)
        self.assertIn("domain.object.pin_type", cg_ids_pin)

    def test_disambiguation_domain_and_ui_concepts(self):
        """Test distinction between domain.space vs workspace, question vs flashcard vs simulado,

        graph vs grafo, and peek vs collapse.
        """
        # space vs workspace (domain.space now has verified real SHA)
        res_space = ki.query_knowledge(self.conn, "espaco")
        self.assertEqual(res_space["concept"]["concept_id"], "domain.space")
        self.assertEqual(
            res_space["concept"]["implementation_sha"],
            "d811241f0a0f694694d35e4636ed46d2e38478c9",
        )
        self.assertEqual(res_space["concept"]["provenance_status"], "verified")
        self.assertTrue(res_space["concept"]["verified"])

        res_ws = ki.query_knowledge(self.conn, "workspace")
        self.assertEqual(res_ws["concept"]["concept_id"], "domain.workspace")
        self.assertEqual(res_ws["concept"]["provenance_status"], "verified")
        self.assertTrue(res_ws["concept"]["verified"])

        # question vs flashcard vs simulado (unverified provenance, implementation_sha is None)
        res_q = ki.query_knowledge(self.conn, "questao")
        self.assertEqual(res_q["concept"]["concept_id"], "domain.question")
        self.assertIsNone(res_q["concept"]["implementation_sha"])
        self.assertEqual(res_q["concept"]["provenance_status"], "unverified")
        self.assertFalse(res_q["concept"]["verified"])

        res_fc = ki.query_knowledge(self.conn, "flashcard")
        self.assertEqual(res_fc["concept"]["concept_id"], "domain.flashcard")
        self.assertIsNone(res_fc["concept"]["implementation_sha"])
        self.assertEqual(res_fc["concept"]["provenance_status"], "unverified")
        self.assertFalse(res_fc["concept"]["verified"])

        res_sim = ki.query_knowledge(self.conn, "simulado")
        self.assertEqual(res_sim["concept"]["concept_id"], "domain.simulado")
        self.assertIsNone(res_sim["concept"]["implementation_sha"])
        self.assertEqual(res_sim["concept"]["provenance_status"], "unverified")
        self.assertFalse(res_sim["concept"]["verified"])

        # ui.graph vs domain.grafo (unverified provenance, implementation_sha is None)
        res_ui_graph = ki.query_knowledge(self.conn, "visualizacao em grafo")
        self.assertEqual(res_ui_graph["concept"]["concept_id"], "ui.graph")
        self.assertIsNone(res_ui_graph["concept"]["implementation_sha"])
        self.assertEqual(res_ui_graph["concept"]["provenance_status"], "unverified")
        self.assertFalse(res_ui_graph["concept"]["verified"])

        res_dom_graph = ki.query_knowledge(self.conn, "grafo de conhecimento")
        self.assertEqual(res_dom_graph["concept"]["concept_id"], "domain.grafo")
        self.assertIsNone(res_dom_graph["concept"]["implementation_sha"])
        self.assertEqual(res_dom_graph["concept"]["provenance_status"], "unverified")
        self.assertFalse(res_dom_graph["concept"]["verified"])

        res_amb_graph = ki.query_knowledge(self.conn, "grafo")
        self.assertTrue(res_amb_graph["is_ambiguous"])

        # ui.sidebar.peek vs ui.sidebar.collapse (verified real SHA)
        res_peek = ki.query_knowledge(self.conn, "espiar")
        self.assertEqual(res_peek["concept"]["concept_id"], "ui.sidebar.peek")
        self.assertTrue(res_peek["concept"]["verified"])
        res_col = ki.query_knowledge(self.conn, "recolher")
        self.assertEqual(res_col["concept"]["concept_id"], "ui.sidebar.collapse")
        self.assertTrue(res_col["concept"]["verified"])

    def test_adr_parsing_and_temporal_validity(self):
        """Acceptance Criteria 2: ADR-0005, ADR-0008, ADR2 find documented versions,

        temporal validity, and supersedes relationships with verified real blob SHAs.
        """
        # ADR-0005: accepted, supersedes ADR-0001
        adr5 = ki.get_adr(self.conn, "ADR 0005")
        self.assertEqual(adr5["decision_id"], "ADR-0005")
        self.assertEqual(adr5["status"], "accepted")
        self.assertEqual(adr5["supersedes_id"], "ADR-0001")
        self.assertEqual(adr5["blob_sha"], "5f2eadd87895150960d5b0086f3772bfc70299f3")
        self.assertEqual(adr5["provenance_status"], "verified")
        self.assertTrue(adr5["verified"])
        self.assertIn("Production Baseline", adr5["title"])

        # ADR-0002 / ADR2: superseded by ADR-0005
        adr2 = ki.get_adr(self.conn, "ADR2")
        self.assertEqual(adr2["decision_id"], "ADR-0002")
        self.assertEqual(adr2["status"], "superseded")
        self.assertEqual(adr2["superseded_by_id"], "ADR-0005")
        self.assertEqual(adr2["valid_until_ref"], "refs/heads/main")
        self.assertEqual(adr2["blob_sha"], "b1b64da0374bb002f797793d0953a7bcf54ae22d")
        self.assertEqual(adr2["provenance_status"], "verified")
        self.assertTrue(adr2["verified"])

        # ADR-0008: accepted
        adr8 = ki.get_adr(self.conn, "ADR-0008")
        self.assertEqual(adr8["decision_id"], "ADR-0008")
        self.assertEqual(adr8["status"], "accepted")
        self.assertEqual(adr8["blob_sha"], "eb3e0712276da0b61ea0058369aca95b5160d59b")
        self.assertEqual(adr8["provenance_status"], "verified")
        self.assertTrue(adr8["verified"])

        # DEC-APP-SHELL-01 and DEC-SIDEBAR-PROTOTIPO-01: verified real blob SHAs
        dec_app = ki.get_adr(self.conn, "DEC-APP-SHELL-01")
        self.assertEqual(dec_app["blob_sha"], "d811241f0a0f694694d35e4636ed46d2e38478c9")
        self.assertEqual(dec_app["provenance_status"], "verified")
        self.assertTrue(dec_app["verified"])

        dec_sidebar = ki.get_adr(self.conn, "DEC-SIDEBAR-PROTOTIPO-01")
        self.assertEqual(dec_sidebar["blob_sha"], "5a6b72be94ccfe4316e65dcd9fafaba9fa9accf1")
        self.assertEqual(dec_sidebar["provenance_status"], "verified")
        self.assertTrue(dec_sidebar["verified"])

    def test_not_recovered_tracking_with_investigated_refs(self):
        """Acceptance Criteria 2: Unrecovered ADRs must register status='not-recovered'

        with explicit investigated_refs inventory and verified=False.
        """
        unrec = ki.get_adr(self.conn, "ADR-0099")
        self.assertEqual(unrec["decision_id"], "ADR-0099")
        self.assertEqual(unrec["status"], "not-recovered")
        self.assertEqual(unrec["provenance_status"], "not-recovered")
        self.assertFalse(unrec["verified"])
        self.assertIsNotNone(unrec["investigated_refs"])
        self.assertTrue(len(unrec["investigated_refs"]) > 0)
        self.assertIn("refs/heads/main", unrec["investigated_refs"])
        self.assertIn("refs/heads/dev", unrec["investigated_refs"])

    def test_validate_git_sha_rejects_artificial_and_invalid_hashes(self):
        """validate_git_sha must reject artificial patterns and non-40-char hex strings."""
        valid_shas = [
            "5f2eadd87895150960d5b0086f3772bfc70299f3",
            "b1b64da0374bb002f797793d0953a7bcf54ae22d",
            "eb3e0712276da0b61ea0058369aca95b5160d59b",
            "d811241f0a0f694694d35e4636ed46d2e38478c9",
            "5a6b72be94ccfe4316e65dcd9fafaba9fa9accf1",
            "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
            "a020d635de368b755992e1282e18af9fdc2b8a03",
        ]
        for sha in valid_shas:
            self.assertTrue(ki.validate_git_sha(sha), f"Expected valid SHA: {sha}")

        invalid_or_artificial = [
            None,
            "",
            "   ",
            "not-a-sha",
            "1234",
            "z" * 40,
            "0" * 40,
            "b000adr00050000000000000000000000000000",
            "b000decappshell000000000000000000000000",
            "d000space000000000000000000000000000000",
            "q000domain00000000000000000000000000000",
            "f000domain00000000000000000000000000000",
            "s000domain00000000000000000000000000000",
            "g000uigraph0000000000000000000000000000",
            "g000domaingrafo000000000000000000000000",
            "b000" + "a" * 36,
            "q000" + "1" * 36,
            "abcdef" + "0" * 34,
        ]
        for bad in invalid_or_artificial:
            self.assertFalse(ki.validate_git_sha(bad), f"Expected rejection for: {bad!r}")

    def test_no_artificial_shas_in_database_tables(self):
        """Ensure zero artificial/invalid SHAs remain in decision_records or glossary_concepts."""
        dec_rows = self.conn.execute(
            "SELECT decision_id, blob_sha, commit_sha, provenance_status, is_synthetic FROM decision_records"
        ).fetchall()
        self.assertGreater(len(dec_rows), 0)
        for row in dec_rows:
            if row["blob_sha"] is not None:
                self.assertTrue(
                    ki.validate_git_sha(row["blob_sha"]),
                    f"Invalid/artificial blob_sha in decision_records[{row['decision_id']}]: {row['blob_sha']}",
                )
            if row["commit_sha"] is not None:
                self.assertTrue(
                    ki.validate_git_sha(row["commit_sha"]),
                    f"Invalid/artificial commit_sha in decision_records[{row['decision_id']}]: {row['commit_sha']}",
                )
            if row["provenance_status"] == "verified":
                self.assertIsNotNone(row["blob_sha"])
                self.assertEqual(row["is_synthetic"], 0)

        occ_rows = self.conn.execute(
            "SELECT decision_id, blob_sha FROM decision_occurrences WHERE blob_sha IS NOT NULL"
        ).fetchall()
        for row in occ_rows:
            self.assertTrue(
                ki.validate_git_sha(row["blob_sha"]),
                f"Invalid/artificial blob_sha in decision_occurrences[{row['decision_id']}]: {row['blob_sha']}",
            )

        concept_rows = self.conn.execute(
            "SELECT concept_id, implementation_sha, provenance_status, is_synthetic FROM glossary_concepts"
        ).fetchall()
        self.assertGreater(len(concept_rows), 0)
        for row in concept_rows:
            if row["implementation_sha"] is not None:
                self.assertTrue(
                    ki.validate_git_sha(row["implementation_sha"]),
                    f"Invalid/artificial implementation_sha in glossary_concepts[{row['concept_id']}]: {row['implementation_sha']}",
                )
                self.assertEqual(row["provenance_status"], "verified")
            else:
                self.assertNotEqual(row["provenance_status"], "verified")

    def test_verified_vs_unverified_filtering(self):
        """Ensure verified_only=True excludes unverified/not-recovered records while preserving verified facts."""
        # Verified concept returns under verified_only=True
        res_verified = ki.query_knowledge(self.conn, "espaco", verified_only=True)
        self.assertEqual(res_verified["concept"]["concept_id"], "domain.space")
        self.assertTrue(res_verified["concept"]["verified"])

        # Unverified concept is excluded under verified_only=True, but returned with verified=False otherwise
        res_unverified = ki.query_knowledge(self.conn, "questao", verified_only=False)
        self.assertEqual(res_unverified["concept"]["concept_id"], "domain.question")
        self.assertFalse(res_unverified["concept"]["verified"])
        self.assertEqual(res_unverified["concept"]["provenance_status"], "unverified")

        res_filtered = ki.query_knowledge(self.conn, "questao", verified_only=True)
        self.assertNotIn("concept", res_filtered)
        matched_ids = [m["entity_id"] for m in res_filtered.get("matches", [])]
        self.assertNotIn("domain.question", matched_ids)
        for m in res_filtered.get("matches", []):
            self.assertTrue(m["verified"])

        # Unverified concept not mentioned in any verified record yields empty matches
        res_fc_filtered = ki.query_knowledge(self.conn, "flashcard", verified_only=True)
        self.assertNotIn("concept", res_fc_filtered)
        self.assertEqual(res_fc_filtered.get("matches"), [])

        # list_glossary respects verified_only
        all_concepts = ki.list_glossary(self.conn)
        verified_concepts = ki.list_glossary(self.conn, verified_only=True)
        self.assertEqual(len(all_concepts), 13)
        self.assertEqual(len(verified_concepts), 8)
        for c in verified_concepts:
            self.assertTrue(c["verified"])
            self.assertEqual(c["provenance_status"], "verified")
            self.assertIsNotNone(c["implementation_sha"])

        # Unrecovered ADR is excluded when verified_only=True
        self.assertEqual(ki.get_adr(self.conn, "ADR-0099", verified_only=True), {})
        self.assertEqual(ki.get_adr(self.conn, "ADR-0005", verified_only=True)["decision_id"], "ADR-0005")

    def test_markdown_file_and_table_extraction(self):
        """Test extraction of ADRs from custom Markdown files and markdown tables."""
        md_content = """# ADR-0015: Standardize Error Boundaries

Status: Proposed
Scope: ui/resilience

## Context
Unexpected React render crashes break user experience.

## Alternatives Considered
- Component-level try/catch
- React ErrorBoundary wrappers

## Consequences
Crash prevention with fallback UI rendering.
"""
        test_file = Path(self.tmp.name) / "0015-error-boundaries.md"
        test_file.write_text(md_content, encoding="utf-8")

        indexed_ids = ki.index_document_file(self.conn, test_file, ref="refs/heads/dev")
        self.assertIn("ADR-0015", indexed_ids)

        record = ki.get_adr(self.conn, "ADR-0015")
        self.assertEqual(record["decision_id"], "ADR-0015")
        self.assertEqual(record["status"], "proposed")
        self.assertEqual(record["scope"], "ui/resilience")
        self.assertIn("React render crashes", record["motivation"])
        self.assertEqual(len(record["alternatives"]), 2)

    def test_blob_sha_deduplication(self):
        """Verify blob SHA deduplication across repositories and paths."""
        md_content = """# ADR-0020: Blob Deduplication Test

Status: Accepted

## Context
Ensure duplicate documents across branches are only parsed once.
"""
        file1 = Path(self.tmp.name) / "adr20-repo1.md"
        file2 = Path(self.tmp.name) / "adr20-repo2.md"
        file1.write_text(md_content, encoding="utf-8")
        file2.write_text(md_content, encoding="utf-8")

        ki.index_document_file(self.conn, file1, repo="repo1", ref="refs/heads/main")
        ki.index_document_file(self.conn, file2, repo="repo2", ref="refs/heads/dev")

        # Check occurrence count
        occ_rows = self.conn.execute(
            "SELECT * FROM decision_occurrences WHERE decision_id = 'ADR-0020'"
        ).fetchall()
        self.assertEqual(len(occ_rows), 2)
        # Check decision records has only one primary entry
        dec_rows = self.conn.execute(
            "SELECT * FROM decision_records WHERE decision_id = 'ADR-0020'"
        ).fetchall()
        self.assertEqual(len(dec_rows), 1)

    def test_cli_invocations_and_json(self):
        """Test CLI command execution with --query, --adr, --glossary, --coverage, --json."""
        cmd_base = [sys.executable, str(SCRIPTS_DIR / "knowledge_indexer.py"), "--db", str(self.db_path)]

        # 1. CLI --query fixar --json
        p_query = subprocess.run([*cmd_base, "--query", "fixar", "--json"], capture_output=True, text=True, check=True)
        data_query = json.loads(p_query.stdout)
        self.assertTrue(data_query["is_ambiguous"])
        self.assertGreater(len(data_query["candidate_groups"]), 1)

        # 2. CLI --adr ADR-0005 --json
        p_adr = subprocess.run([*cmd_base, "--adr", "ADR-0005", "--json"], capture_output=True, text=True, check=True)
        data_adr = json.loads(p_adr.stdout)
        self.assertEqual(data_adr["decision_id"], "ADR-0005")
        self.assertEqual(data_adr["status"], "accepted")
        self.assertEqual(data_adr["provenance_status"], "verified")
        self.assertTrue(data_adr["verified"])

        # 3. CLI --glossary --json and --verified-only
        p_gloss = subprocess.run([*cmd_base, "--glossary", "--json"], capture_output=True, text=True, check=True)
        data_gloss = json.loads(p_gloss.stdout)
        self.assertIsInstance(data_gloss, list)
        self.assertEqual(len(data_gloss), 13)

        p_gloss_verified = subprocess.run(
            [*cmd_base, "--glossary", "--verified-only", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        data_gloss_verified = json.loads(p_gloss_verified.stdout)
        self.assertEqual(len(data_gloss_verified), 8)

        # 4. CLI --coverage --json
        p_cov = subprocess.run([*cmd_base, "--coverage", "--json"], capture_output=True, text=True, check=True)
        data_cov = json.loads(p_cov.stdout)
        self.assertIn("decisions", data_cov)
        self.assertIn("glossary", data_cov)
        self.assertIn("benchmark", data_cov)
        self.assertEqual(data_cov["benchmark"]["recall_at_1"], 1.0)

    def test_zero_emoji_policy(self):
        """Zero Emoji Policy: Absolutely NO Unicode emojis [\\U00010000-\\U0010ffff] anywhere."""
        for path in [SCRIPTS_DIR / "knowledge_indexer.py", Path(__file__)]:
            content = path.read_text(encoding="utf-8")
            emojis = EMOJI_REGEX.findall(content)
            self.assertEqual(len(emojis), 0, f"Found emojis in {path}: {emojis}")


if __name__ == "__main__":
    unittest.main()
