import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("visual_reference_index", Path(__file__).resolve().parents[1] / "scripts/visual_reference_index.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class VisualReferenceTests(unittest.TestCase):
    def test_integrity(self):
        rows = mod.load()
        self.assertGreaterEqual(len(rows), 36)
        self.assertEqual(mod.verify(rows), [])
    def test_legacy_visual_copies_reconcile(self):
        result = mod.reconcile_legacy_assets(mod.load())
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["legacy_records"], 14)
        self.assertEqual(result["byte_verified"], 14)
        self.assertEqual(result["source_matched"], 14)
        self.assertEqual(result["canonical_copy_verified"], 14)
        self.assertEqual(result["semantic_inspection"], "not_assessed")

    def test_legacy_reconciliation_detects_missing_canonical_record(self):
        rows = [r for r in mod.load() if r["id"] != "excalidraw-collaboration"]
        result = mod.reconcile_legacy_assets(rows)
        self.assertFalse(result["integrity_passed"])
        self.assertTrue(any("canonical source mismatch" in e for e in result["errors"]))

    def test_segments(self):
        rows = mod.load()
        timed = [r for r in rows if r.get("segment_evidence")]
        for row in timed:
            e = row["segment_evidence"]
            self.assertEqual(e["source_blob_sha"], row["blob_sha"])
            self.assertGreaterEqual(len(e["keyframes"]), 2)
            self.assertLessEqual(len(e["keyframes"]), 3)
            self.assertIn(e["semantic_review"], {"not-inspected", "sampled-frames-reviewed"})
            if e["semantic_review"] == "sampled-frames-reviewed":
                self.assertEqual(len(e["observations"]), len(e["keyframes"]))
                for obs, frame in zip(e["observations"], e["keyframes"]):
                    self.assertEqual(obs["frame_sha256"], frame["sha256"])
                    self.assertEqual(obs["timestamp_seconds"], frame["timestamp_seconds"])
                self.assertIsNone(e["motion_contract"]["easing"])
            if e["clip"]:
                self.assertLessEqual(e["clip"]["duration_seconds"], 8.1)
    def test_search(self):
        self.assertTrue(mod.search(mod.load(), "side panel"))
        videos = mod.search(mod.load(), kind="video", status="archived-blob-verified")
        self.assertGreaterEqual(len(videos), 7)
        self.assertTrue(mod.search(videos, "storybook accessibility"))
        self.assertTrue(mod.search(mod.load(), "shadcn sidebar"))
        self.assertTrue(mod.search(mod.load(), "excalidraw wireframe"))
        self.assertTrue(mod.search(mod.load(), "kanban drag"))

if __name__ == "__main__":
    unittest.main()
