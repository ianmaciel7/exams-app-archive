#!/usr/bin/env python3
"""Copy source releases into the archive without exposing private data.

Requires Python 3.11+, authenticated gh, read access to sources and contents
write access to the destination. No source writes or deletion. Destination
must be PRIVATE, even for draft releases. Dry-run unless --apply is specified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ARCHIVE = "ianmaciel7/exams-app-archive"
SOURCES = ("ianmaciel7/notes-app", "ianmaciel7/exams-app")
RECEIPT = "SOURCE-RELEASE.json"


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True)


def api(path: str):
    return json.loads(gh("api", path))


def pages(path: str):
    return [item for page in json.loads(gh("api", path, "--paginate", "--slurp"))
            for item in page]


def require_private():
    if api("repos/" + ARCHIVE).get("private") is not True:
        raise RuntimeError("Destination must be private before any upload.")


def releases(repo):
    return pages(f"repos/{repo}/releases?per_page=100")


def assets(repo, release_id):
    return pages(f"repos/{repo}/releases/{release_id}/assets?per_page=100")


def safe_name(name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise ValueError("Unsupported asset filename")
    return name


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(repo, asset, target):
    # Download by exact asset ID rather than matching a wildcard or a tag.
    with target.open("xb") as stream:
        subprocess.run(["gh", "api",
                        f"repos/{repo}/releases/assets/{asset['id']}",
                        "-H", "Accept: application/octet-stream"],
                       stdout=stream, check=True)
    if target.stat().st_size != asset["size"]:
        raise RuntimeError("Release asset size mismatch")
    digest = checksum(target)
    expected = asset.get("digest")
    if expected and expected != "sha256:" + digest:
        raise RuntimeError("Release asset digest mismatch")
    return digest


def copy_release(source, release, existing):
    tag = "preserved-" + source.split("/")[-1] + "-" + release["tag_name"]
    # Validate exact ref syntax without accepting shell interpolation.
    subprocess.run(["git", "check-ref-format", "refs/tags/" + tag], check=True)
    source_assets = assets(source, release["id"])
    names = [safe_name(a["name"]) for a in source_assets]
    if len(names) != len(set(names)) or RECEIPT in names:
        raise RuntimeError("Asset name collision")
    if any(a["state"] != "uploaded" for a in source_assets):
        raise RuntimeError("Incomplete source release asset")
    with tempfile.TemporaryDirectory(prefix="archive-transfer-") as tmp:
        root = Path(tmp)
        original = root / "original"
        original.mkdir()
        receipt_assets = []
        for item in source_assets:
            digest = download(source, item, original / item["name"])
            receipt_assets.append({"name": item["name"], "id": item["id"],
                                   "bytes": item["size"], "sha256": digest})
        # Keep original release metadata including original tag, target, dates,
        # notes, asset labels and IDs. New destination tags are archive locators,
        # not substitutes for the original Git refs in the historical bundle.
        metadata = {k: v for k, v in release.items() if k != "assets"}
        receipt = {"source_repository": source, "release": metadata,
                   "assets": receipt_assets, "original_asset_metadata": source_assets}
        (original / RECEIPT).write_text(json.dumps(receipt, sort_keys=True,
                                                   ensure_ascii=False, indent=2),
                                        encoding="utf-8")
        target_release = existing.get(tag)
        require_private()
        if target_release is None:
            gh("release", "create", tag, "-R", ARCHIVE, "--target", "main",
               "--draft", "--title", "Preserved source release",
               "--notes", "Original metadata and asset hashes are in " + RECEIPT)
            target_release = next(x for x in releases(ARCHIVE) if x["tag_name"] == tag)
        dest_assets = {a["name"]: a for a in assets(ARCHIVE, target_release["id"])}
        expected_names = set(names) | {RECEIPT}
        if set(dest_assets) - expected_names:
            raise RuntimeError("Unexpected destination assets; refusing overwrite")
        # Resume an interrupted draft without replacing any existing assets.
        for filename in sorted(expected_names - set(dest_assets)):
            if not target_release["draft"]:
                raise RuntimeError("Published release incomplete; manual review required")
            require_private()
            gh("release", "upload", tag, str(original / filename), "-R", ARCHIVE)
        dest_assets = {a["name"]: a for a in assets(ARCHIVE, target_release["id"])}
        if set(dest_assets) != expected_names:
            raise RuntimeError("Destination asset inventory mismatch")
        recovered = root / "recovered"
        recovered.mkdir()
        for filename, item in dest_assets.items():
            if download(ARCHIVE, item, recovered / filename) != checksum(original / filename):
                raise RuntimeError("Destination round-trip hash mismatch")
        # Preserve a source draft as a draft, and preserve its prerelease status.
        if target_release["draft"] and not release["draft"]:
            require_private()
            gh("release", "edit", tag, "-R", ARCHIVE, "--draft=false",
               "--prerelease=" + str(bool(release["prerelease"])).lower())
        return {"source": source, "source_release_id": release["id"],
                "destination_tag": tag, "assets_verified": len(names),
                "metadata_verified": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source_releases = [(source, release) for source in SOURCES
                       for release in releases(source)]
    if not args.apply:
        print(json.dumps({"mode": "dry-run", "source_releases": len(source_releases),
                          "destination_private": api("repos/" + ARCHIVE)["private"]}))
        return
    require_private()
    existing = {x["tag_name"]: x for x in releases(ARCHIVE)}
    results = [copy_release(source, release, existing) for source, release in source_releases]
    current = [(source, release["id"]) for source in SOURCES
               for release in releases(source)]
    expected = [(source, release["id"]) for source, release in source_releases]
    if set(current) != set(expected):
        raise RuntimeError("Source release inventory changed; rerun before deletion")
    print(json.dumps({"release_transfer_verified": True, "releases": len(results),
                      "assets_verified": sum(x["assets_verified"] for x in results),
                      "source_deletion_authorized": False, "results": results}))


if __name__ == "__main__":
    main()
