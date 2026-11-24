#!/usr/bin/env python3
"""Tests for scripts/document_extractor.py, benchmark report, and zero-emoji compliance."""
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

import document_extractor as de  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


def run_git(*args: str, cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


class DocumentExtractorTests(unittest.TestCase):
    def test_markdown_hierarchy_tables_links_and_provenance(self):
        md = (
            "---\n"
            "title: Arquitetura de Simulados\n"
            "---\n\n"
            "# Arquitetura\n\n"
            "Texto introdutorio com ![Tela Inicial](assets/home-screen.png).\n\n"
            "## Modelo de Dados\n\n"
            "| Campo | Tipo | Origem |\n"
            "|---|---|---|\n"
            "| id | string | `src/domain/exam.ts` |\n"
            "| score | number | `src/domain/score.ts` |\n\n"
            "### Diagrama Mermaid\n\n"
            "```mermaid\n"
            "flowchart TD\n"
            "  A[Inicio] --> B[Fim]\n"
            "```\n\n"
            "# Decisoes\n\n"
            "Ver [Fluxo](docs/diagrams/flow.drawio) e <img src=\"assets/graph.webp\" alt=\"Grafo\" />.\n"
        )
        sha = "a" * 40
        res = de.extract_document_bytes(
            md.encode("utf-8"),
            path="docs/architecture.md",
            repo="exams-app",
            ref="refs/heads/dev",
            commit_sha=sha,
        )

        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["provenance"]["document_type"], "markdown")
        self.assertEqual(res["provenance"]["sha256"], de.sha256_bytes(md.encode("utf-8")))
        self.assertEqual(res["metadata"]["title"], "Arquitetura de Simulados")
        self.assertEqual(res["metadata"]["heading_levels"], [1, 2, 3])
        self.assertEqual(res["metadata"]["section_count"], 4)
        self.assertEqual(res["metadata"]["table_count"], 1)
        self.assertEqual(res["metadata"]["diagram_link_count"], 4)

        sections = res["sections"]
        self.assertEqual(sections[0]["section_path"], "Arquitetura")
        self.assertIsNone(sections[0]["parent_id"])
        self.assertEqual(sections[1]["section_path"], "Arquitetura > Modelo de Dados")
        self.assertEqual(sections[1]["parent_id"], sections[0]["element_id"])
        self.assertEqual(sections[2]["section_path"], "Arquitetura > Modelo de Dados > Diagrama Mermaid")
        self.assertEqual(sections[2]["parent_id"], sections[1]["element_id"])
        self.assertEqual(sections[3]["section_path"], "Decisoes")
        self.assertIsNone(sections[3]["parent_id"])

        for sec in sections:
            self.assertEqual(sec["content_sha256"], de.sha256_text(sec["content"]))
            prov = sec["provenance"]
            self.assertEqual(prov["repo"], "exams-app")
            self.assertEqual(prov["ref"], "refs/heads/dev")
            self.assertEqual(prov["commit_sha"], sha)
            self.assertEqual(prov["path"], "docs/architecture.md")
            self.assertEqual(prov["pdf_page"], 1)
            self.assertEqual(prov["extractor_version"], de.EXTRACTOR_VERSION)
            self.assertIn(sec["element_id"], prov["citation_key"])

        tbl = res["tables"][0]
        self.assertEqual(tbl["headers"], ["Campo", "Tipo", "Origem"])
        self.assertEqual(tbl["row_count"], 2)
        self.assertEqual(tbl["col_count"], 3)
        self.assertEqual(tbl["section_path"], "Arquitetura > Modelo de Dados")

        targets = {lnk["target"]: lnk for lnk in res["diagram_links"]}
        self.assertIn("assets/home-screen.png", targets)
        self.assertIn("docs/diagrams/flow.drawio", targets)
        self.assertIn("assets/graph.webp", targets)
        self.assertTrue(any(k.startswith("inline:mermaid:") for k in targets))
        for lnk in res["diagram_links"]:
            self.assertFalse(lnk["understood"])

    def test_plain_text_and_json_spec_extraction(self):
        txt = (
            "Plano Historico\n"
            "===============\n\n"
            "1. Contexto\n"
            "Screenshot em old-10-home.png.\f"
            "2. Resultados\n"
            "2.1 Metricas\n"
            "Operacao deterministica.\n"
        )
        res_txt = de.extract_document_bytes(
            txt.encode("utf-8"),
            path="notes/plan.txt",
            repo="notes-app",
            ref="old-10",
            commit_sha="b" * 40,
        )
        self.assertEqual(res_txt["status"], "ok")
        self.assertEqual(res_txt["metadata"]["page_count"], 2)
        self.assertEqual([s["page"] for s in res_txt["sections"]], [1, 1, 2, 2])
        self.assertEqual(res_txt["sections"][3]["section_path"], "2. Resultados > 2.1 Metricas")
        self.assertEqual(res_txt["diagram_links"][0]["target"], "old-10-home.png")
        self.assertFalse(res_txt["diagram_links"][0]["understood"])

        json_spec = (
            "{\n"
            "  // JSONC comment\n"
            '  "name": "graph-spec",\n'
            '  "nodes": [\n'
            '    {"id": "n1", "label": "Exam", "icon": "assets/exam.svg"},\n'
            '    {"id": "n2", "label": "Recall", "icon": "assets/recall.svg"}\n'
            "  ],\n"
            '  "limits": {"max_nodes": 500}\n'
            "}\n"
        )
        res_json = de.extract_document_bytes(
            json_spec.encode("utf-8"),
            path="specs/graph.jsonc",
            repo="exams-app",
            ref="main",
            commit_sha="c" * 40,
        )
        self.assertEqual(res_json["status"], "ok")
        self.assertEqual(res_json["provenance"]["document_type"], "json_spec")
        self.assertEqual(res_json["metadata"]["title"], "graph-spec")
        self.assertEqual(res_json["metadata"]["table_count"], 1)
        self.assertEqual(res_json["tables"][0]["headers"], ["id", "label", "icon"])
        self.assertEqual(res_json["tables"][0]["row_count"], 2)
        self.assertEqual(res_json["metadata"]["diagram_link_count"], 2)

    def test_pdf_native_text_tables_bboxes_and_scanned_page_detection(self):
        pdf_bytes = de.build_synthetic_pdf_bytes([
            {
                "stream": (
                    "BT /F1 18 Tf 72 720 Td (1. Historical Spec) Tj "
                    "/F1 11 Tf 0 -24 Td (Summary of exam domain decisions.) Tj "
                    "0 -24 Td (Component) Tj 180 0 Td (Status) Tj "
                    "-180 -16 Td (Sidebar) Tj 180 0 Td (Migrated) Tj "
                    "-180 -16 Td (Graph) Tj 180 0 Td (Active) Tj ET"
                ),
                "has_image_xobject": False,
            },
            {
                "stream": "q 320 0 0 240 100 300 cm /Im1 Do Q",
                "has_image_xobject": True,
            },
        ])
        res = de.extract_document_bytes(
            pdf_bytes,
            path="docs/legacy-spec.pdf",
            repo="exams-app-old",
            ref="refs/heads/main",
            commit_sha="d" * 40,
        )
        self.assertEqual(res["provenance"]["document_type"], "pdf")
        self.assertEqual(res["status"], "partial")
        self.assertEqual(res["metadata"]["page_count"], 2)
        self.assertEqual(res["uninterpreted_pages"], [2])
        self.assertEqual(res["pages"][0]["extraction_mode"], "native_text")
        self.assertEqual(res["pages"][1]["extraction_mode"], "image_only_needs_ocr")
        self.assertEqual(res["pages"][1]["image_xobjects"], 1)

        self.assertGreaterEqual(res["metadata"]["section_count"], 1)
        sec = res["sections"][0]
        self.assertEqual(sec["title"], "1. Historical Spec")
        self.assertEqual(sec["page"], 1)
        self.assertIsNotNone(sec["bounding_box"])
        self.assertEqual(len(sec["bounding_box"]), 4)
        self.assertIsNotNone(sec["provenance"]["bounding_box"])

        self.assertEqual(res["metadata"]["table_count"], 1)
        tbl = res["tables"][0]
        self.assertEqual(tbl["headers"], ["Component", "Status"])
        self.assertEqual(tbl["rows"], [["Sidebar", "Migrated"], ["Graph", "Active"]])
        self.assertIsNotNone(tbl["bounding_box"])

        self.assertEqual(res["metadata"]["diagram_link_count"], 1)
        fig = res["diagram_links"][0]
        self.assertEqual(fig["kind"], "pdf_image_xobject")
        self.assertEqual(fig["page"], 2)
        self.assertEqual(fig["bounding_box"], [100.0, 300.0, 420.0, 540.0])
        self.assertFalse(fig["understood"])

    def test_explicit_skips_for_missing_encrypted_binary_and_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = de.extract_document_file(root / "does-not-exist.pdf")
            self.assertEqual(missing["status"], "skipped")
            self.assertEqual(missing["skip_reason"], "missing_file")

        encrypted = de.build_synthetic_pdf_bytes(
            [{"stream": "BT /F1 12 Tf 72 720 Td (Confidential) Tj ET"}],
            encrypt=True,
        )
        res_enc = de.extract_document_bytes(encrypted, path="archive/locked.pdf")
        self.assertEqual(res_enc["status"], "skipped")
        self.assertEqual(res_enc["skip_reason"], "encrypted_pdf")

        res_bin = de.extract_document_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00", path="docs/corrupt.md")
        self.assertEqual(res_bin["status"], "skipped")
        self.assertEqual(res_bin["skip_reason"], "binary_non_document")

        res_secret_path = de.extract_document_bytes(b"SECRET=123\n", path="secrets/credentials.json")
        self.assertEqual(res_secret_path["status"], "skipped")
        self.assertEqual(res_secret_path["skip_reason"], "secret_path_blocked")

        res_secret_body = de.extract_document_bytes(
            b"# Config\ntoken: ghp_syntheticTokenValue1234567890123456\n",
            path="docs/leak.md",
        )
        self.assertEqual(res_secret_body["status"], "skipped")
        self.assertEqual(res_secret_body["skip_reason"], "secret_content_blocked")

    def test_scan_sqlite_fts5_search_and_git_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs_dir = root / "docs"
            docs_dir.mkdir()
            (docs_dir / "guide.md").write_text(
                "# Guia de Busca\n\n## FTS5\nIndice deterministico para documentos.\n",
                encoding="utf-8",
            )
            db_path = root / "docs.sqlite"
            scan_res = de.scan_directory(docs_dir, repo_name="test-repo", ref="main", db_path=db_path)
            self.assertEqual(scan_res["totals"]["extracted_ok"], 1)
            self.assertGreaterEqual(scan_res["totals"]["sections"], 2)

            conn = de.open_doc_db(db_path)
            try:
                hits = de.search_documents(conn, "deterministico")
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0]["path"], "guide.md")
                self.assertEqual(hits[0]["pdf_page"], 1)
                self.assertEqual(hits[0]["section_path"], "Guia de Busca > FTS5")
                self.assertEqual(hits[0]["extractor_version"], de.EXTRACTOR_VERSION)
            finally:
                conn.close()

            # Test direct Git repo extraction without checkout
            work = root / "work"
            work.mkdir()
            run_git("init", "-q", "-b", "main", str(work))
            run_git("config", "user.email", "doc@example.invalid", cwd=work)
            run_git("config", "user.name", "Doc Test", cwd=work)
            (work / "SPEC.md").write_text("# Spec\n\n## Tabela\n| A | B |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
            run_git("add", "SPEC.md", cwd=work)
            run_git("commit", "-qm", "docs: add spec", cwd=work)
            sha = run_git("rev-parse", "HEAD", cwd=work).strip()

            bare = root / "bare.git"
            run_git("clone", "--mirror", "-q", str(work), str(bare))
            git_res = de.extract_from_git(bare, commit_sha=sha, path="SPEC.md", repo_name="hist", ref="main")
            self.assertEqual(git_res["status"], "ok")
            self.assertEqual(git_res["metadata"]["table_count"], 1)
            self.assertEqual(git_res["provenance"]["commit_sha"], sha)

    def test_benchmark_cli_and_report_and_zero_emoji(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "document_extractor.py"), "benchmark"],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["extractor_version"], de.EXTRACTOR_VERSION)
        self.assertEqual(payload["synthetic_benchmark"]["fixtures"], 5)

        report_path = ROOT / "reports" / "DOCUMENT-EXTRACTION-BENCHMARK.md"
        self.assertTrue(report_path.is_file())
        report_text = report_path.read_text(encoding="utf-8")
        for keyword in ("Docling", "PageIndex", "Xberg", "OpenDataLoader", "ADOTAR", "OPCIONAL"):
            self.assertIn(keyword.lower(), report_text.lower())

        for target in (
            SCRIPTS_DIR / "document_extractor.py",
            report_path,
            Path(__file__),
        ):
            content = target.read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(content), [], f"Unexpected emoji in {target}")


if __name__ == "__main__":
    unittest.main()
