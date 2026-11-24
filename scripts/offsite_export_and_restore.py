#!/usr/bin/env python3
"""Download verified archive releases to a user-controlled independent directory.

No GitHub writes, no credential output, no deletion authorization.
Run with authenticated gh and git after securing the archive visibility.
The destination should be encrypted or a private, independently backed-up drive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import tarfile
import zipfile
from datetime import datetime, timezone

ARCHIVE = "ianmaciel7/exams-app-archive"
RELEASES = (
    "archive-2026-11-23-all-refs",
    "exams-app-2026-11-23-complete",
    "notes-app-2026-11-23-private-full",
    "public-metadata-2026-11-23",
    "legacy-ci-artifacts-2026-11-23-bulk",
    "legacy-github-extras-2026-11-23",
    "exams-app-2026-11-23-ci-logs",
    "index-2026-11-23-exams-complete",
)
AUXILIARY = ("fcc-responsive-web-design.", "ianmaciel7.")
BUNDLES = {
    "exams-app-old": (RELEASES[0], "exams-app-old.bundle"),
    "exams-app-antigo-2": (RELEASES[0], "exams-app-antigo-2.bundle"),
    "shadcn-template": (RELEASES[0], "shadcn-template.bundle"),
    "shadcn-firebase-template": (RELEASES[0], "shadcn-firebase-template.bundle"),
    "exams-app": (RELEASES[1], "exams-app-all-refs.bundle"),
    "notes-app": (RELEASES[2], "notes-app-all-refs.bundle"),
}

def run(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout

def sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def safe_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) or name in (".", ".."):
        raise ValueError("Unsafe release asset name")
    return name

def verify_file(path: Path, expected: dict) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or unsafe file: " + path.name)
    if path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
        raise ValueError("Size or SHA-256 mismatch: " + path.name)

def download(root: Path) -> dict:
    visibility = run("gh", "repo", "view", ARCHIVE, "--json", "visibility", "--jq", ".visibility").strip()
    if visibility != "PRIVATE":
        raise RuntimeError("Secure the archive before copying private contents")
    records = []
    for tag in RELEASES:
        release = json.loads(run("gh", "api", f"repos/{ARCHIVE}/releases/tags/{tag}"))
        if release.get("draft"):
            raise ValueError("Unpublished source release: " + tag)
        target = root / tag
        target.mkdir(mode=0o700, parents=True, exist_ok=True)
        if target.is_symlink():
            raise ValueError("Symlink release directory")
        for asset in release["assets"]:
            name = safe_name(asset["name"])
            if name.startswith(AUXILIARY):
                continue
            digest = asset.get("digest", "")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                raise ValueError("Missing authoritative digest: " + name)
            if asset["state"] != "uploaded":
                raise ValueError("Incomplete asset: " + name)
            record = {"path": f"{tag}/{name}", "bytes": asset["size"], "sha256": digest[7:]}
            p = target / name
            if not p.exists():
                with tempfile.TemporaryDirectory(dir=target) as tmp:
                    run("gh", "release", "download", tag, "-R", ARCHIVE, "--pattern", name, "--dir", tmp)
                    fetched = Path(tmp) / name
                    verify_file(fetched, record)
                    os.replace(fetched, p)
            verify_file(p, record)
            records.append(record)
    return {"source": ARCHIVE, "files": records, "created_at": datetime.now(timezone.utc).isoformat()}

def read_refs(root: Path) -> dict:
    public = json.loads((root / RELEASES[0] / "MANIFEST.json").read_text(encoding="utf-8"))
    exams = json.loads((root / RELEASES[1] / "MANIFEST.json").read_text(encoding="utf-8"))
    notes = json.loads((root / RELEASES[2] / "MANIFEST.json").read_text(encoding="utf-8"))
    refs = {a["repository"].split("/")[-1]: a["refs"] for a in public["assets"] if "refs" in a}
    refs["exams-app"] = exams["all_advertised_refs"]
    refs["notes-app"] = notes["all_refs"]
    return refs

def restore_offline(root: Path, manifest: dict) -> dict:
    # This function requires only local files and Git; no remote requests.
    seen = set()
    for record in manifest["files"]:
        parts = record["path"].split("/")
        if len(parts) != 2 or parts[0] not in RELEASES:
            raise ValueError("Unexpected manifest path")
        tag, name = parts
        safe_name(name)
        if record["path"] in seen or (root / tag).is_symlink():
            raise ValueError("Duplicate or unsafe manifest record")
        seen.add(record["path"])
        verify_file(root / tag / name, record)
    refs = read_refs(root)
    restored = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, (tag, asset) in BUNDLES.items():
            if f"{tag}/{asset}" not in seen:
                raise ValueError("Required bundle missing from receipt: " + name)
            bare = Path(tmp) / (name + ".git")
            run("git", "clone", "--mirror", "--no-local", str(root / tag / asset), str(bare))
            run("git", f"--git-dir={bare}", "fsck", "--full")
            actual = {line.split(" ", 1)[1]: line.split(" ", 1)[0]
                      for line in run("git", f"--git-dir={bare}", "show-ref").splitlines()}
            if actual != refs[name]:
                raise ValueError("Restored refs differ: " + name)
            restored[name] = len(actual)
    ci = root / RELEASES[4]
    bulk = json.loads((ci / "BULK-MANIFEST.json").read_text(encoding="utf-8"))
    if not bulk.get("complete") or bulk.get("expected_artifacts") != 2883:
        raise ValueError("Incomplete CI manifest")
    count = 0
    for shard in range(16):
        filename = f"legacy-ci-{shard:02d}.tar"
        if f"{RELEASES[4]}/{filename}" not in seen:
            raise ValueError("Missing CI partition")
        with tarfile.open(ci / filename) as tar:
            for member in tar:
                if not member.isfile():
                    continue
                with tar.extractfile(member) as stream:
                    with zipfile.ZipFile(stream) as archive:
                        if archive.testzip() is not None:
                            raise ValueError("Invalid CI evidence ZIP")
                count += 1
    if count != 2883:
        raise ValueError("Unexpected CI evidence count")
    return {"restored_refs": restored, "ci_zips_crc_verified": count,
            "verified": True, "deletion_authorized": False,
            "independent_storage_confirmation_required": True}

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--destination", required=True, type=Path)
    ap.add_argument("--verify-only", action="store_true", help="No network; use the existing receipt")
    args = ap.parse_args()
    root = args.destination.expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    receipt = root / "OFFSITE-MANIFEST.json"
    if args.verify_only:
        manifest = json.loads(receipt.read_text(encoding="utf-8"))
    else:
        manifest = download(root)
        receipt.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    result = restore_offline(root, manifest)
    (root / "OFFSITE-RESTORE.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
