#!/usr/bin/env python3
"""Reconcile archive coverage without publishing historical secrets or new private data."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile
from collections import Counter
from audit_release_bytes import BUNDLES, META, NOTES, download, command, expected_refs
from archive_index import ingest, open_db
from secrets_gate import scan_git_repo_or_bundle

def restore(root, name):
    tag, asset = BUNDLES[name]
    file = download(root, tag, asset)
    bare = root / (name + ".git")
    command("git", "clone", "--mirror", str(file), str(bare))
    return bare

def metadata(root):
    path = download(root, META, "exams-app-old.platform.zip")
    with zipfile.ZipFile(path) as z:
        pulls = json.loads(z.read("pulls.json"))
        issues = json.loads(z.read("issues.json"))
        details = json.loads(z.read("pull_request_details.json"))
    existing = {x["number"] for x in pulls}
    expected = {x["number"] for x in issues if x.get("pull_request")}
    missing = sorted(expected - existing)
    detail_missing = sorted(expected - {x["number"] for x in details})
    print(json.dumps({"kind":"pr_reconciliation", "expected":len(expected),"archived":len(existing),
                      "missing_public_pr_numbers":missing,"missing_detail_numbers":detail_missing}), flush=True)

def full_index_and_submodules(root):
    repos = {name: restore(root, name) for name in BUNDLES}
    notes = repos["notes-app"]
    trees = command("git", f"--git-dir={notes}", "cat-file", "--batch-all-objects",
                    "--batch-check=%(objectname) %(objecttype)").decode().splitlines()
    links = set()
    for row in trees:
        sha, kind = row.split()
        if kind == "tree":
            for entry in command("git", f"--git-dir={notes}", "ls-tree", sha).decode(errors="replace").splitlines():
                if entry.startswith("160000 "):
                    links.add(entry.split()[2])
    recovered = 0
    missing = 0
    for sha in sorted(links):
        found = False
        for bare in repos.values():
            try:
                command("git", f"--git-dir={bare}", "cat-file", "-e", sha+"^{commit}")
                found = True
                break
            except RuntimeError:
                pass
        recovered += int(found)
        missing += int(not found)
    print(json.dumps({"kind":"submodule_reconciliation","unique_target_commits":len(links),
                      "targets_in_six_bundles":recovered,"targets_not_found":missing}), flush=True)
    db = root / "complete.sqlite"
    conn = open_db(db)
    results = []
    for name, bare in repos.items():
        info = ingest(bare, name, conn)
        count = conn.execute("SELECT count(*) FROM refs r JOIN repositories p ON r.repo_id=p.id WHERE p.name=?", (name,)).fetchone()[0]
        if count != len(expected_refs(name)):
            raise ValueError("index_ref_count_mismatch")
        results.append({"name":name,"refs":count,"commits":info["commits"],"changes":info["changes"],"images":info["images"]})
    conn.commit()
    if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("sqlite_integrity_failed")
    conn.close()
    print(json.dumps({"kind":"index_rebuild","integrity":True,"sources":results,
                      "published":False,"reason":"unredacted derived index remains local"}), flush=True)

def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            metadata(root)
            full_index_and_submodules(root)
        except Exception as e:
            print(json.dumps({"ok":False,"category":type(e).__name__}),flush=True)
            raise SystemExit(1) from None

if __name__ == "__main__":
    main()
