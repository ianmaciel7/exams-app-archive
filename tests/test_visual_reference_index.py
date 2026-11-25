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
