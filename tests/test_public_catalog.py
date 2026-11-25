import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("public_catalog", ROOT/"scripts/build_public_catalog.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CatalogTests(unittest.TestCase):
    def request(self,path,paginate=False):
        if path=="repos/ianmaciel7/exams-app":return {"private":False,"visibility":"public"}
        if "/branches?" in path:return [{"name":"dev","commit":{"sha":"a"*40}},{"name":"main","commit":{"sha":"a"*40}}]
        if "/tags?" in path:return [{"name":"v1","commit":{"sha":"a"*40}}]
        if "/commits/" in path:return {"commit":{"tree":{"sha":"b"*40}}}
        if "/git/trees/" in path:return {"truncated":False,"tree":[{"type":"blob","mode":"100644","sha":"c"*40,"path":"src/NewSidebar.tsx","size":20},{"type":"blob","mode":"100644","sha":"d"*40,"path":".env.example"},{"type":"blob","mode":"120000","sha":"e"*40,"path":"src/link.ts"}]}
        raise AssertionError(path)
    def test_discovery_and_deduplication(self):
        data=mod.build({"repositories":["ianmaciel7/exams-app"]},self.request)
        self.assertEqual(data["coverage"][0]["refs"],3)
        self.assertEqual(len(data["snapshots"]),1)
        self.assertEqual(data["snapshots"][0]["files"][0]["path"],"src/NewSidebar.tsx")
        self.assertEqual(len(data["snapshots"][0]["files"]),1)
    def test_private_fails_closed(self):
        with self.assertRaises(ValueError):
            mod.build({"repositories":["ianmaciel7/exams-app"]},lambda *a:{"private":True,"visibility":"private"})

    def test_canonical_empty_tree_does_not_require_api_object(self):
        def request(path, paginate=False):
            if "/commits/" in path:
                return {"commit":{"tree":{"sha":"4b825dc642cb6eb9a060e54bf8d69288fbee4904"}}}
            if "/git/trees/" in path:
                raise AssertionError("Empty tree must not be fetched")
            return self.request(path, paginate)
        data = mod.build({"repositories":["ianmaciel7/exams-app"]}, request)
        self.assertEqual(data["snapshots"][0]["files"], [])
        self.assertEqual(data["coverage"][0]["refs"], 3)
