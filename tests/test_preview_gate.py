#!/usr/bin/env python3
"""Unit tests for scripts/preview_gate.py (Issue #46).

Tests:
  - Feature matrix extraction from TSX/CSS/HTML source samples
    (tabs.pin_unpin, sidebar.pinned_section, sidebar.hover_peek, shell.mobile_drawer, etc.).
  - Hard gate rejection when a proven feature is silently omitted from preview.
  - Gate passing when all features are implemented.
  - Gate passing when omitted features are explicitly documented with justifications.
  - Omissions matrix parsing from JSON and Markdown tables/lists.
  - Strict mode behavior (partially-mocked rejection and motion contract validation).
  - Markdown report and JSON output generation.
  - Zero Emoji Policy compliance across all code, tests, and outputs.
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

import preview_gate  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

SAMPLE_APP_HEADER_TABS_TSX = """import React, { useState } from 'react';

// repo: ianmaciel7/notes-app@old-5/src/app/_components/workspace/app-header-tabs.tsx
// commit: 4eb93c5013c27ba6724b4f116cc9fe5846398eb8

export interface TabItem {
  id: string;
  title: string;
  pinned?: boolean;
}

export function AppHeaderTabs({ tabs, activeId }: { tabs: TabItem[]; activeId: string }) {
  const [pinnedTabIds, setPinnedTabIds] = useState<string[]>([]);
  const [openInNewPane, setOpenInNewPane] = useState(false);

  const togglePin = (tabId: string) => {
    setPinnedTabIds(prev =>
      prev.includes(tabId) ? prev.filter(id => id !== tabId) : [...prev, tabId]
    );
  };

  const handleShiftOpen = (tabId: string, event: React.MouseEvent) => {
    if (event.shiftKey) {
      setOpenInNewPane(true);
    }
  };

  return (
    <header className="tabs-header flex items-center transition-all duration-200 ease-out motion-reduce:transition-none">
      {tabs.map(tab => (
        <div key={tab.id} className="tab-item" onClick={(e) => handleShiftOpen(tab.id, e)}>
          <span>{tab.title}</span>
          <button
            title="Pin Tab"
            className="pin-btn"
            onClick={(e) => {
              e.stopPropagation();
              togglePin(tab.id);
            }}
          >
            Pin
          </button>
        </div>
      ))}
    </header>
  );
}
"""

SAMPLE_APP_SIDEBAR_OVERVIEW_TSX = """import React, { useState, useRef } from 'react';

// repo: ianmaciel7/notes-app@old-5/src/app/_components/workspace/app-sidebar-overview.tsx
// commit: a020d635de368b755992e1282e18af9fdc2b8a03

export function AppSidebarOverview({ collapsed }: { collapsed: boolean }) {
  const [pinnedItems, setPinnedItems] = useState<string[]>(['Doc1', 'Exam2026']);
  const [isPeekOpen, setIsPeekOpen] = useState(false);
  const openTimerRef = useRef<number | null>(null);

  const handleMouseEnter = () => {
    if (!collapsed) return;
    openTimerRef.current = window.setTimeout(() => {
      setIsPeekOpen(true);
    }, 180);
  };

  return (
    <aside
      onMouseEnter={handleMouseEnter}
      className="sidebar-overview transition-all duration-200 ease-out motion-reduce:transition-none"
    >
      <section className="pinned-section">
        <h3>Fixados</h3>
        <ul className="pinnedlist">
          {pinnedItems.map(item => (
            <li key={item} className="pinned-item">{item}</li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
"""


class PreviewGateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_feature_matrix_extraction_from_source_samples(self):
        """Test accurate extraction of Feature Matrix from canonical component sources."""
        # 1. Tabs component extraction
        tab_feats = preview_gate.extract_features_from_source(
            SAMPLE_APP_HEADER_TABS_TSX, filename="app-header-tabs.tsx"
        )
        feat_ids = {f.feature_id: f for f in tab_feats}

        self.assertIn("tabs.pin_unpin", feat_ids)
        pin_feat = feat_ids["tabs.pin_unpin"]
        self.assertEqual(pin_feat.component, "AppHeaderTabs")
        self.assertEqual(pin_feat.symbol_handler, "togglePin")
        self.assertEqual(pin_feat.state_binding, "pinnedTabIds")
        self.assertEqual(pin_feat.trigger_gesture_shortcut, "click")
        self.assertEqual(pin_feat.motion_contract.transition_duration_ms, 200.0)
        self.assertEqual(pin_feat.motion_contract.easing, "ease-out")
        self.assertTrue(pin_feat.motion_contract.reduced_motion)
        self.assertEqual(
            pin_feat.provenance.repo_ref_path,
            "ianmaciel7/notes-app@old-5/src/app/_components/workspace/app-header-tabs.tsx",
        )
        self.assertEqual(
            pin_feat.provenance.commit_sha,
            "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
        )

        self.assertIn("tabs.shift_open", feat_ids)
        shift_feat = feat_ids["tabs.shift_open"]
        self.assertEqual(shift_feat.trigger_gesture_shortcut, "Shift+Click")

        # 2. Sidebar component extraction
        sidebar_feats = preview_gate.extract_features_from_source(
            SAMPLE_APP_SIDEBAR_OVERVIEW_TSX, filename="app-sidebar-overview.tsx"
        )
        sb_ids = {f.feature_id: f for f in sidebar_feats}

        self.assertIn("sidebar.pinned_section", sb_ids)
        pinned_sec = sb_ids["sidebar.pinned_section"]
        self.assertEqual(pinned_sec.component, "AppSidebarOverview")
        self.assertIn("pinned", pinned_sec.state_binding.lower())
        self.assertEqual(
            pinned_sec.provenance.commit_sha,
            "a020d635de368b755992e1282e18af9fdc2b8a03",
        )

        self.assertIn("sidebar.hover_peek", sb_ids)
        peek_feat = sb_ids["sidebar.hover_peek"]
        self.assertEqual(peek_feat.motion_contract.dwell_delay_ms, 180.0)
        self.assertEqual(peek_feat.motion_contract.transition_duration_ms, 200.0)
        self.assertTrue(peek_feat.motion_contract.reduced_motion)

    def test_hard_gate_rejection_when_proven_feature_silently_omitted(self):
        """Hard gate failure (gate_passed = False, exit code 1) when verified features are omitted."""
        src_path = self.root / "app-header-tabs.tsx"
        src_path.write_text(SAMPLE_APP_HEADER_TABS_TSX, encoding="utf-8")

        # Preview HTML that renders tabs but completely ignores pin/unpin and shift_open
        preview_html = """<!doctype html>
        <html>
          <body>
            <header class="tabs-header">
              <div class="tab-item"><span>Document 1</span></div>
              <div class="tab-item"><span>Document 2</span></div>
            </header>
          </body>
        </html>
        """
        preview_path = self.root / "incomplete_preview.html"
        preview_path.write_text(preview_html, encoding="utf-8")

        gate_passed, report = preview_gate.run_preview_gate(
            sources=[src_path],
            preview_path=preview_path,
            omissions_path=None,
        )

        self.assertFalse(gate_passed)
        self.assertGreaterEqual(report["counts"]["omitted"], 1)

        omitted_ids = [
            f["feature_id"]
            for f in report["features"]
            if f["status"] == "omitted"
        ]
        self.assertIn("tabs.pin_unpin", omitted_ids)

        rejection_text = " ".join(report["rejection_reasons"])
        self.assertIn("SILENT OMISSION DETECTED", rejection_text)
        self.assertIn("tabs.pin_unpin", rejection_text)

    def test_gate_passing_when_all_features_implemented(self):
        """Gate passes when preview artifact implements all expected features."""
        src_path = self.root / "app-header-tabs.tsx"
        src_path.write_text(SAMPLE_APP_HEADER_TABS_TSX, encoding="utf-8")

        # Complete preview implementing both pin/unpin and shift_open
        preview_html = """<!doctype html>
        <html>
          <body>
            <header class="tabs-header">
              <div class="tab-item">
                <span class="tab-title">Doc 1</span>
                <button class="pin-btn" title="Pin Tab" onclick="togglePin('doc1')">Pin</button>
              </div>
            </header>
            <script>
              let pinnedTabIds = [];
              function togglePin(tabId) {
                if (pinnedTabIds.includes(tabId)) {
                  pinnedTabIds = pinnedTabIds.filter(id => id !== tabId);
                } else {
                  pinnedTabIds.push(tabId);
                }
              }
              function handleTabClick(e, tabId) {
                if (e.shiftKey) {
                  openInNewPane(tabId);
                }
              }
            </script>
          </body>
        </html>
        """
        preview_path = self.root / "complete_preview.html"
        preview_path.write_text(preview_html, encoding="utf-8")

        gate_passed, report = preview_gate.run_preview_gate(
            sources=[src_path],
            preview_path=preview_path,
        )

        self.assertTrue(gate_passed)
        self.assertEqual(report["counts"]["omitted"], 0)
        self.assertEqual(len(report["rejection_reasons"]), 0)

        statuses = {f["feature_id"]: f["status"] for f in report["features"]}
        self.assertEqual(statuses.get("tabs.pin_unpin"), "implemented")
        self.assertEqual(statuses.get("tabs.shift_open"), "implemented")

    def test_gate_passing_when_omitted_features_justified_in_omissions_matrix_json(self):
        """Gate passes when missing features are explicitly documented in JSON omissions matrix."""
        src_path = self.root / "app-header-tabs.tsx"
        src_path.write_text(SAMPLE_APP_HEADER_TABS_TSX, encoding="utf-8")

        # Preview implements pin/unpin, but tabs.shift_open is omitted
        preview_html = """<!doctype html>
        <html>
          <body>
            <button title="Pin Tab" onclick="togglePin('doc1')">Pin</button>
            <script>
              let pinnedTabIds = [];
              function togglePin(id) { pinnedTabIds.push(id); }
            </script>
          </body>
        </html>
        """
        preview_path = self.root / "preview.html"
        preview_path.write_text(preview_html, encoding="utf-8")

        # Explicit JSON omissions matrix documenting tabs.shift_open
        omissions_data = {
            "omissions": [
                {
                    "feature_id": "tabs.shift_open",
                    "justification": "Multi-pane split view deferred due to standalone chat embed single-column layout constraints.",
                }
            ]
        }
        omissions_path = self.root / "omissions.json"
        omissions_path.write_text(json.dumps(omissions_data), encoding="utf-8")

        gate_passed, report = preview_gate.run_preview_gate(
            sources=[src_path],
            preview_path=preview_path,
            omissions_path=omissions_path,
        )

        self.assertTrue(gate_passed)
        self.assertEqual(report["counts"]["omitted"], 0)
        self.assertEqual(report["counts"]["omitted_with_justification"], 1)

        statuses = {f["feature_id"]: f["status"] for f in report["features"]}
        self.assertEqual(statuses.get("tabs.pin_unpin"), "implemented")
        self.assertEqual(statuses.get("tabs.shift_open"), "omitted-with-justification")

    def test_omissions_matrix_parsing_from_markdown_table_and_list(self):
        """Test omissions matrix parsing from Markdown documentation."""
        md_table = """# Omissions Matrix
| Feature ID | Justification |
| --- | --- |
| tabs.shift_open | Split panes deferred due to chat width limits |
| tabs.dnd_reorder | Touch DnD coordinates deferred to mobile sprint |
"""
        table_path = self.root / "omissions_table.md"
        table_path.write_text(md_table, encoding="utf-8")

        omissions = preview_gate.load_omissions_matrix(table_path)
        self.assertIn("tabs.shift_open", omissions)
        self.assertIn("tabs.dnd_reorder", omissions)
        self.assertEqual(omissions["tabs.shift_open"], "Split panes deferred due to chat width limits")

        md_list = """# Omissions
- **tabs.shift_open**: Split pane not supported in embed
- **shell.mobile_drawer**: Mobile drawer deferred
"""
        list_path = self.root / "omissions_list.md"
        list_path.write_text(md_list, encoding="utf-8")
        omissions_list = preview_gate.load_omissions_matrix(list_path)
        self.assertIn("tabs.shift_open", omissions_list)
        self.assertIn("shell.mobile_drawer", omissions_list)

    def test_rejection_on_empty_justification_in_omissions(self):
        """Rejects omission if justification is empty string."""
        src_path = self.root / "app-header-tabs.tsx"
        src_path.write_text(SAMPLE_APP_HEADER_TABS_TSX, encoding="utf-8")

        omissions_data = {"omissions": [{"feature_id": "tabs.pin_unpin", "justification": ""}]}
        omissions_path = self.root / "empty_omissions.json"
        omissions_path.write_text(json.dumps(omissions_data), encoding="utf-8")

        gate_passed, report = preview_gate.run_preview_gate(
            sources=[src_path],
            preview_path=None,
            omissions_path=omissions_path,
        )
        self.assertFalse(gate_passed)
        self.assertTrue(any("empty justification" in r for r in report["rejection_reasons"]))

    def test_strict_mode_rejects_partially_mocked_features(self):
        """In strict mode, partially-mocked features trigger gate rejection."""
        src_path = self.root / "app-header-tabs.tsx"
        src_path.write_text(SAMPLE_APP_HEADER_TABS_TSX, encoding="utf-8")

        preview_html = """<!doctype html>
        <html>
          <body>
            <button data-mocked="true" title="Pin Tab" onclick="alert('mock')">Pin</button>
          </body>
        </html>
        """
        preview_path = self.root / "mock_preview.html"
        preview_path.write_text(preview_html, encoding="utf-8")

        # Justify shift_open so it does not block
        omissions_path = self.root / "omissions.json"
        omissions_path.write_text(
            json.dumps({"omissions": [{"feature_id": "tabs.shift_open", "justification": "Deferred"}]}),
            encoding="utf-8",
        )

        # Standard mode allows partially-mocked
        passed_standard, report_std = preview_gate.run_preview_gate(
            sources=[src_path],
            preview_path=preview_path,
            omissions_path=omissions_path,
            strict=False,
        )
        self.assertTrue(passed_standard)
        self.assertEqual(report_std["counts"]["partially_mocked"], 1)

        # Strict mode rejects partially-mocked
        passed_strict, report_strict = preview_gate.run_preview_gate(
            sources=[src_path],
            preview_path=preview_path,
            omissions_path=omissions_path,
            strict=True,
        )
        self.assertFalse(passed_strict)
        self.assertTrue(any("partially-mocked" in r for r in report_strict["rejection_reasons"]))

    def test_report_generation_md_and_json_and_cli_exit_codes(self):
        """Test Markdown report, JSON report, and CLI exit code behavior."""
        src_path = self.root / "app-header-tabs.tsx"
        src_path.write_text(SAMPLE_APP_HEADER_TABS_TSX, encoding="utf-8")

        preview_html = """<!doctype html>
        <html>
          <body>
            <button title="Pin Tab" onclick="togglePin('tab1')">Pin</button>
            <script>
              let pinnedTabIds = [];
              function togglePin(id) { pinnedTabIds.push(id); }
            </script>
          </body>
        </html>
        """
        preview_path = self.root / "preview.html"
        preview_path.write_text(preview_html, encoding="utf-8")

        omissions_path = self.root / "omissions.json"
        omissions_path.write_text(
            json.dumps({"omissions": [{"feature_id": "tabs.shift_open", "justification": "Deferred to v2"}]}),
            encoding="utf-8",
        )

        md_out = self.root / "gate_report.md"
        json_out = self.root / "gate_report.json"

        # Run CLI with passing inputs
        cmd_pass = [
            sys.executable,
            str(SCRIPTS_DIR / "preview_gate.py"),
            "--sources",
            str(src_path),
            "--preview",
            str(preview_path),
            "--omissions",
            str(omissions_path),
            "--report-md",
            str(md_out),
            "--json",
            str(json_out),
        ]
        res_pass = subprocess.run(cmd_pass, capture_output=True, text=True)
        self.assertEqual(res_pass.returncode, 0)
        self.assertIn("[PASS]", res_pass.stdout)

        # Verify Markdown report content
        self.assertTrue(md_out.exists())
        md_text = md_out.read_text(encoding="utf-8")
        self.assertIn("# Preview Functional Coverage Quality Gate Report [GATE PASSED]", md_text)
        self.assertIn("| Feature ID | Component | Symbol Handler |", md_text)
        self.assertIn("tabs.pin_unpin", md_text)
        self.assertIn("[IMPLEMENTED]", md_text)
        self.assertIn("[OMITTED-WITH-JUSTIFICATION]", md_text)

        # Verify JSON report content
        self.assertTrue(json_out.exists())
        json_data = json.loads(json_out.read_text(encoding="utf-8"))
        self.assertTrue(json_data["gate_passed"])
        self.assertEqual(json_data["counts"]["implemented"], 1)
        self.assertEqual(json_data["counts"]["omitted_with_justification"], 1)

        # Run CLI without omissions to trigger exit code 1
        cmd_fail = [
            sys.executable,
            str(SCRIPTS_DIR / "preview_gate.py"),
            "--sources",
            str(src_path),
            "--preview",
            str(preview_path),
        ]
        res_fail = subprocess.run(cmd_fail, capture_output=True, text=True)
        self.assertEqual(res_fail.returncode, 1)
        self.assertIn("[FAIL]", res_fail.stderr)

    def test_zero_emoji_policy_compliance(self):
        """Assert zero Unicode emojis in scripts/preview_gate.py and tests/test_preview_gate.py."""
        script_file = SCRIPTS_DIR / "preview_gate.py"
        test_file = Path(__file__).resolve()

        self.assertIsNone(
            EMOJI_REGEX.search(script_file.read_text(encoding="utf-8")),
            "Emoji found in scripts/preview_gate.py",
        )
        self.assertIsNone(
            EMOJI_REGEX.search(test_file.read_text(encoding="utf-8")),
            "Emoji found in tests/test_preview_gate.py",
        )


if __name__ == "__main__":
    unittest.main()
