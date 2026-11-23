#!/usr/bin/env python3
"""Execute bounded JSON queries on the private GitHub Actions archive index."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{5,63}\Z")
REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9@._-]{0,99}\Z")


def valid(path, data):
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Expected a version 1 JSON request")
    if not isinstance(data.get("id"), str) or data["id"] != path.stem or not ID.fullmatch(data["id"]):
        raise ValueError("Request ID must match filename")
    if set(data) - {"version", "id", "operation", "query", "repo", "kind", "limit", "deleted_only"}:
        raise ValueError("Unexpected request fields")
    op = data.get("operation")
    if op not in {"search", "images", "stats"}:
        raise ValueError("Invalid operation")
    repo = data.get("repo")
    if repo is not None and (not isinstance(repo, str) or not REPO.fullmatch(repo)):
        raise ValueError("Invalid repo")
    limit = data.get("limit", 15)
    if type(limit) is not int or not 1 <= limit <= 40:
        raise ValueError("Invalid limit")
    if op == "search":
        q = data.get("query")
        if not isinstance(q, str) or not 1 <= len(q.strip()) <= 120 or q.startswith("-"):
            raise ValueError("Search query must have 1-120 characters and not start with -")
        if any(ord(ch) < 32 for ch in q):
            raise ValueError("Control character in query")
        if data.get("kind", "all") not in {"all", "commit", "file", "image"}:
            raise ValueError("Invalid kind")
    elif "query" in data or "kind" in data:
        raise ValueError("query and kind only valid with search")
    if "deleted_only" in data and (op != "images" or type(data["deleted_only"]) is not bool):
        raise ValueError("deleted_only only valid for images")
    return data


def execute(cli, db, req):
    op = req["operation"]
    cmd = [sys.executable, str(cli), "--db", str(db), op]
    if op == "search":
        cmd.append(req["query"])
        if req.get("kind"):
            cmd += ["--kind", req["kind"]]
    if op in ("search", "images"):
        if req.get("repo"):
            cmd += ["--repo", req["repo"]]
        cmd += ["--limit", str(req.get("limit", 15))]
    if op == "images" and req.get("deleted_only", False):
        cmd.append("--deleted-only")
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if p.returncode:
        raise RuntimeError("Query failed in the private index")
    return json.loads(p.stdout)


def process(root, requests, results, db, offline=False):
    cli = root / "plugins/exams-archive/scripts/archive_query.py"
    if not cli.is_file() or not requests.is_dir():
        raise RuntimeError("Trusted archive CLI or request directory missing")
    results.mkdir(parents=True, exist_ok=True)
    pending = []
    for path in sorted(requests.glob("*.json")):
        if not ID.fullmatch(path.stem) or path.stat().st_size > 4096:
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        target = results / path.name
        if target.exists():
            try:
                if json.loads(target.read_text()).get("request_sha256") == digest:
                    continue
            except (OSError, ValueError):
                pass
        pending.append((path, raw, digest, target))
        if len(pending) == 30:
            break
    if not pending:
        return {"processed": 0}
    if offline:
        with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as conn:
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise RuntimeError("Invalid SQLite test fixture")
        provenance = {"index_release": "offline-test", "index_checksum": None}
    else:
        p = subprocess.run([sys.executable, str(cli), "--db", str(db), "sync"],
                           capture_output=True, text=True, timeout=300)
        if p.returncode:
            raise RuntimeError("Private release download or checksum verification failed")
        meta = json.loads(p.stdout)
        if not meta.get("sha256_gzip") or not meta.get("release"):
            raise RuntimeError("Missing index provenance")
        provenance = {"index_release": meta["release"], "index_checksum": meta["sha256_gzip"]}
    count = 0
    for path, raw, digest, target in pending:
        outcome = {"version": 1, "id": path.stem, "request_sha256": digest, **provenance}
        try:
            req = valid(path, json.loads(raw))
            outcome.update({"ok": True, "operation": req["operation"], "query": req.get("query"),
                            "results": execute(cli, db, req),
                            "limitation": "FTS indexes paths and commit subjects, not full blob text"})
        except (ValueError, TypeError, RuntimeError, subprocess.TimeoutExpired) as exc:
            outcome.update({"ok": False, "error": str(exc)[:200]})
        temp = target.with_suffix(".tmp")
        try:
            temp.write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n")
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)
        count += 1
    return {"processed": count}


def main():
    parser = argparse.ArgumentParser()
    for opt in ("root", "requests", "results", "db"):
        parser.add_argument("--" + opt, type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(process(args.root, args.requests, args.results, args.db, args.offline)))
    except (RuntimeError, OSError, ValueError, sqlite3.Error) as exc:
        print("Private search failed: " + str(exc)[:200], file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
