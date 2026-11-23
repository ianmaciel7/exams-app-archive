#!/usr/bin/env python3
"""Offline tests for the private historical image catalog (synthetic Git repos/bundles)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import image_catalog  # noqa: E402

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


def make_png(width: int, height: int) -> bytes:
    """Create a minimal valid RGBA PNG with exact IHDR dimensions using stdlib only."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(ctype: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + ctype + payload + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw_scanlines = b"".join(b"\x00" + (b"\x20\x80\xff\xff" * width) for _ in range(height))
    idat = zlib.compress(raw_scanlines)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def make_gif(width: int, height: int) -> bytes:
    """Create a minimal valid GIF89a header + empty image block with exact dimensions."""
    header = b"GIF89a" + struct.pack("<HHBBB", width, height, 0x80, 0, 0)
    gct = b"\x00\x00\x00\xff\xff\xff"
    trailer = b"\x3b"
    return header + gct + trailer


def make_jpeg_sof0(width: int, height: int) -> bytes:
    """Create minimal JPEG byte stream containing SOF0 dimensions."""
    soi = b"\xff\xd8"
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0_payload = struct.pack(">BHHB", 8, height, width, 1) + b"\x01\x11\x00"
    sof0 = b"\xff\xc0" + struct.pack(">H", len(sof0_payload) + 2) + sof0_payload
    eoi = b"\xff\xd9"
    return soi + app0 + sof0 + eoi


class ImageCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        run_git("init", "-q", "-b", "main", str(self.work))
        run_git("config", "user.email", "catalog-test@example.invalid", cwd=self.work)
        run_git("config", "user.name", "Catalog Test", cwd=self.work)

        # Commit 1: PNG, GIF, JPG, and SVG with an embedded <script> tag
        self.png_bytes = make_png(32, 18)
        self.gif_bytes = make_gif(24, 12)
        self.jpg_bytes = make_jpeg_sof0(64, 48)
        self.svg_bytes = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<svg xmlns="http://www.w3.org/2000/svg" width="120px" height="80px" viewBox="0 0 120 80">\n'
            b'  <script>throw new Error("must never execute");</script>\n'
            b'  <rect x="0" y="0" width="120" height="80" fill="#111"/>\n'
            b"</svg>\n"
        )
        self.deleted_png_bytes = make_png(10, 14)

        (self.work / "assets").mkdir()
        (self.work / "assets" / "sidebar-v1.png").write_bytes(self.png_bytes)
        (self.work / "assets" / "anim.gif").write_bytes(self.gif_bytes)
        (self.work / "assets" / "photo.jpg").write_bytes(self.jpg_bytes)
        (self.work / "assets" / "grafo.svg").write_bytes(self.svg_bytes)
        (self.work / "assets" / "old-sidebar.png").write_bytes(self.deleted_png_bytes)

        run_git("add", ".", cwd=self.work)
        run_git("commit", "-qm", "feat: initial historical images", cwd=self.work)
        self.initial_commit = run_git("rev-parse", "HEAD", cwd=self.work).strip()

        # Commit 2: delete old-sidebar.png to test deleted historical image tracking
        (self.work / "assets" / "old-sidebar.png").unlink()
        run_git("add", "-u", cwd=self.work)
        run_git("commit", "-qm", "chore: remove old sidebar screenshot", cwd=self.work)
        self.delete_commit = run_git("rev-parse", "HEAD", cwd=self.work).strip()

        self.bare = self.root / "source.git"
        run_git("clone", "--mirror", "-q", str(self.work), str(self.bare))
        self.bundle = self.root / "source.bundle"
        run_git("--git-dir=" + str(self.bare), "bundle", "create", str(self.bundle), "--all")

    def test_catalog_dimensions_sha_deleted_and_inert_svg(self):
        catalog = image_catalog.catalog_git_source(
            self.bare,
            origin="exams-app-synthetic",
            check_paths=["assets/nonexistent.png"],
            force_no_pillow=True,
        )
        self.assertEqual(catalog["version"], 1)
        self.assertTrue(catalog["private"])
        self.assertEqual(catalog["origin"], "exams-app-synthetic")
        self.assertFalse(catalog["pillow_available"])

        items_by_path = {item["path"]: item for item in catalog["items"]}
        self.assertIn("assets/sidebar-v1.png", items_by_path)
        self.assertIn("assets/anim.gif", items_by_path)
        self.assertIn("assets/photo.jpg", items_by_path)
        self.assertIn("assets/grafo.svg", items_by_path)
        self.assertIn("assets/old-sidebar.png", items_by_path)
        self.assertIn("assets/nonexistent.png", items_by_path)

        png_item = items_by_path["assets/sidebar-v1.png"]
        self.assertEqual(png_item["extension"], ".png")
        self.assertEqual(png_item["width"], 32)
        self.assertEqual(png_item["height"], 18)
        self.assertEqual(png_item["sha256"], hashlib.sha256(self.png_bytes).hexdigest())
        self.assertFalse(png_item["deleted"])
        self.assertEqual(png_item["status"], "present")
        self.assertEqual(png_item["ref"], "refs/heads/main")
        self.assertEqual(png_item["commit"], self.delete_commit)

        gif_item = items_by_path["assets/anim.gif"]
        self.assertEqual((gif_item["width"], gif_item["height"]), (24, 12))
        self.assertEqual(gif_item["sha256"], hashlib.sha256(self.gif_bytes).hexdigest())

        jpg_item = items_by_path["assets/photo.jpg"]
        self.assertEqual((jpg_item["width"], jpg_item["height"]), (64, 48))
        self.assertEqual(jpg_item["sha256"], hashlib.sha256(self.jpg_bytes).hexdigest())

        svg_item = items_by_path["assets/grafo.svg"]
        self.assertEqual((svg_item["width"], svg_item["height"]), (120, 80))
        self.assertEqual(svg_item["sha256"], hashlib.sha256(self.svg_bytes).hexdigest())
        self.assertTrue(svg_item["inert"])
        self.assertTrue(svg_item["script_detected"])
        self.assertEqual(svg_item["thumbnail_status"], "skipped_inert_svg")
        self.assertIsNone(svg_item["thumbnail"])

        deleted_item = items_by_path["assets/old-sidebar.png"]
        self.assertTrue(deleted_item["deleted"])
        self.assertEqual(deleted_item["status"], "deleted")
        self.assertEqual(deleted_item["commit"], self.initial_commit)
        self.assertEqual(deleted_item["deleted_in_commit"], self.delete_commit)
        self.assertEqual((deleted_item["width"], deleted_item["height"]), (10, 14))
        self.assertEqual(
            deleted_item["sha256"],
            hashlib.sha256(self.deleted_png_bytes).hexdigest(),
        )

        missing_item = items_by_path["assets/nonexistent.png"]
        self.assertTrue(missing_item["missing"])
        self.assertEqual(missing_item["status"], "missing")
        self.assertIsNone(missing_item["sha256"])
        self.assertIsNone(missing_item["width"])
        self.assertEqual(missing_item["thumbnail_status"], "skipped_missing")

    def test_bundle_source_and_pagination_limits(self):
        page1 = image_catalog.catalog_git_source(
            self.bundle,
            origin="bundle-source",
            page=1,
            page_size=2,
            force_no_pillow=True,
        )
        page2 = image_catalog.catalog_git_source(
            self.bundle,
            origin="bundle-source",
            page=2,
            page_size=2,
            force_no_pillow=True,
        )
        page3 = image_catalog.catalog_git_source(
            self.bundle,
            origin="bundle-source",
            page=3,
            page_size=2,
            force_no_pillow=True,
        )
        self.assertEqual(page1["source_type"], "bundle")
        self.assertEqual(page1["pagination"]["total_items"], 5)
        self.assertEqual(page1["pagination"]["total_pages"], 3)
        self.assertTrue(page1["pagination"]["has_next"])
        self.assertFalse(page1["pagination"]["has_prev"])
        self.assertEqual(len(page1["items"]), 2)
        self.assertEqual(len(page2["items"]), 2)
        self.assertEqual(len(page3["items"]), 1)
        self.assertFalse(page3["pagination"]["has_next"])
        self.assertTrue(page3["pagination"]["has_prev"])

        seen_paths = [i["path"] for i in page1["items"] + page2["items"] + page3["items"]]
        self.assertEqual(len(seen_paths), len(set(seen_paths)))

        with self.assertRaises(ValueError):
            image_catalog.catalog_git_source(self.bundle, page=0)
        with self.assertRaises(ValueError):
            image_catalog.catalog_git_source(self.bundle, page_size=image_catalog.MAX_PAGE_SIZE + 1)
        with self.assertRaises(ValueError):
            image_catalog.catalog_git_source(self.bundle, limit=image_catalog.MAX_LIMIT + 1)

    def test_stdlib_fallback_skips_non_png_thumbnails_and_keeps_dimensions(self):
        thumb_dir = self.root / "thumbs"
        catalog1 = image_catalog.catalog_git_source(
            self.bare,
            origin="no-pillow-test",
            thumb_dir=thumb_dir,
            thumb_size=16,
            force_no_pillow=True,
        )
        catalog2 = image_catalog.catalog_git_source(
            self.bare,
            origin="no-pillow-test",
            thumb_dir=thumb_dir,
            thumb_size=16,
            force_no_pillow=True,
        )
        png1 = next(i for i in catalog1["items"] if i["path"] == "assets/sidebar-v1.png")
        png2 = next(i for i in catalog2["items"] if i["path"] == "assets/sidebar-v1.png")
        self.assertEqual((png1["width"], png1["height"]), (32, 18))
        self.assertEqual(png1["thumbnail_status"], "generated")
        self.assertEqual(png1["thumbnail_sha256"], png2["thumbnail_sha256"])
        self.assertEqual(png1["thumbnail_dimensions"], {"width": 16, "height": 9})

        jpg = next(i for i in catalog1["items"] if i["path"] == "assets/photo.jpg")
        self.assertEqual((jpg["width"], jpg["height"]), (64, 48))
        self.assertEqual(jpg["thumbnail_status"], "skipped_no_pillow")
        self.assertIsNone(jpg["thumbnail"])

        gif = next(i for i in catalog1["items"] if i["path"] == "assets/anim.gif")
        self.assertEqual((gif["width"], gif["height"]), (24, 12))
        self.assertEqual(gif["thumbnail_status"], "skipped_no_pillow")
        self.assertIsNone(gif["thumbnail"])

        svg = next(i for i in catalog1["items"] if i["path"] == "assets/grafo.svg")
        self.assertEqual((svg["width"], svg["height"]), (120, 80))
        self.assertEqual(svg["thumbnail_status"], "skipped_inert_svg")
        self.assertIsNone(svg["thumbnail"])

    def test_refuses_writing_inside_site_directory(self):
        with self.assertRaises(ValueError):
            image_catalog.validate_private_output_path(ROOT / "site" / "catalog.json")
        with self.assertRaises(ValueError):
            image_catalog.validate_private_output_path(Path("site/thumbs"))

    def test_cli_private_json_output(self):
        out_json = self.root / "private-catalog.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "image_catalog.py"),
                "--source",
                str(self.bundle),
                "--origin",
                "cli-test",
                "--query",
                "sidebar",
                "--no-pillow",
                "--output",
                str(out_json),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(data["summary"]["total_images"], 2)
        paths = {i["path"] for i in data["items"]}
        self.assertEqual(paths, {"assets/sidebar-v1.png", "assets/old-sidebar.png"})

    def test_zero_emoji_policy(self):
        for rel in ("scripts/image_catalog.py", "tests/test_image_catalog.py"):
            content = (ROOT / rel).read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(content), [], f"Found emoji in {rel}")


if __name__ == "__main__":
    unittest.main()
