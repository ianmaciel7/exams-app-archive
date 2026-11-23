#!/usr/bin/env python3
"""Read-only, authenticated local search of Exams App archive (stdlib only)."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ARCHIVE = "ianmaciel7/exams-app-archive"
REPORT_PATH = "reports/FULL-INDEX.json"
DEFAULT_TAG = "index-2026-11-23-exams-complete"
CACHE = Path.home() / ".cache" / "exams-app-archive"
DEFAULT_DB = CACHE / "full-index.sqlite"
COLUMNS = ("repository", "kind", "sha", "path", "summary", "blob", "bytes", "deleted")


def run(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, check=True).stdout
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing executable: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{cmd[0]} exited with {exc.returncode}: {exc.stderr.strip()[:400]}") from exc


def read_db(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise RuntimeError(f"Index not found: {path}. Run 'sync' first.")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def sync(path: Path, force: bool = False) -> dict:
    if path.exists() and not force:
        with read_db(path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM repositories").fetchone()[0]
        return {"index": str(path), "sources": count, "cached": True}
    report = json.loads(run("gh", "api", "-H", "Accept: application/vnd.github.raw",
                            f"repos/{ARCHIVE}/contents/{REPORT_PATH}"))
    tag, expected = report.get("release_tag", DEFAULT_TAG), report.get("gzip_sha256")
    if not isinstance(tag, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", tag):
        raise RuntimeError("Invalid release tag")
    if not isinstance(expected, str) or not re.fullmatch("[0-9a-f]{64}", expected):
        raise RuntimeError("Archive checksum missing or invalid")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="archive-", dir=path.parent) as temp:
        folder = Path(temp)
        run("gh", "release", "download", tag, "--repo", ARCHIVE,
            "--pattern", "full-index.sqlite.gz", "--dir", str(folder))
        packed = folder / "full-index.sqlite.gz"
        actual = hashlib.sha256(packed.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError("Archive checksum mismatch; index was not installed")
        unpacked = folder / "full-index.sqlite"
        with gzip.open(packed, "rb") as src, unpacked.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        with read_db(unpacked) as conn:
            check = conn.execute("PRAGMA quick_check").fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM repositories").fetchone()[0]
        if check != "ok" or not count:
            raise RuntimeError("Downloaded SQLite failed integrity check")
        os.replace(unpacked, path)
    return {"index": str(path), "release": tag, "sources": count, "sha256_gzip": actual, "cached": False}


def build_results(conn: sqlite3.Connection, query: str, repo: str | None,
                  kind: str, limit: int) -> list[dict]:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)[:6]
    if not tokens:
        return []
    matcher = " OR ".join('"' + token.replace('"', '') + '"*' for token in tokens)
    results: list[dict] = []
    kinds = ("commit", "file", "image") if kind == "all" else (kind,)
    for current in kinds:
        params: list = []
        if current == "commit":
            sql = """SELECT r.name AS repository,'commit' AS kind,c.sha AS sha,'' AS path,
                     c.subject AS summary,'' AS blob,0 AS bytes,0 AS deleted
                     FROM commit_fts f JOIN repositories r ON r.id=CAST(f.repo_id AS INTEGER)
                     JOIN commits c ON c.repo_id=r.id AND c.sha=f.sha
                     WHERE commit_fts MATCH ?"""
            params.append(matcher)
        elif current == "file":
            sql = """SELECT r.name AS repository,'file' AS kind,f.sha AS sha,f.path AS path,
                     '' AS summary,'' AS blob,0 AS bytes,0 AS deleted
                     FROM change_fts f JOIN repositories r ON r.id=CAST(f.repo_id AS INTEGER)
                     WHERE change_fts MATCH ?"""
            params.append(matcher)
        else:
            sql = """SELECT r.name AS repository,'image' AS kind,i.commit_sha AS sha,i.path AS path,
                     i.kind AS summary,i.blob AS blob,i.bytes AS bytes,
                     (i.kind='deleted') AS deleted
                     FROM images i JOIN repositories r ON r.id=i.repo_id WHERE (""" + (
                    " OR ".join("lower(i.path) LIKE ? ESCAPE '\\'" for _ in tokens)) + ")"
            params.extend("%" + t.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
                          for t in tokens)
        if repo:
            sql += " AND r.name=?"
            params.append(repo)
        sql += " LIMIT ?"
        params.append(limit)
        for row in conn.execute(sql, params):
            results.append(dict(row))
    return results[:limit]


def list_images(conn: sqlite3.Connection, repo: str | None,
                deleted_only: bool, limit: int) -> list[dict]:
    sql = """SELECT r.name AS repository,'image' AS kind,i.commit_sha AS sha,i.path AS path,
             i.kind AS summary,i.blob AS blob,i.bytes AS bytes,(i.kind='deleted') AS deleted
             FROM images i JOIN repositories r ON r.id=i.repo_id WHERE 1=1"""
    params: list = []
    if repo:
        sql += " AND r.name=?"
        params.append(repo)
    if deleted_only:
        sql += " AND i.kind='deleted'"
    sql += " ORDER BY i.bytes DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


def export_pages(conn: sqlite3.Connection, destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    queries = [
        """SELECT r.name AS repository,'commit' AS kind,c.sha AS sha,'' AS path,
           c.subject AS summary,'' AS blob,0 AS bytes,0 AS deleted
           FROM commits c JOIN repositories r ON r.id=c.repo_id""",
        """SELECT r.name AS repository,'file' AS kind,x.sha AS sha,x.path AS path,
           '' AS summary,'' AS blob,0 AS bytes,(x.status='D') AS deleted
           FROM changes x JOIN repositories r ON r.id=x.repo_id""",
        """SELECT r.name AS repository,'image' AS kind,i.commit_sha AS sha,i.path AS path,
           i.kind AS summary,i.blob AS blob,i.bytes AS bytes,(i.kind='deleted') AS deleted
           FROM images i JOIN repositories r ON r.id=i.repo_id"""
    ]
    count = 0
    output_stream = destination.open("x", encoding="utf-8")
    try:
        with output_stream as out:
            out.write(json.dumps({"version": 1, "generated_at": datetime.now(timezone.utc).isoformat()})[:-1])
            out.write(',"records":[')
            for query in queries:
                for row in conn.execute(query):
                    if count:
                        out.write(",")
                    out.write(json.dumps(dict(row), ensure_ascii=False, separators=(",", ":")))
                    count += 1
            out.write("]}\n")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"output": str(destination), "records": count, "private": True}


def recover(bare: Path, sha: str, path: str, output: Path) -> dict:
    if not re.fullmatch("[0-9a-f]{40,64}", sha):
        raise ValueError("A full commit SHA is required")
    if not path or path.startswith(("/", "-")) or "\\" in path or ":" in path or \
            ".." in Path(path).parts or "\0" in path:
        raise ValueError("Unsafe historical path")
    if not (bare / "HEAD").is_file():
        raise ValueError("Use the path to a bare Git mirror of the downloaded bundle")
    output.parent.mkdir(parents=True, exist_ok=True)
    output_stream = output.open("xb")
    try:
        with output_stream as target:
            subprocess.run(["git", f"--git-dir={bare}", "show", f"{sha}:{path}"],
                           stdout=target, stderr=subprocess.PIPE, check=True)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {"output": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "bytes": output.stat().st_size, "sha": sha, "path": path}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sync", help="Download and verify private release index")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--repo")
    p.add_argument("--kind", choices=("all", "file", "commit", "image"), default="all")
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("images")
    p.add_argument("--repo")
    p.add_argument("--deleted-only", action="store_true")
    p.add_argument("--limit", type=int, default=20)
    sub.add_parser("stats")
    p = sub.add_parser("export-pages")
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("recover")
    p.add_argument("--git-dir", type=Path, required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "sync":
        result = sync(args.db, args.force)
    elif args.command == "recover":
        result = recover(args.git_dir, args.sha, args.path, args.output)
    else:
        with read_db(args.db) as conn:
            if args.command == "search":
                result = build_results(conn, args.query, args.repo, args.kind,
                                       max(1, min(args.limit, 100)))
            elif args.command == "images":
                result = list_images(conn, args.repo, args.deleted_only, max(1, min(args.limit, 100)))
            elif args.command == "stats":
                result = [dict(row) for row in conn.execute(
                    """SELECT r.name AS repository,COUNT(DISTINCT c.sha) AS commits
                       FROM repositories r LEFT JOIN commits c ON c.repo_id=r.id
                       GROUP BY r.id ORDER BY r.name""")]
            else:
                result = export_pages(conn, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, FileExistsError, sqlite3.Error, OSError,
            subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
