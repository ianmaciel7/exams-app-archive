#!/usr/bin/env python3
"""Read-only archive audit. Public CI emits only aggregate counts and error categories.
No source checkout, secret values, filenames from historical blobs, or raw subprocess logs.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tarfile
import tempfile
import zipfile

ARCHIVE = "ianmaciel7/exams-app-archive"
ALL = "archive-2026-11-23-all-refs"
EXAMS = "exams-app-2026-11-23-complete"
NOTES = "notes-app-2026-11-23-private-full"
META = "public-metadata-2026-11-23"
CI = "legacy-ci-artifacts-2026-11-23-bulk"
INDEX = "index-2026-11-23-exams-complete"
BUNDLES = {
    "exams-app-old": (ALL, "exams-app-old.bundle"),
    "exams-app-antigo-2": (ALL, "exams-app-antigo-2.bundle"),
    "shadcn-template": (ALL, "shadcn-template.bundle"),
    "shadcn-firebase-template": (ALL, "shadcn-firebase-template.bundle"),
    "exams-app": (EXAMS, "exams-app-all-refs.bundle"),
    "notes-app": (NOTES, "notes-app-all-refs.bundle"),
}
ROOT = Path(__file__).resolve().parents[1]

def command(*args: str) -> bytes:
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError("command_failed")
    return result.stdout

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def release_assets(tag: str):
    data = json.loads(command("gh", "api", f"repos/{ARCHIVE}/releases/tags/{tag}"))
    return {a["name"]: a for a in data["assets"]}

def digest(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def download(root: Path, tag: str, name: str):
    asset = release_assets(tag)[name]
    command("gh", "release", "download", tag, "-R", ARCHIVE, "--pattern", name, "--dir", str(root))
    path = root / name
    if path.stat().st_size != asset["size"] or "sha256:" + digest(path) != asset.get("digest"):
        raise ValueError("asset_integrity_failed")
    return path

def expected_refs(name: str):
    manifests = ROOT / "manifests"
    if name == "notes-app":
        return read_json(manifests / "notes-app-private-full.json")["all_refs"]
    if name == "exams-app":
        return read_json(manifests / "exams-app-complete-2026-11-23.json")["all_advertised_refs"]
    data = read_json(manifests / "release-2026-11-23-all-refs.json")
    return next(a["refs"] for a in data["assets"] if a["repository"].endswith("/" + name))

def bundle_audit(root: Path, name: str):
    from secrets_gate import scan_git_repo_or_bundle
    tag, asset = BUNDLES[name]
    path = download(root, tag, asset)
    bare = root / "restored.git"
    command("git", "clone", "--mirror", str(path), str(bare))
    command("git", f"--git-dir={bare}", "fsck", "--full", "--strict")
    refs = dict((line.split()[1], line.split()[0]) for line in command("git", f"--git-dir={bare}", "show-ref").decode().splitlines())
    if refs != expected_refs(name):
        raise ValueError("ref_mismatch")
    objects = command("git", f"--git-dir={bare}", "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)").decode().splitlines()
    lfs = 0
    trees = 0
    gitlinks = 0
    for row in objects:
        sha, kind, size = row.split()
        if kind == "blob" and int(size) <= 1024:
            blob = command("git", f"--git-dir={bare}", "cat-file", "blob", sha)
            lfs += int(blob.startswith(b"version https://git-lfs.github.com/spec/v1\n"))
        elif kind == "tree":
            trees += 1
            tree = command("git", f"--git-dir={bare}", "ls-tree", sha)
            gitlinks += sum(line.startswith(b"160000 ") for line in tree.splitlines())
    report = scan_git_repo_or_bundle(bare)
    findings = report["findings"]
    from collections import Counter
    return {"name": name, "integrity": True, "refs": len(refs), "objects": len(objects),
            "trees": trees, "lfs_pointers": lfs, "gitlink_entries": gitlinks,
            "text_blobs_scanned": report["items_scanned"], "secret_candidate_counts": dict(Counter(f["rule_id"] for f in findings)),
            "limitations": ["secret scanner skips binary and large blobs; candidates are not validated credentials"]}

def ci_audit(root: Path, shard: str):
    manifest = download(root, CI, f"legacy-ci-{shard}.manifest.json")
    tar = download(root, CI, f"legacy-ci-{shard}.tar")
    data = read_json(manifest)
    expected = data["counts"]["saved"]
    count = 0
    with tarfile.open(tar, "r:*") as archive:
        for member in archive:
            if not member.isfile():
                continue
            with archive.extractfile(member) as stream:
                with zipfile.ZipFile(stream) as zipped:
                    if zipped.testzip() is not None:
                        raise ValueError("ci_zip_crc_failed")
            count += 1
    if count != expected or data["counts"]["failed"] != 0:
        raise ValueError("ci_count_mismatch")
    return {"shard": shard, "zip_crc_verified": count, "integrity": True}

def metadata_audit(root: Path, name: str):
    tag, asset = (NOTES, "notes-app-github-metadata.zip") if name == "notes-app" else (META, name + ".platform.zip")
    path = download(root, tag, asset)
    with zipfile.ZipFile(path) as zipped:
        if zipped.testzip() is not None:
            raise ValueError("metadata_zip_crc_failed")
        counts = {}
        for entry in zipped.namelist():
            if not entry.endswith(".json"):
                continue
            data = json.loads(zipped.read(entry))
            key = Path(entry).stem
            if key in {"issues", "pulls", "workflow_runs", "releases", "artifacts"}:
                if isinstance(data, list):
                    counts[key] = len(data)
                elif isinstance(data, dict):
                    for v in data.values():
                        if isinstance(v, list):
                            counts[key] = len(v)
                            break
            elif isinstance(data, dict) and isinstance(data.get("data"), dict):
                for k, v in data["data"].items():
                    if k in {"issues", "pulls", "workflow_runs", "releases", "artifacts"} and isinstance(v, list):
                        counts[k] = len(v)
        return {"name": name, "zip_crc_verified": True, "entry_count": len(zipped.namelist()), "counts": counts}

def index_audit(root: Path):
    path = download(root, INDEX, "full-index.sqlite.gz")
    db = root / "index.sqlite"
    with gzip.open(path, "rb") as source, db.open("wb") as dest:
        import shutil
        shutil.copyfileobj(source, dest)
    with sqlite3.connect(db) as con:
        ok = con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    if not ok:
        raise ValueError("sqlite_integrity_failed")
    return {"index_integrity": True, "release": INDEX, "coverage": "historical index; not full Notes"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["bundle", "ci", "metadata", "index"])
    ap.add_argument("name")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            func = {"bundle": bundle_audit, "ci": ci_audit, "metadata": metadata_audit, "index": lambda root, _: index_audit(root)}[args.kind]
            report = func(root, args.name)
            print(json.dumps({"ok": True, **report}, sort_keys=True))
        except Exception as error:
            # Never print raw historical paths, values, or command stderr.
            print(json.dumps({"ok": False, "category": type(error).__name__, "task": args.kind}))
            raise SystemExit(1) from None

if __name__ == "__main__":
    main()
