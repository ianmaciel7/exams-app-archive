#!/usr/bin/env python3
"""Preserve refs missed by the initial release. Never changes source repositories.

GitHub Actions requires a contents:write GH_TOKEN for the PRIVATE archive only.
All upstream clones are read-only and public. Never imports notes-app private data.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = "ianmaciel7/exams-app-archive"
TAG = "archive-2026-11-23-audit-complements"
SOURCES = {
    "shadcn-template": "Exam UI template — include feature/automation refs",
    "shadcn-firebase-template": "Exam Firebase template — include automation refs",
    "fcc-responsive-web-design": "Auxiliary public repository — inventoried for completeness",
    "ianmaciel7": "Auxiliary public profile repository — inventoried for completeness",
}


def run(*args: str, stdout=None, timeout=900) -> str:
    p = subprocess.run(args, stdout=stdout if stdout is not None else subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout, check=False)
    if p.returncode:
        raise RuntimeError(f"{args[:4]} exited {p.returncode}: {p.stderr.decode(errors='replace')[-900:]}")
    return p.stdout.decode(errors="replace") if stdout is None else ""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda: f.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def refs(repo: Path) -> dict[str, str]:
    out = run("git", f"--git-dir={repo}", "for-each-ref",
              "--format=%(refname) %(objectname)", "refs/heads", "refs/tags")
    return dict(line.rsplit(" ", 1) for line in out.splitlines() if line)


def bundle_refs(bundle: Path) -> dict[str, str]:
    # git bundle list-heads: sha and refname; refname may be HEAD, ignored.
    items = [l.strip().split(" ", 1) for l in run("git", "bundle", "list-heads", str(bundle)).splitlines()]
    return {name: sha for sha, name in items if name.startswith(("refs/heads/", "refs/tags/"))}


def main() -> None:
    if not os.environ.get("GH_TOKEN"):
        raise RuntimeError("GH_TOKEN not configured")
    visibility = run("gh", "repo", "view", REPO, "--json", "visibility", "--jq", ".visibility").strip()
    if visibility != "PRIVATE":
        raise RuntimeError("Target must remain PRIVATE")
    if subprocess.run(["gh", "release", "view", TAG, "--repo", REPO], capture_output=True).returncode == 0:
        print(f"Release {TAG} already exists, no replacements.")
        return

    with tempfile.TemporaryDirectory(prefix="exams-archive-audit-") as d:
        home = Path(d)
        assets = home / "assets"
        assets.mkdir()
        manifest = {
            "tag": TAG, "created_at": datetime.now(timezone.utc).isoformat(),
            "archive": REPO, "reason": "Initial release only included main for two templates, and omitted two auxiliary public repositories.",
            "assets": [], "excluded": [
                "notes-app private repository — no cross-repository authentication available",
                "exams-app/chore/consolidate-legacy-sources-20261123 — generated transient migration copy; excluded deliberately",
                "exams-app/claude/project-thread-o4dym1 — ancestor of dev, commits already included in exams-app.bundle",
                "exams-app-archive — current destination; self-archival is unnecessary",
            ]
        }
        for name, purpose in SOURCES.items():
            source = home / (name + ".git")
            run("git", "clone", "--mirror", "--quiet",
                f"https://github.com/ianmaciel7/{name}.git", str(source), timeout=1200)
            expected = refs(source)
            if not expected:
                raise RuntimeError(f"No refs in {name}")
            target = assets / (name + ".bundle")
            run("git", f"--git-dir={source}", "bundle", "create", str(target), "--branches", "--tags", timeout=1800)
            verify_home = home / (name + ".verify.git")
            run("git", "init", "--bare", "-q", str(verify_home))
            run("git", f"--git-dir={verify_home}", "bundle", "verify", str(target))
            actual = bundle_refs(target)
            if expected != actual:
                raise RuntimeError(f"Ref mismatch {name}: missing={sorted(set(expected)-set(actual))}, extra={sorted(set(actual)-set(expected))}")
            manifest["assets"].append({
                "asset": target.name, "repository": f"ianmaciel7/{name}",
                "purpose": purpose, "sha256": sha256(target),
                "size_bytes": target.stat().st_size, "refs": expected,
                "verified": True
            })
            print(f"{name}: verified {len(actual)} heads/tags ({target.stat().st_size():,} bytes)", flush=True)
        sums = assets / "SHA256SUMS.txt"
        sums.write_text("".join(f"{e['sha256']}  {e['asset']}\n" for e in manifest["assets"]))
        (assets / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        run("gh", "release", "create", TAG, "--repo", REPO, "--draft",
            "--title", "Audit supplement — previously missing branches (2026-11-23)",
            "--notes", "Verified branch-complete Git bundles for two UI templates plus two auxiliary public repositories. Does not add any branches to archive repo.")
        for item in sorted(assets.iterdir()):
            run("gh", "release", "upload", TAG, str(item), "--repo", REPO, timeout=900)
        # Read-back one previously missing refs-rich asset from release.
        checked = home / "download"
        checked.mkdir()
        run("gh", "release", "download", TAG, "--repo", REPO, "--pattern", "shadcn-template.bundle", "--dir", str(checked))
        saved = next(v for v in manifest["assets"] if v["asset"] == "shadcn-template.bundle")
        if sha256(checked / "shadcn-template.bundle") != saved["sha256"]:
            raise RuntimeError("Roundtrip digest mismatch")
        if bundle_refs(checked / "shadcn-template.bundle") != saved["refs"]:
            raise RuntimeError("Roundtrip refs mismatch")
        manifest["roundtrip_verified_asset"] = "shadcn-template.bundle"
        run("gh", "release", "edit", TAG, "--repo", REPO, "--draft=false")
        out = Path("manifests")
        out.mkdir(exist_ok=True)
        (out / "release-2026-11-23-audit-complements.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"success": True, "assets": len(manifest["assets"]), "roundtrip": True}), flush=True)


if __name__ == "__main__":
    main()
