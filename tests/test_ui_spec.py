#!/usr/bin/env python3
"""Tests for UI specifications, design tokens, component catalog, motion spec, provenance matrix, and zero-emoji compliance (Issue #24)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

REQUIRED_DOCS = [
    DOCS_DIR / "UI-DESIGN-TOKENS.md",
    DOCS_DIR / "UI-COMPONENT-CATALOG.md",
    DOCS_DIR / "UI-MOTION-SPEC.md",
    DOCS_DIR / "UI-PROVENANCE-MATRIX.md",
]


class UISpecTests(unittest.TestCase):
    def test_all_consolidated_ui_docs_exist(self) -> None:
        for doc in REQUIRED_DOCS:
            self.assertTrue(doc.is_file(), f"Missing required document: {doc}")

    def test_zero_emoji_policy_across_ui_docs_and_test(self) -> None:
        targets = [*REQUIRED_DOCS, Path(__file__)]
        for target in targets:
            content = target.read_text(encoding="utf-8")
            emojis = EMOJI_REGEX.findall(content)
            self.assertEqual(
                emojis,
                [],
                f"Disallowed Unicode emoji found in {target}: {emojis}",
            )

    def test_privacy_rules_and_no_private_paths_inside_site(self) -> None:
        forbidden_patterns = [
            r"site/.*\.sqlite",
            r"site/.*\.db",
            r"site/.*\.bundle",
            r"ghp_[A-Za-z0-9_]{20,}",
            r"github_pat_[A-Za-z0-9_]{20,}",
            r"AIzaSy[A-Za-z0-9_-]{20,}",
        ]
        for doc in REQUIRED_DOCS:
            text = doc.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                match = re.search(pattern, text)
                self.assertIsNone(
                    match,
                    f"Forbidden pattern '{pattern}' found in {doc}: {match}",
                )

    def test_design_tokens_content_contracts(self) -> None:
        doc_text = (DOCS_DIR / "UI-DESIGN-TOKENS.md").read_text(encoding="utf-8")
        required_tokens = [
            "--surface-canvas",
            "--surface-panel",
            "--surface-panel-muted",
            "--surface-hover",
            "--surface-active",
            "--content-primary",
            "--content-secondary",
            "--content-tertiary",
            "--content-active",
            "--border-subtle",
            "Geist Sans",
            "Geist Mono",
            "29px",
            "46px",
        ]
        for token in required_tokens:
            self.assertIn(token, doc_text, f"Missing token/spec '{token}' in UI-DESIGN-TOKENS.md")

    def test_component_catalog_content_contracts(self) -> None:
        doc_text = (DOCS_DIR / "UI-COMPONENT-CATALOG.md").read_text(encoding="utf-8")
        required_components = [
            "AppShell",
            "AppHeader",
            "AppSidebar",
            "AppHeaderTabs",
            "QuestionCard",
            "QuestionNavigator",
            "FlashcardViewer",
            "RatingButtons",
            "GraphCanvas",
            "SidePanelSearchOverlay",
        ]
        for comp in required_components:
            self.assertIn(comp, doc_text, f"Missing component '{comp}' in UI-COMPONENT-CATALOG.md")

    def test_motion_spec_content_contracts(self) -> None:
        doc_text = (DOCS_DIR / "UI-MOTION-SPEC.md").read_text(encoding="utf-8")
        required_concepts = [
            "Dwell Delay",
            "Transition Duration",
            "180 ms",
            "prefers-reduced-motion",
            "Playwright",
            "skeletonPulse",
            "translateX(-105%)",
        ]
        for concept in required_concepts:
            self.assertIn(concept, doc_text, f"Missing concept '{concept}' in UI-MOTION-SPEC.md")

    def test_provenance_matrix_content_contracts(self) -> None:
        doc_text = (DOCS_DIR / "UI-PROVENANCE-MATRIX.md").read_text(encoding="utf-8")
        required_shas = [
            "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
            "a020d635de368b755992e1282e18af9fdc2b8a03",
            "c8149bad08ee026dec049371d3814c29aec8b89a",
            "783b7041913a8ddc01c7bd2aa1ee6bbf6eeb7e1a",
        ]
        required_confidence_levels = [
            "verified-in-source",
            "measured-in-browser",
            "inferred",
        ]
        for sha in required_shas:
            self.assertIn(sha, doc_text, f"Missing SHA '{sha}' in UI-PROVENANCE-MATRIX.md")
        for conf in required_confidence_levels:
            self.assertIn(conf, doc_text, f"Missing confidence level '{conf}' in UI-PROVENANCE-MATRIX.md")


if __name__ == "__main__":
    unittest.main()
