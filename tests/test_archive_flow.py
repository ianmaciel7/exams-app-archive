#!/usr/bin/env python3
"""End-to-end offline tests for scripts/archive_flow.py using synthetic Git repos and bundles."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zlib
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import archive_flow  # noqa: E402
import content_index  # noqa: E402

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")


def run_git(*args: str, cwd: Path | None = None, env: dict | None = None) -> str:
    eff_env = dict(os.environ)
    if env:
        eff_env.update(env)
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=eff_env,
    )
    return proc.stdout


def make_png(width: int, height: int) -> bytes:
    """Create a valid deterministic RGBA PNG using stdlib only."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(ctype: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + ctype + payload + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    rows = b"".join(b"\x00" + (b"\x10\x60\xd0\xff" * width) for _ in range(height))
    idat = zlib.compress(rows, level=6)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


class ArchiveFlowEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()

        run_git("init", "-q", "-b", "main", str(self.work))
        run_git("config", "user.email", "flow-test@example.invalid", cwd=self.work)
        run_git("config", "user.name", "Flow Test", cwd=self.work)

        (self.work / "src").mkdir()
        (self.work / "docs").mkdir()
        (self.work / "assets").mkdir()

        # Commit 1: code, markdown, active image, deleted code, deleted image, and secret file
        code_lines = [f"// preamble line {i}" for i in range(1, 55)]
        code_lines.extend(
            [
                "export function buildExamSidebar(collapsed: boolean) {",
                "  return { panel: 'capacities-sidebar', collapsed };",
                "}",
            ]
        )
        self.sidebar_text = "\n".join(code_lines) + "\n"
        self.sidebar_bytes = self.sidebar_text.encode("utf-8")
        (self.work / "src" / "sidebar.ts").write_bytes(self.sidebar_bytes)

        self.markdown_text = (
            "# Sidebar Decisions\n\n"
            "Historical `capacities-sidebar` specification and layout notes.\n"
        )
        self.markdown_bytes = self.markdown_text.encode("utf-8")
        (self.work / "docs" / "decisions.md").write_bytes(self.markdown_bytes)

        self.active_png = make_png(48, 24)
        (self.work / "assets" / "sidebar-preview.png").write_bytes(self.active_png)

        self.deleted_code_text = (
            "export const DELETED_GRAPH_ENGINE = 'legacy-force-layout-v1';\n"
            "export function runLegacyGraph() { return DELETED_GRAPH_ENGINE; }\n"
        )
        self.deleted_code_bytes = self.deleted_code_text.encode("utf-8")
        (self.work / "src" / "legacy_graph.ts").write_bytes(self.deleted_code_bytes)

        self.deleted_png = make_png(32, 16)
        (self.work / "assets" / "removed-grafo.png").write_bytes(self.deleted_png)

        self.svg_bytes = (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="32" viewBox="0 0 64 32">\n'
            b'  <script>alert("never-run");</script>\n'
            b'  <rect width="64" height="32" fill="#222"/>\n'
            b"</svg>\n"
        )
        (self.work / "assets" / "icon.svg").write_bytes(self.svg_bytes)

        (self.work / ".env").write_text("SECRET_TOKEN=ghp_syntheticFlowSecretTokenValue123456\n", encoding="utf-8")

        run_git("add", ".", cwd=self.work)
        run_git("commit", "-qm", "feat: initial synthetic archive fixtures", cwd=self.work)
        self.initial_sha = run_git("rev-parse", "HEAD", cwd=self.work).strip()

        # Commit 2 on main: delete legacy_graph.ts and removed-grafo.png
        (self.work / "src" / "legacy_graph.ts").unlink()
        (self.work / "assets" / "removed-grafo.png").unlink()
        run_git("add", "-u", cwd=self.work)
        run_git("commit", "-qm", "chore: remove legacy graph module and screenshot", cwd=self.work)
        self.main_sha = run_git("rev-parse", "HEAD", cwd=self.work).strip()

        self.bare = self.root / "synthetic.git"
        run_git("clone", "--mirror", "-q", str(self.work), str(self.bare))
        self.bundle = self.root / "synthetic.bundle"
        run_git("--git-dir=" + str(self.bare), "bundle", "create", str(self.bundle), "--all")

        self.db_path = self.root / "content-index.sqlite"
        conn = content_index.open_db(self.db_path)
        try:
            content_index.ingest_repo(self.bundle, "exams-app-synthetic", conn)
        finally:
            conn.close()

    def _assert_structured_fields(self, doc: dict, *, expect_content_key: str) -> None:
        for field in ("source_repo", "ref", "full_sha", "path", "mime", "sha256", expect_content_key, "tokens"):
            self.assertIn(field, doc, f"Missing required field {field!r}")
        self.assertRegex(doc["full_sha"], r"^[0-9a-f]{40,64}$")
        self.assertRegex(doc["sha256"], r"^[0-9a-f]{64}$")
        self.assertGreater(doc["tokens"]["estimated_tokens"], 0)

    def test_end_to_end_code_and_markdown_flow(self):
        # 1. Search -> finds TypeScript code and Markdown deterministically
        search_res = archive_flow.flow_search(
            "capacities-sidebar",
            db_path=self.db_path,
            source=self.bundle,
            repo="exams-app-synthetic",
            limit=10,
        )
        self.assertTrue(search_res["ok"])
        self.assertGreaterEqual(search_res["returned"], 2)
        self.assertGreater(search_res["tokens"]["estimated_tokens"], 0)

        by_path = {r["path"]: r for r in search_res["results"]}
        self.assertIn("src/sidebar.ts", by_path)
        self.assertIn("docs/decisions.md", by_path)

        ts_hit = by_path["src/sidebar.ts"]
        self.assertEqual(ts_hit["mime"], "text/typescript")
        self.assertEqual(ts_hit["sha256"], hashlib.sha256(self.sidebar_bytes).hexdigest())
        self.assertEqual(ts_hit["full_sha"], self.main_sha)
        self.assertEqual(ts_hit["ref"], "refs/heads/main")

        md_hit = by_path["docs/decisions.md"]
        self.assertEqual(md_hit["mime"], "text/markdown")
        self.assertEqual(md_hit["sha256"], hashlib.sha256(self.markdown_bytes).hexdigest())

        # 2. Preview -> bounded deterministic line slice
        prev_res = archive_flow.flow_preview(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=ts_hit["full_sha"],
            ref=ts_hit["ref"],
            path=ts_hit["path"],
            start_line=1,
            max_lines=10,
        )
        self._assert_structured_fields(prev_res, expect_content_key="preview")
        self.assertTrue(prev_res["truncated"])
        self.assertEqual(prev_res["start_line"], 1)
        self.assertEqual(prev_res["end_line"], 10)
        self.assertEqual(prev_res["sha256"], ts_hit["sha256"])

        # 3. Fetch -> targeted line range matching original evidence
        fetch_res = archive_flow.flow_fetch(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=ts_hit["full_sha"],
            ref=ts_hit["ref"],
            path=ts_hit["path"],
            start_line=ts_hit["start_line"],
            end_line=ts_hit["end_line"],
            expected_sha256=ts_hit["sha256"],
        )
        self._assert_structured_fields(fetch_res, expect_content_key="content")
        self.assertEqual(fetch_res["content"], ts_hit["preview"])
        self.assertFalse(fetch_res["deleted_at_ref_head"])

        # 4. Recover -> full markdown verification and exact-byte private file output
        out_md = self.root / "recovered" / "decisions.md"
        rec_res = archive_flow.flow_recover(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=md_hit["full_sha"],
            ref=md_hit["ref"],
            path=md_hit["path"],
            output=out_md,
            expected_sha256=md_hit["sha256"],
        )
        self._assert_structured_fields(rec_res, expect_content_key="content")
        self.assertTrue(rec_res["recovered"])
        self.assertEqual(rec_res["output_sha256"], md_hit["sha256"])
        self.assertEqual(out_md.read_bytes(), self.markdown_bytes)

        # 5. Fetch with start_line only -> returns bounded tail slice cleanly
        tail_res = archive_flow.flow_fetch(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=ts_hit["full_sha"],
            ref=ts_hit["ref"],
            path=ts_hit["path"],
            start_line=55,
        )
        self._assert_structured_fields(tail_res, expect_content_key="content")
        self.assertEqual(tail_res["start_line"], 55)
        self.assertIn("buildExamSidebar", tail_res["content"])

    def test_end_to_end_image_and_deleted_artifacts_flow(self):
        # Search for images (both active and deleted)
        img_search = archive_flow.flow_search(
            "sidebar",
            source=self.bundle,
            repo="exams-app-synthetic",
            kind="image",
            limit=10,
        )
        self.assertEqual(img_search["returned"], 1)
        img_hit = img_search["results"][0]
        self.assertEqual(img_hit["path"], "assets/sidebar-preview.png")
        self.assertEqual(img_hit["mime"], "image/png")
        self.assertEqual(img_hit["sha256"], hashlib.sha256(self.active_png).hexdigest())

        # Preview active image -> returns base64 bytes and inert/thumbnail metadata
        img_prev = archive_flow.flow_preview(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=img_hit["full_sha"],
            ref=img_hit["ref"],
            path=img_hit["path"],
            thumb_size=16,
            force_no_pillow=True,
        )
        self._assert_structured_fields(img_prev, expect_content_key="preview")
        self.assertEqual(img_prev["encoding"], "base64")
        preview_bytes = base64.b64decode(img_prev["content_base64"])
        self.assertTrue(preview_bytes.startswith(b"\x89PNG"))

        # Search and recover deleted code file
        del_code_search = archive_flow.flow_search(
            "DELETED_GRAPH_ENGINE",
            db_path=self.db_path,
            source=self.bundle,
            status="deleted",
            limit=5,
        )
        self.assertEqual(del_code_search["returned"], 1)
        del_code_hit = del_code_search["results"][0]
        self.assertEqual(del_code_hit["full_sha"], self.initial_sha)
        self.assertEqual(del_code_hit["path"], "src/legacy_graph.ts")

        del_code_rec = archive_flow.flow_recover(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=del_code_hit["full_sha"],
            path=del_code_hit["path"],
            expected_sha256=hashlib.sha256(self.deleted_code_bytes).hexdigest(),
        )
        self._assert_structured_fields(del_code_rec, expect_content_key="content")
        self.assertIn("DELETED_GRAPH_ENGINE", del_code_rec["content"])
        self.assertTrue(del_code_rec["deleted_at_ref_head"])

        # Search and recover deleted PNG image as verified base64 bytes
        del_img_search = archive_flow.flow_search(
            "removed-grafo",
            source=self.bundle,
            repo="exams-app-synthetic",
            kind="image",
            status="deleted",
            limit=5,
        )
        self.assertEqual(del_img_search["returned"], 1)
        del_img_hit = del_img_search["results"][0]
        self.assertEqual(del_img_hit["full_sha"], self.initial_sha)

        out_png = self.root / "recovered" / "removed-grafo.png"
        del_img_rec = archive_flow.flow_recover(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=del_img_hit["full_sha"],
            path=del_img_hit["path"],
            expected_sha256=del_img_hit["sha256"],
            output=out_png,
        )
        self._assert_structured_fields(del_img_rec, expect_content_key="content_base64")
        decoded_png = base64.b64decode(del_img_rec["content_base64"])
        self.assertEqual(decoded_png, self.deleted_png)
        self.assertEqual(out_png.read_bytes(), self.deleted_png)
        self.assertEqual(del_img_rec["sha256"], hashlib.sha256(self.deleted_png).hexdigest())

        # SVG preview stays inert and marks script_detected
        svg_prev = archive_flow.flow_preview(
            source=self.bundle,
            sha=self.main_sha,
            path="assets/icon.svg",
        )
        self.assertTrue(svg_prev["inert"])
        self.assertTrue(svg_prev["script_detected"])
        self.assertEqual(svg_prev["mime"], "image/svg+xml")

    def test_explicit_errors_and_limited_retry(self):
        # 1. Not found path
        with self.assertRaises(archive_flow.NotFoundError):
            archive_flow.flow_fetch(
                source=self.bundle,
                sha=self.main_sha,
                path="src/does-not-exist.ts",
            )

        # 2. Missing release offline
        with self.assertRaises(archive_flow.ReleaseMissingError):
            archive_flow.resolve_release_asset(
                release_tag="archive-missing-tag",
                asset="exams-app.bundle",
                release_dir=self.root / "releases",
            )

        # 3. Checksum mismatch
        with self.assertRaises(archive_flow.ChecksumMismatchError):
            archive_flow.flow_fetch(
                source=self.bundle,
                sha=self.main_sha,
                path="src/sidebar.ts",
                expected_sha256="0" * 64,
            )

        # 4. Size limit & payload limit
        with self.assertRaises(archive_flow.SizeLimitExceededError):
            archive_flow.flow_fetch(
                source=self.bundle,
                sha=self.main_sha,
                path="src/sidebar.ts",
                max_bytes=16,
            )

        with self.assertRaises(archive_flow.PayloadLimitExceededError):
            archive_flow.flow_fetch(
                source=self.bundle,
                sha=self.main_sha,
                path="assets/sidebar-preview.png",
                max_payload_bytes=64,
            )

        # 5. Secret path blocked explicitly
        with self.assertRaises(archive_flow.PermissionDeniedError):
            archive_flow.flow_fetch(
                source=self.bundle,
                sha=self.initial_sha,
                path=".env",
            )

        # 6. Timeout with limited retry (max_retries=2 -> exactly 3 attempts)
        calls = {"count": 0}

        def always_timeout(*_args, **_kwargs):
            calls["count"] += 1
            raise subprocess.TimeoutExpired(cmd=["git", "show"], timeout=0.1)

        with mock.patch.object(archive_flow.subprocess, "run", side_effect=always_timeout):
            with self.assertRaises(archive_flow.ArchiveTimeoutError) as ctx:
                archive_flow.flow_fetch(
                    source=self.bare,
                    sha=self.main_sha,
                    path="src/sidebar.ts",
                    timeout=0.1,
                    max_retries=2,
                    retry_delay=0.0,
                )
        self.assertEqual(calls["count"], 3)
        self.assertEqual(ctx.exception.attempts, 3)
        self.assertEqual(ctx.exception.to_dict()["error"]["code"], "timeout")

        # 7. Transient failure succeeds on retry within limit
        flaky_calls = {"count": 0}
        real_bundle_dir = self.root / "releases" / "v-test"
        real_bundle_dir.mkdir(parents=True)
        bundle_copy = real_bundle_dir / "synthetic.bundle"
        bundle_copy.write_bytes(self.bundle.read_bytes())
        expected_bundle_sha = hashlib.sha256(bundle_copy.read_bytes()).hexdigest()

        def flaky_fetcher(_tag: str, _asset: str, _dest: Path, _timeout: float) -> Path:
            flaky_calls["count"] += 1
            if flaky_calls["count"] < 2:
                raise archive_flow.ArchiveTimeoutError("transient network hiccup")
            return bundle_copy

        resolved = archive_flow.resolve_release_asset(
            release_tag="v-test",
            asset="synthetic.bundle",
            expected_sha256=expected_bundle_sha,
            max_retries=2,
            retry_delay=0.0,
            fetcher=flaky_fetcher,
        )
        self.assertEqual(resolved["attempts"], 2)
        self.assertEqual(resolved["sha256"], expected_bundle_sha)

    def test_private_outputs_never_written_inside_site(self):
        site_target = ROOT / "site" / "leaked-recovery.ts"
        self.addCleanup(lambda: site_target.unlink(missing_ok=True))

        with self.assertRaises(archive_flow.PermissionDeniedError):
            archive_flow.flow_recover(
                source=self.bundle,
                sha=self.main_sha,
                path="src/sidebar.ts",
                output=site_target,
            )
        self.assertFalse(site_target.exists())

        site_thumb_dir = ROOT / "site" / "thumbs"
        with self.assertRaises(archive_flow.PermissionDeniedError):
            archive_flow.flow_preview(
                source=self.bundle,
                sha=self.main_sha,
                path="assets/sidebar-preview.png",
                thumb_dir=site_thumb_dir,
            )
        self.assertFalse(site_thumb_dir.exists())

    def test_cli_determinism_and_zero_emoji_policy(self):
        cli = SCRIPTS_DIR / "archive_flow.py"
        cmd = [
            sys.executable,
            str(cli),
            "search",
            "capacities-sidebar",
            "--db",
            str(self.db_path),
            "--source",
            str(self.bundle),
            "--limit",
            "5",
        ]
        run1 = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
        run2 = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
        self.assertEqual(run1, run2)

        parsed = json.loads(run1)
        self.assertTrue(parsed["ok"])
        hit = next(r for r in parsed["results"] if r["path"] == "src/sidebar.ts")

        rec_out = self.root / "cli-recovered.ts"
        rec_proc = subprocess.run(
            [
                sys.executable,
                str(cli),
                "recover",
                "--source",
                str(self.bundle),
                "--sha",
                hit["full_sha"],
                "--ref",
                hit["ref"],
                "--path",
                hit["path"],
                "--expected-sha256",
                hit["sha256"],
                "--output",
                str(rec_out),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        rec_json = json.loads(rec_proc.stdout)
        self.assertTrue(rec_json["ok"])
        self.assertEqual(rec_json["sha256"], hit["sha256"])
        self.assertEqual(rec_json["output_sha256"], hit["sha256"])
        self.assertEqual(rec_out.read_bytes(), self.sidebar_bytes)

        # Explicit error CLI output goes to stderr as structured JSON with non-zero exit
        err_proc = subprocess.run(
            [
                sys.executable,
                str(cli),
                "fetch",
                "--source",
                str(self.bundle),
                "--sha",
                self.main_sha,
                "--path",
                "missing/file.ts",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(err_proc.returncode, 0)
        err_json = json.loads(err_proc.stderr)
        self.assertFalse(err_json["ok"])
        self.assertEqual(err_json["error"]["code"], "not_found")

        # Unsafe path via CLI fails with unsafe_input
        unsafe_proc = subprocess.run(
            [
                sys.executable,
                str(cli),
                "fetch",
                "--source",
                str(self.bundle),
                "--sha",
                self.main_sha,
                "--path",
                "../etc/passwd",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(unsafe_proc.returncode, 0)
        unsafe_json = json.loads(unsafe_proc.stderr)
        self.assertFalse(unsafe_json["ok"])
        self.assertEqual(unsafe_json["error"]["code"], "unsafe_input")

        # Zero Emoji Policy on new script and test file
        for target in (cli, Path(__file__)):
            text = target.read_text(encoding="utf-8")
            self.assertEqual(EMOJI_REGEX.findall(text), [], f"Unexpected emoji in {target}")

    def test_release_manifest_resolution_and_checksum_validation(self):
        release_dir = self.root / "rel-store" / "archive-test-v1"
        release_dir.mkdir(parents=True)
        bundle_asset = release_dir / "synthetic.bundle"
        bundle_asset.write_bytes(self.bundle.read_bytes())
        bundle_sha = hashlib.sha256(bundle_asset.read_bytes()).hexdigest()

        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "tag": "archive-test-v1",
                    "assets": [{"asset": "synthetic.bundle", "sha256": bundle_sha}],
                }
            ),
            encoding="utf-8",
        )
        info = archive_flow.resolve_release_asset(
            release_tag="archive-test-v1",
            asset="synthetic.bundle",
            release_dir=self.root / "rel-store",
            manifest_path=manifest_path,
        )
        self.assertEqual(info["sha256"], bundle_sha)

        manifest_path.write_text(
            json.dumps(
                {
                    "tag": "archive-test-v1",
                    "assets": [{"asset": "synthetic.bundle", "sha256": "f" * 64}],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(archive_flow.ChecksumMismatchError):
            archive_flow.resolve_release_asset(
                release_tag="archive-test-v1",
                asset="synthetic.bundle",
                release_dir=self.root / "rel-store",
                manifest_path=manifest_path,
            )

    def test_queue_retention_based_on_git_commit_timestamp(self):
        repo_dir = self.root / "queue_repo"
        repo_dir.mkdir()
        run_git("init", "-q", "-b", "main", str(repo_dir))
        run_git("config", "user.email", "flow-test@example.invalid", cwd=repo_dir)
        run_git("config", "user.name", "Flow Test", cwd=repo_dir)

        req_dir = repo_dir / "requests"
        res_dir = repo_dir / "results"
        req_dir.mkdir()
        res_dir.mkdir()

        old_req_data = {"version": 1, "id": "req-old-01", "operation": "search", "query": "old"}
        old_req_bytes = json.dumps(old_req_data).encode("utf-8")
        old_digest = hashlib.sha256(old_req_bytes).hexdigest()
        old_res_data = {"version": 1, "id": "req-old-01", "request_sha256": old_digest, "ok": True}

        old_req_path = req_dir / "req-old-01.json"
        old_res_path = res_dir / "req-old-01.json"
        old_req_path.write_bytes(old_req_bytes)
        old_res_path.write_text(json.dumps(old_res_data, indent=2) + "\n", encoding="utf-8")

        run_git("add", ".", cwd=repo_dir)
        old_date_env = {
            "GIT_AUTHOR_DATE": "2026-10-01T12:00:00Z",
            "GIT_COMMITTER_DATE": "2026-10-01T12:00:00Z",
        }
        run_git("commit", "-qm", "chore: record old processed query", cwd=repo_dir, env=old_date_env)

        new_req_data = {"version": 1, "id": "req-recent-02", "operation": "search", "query": "recent"}
        new_req_bytes = json.dumps(new_req_data).encode("utf-8")
        new_digest = hashlib.sha256(new_req_bytes).hexdigest()
        new_res_data = {"version": 1, "id": "req-recent-02", "request_sha256": new_digest, "ok": True}

        new_req_path = req_dir / "req-recent-02.json"
        new_res_path = res_dir / "req-recent-02.json"
        new_req_path.write_bytes(new_req_bytes)
        new_res_path.write_text(json.dumps(new_res_data, indent=2) + "\n", encoding="utf-8")

        run_git("add", ".", cwd=repo_dir)
        run_git("commit", "-qm", "chore: record recent processed query", cwd=repo_dir)

        current_time = time.time()
        os.utime(old_req_path, (current_time, current_time))
        os.utime(old_res_path, (current_time, current_time))
        self.assertGreaterEqual(old_res_path.stat().st_mtime, current_time - 2)

        commit_ts = archive_flow.get_git_commit_timestamp(old_res_path, repo_root=repo_dir)
        self.assertIsNotNone(commit_ts)
        self.assertLess(commit_ts, current_time - (15 * 86400))

        pruned_count = archive_flow.prune_queue(req_dir, res_dir, retention_days=14, repo_root=repo_dir)
        self.assertEqual(pruned_count, 1)
        self.assertFalse(old_req_path.exists())
        self.assertFalse(old_res_path.exists())
        self.assertTrue(new_req_path.exists())
        self.assertTrue(new_res_path.exists())

    def test_queue_batch_handling_and_loop_processing(self):
        req_dir = self.root / "batch_q_requests"
        res_dir = self.root / "batch_q_results"
        req_dir.mkdir()
        res_dir.mkdir()

        for idx in range(1, 6):
            doc = {
                "version": 1,
                "id": f"req-batch-{idx:02d}",
                "operation": "fetch",
                "path": "src/sidebar.ts",
                "sha": self.main_sha,
                "source_repo": "exams-app-synthetic",
                "start_line": 1,
                "end_line": idx * 5,
            }
            (req_dir / f"req-batch-{idx:02d}.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")

        batch1 = archive_flow.process_queue_batch(
            req_dir,
            res_dir,
            source=self.bundle,
            batch_limit=2,
            loop_until_empty=False,
        )
        self.assertTrue(batch1["ok"])
        self.assertEqual(batch1["processed"], 2)
        self.assertEqual(batch1["pending_remaining"], 3)
        self.assertEqual(batch1["status"], "pending")
        self.assertGreater(batch1["tokens"]["estimated_tokens"], 0)

        res1 = json.loads((res_dir / "req-batch-01.json").read_text(encoding="utf-8"))
        self.assertTrue(res1["ok"])
        self.assertIn("content", res1)
        self.assertEqual(res1["end_line"], 5)

        res3 = json.loads((res_dir / "req-batch-03.json").read_text(encoding="utf-8"))
        self.assertTrue(res3["ok"])
        self.assertEqual(res3["status"], "pending")
        self.assertIn("exceeds batch limit", res3["message"])

        batch_loop = archive_flow.process_queue_batch(
            req_dir,
            res_dir,
            source=self.bundle,
            batch_limit=2,
            loop_until_empty=True,
        )
        self.assertTrue(batch_loop["ok"])
        self.assertEqual(batch_loop["processed"], 3)
        self.assertEqual(batch_loop["pending_remaining"], 0)
        self.assertEqual(batch_loop["status"], "complete")
        self.assertGreaterEqual(batch_loop["loops"], 2)

        for idx in range(1, 6):
            target = res_dir / f"req-batch-{idx:02d}.json"
            self.assertTrue(target.exists())
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertTrue(data["ok"])
            self.assertNotEqual(data.get("status"), "pending")
            self.assertIn("content", data)

        idle_batch = archive_flow.process_queue_batch(
            req_dir,
            res_dir,
            source=self.bundle,
            batch_limit=2,
            loop_until_empty=True,
        )
        self.assertEqual(idle_batch["processed"], 0)
        self.assertEqual(idle_batch["pending_remaining"], 0)
        self.assertEqual(idle_batch["status"], "complete")

    def test_recovery_of_code_markdown_images_and_deleted_with_sha_validation(self):
        code_out = self.root / "recovered" / "sidebar.ts"
        rec_code = archive_flow.flow_recover(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=self.main_sha,
            ref="refs/heads/main",
            path="src/sidebar.ts",
            output=code_out,
            expected_sha256=hashlib.sha256(self.sidebar_bytes).hexdigest(),
        )
        self._assert_structured_fields(rec_code, expect_content_key="content")
        self.assertEqual(rec_code["source_repo"], "exams-app-synthetic")
        self.assertEqual(rec_code["ref"], "refs/heads/main")
        self.assertEqual(rec_code["full_sha"], self.main_sha)
        self.assertEqual(rec_code["path"], "src/sidebar.ts")
        self.assertEqual(rec_code["mime"], "text/typescript")
        self.assertEqual(rec_code["sha256"], hashlib.sha256(self.sidebar_bytes).hexdigest())
        self.assertEqual(rec_code["output_sha256"], rec_code["sha256"])
        self.assertEqual(code_out.read_bytes(), self.sidebar_bytes)

        with self.assertRaises(archive_flow.ChecksumMismatchError):
            archive_flow.flow_recover(
                source=self.bundle,
                sha=self.main_sha,
                path="src/sidebar.ts",
                expected_sha256="1" * 64,
            )

        md_out = self.root / "recovered" / "decisions_rec.md"
        rec_md = archive_flow.flow_recover(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=self.main_sha,
            path="docs/decisions.md",
            output=md_out,
            expected_sha256=hashlib.sha256(self.markdown_bytes).hexdigest(),
        )
        self._assert_structured_fields(rec_md, expect_content_key="content")
        self.assertEqual(rec_md["mime"], "text/markdown")
        self.assertEqual(rec_md["sha256"], hashlib.sha256(self.markdown_bytes).hexdigest())
        self.assertEqual(md_out.read_bytes(), self.markdown_bytes)
        self.assertGreater(rec_md["tokens"]["estimated_tokens"], 0)
        self.assertGreater(rec_md["tokens"]["content_tokens"], 0)

        img_out = self.root / "recovered" / "sidebar-preview-rec.png"
        rec_img = archive_flow.flow_recover(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=self.main_sha,
            path="assets/sidebar-preview.png",
            output=img_out,
            expected_sha256=hashlib.sha256(self.active_png).hexdigest(),
        )
        self._assert_structured_fields(rec_img, expect_content_key="content_base64")
        self.assertEqual(rec_img["mime"], "image/png")
        self.assertEqual(rec_img["sha256"], hashlib.sha256(self.active_png).hexdigest())
        self.assertEqual(img_out.read_bytes(), self.active_png)
        self.assertEqual(base64.b64decode(rec_img["content_base64"]), self.active_png)

        del_code_out = self.root / "recovered" / "legacy_graph_rec.ts"
        rec_del_code = archive_flow.flow_recover(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=self.initial_sha,
            path="src/legacy_graph.ts",
            output=del_code_out,
            expected_sha256=hashlib.sha256(self.deleted_code_bytes).hexdigest(),
        )
        self._assert_structured_fields(rec_del_code, expect_content_key="content")
        self.assertTrue(rec_del_code["deleted_at_ref_head"])
        self.assertEqual(del_code_out.read_bytes(), self.deleted_code_bytes)
        self.assertEqual(rec_del_code["sha256"], hashlib.sha256(self.deleted_code_bytes).hexdigest())

        del_img_out = self.root / "recovered" / "removed-grafo-rec.png"
        rec_del_img = archive_flow.flow_recover(
            source=self.bundle,
            source_repo="exams-app-synthetic",
            sha=self.initial_sha,
            path="assets/removed-grafo.png",
            output=del_img_out,
            expected_sha256=hashlib.sha256(self.deleted_png).hexdigest(),
        )
        self._assert_structured_fields(rec_del_img, expect_content_key="content_base64")
        self.assertTrue(rec_del_img["deleted_at_ref_head"])
        self.assertEqual(del_img_out.read_bytes(), self.deleted_png)
        self.assertEqual(base64.b64decode(rec_del_img["content_base64"]), self.deleted_png)
        self.assertEqual(rec_del_img["sha256"], hashlib.sha256(self.deleted_png).hexdigest())


if __name__ == "__main__":
    unittest.main()
