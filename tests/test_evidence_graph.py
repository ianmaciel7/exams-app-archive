#!/usr/bin/env python3
"""Unit tests for scripts/evidence_graph.py.

Covers:
- Event handler and shortcut extraction from TSX (onClick, onKeyDown, pointer, drag, drop, contextMenu, Shift/Escape/Ctrl)
- State reading and mutation tracking (useState, useReducer, zustand, localStorage, ARIA/data-attributes)
- UX motion contracts (intention dwell delay vs transition duration, easing, reduced motion, provenance)
- Multi-layer graph traversal with bounded 1-3 hops, token budgeting, and gap reporting
- Canonical query test for 'app-shell'
- CLI interface and export evidence
- Zero Emoji Policy enforcement

Zero external dependencies (Python standard library only).
Zero Unicode emoji policy strictly enforced.
"""
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

import evidence_graph  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


SAMPLE_COMPLEX_TSX = """
import React, { useState, useReducer, useEffect } from 'react';
import { create } from 'zustand';

interface Props {
  initialPinned?: boolean;
}

export function TabManager({ initialPinned = false }: Props) {
  const [pinned, setPinned] = useState<boolean>(initialPinned);
  const [dragging, setDragging] = useState<boolean>(false);
  const [query, setQuery] = useState<string>('');

  const [filterState, dispatchFilter] = useReducer((state: any, action: any) => {
    switch (action.type) {
      case 'RESET': return { ...state, filter: '' };
      default: return state;
    }
  }, { filter: '' });

  const storedLayout = localStorage.getItem('notes-layout-pref');

  useEffect(() => {
    const timer = setTimeout(() => {
      console.log('Intention dwell delay triggered');
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const handleToggle = () => {
    setPinned(!pinned);
    localStorage.setItem('notes-layout-pref', JSON.stringify({ pinned: !pinned }));
  };

  return (
    <div
      className="tab-manager-root transition-all duration-300 ease-out motion-reduce:transition-none"
      data-state={pinned ? 'pinned' : 'idle'}
      data-pinned={pinned ? 'true' : 'false'}
      aria-expanded={pinned}
      aria-selected={dragging}
      onContextMenu={(e) => {
        e.preventDefault();
        console.log('Context menu triggered');
      }}
    >
      <button
        type="button"
        className="pin-button duration-150"
        onClick={(event) => {
          if (event.shiftKey) {
            console.log('Shift+Click action');
          } else {
            handleToggle();
          }
        }}
        onPointerEnter={(e) => {
          console.log('Hover preview intention');
        }}
        onPointerLeave={() => {
          console.log('Hover close');
        }}
      >
        Toggle Pin
      </button>

      <button
        type="button"
        className="new-tab-button"
        onClick={(event) => {
          if (event.metaKey || event.ctrlKey) {
            console.log('Ctrl/Cmd+Click action');
          }
        }}
      >
        New Tab
      </button>

      <div
        className="draggable-tab"
        draggable
        onDragStart={(e) => {
          setDragging(true);
        }}
        onDrop={(e) => {
          setDragging(false);
        }}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            setDragging(false);
          } else if (event.metaKey || event.ctrlKey) {
            console.log('Ctrl shortcut');
          }
        }}
      >
        Draggable Item
      </div>
    </div>
  );
}
"""


class EvidenceGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.db_path = self.tmp_path / "evidence_test.sqlite"
        self.conn = evidence_graph.open_db(self.db_path)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def test_event_handler_and_shortcut_extraction_from_tsx(self) -> None:
        """Verify extraction of event handlers and shortcuts with exact line ranges."""
        components = evidence_graph.parse_tsx_file(SAMPLE_COMPLEX_TSX, path="src/components/tab-manager.tsx")
        self.assertEqual(len(components), 1)
        comp = components[0]
        self.assertEqual(comp.name, "TabManager")

        handlers = comp.event_handlers
        self.assertGreater(len(handlers), 0)

        events_found = {h.event_name for h in handlers}
        self.assertIn("onClick", events_found)
        self.assertIn("onPointerEnter", events_found)
        self.assertIn("onPointerLeave", events_found)
        self.assertIn("onDragStart", events_found)
        self.assertIn("onDrop", events_found)
        self.assertIn("onKeyDown", events_found)
        self.assertIn("onContextMenu", events_found)

        # Check line ranges
        for h in handlers:
            self.assertGreater(h.line_start, 0)
            self.assertGreaterEqual(h.line_end, h.line_start)
            self.assertTrue(bool(h.snippet))

        # Check shortcuts
        shortcuts_found = {h.shortcut for h in handlers if h.shortcut}
        self.assertIn("Shift+Click", shortcuts_found)
        self.assertIn("Escape", shortcuts_found)
        self.assertIn("Ctrl/Cmd+Click", shortcuts_found)

    def test_state_reading_mutation_tracking_and_aria_data_state(self) -> None:
        """Verify tracking of useState, useReducer, localStorage, and DOM/ARIA attributes."""
        components = evidence_graph.parse_tsx_file(SAMPLE_COMPLEX_TSX, path="src/components/tab-manager.tsx")
        comp = components[0]
        state_bindings = comp.state_bindings
        kinds_found = {s.binding_kind for s in state_bindings}

        # Check useState
        self.assertIn("useState", kinds_found)
        state_names = {s.variable for s in state_bindings if s.binding_kind == "useState"}
        self.assertIn("pinned", state_names)
        self.assertIn("dragging", state_names)
        self.assertIn("query", state_names)

        # Check useReducer
        self.assertIn("useReducer", kinds_found)
        reducer_names = {s.variable for s in state_bindings if s.binding_kind == "useReducer"}
        self.assertIn("filterState", reducer_names)

        # Check localStorage
        self.assertIn("localStorage", kinds_found)
        ls_binding = next(s for s in state_bindings if s.binding_kind == "localStorage")
        self.assertIn("notes-layout-pref", ls_binding.name)
        self.assertGreater(len(ls_binding.reads), 0)
        self.assertGreater(len(ls_binding.mutations), 0)

        # Check ARIA and data attributes
        self.assertIn("aria_attr", kinds_found)
        self.assertIn("data_attr", kinds_found)
        attr_names = {s.name for s in state_bindings if s.binding_kind in ("aria_attr", "data_attr")}
        self.assertTrue(any("aria-expanded" in a for a in attr_names))
        self.assertTrue(any("aria-selected" in a for a in attr_names))
        self.assertTrue(any("data-state" in a for a in attr_names))
        self.assertTrue(any("data-pinned" in a for a in attr_names))

    def test_motion_contract_dwell_vs_duration_distinction(self) -> None:
        """Verify distinction between intention dwell/delay and transition duration."""
        components = evidence_graph.parse_tsx_file(SAMPLE_COMPLEX_TSX, path="src/components/tab-manager.tsx")
        comp = components[0]
        motion = comp.motion_contracts
        self.assertGreater(len(motion), 0)

        # Verify dwell delay vs transition duration
        dwells = [m.dwell_delay_ms for m in motion if m.dwell_delay_ms is not None]
        durations = [m.transition_duration_ms for m in motion if m.transition_duration_ms is not None]

        self.assertIn(250.0, dwells)
        self.assertTrue(any(d in (300.0, 150.0) for d in durations))

        # Verify easing and reduced motion
        easings = [m.easing for m in motion if m.easing]
        self.assertIn("ease-out", easings)
        red_motions = [m.reduced_motion for m in motion if m.reduced_motion]
        self.assertTrue(any("motion-reduce:transition-none" in rm for rm in red_motions))

        # Ingest into DB and verify provenance
        evidence_graph.ingest_tsx_file(self.conn, "src/components/tab-manager.tsx", SAMPLE_COMPLEX_TSX)
        rows = self.conn.execute("SELECT * FROM graph_nodes WHERE node_type='MotionContract'").fetchall()
        self.assertGreater(len(rows), 0)
        for r in rows:
            meta = json.loads(r["metadata_json"])
            self.assertIn(meta.get("provenance"), evidence_graph.PROVENANCE_SET)

    def test_multi_hop_traversal_token_budgeting_and_gap_reporting(self) -> None:
        """Verify bounded 1-3 hop traversals, token budget limit, and gap reporting."""
        evidence_graph.build_canonical_notes_evidence(self.conn)

        # Hop bounding checks
        res_hop1 = evidence_graph.traverse_evidence_graph(self.conn, "app-shell", hops=1, token_budget=4000)
        self.assertEqual(res_hop1["feature_matrix"]["hops"], 1)

        res_hop2 = evidence_graph.traverse_evidence_graph(self.conn, "app-shell", hops=2, token_budget=4000)
        self.assertEqual(res_hop2["feature_matrix"]["hops"], 2)

        res_hop3 = evidence_graph.traverse_evidence_graph(self.conn, "app-shell", hops=3, token_budget=4000)
        self.assertEqual(res_hop3["feature_matrix"]["hops"], 3)

        # Token budget limit verification
        budget = 500
        res_budget = evidence_graph.traverse_evidence_graph(self.conn, "app-shell", hops=2, token_budget=budget)
        tokens_used = res_budget["feature_matrix"]["tokens_used"]
        self.assertLessEqual(tokens_used, budget)

        # Verify token pruning gaps were logged
        pruned_gaps = [g for g in res_budget["uninspected_gaps"] if g["gap_type"] == "token_budget_pruned"]
        self.assertGreater(len(pruned_gaps), 0)

        # Verify hop boundary gaps were logged
        hop_gaps = [g for g in res_hop1["uninspected_gaps"] if g["gap_type"] == "hop_boundary"]
        self.assertGreater(len(hop_gaps), 0)

        # Verify structured payload format
        self.assertIn("feature_matrix", res_hop2)
        self.assertIn("evidence_bundle", res_hop2)
        self.assertIn("uninspected_gaps", res_hop2)

        bundle = res_hop2["evidence_bundle"]
        self.assertIn("component", bundle)
        self.assertIn("files", bundle)
        self.assertIn("symbols", bundle)
        self.assertIn("handlers", bundle)
        self.assertIn("state", bundle)
        self.assertIn("motion", bundle)
        self.assertIn("docs_and_adrs", bundle)
        self.assertIn("screenshots", bundle)

    def test_canonical_query_app_shell(self) -> None:
        """Canonical test: querying 'app-shell' returns app-header-tabs.tsx (pin tab),

        app-sidebar-overview.tsx (pinned section), handlers, state, motion, and decisions.
        """
        evidence_graph.build_canonical_notes_evidence(self.conn)
        result = evidence_graph.traverse_evidence_graph(self.conn, "app-shell", hops=2, token_budget=4000)

        bundle = result["evidence_bundle"]
        files = [f["label"] for f in bundle["files"]]
        self.assertIn("app-header-tabs.tsx", files)
        self.assertIn("app-sidebar-overview.tsx", files)

        handlers = bundle["handlers"]
        handlers_text = " ".join(h["label"] + " " + str(h.get("metadata", {})) for h in handlers)
        self.assertTrue(
            "pin" in handlers_text.lower(),
            f"Expected 'pin' in handlers, got: {[h['label'] for h in handlers]}",
        )

        state = bundle["state"]
        state_text = " ".join(s["label"] + " " + str(s.get("metadata", {})) for s in state)
        self.assertTrue(
            "pin" in state_text.lower() or "drag" in state_text.lower() or "aria" in state_text.lower(),
            f"Expected pin/drag/aria state bindings, got: {[s['label'] for s in state]}",
        )

        motion = bundle["motion"]
        self.assertGreater(len(motion), 0)

        decisions = bundle["docs_and_adrs"]
        self.assertGreaterEqual(len(decisions), 2)
        dec_labels = [d["label"] for d in decisions]
        self.assertTrue(any("spec" in l.lower() or "design" in l.lower() or "tasks" in l.lower() for l in dec_labels))

        # Check feature matrix component summaries
        fm_comps = result["feature_matrix"]["components"]
        comp_names = [c["name"] for c in fm_comps]
        self.assertTrue(any("AppShell" in n for n in comp_names))

    def test_cli_execution_and_export(self) -> None:
        """Verify command line execution and JSON evidence export."""
        evidence_graph.build_canonical_notes_evidence(self.conn)
        self.conn.commit()
        self.conn.close()
        export_file = self.tmp_path / "exported_evidence.json"

        cmd = [
            sys.executable,
            str(SCRIPTS_DIR / "evidence_graph.py"),
            "--db",
            str(self.db_path),
            "--query",
            "app-shell",
            "--hops",
            "2",
            "--token-budget",
            "4000",
            "--export-evidence",
            str(export_file),
            "--json",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(proc.stdout)
        self.assertIn("feature_matrix", data)
        self.assertIn("evidence_bundle", data)

        self.assertTrue(export_file.is_file())
        file_data = json.loads(export_file.read_text(encoding="utf-8"))
        self.assertEqual(data["feature_matrix"]["query"], file_data["feature_matrix"]["query"])

    def test_zero_emoji_policy(self) -> None:
        """Strictly enforce Zero Emoji Policy on code, tests, and outputs."""
        for target in (SCRIPTS_DIR / "evidence_graph.py", Path(__file__)):
            content = target.read_text(encoding="utf-8")
            matches = EMOJI_REGEX.findall(content)
            self.assertEqual(
                matches,
                [],
                f"Found Unicode emojis in {target}: {matches}",
            )


if __name__ == "__main__":
    unittest.main()
