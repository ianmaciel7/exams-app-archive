#!/usr/bin/env python3
"""Preserve both sources' release bytes in the PUBLIC archive, encrypted with age.

Run in a trusted terminal with Python 3.11+, gh, age and authenticated read/write
permissions. age prompts for a passphrase in the terminal; never put it in
GitHub, an environment variable, or a command argument. Keep it independently
of the repositories. No plaintext or plaintext metadata is uploaded.
No source writes or deletion. Dry-run unless --apply is supplied.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

from consolidate_source_releases import (
    ARCHIVE, SOURCES, assets, releases, download, checksum, gh, safe_name
)

CIPHER = "source-releases.tar.age"
MAX_ASSET = 2 * 1024**3


def build_payload(root: Path, inventory: list) -> int:
    payload = root / "payload"
    payload.mkdir(mode=0o700)
    count = 0
    for source, release in inventory:
        folder = payload / source.split("/")[-1] / str(release["id"])
        folder.mkdir(mode=0o700, parents=True)
        records = []
        names = set()
        for asset in assets(source, release["id"]):
            name = safe_name(asset["name"])
            if name in names or asset["state"] != "uploaded":
                raise RuntimeError("Duplicate or incomplete source asset")
            names.add(name)
            files = folder / "assets"
            files.mkdir(exist_ok=True)
            digest = download(source, asset, files / name)
            records.append({"name": name, "bytes": asset["size"],
                            "sha256": digest, "metadata": asset})
            count += 1
        (folder / "release.json").write_text(json.dumps(
            {"source": source, "release": release, "assets": records},
            ensure_ascii=False, indent=2), encoding="utf-8")
    with tarfile.open(root / "source-releases.tar", "w") as tar:
        tar.add(payload, arcname="payload")
    return count


def inventory_snapshot():
    return [(source, release) for source in SOURCES for release in releases(source)]


def inventory_signature(inventory):
    return {(source, release["id"], release["updated_at"],
             tuple(sorted((a["id"], a["size"], a.get("digest"))
                          for a in assets(source, release["id"]))))
            for source, release in inventory}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--tag", help="Unused destination release tag")
    args = parser.parse_args()
    inventory = inventory_snapshot()
    print(json.dumps({"source_releases": len(inventory), "apply": args.apply}))
    if not args.apply:
        return
    tag = args.tag or datetime.now(timezone.utc).strftime("encrypted-source-releases-%Y%m%dT%H%M%SZ")
    safe_name(tag)
    if any(x["tag_name"] == tag for x in releases(ARCHIVE)):
        raise RuntimeError("Destination release already exists; refusing overwrite")
    before = inventory_signature(inventory)
    # Temp data is private to the trusted local user. Use an encrypted disk
    # and set TMPDIR/TEMP appropriately; never execute this on a public runner.
    with tempfile.TemporaryDirectory(prefix="archive-encrypted-") as directory:
        root = Path(directory)
        count = build_payload(root, inventory)
        if before != inventory_signature(inventory_snapshot()):
            raise RuntimeError("Source releases changed during backup; retry")
        original = root / "source-releases.tar"
        cipher = root / CIPHER
        subprocess.run(["age", "-p", "-o", str(cipher), str(original)], check=True)
        if cipher.stat().st_size >= MAX_ASSET:
            raise RuntimeError("Encrypted archive exceeds GitHub asset limit; partition the inventory")
        # Prove the passphrase works BEFORE publication.
        proof = root / "local-restore.tar"
        subprocess.run(["age", "-d", "-o", str(proof), str(cipher)], check=True)
        if checksum(proof) != checksum(original):
            raise RuntimeError("Local decryption verification failed")
        proof.unlink()
        cipher_hash = checksum(cipher)
        # Only generic release metadata and authenticated ciphertext go public.
        gh("release", "create", tag, "-R", ARCHIVE, "--target", "main",
           "--draft", "--title", "Encrypted historical archive",
           "--notes", "Authenticated age ciphertext. SHA-256: " + cipher_hash)
        gh("release", "upload", tag, str(cipher), "-R", ARCHIVE)
        target = next(x for x in releases(ARCHIVE) if x["tag_name"] == tag)
        uploaded = assets(ARCHIVE, target["id"])
        if len(uploaded) != 1 or uploaded[0]["name"] != CIPHER:
            raise RuntimeError("Unexpected destination assets")
        returned = root / "returned.age"
        if download(ARCHIVE, uploaded[0], returned) != cipher_hash:
            raise RuntimeError("Ciphertext round-trip mismatch")
        subprocess.run(["age", "-d", "-o", str(proof), str(returned)], check=True)
        if checksum(proof) != checksum(original):
            raise RuntimeError("Remote decryption round-trip mismatch")
        if before != inventory_signature(inventory_snapshot()):
            raise RuntimeError("Source releases changed; retain draft for review")
        gh("release", "edit", tag, "-R", ARCHIVE, "--draft=false")
        print(json.dumps({"release_transfer_verified": True, "destination_tag": tag,
                          "releases": len(inventory), "assets_verified": count,
                          "cipher_sha256": cipher_hash, "source_deleted": False}))


if __name__ == "__main__":
    main()
