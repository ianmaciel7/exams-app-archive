#!/usr/bin/env python3
"""Offline triage of historical text blobs; public output contains aggregate counts only."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import tempfile
from audit_release_bytes import BUNDLES, download, command
import secrets_gate as gate
import content_index

KEY_BLOCK = re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----[\s\S]{1,20000}?-----END (?:[A-Z]+ )*PRIVATE KEY-----")
MAX = 16 * 1024 * 1024

def triage(repo):
    objects = command("git", f"--git-dir={repo}", "cat-file", "--batch-all-objects",
                      "--batch-check=%(objectname) %(objecttype) %(objectsize)").decode().splitlines()
    pending = []
    counts = Counter()
    for row in objects:
        sha, kind, size = row.split()
        if kind != "blob":
            continue
        if int(size) > MAX:
            counts["large_blobs_not_scanned"] += 1
        else:
            pending.append(sha)
    findings = Counter()
    for start in range(0, len(pending), 100):
        batch = content_index.read_blobs_batch(repo, pending[start:start+100])
        for sha, data in batch.items():
            if content_index.is_binary_bytes(data):
                counts["binary_blobs_not_scanned"] += 1
                continue
            counts["text_blobs_scanned"] += 1
            text = data.decode("utf-8", errors="replace")
            for f in gate.scan_text(text, location="blob"):
                findings[f.rule_id] += 1
            normalized = text.replace("\\n", "\n")
            if "PRIVATE KEY-----" in normalized:
                blocks = KEY_BLOCK.findall(normalized)
                if not blocks:
                    counts["pem_header_without_complete_block"] += 1
                for block in blocks:
                    counts["complete_pem_blocks"] += 1
                    try:
                        p = subprocess.run(["openssl", "pkey", "-noout", "-passin", "pass:"],
                                           input=block.encode(), stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, timeout=4)
                        counts["parseable_private_keys" if p.returncode == 0 else "unparseable_or_encrypted_pem"] += 1
                    except (OSError, subprocess.TimeoutExpired):
                        counts["pem_check_unavailable"] += 1
    return {"coverage":dict(counts), "candidate_counts":dict(findings),
            "limitations":["no online credential validation", "binary and oversized blobs excluded", "parseable private keys require owner review and rotation if real"]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source", choices=sorted(BUNDLES))
    args=ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        try:
            tag, asset=BUNDLES[args.source]
            path=download(root,tag,asset)
            repo=root/"restored.git"
            command("git","clone","--mirror",str(path),str(repo))
            result=triage(repo)
            print(json.dumps({"ok":True,"source":args.source,**result},sort_keys=True),flush=True)
        except Exception as exc:
            print(json.dumps({"ok":False,"category":type(exc).__name__}),flush=True)
            raise SystemExit(1) from None
if __name__=="__main__":
    main()
