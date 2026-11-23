#!/usr/bin/env python3
"""Check the published exams-app backup for all refs, files, media, LFS and CI metadata.

Read Git history from the PRIVATE release, not from upstream. Export public
workflow run metadata and (when readable) public logs to a second private
release. Never changes the source repository or exposes secrets.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE = "ianmaciel7/exams-app-archive"
SOURCE = "ianmaciel7/exams-app"
SOURCE_TAG = "exams-app-2026-11-23-complete"
TAG = "exams-app-2026-11-23-verification"
MANIFEST_PATH = Path("manifests/exams-app-complete-2026-11-23.json")
MEDIA = (".png", ".webp", ".jpg", ".jpeg", ".gif", ".svg", ".pdf")


def run(*args, output=None, timeout=900):
    proc = subprocess.run(
        args, stdout=output if output is not None else subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=timeout, check=False
    )
    if proc.returncode:
        raise RuntimeError(f"{args[:4]} failed ({proc.returncode}): " +
                           proc.stderr.decode("utf-8", "replace")[-750:])
    return proc.stdout if output is None else b""


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def gh_json(endpoint):
    return json.loads(run("gh", "api", endpoint).decode("utf-8"))


def branch_files(repo, ref):
    blob = run("git", f"--git-dir={repo}", "ls-tree", "--long", "-r", "-z", ref)
    result = []
    for row in blob.split(b"\x00"):
        if not row or b"\t" not in row:
            continue
        meta, path = row.split(b"\t", 1)
        mode, kind, sha, size = meta.decode("ascii").split()
        result.append({
            "mode": mode, "kind": kind, "sha": sha,
            "size": int(size) if size.isdigit() else None,
            "path": path.decode("utf-8", "replace")
        })
    return result


def refs(repo):
    data = run("git", f"--git-dir={repo}", "for-each-ref",
               "--format=%(objectname) %(refname)").decode()
    return {ref: sha for sha, ref in (x.split(" ", 1) for x in data.splitlines())}


def detect_lfs(repo):
    # Includes all available objects, not only present-day branch heads.
    all_objects = run(
        "git", f"--git-dir={repo}", "cat-file",
        "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
        timeout=900
    ).decode()
    candidates = []
    for line in all_objects.splitlines():
        sha, kind, size = line.split()
        if kind == "blob" and 75 <= int(size) <= 800:
            candidates.append(sha)
    pointers = []
    for sha in candidates:
        content = run("git", f"--git-dir={repo}", "cat-file", "blob", sha)
        if content.startswith(b"version https://git-lfs.github.com/spec/v1"):
            pointers.append({
                "blob": sha,
                "content": content.decode("utf-8", "replace")[:400]
            })
    return {
        "total_objects_scanned": len(all_objects.splitlines()),
        "candidate_small_blobs_scanned": len(candidates),
        "lfs_pointers_found": len(pointers),
        "pointers": pointers[:40],
        "pointers_truncated": len(pointers) > 40,
    }


def github_runs():
    try:
        runs = gh_json(f"repos/{SOURCE}/actions/runs?per_page=100")
        n = runs.get("total_count", 0)
        if n > 100:
            raise RuntimeError("More than 100 actions runs; pagination needed")
        details = []
        for r in runs.get("workflow_runs", []):
            run_id = r["id"]
            jobs = gh_json(f"repos/{SOURCE}/actions/runs/{run_id}/jobs?per_page=100")
            artifacts = gh_json(f"repos/{SOURCE}/actions/runs/{run_id}/artifacts?per_page=100")
            details.append({
                "id": run_id, "name": r.get("name"), "event": r.get("event"),
                "created_at": r.get("created_at"), "status": r.get("status"),
                "conclusion": r.get("conclusion"), "url": r.get("html_url"),
                "jobs": [{"id": x["id"], "name": x.get("name"),
                          "status": x.get("status"), "conclusion": x.get("conclusion")}
                         for x in jobs.get("jobs", [])],
                "artifacts_count": artifacts.get("total_count", 0),
                "artifacts": [{"id":a.get("id"), "name":a.get("name"),
                               "expired":a.get("expired"), "size_in_bytes":a.get("size_in_bytes")}
                              for a in artifacts.get("artifacts", [])],
            })
        return {"verified": True, "total_runs": n, "runs": details}
    except Exception as exc:
        return {"verified": False, "error": str(exc)[:500]}


def main():
    if not os.environ.get("GH_TOKEN"):
        raise RuntimeError("GH_TOKEN missing")
    if run("gh", "repo", "view", ARCHIVE, "--json", "visibility", "--jq", ".visibility").decode().strip() != "PRIVATE":
        raise RuntimeError("Archive must stay private")
    if subprocess.run(["gh", "release", "view", TAG, "--repo", ARCHIVE], capture_output=True).returncode == 0:
        print("Audit release already exists; not overwriting")
        return
    manifest = json.loads(MANIFEST_PATH.read_text())
    with tempfile.TemporaryDirectory(prefix="exams-integrity-") as folder:
        root = Path(folder)
        run("gh", "release", "download", SOURCE_TAG, "--repo", ARCHIVE,
            "--pattern", "exams-app-all-refs.bundle", "--dir", str(root), timeout=900)
        run("gh", "release", "download", SOURCE_TAG, "--repo", ARCHIVE,
            "--pattern", "exams-app-dev-snapshot.tar.gz", "--dir", str(root), timeout=900)
        bundle = root / "exams-app-all-refs.bundle"
        snapshot = root / "exams-app-dev-snapshot.tar.gz"
        def expected_digest(name):
            return next(x["sha256"] for x in manifest["assets"] if x["name"] == name)
        if sha256(bundle) != expected_digest(bundle.name):
            raise RuntimeError("Bundle checksum mismatch")
        if sha256(snapshot) != expected_digest(snapshot.name):
            raise RuntimeError("dev snapshot checksum mismatch")
        gitdir = root / "restored.git"
        run("git", "clone", "--mirror", "--quiet", str(bundle), str(gitdir), timeout=1200)
        run("git", f"--git-dir={gitdir}", "fsck", "--full", "--no-reflogs", timeout=1200)
        backed_up_refs = refs(gitdir)
        expected_refs = manifest["all_advertised_refs"]
        if backed_up_refs != expected_refs:
            raise RuntimeError("Backup refs do not match the original all-ref inventory")
        branch_checks = []
        attrs = []
        submodules = []
        for branch in manifest["branch_summaries"]:
            ref = "refs/heads/" + branch["branch"]
            got_sha = run("git", f"--git-dir={gitdir}", "rev-parse", ref).decode().strip()
            if got_sha != branch["sha"]:
                raise RuntimeError("Branch SHA mismatch: " + ref)
            files = branch_files(gitdir, ref)
            if len(files) != branch["file_count"]:
                raise RuntimeError("File count mismatch: " + ref)
            media = [x for x in files if x["path"].lower().endswith(MEDIA)]
            if len(media) != branch["media_file_count"]:
                raise RuntimeError("Media count mismatch: " + ref)
            attrs += [branch["branch"] + ":" + x["path"] for x in files if x["path"].endswith(".gitattributes")]
            submodules += [branch["branch"] + ":" + x["path"] for x in files if x["mode"] == "160000"]
            branch_checks.append({"branch": branch["branch"],
                "head": got_sha, "files": len(files), "media": len(media),
                "blob_bytes": sum(x["size"] or 0 for x in files), "verified": True})

        with tarfile.open(snapshot, "r:gz") as t:
            members = t.getmembers()
            archived = {x.name for x in members if x.isfile() or x.issym() or x.islnk()}
        dev = branch_files(gitdir, "refs/heads/dev")
        actual_dev_files = {x["path"] for x in dev}
        if archived != actual_dev_files:
            raise RuntimeError(
                f"dev TAR member mismatch: {len(archived)} != {len(actual_dev_files)}, "
                f"missing={sorted(actual_dev_files-archived)[:4]}, extra={sorted(archived-actual_dev_files)[:4]}"
            )
        lfs = detect_lfs(gitdir)
        actions = github_runs()

        logs = []
        for item in actions.get("runs", []):
            for job in item.get("jobs", []):
                out = root / f"exams-app-job-{job['id']}.log.gz"
                try:
                    # GH API follows GitHub's signed log redirect when authorized.
                    raw = run("gh", "api", f"repos/{SOURCE}/actions/jobs/{job['id']}/logs", timeout=150)
                    if not raw.strip():
                        raise RuntimeError("Empty log")
                    with gzip.open(out, "wb", compresslevel=6) as o:
                        o.write(raw)
                    logs.append({"job_id": job["id"], "asset": out.name,
                                 "bytes": out.stat().st_size,
                                 "sha256": sha256(out), "saved": True})
                except Exception as e:
                    logs.append({"job_id": job["id"], "saved": False, "error": str(e)[:220]})

        report = {
            "source": SOURCE,
            "archive": ARCHIVE,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "release_checked": SOURCE_TAG,
            "integrity": {
                "bundle_sha256_valid": True,
                "snapshot_sha256_valid": True,
                "git_fsck_full": True,
                "all_refs_match": True,
                "branch_heads_and_file_counts_match": True,
                "dev_tar_files_match": True
            },
            "refs_count": len(backed_up_refs),
            "branches": branch_checks,
            "gitmodules": submodules,
            "gitattributes_files": attrs,
            "git_lfs": lfs,
            "github_actions": actions,
            "workflow_job_logs": logs,
            "limitations": [
                "All Git refs and objects reachable by the release were verified, not unreachable/pruned upstream objects.",
                "GitHub Actions logs were saved only if their source API endpoint allowed reading them.",
                "GitHub API metadata, including some platform settings, may change after this snapshot.",
                "External website assets and third-party services referenced in documents are not bundled.",
                "Checks on other repositories, including notes-app private, are tracked separately."
            ]
        }
        asset_dir = root / "assets"
        asset_dir.mkdir()
        metadata = asset_dir / "GIT-AND-ACTIONS-VERIFICATION.json"
        metadata.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        for item in logs:
            if item.get("saved"):
                (root / item["asset"]).rename(asset_dir / item["asset"])
        run("gh", "release", "create", TAG, "--repo", ARCHIVE, "--draft",
            "--title", "Exams App integrity + LFS and workflow audit",
            "--notes", "Validates all four branches, git fsck, source refs, dev snapshot and possible LFS pointers. Includes Actions job logs if accessible.")
        for asset in sorted(asset_dir.iterdir()):
            run("gh", "release", "upload", TAG, str(asset), "--repo", ARCHIVE, timeout=300)
        run("gh", "release", "edit", TAG, "--repo", ARCHIVE, "--draft=false")
        Path("reports").mkdir(exist_ok=True)
        Path("reports/EXAMS-APP-VERIFY.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        lines = [
            "# Verificação adicional do exams-app", "",
            "Bundle original e TAR extraídos da release privada; nenhum repositório de origem foi modificado.", "",
            "| Verificação | Resultado |", "|---|---|",
            "| Git Bundle SHA-256 | Passou |", "| Snapshot dev SHA-256 | Passou |",
            "| git fsck --full | Passou |", "| SHA de todas as refs | Passou |",
            "| Todas as quatro branches: SHA, arquivos e mídia | Passou |",
            "| Arquivos do TAR dev contra árvore Git | Passou |",
            f"| Ponteiros Git LFS detectados (todos os objetos do bundle) | {lfs['lfs_pointers_found']} |",
            f"| Submódulos nos HEADs | {len(submodules)} |",
            f"| .gitattributes nos HEADs | {len(attrs)} |",
            f"| Workflows antigos | {actions.get('total_runs', 'não verificado')} |",
            f"| Artifacts de CI | {sum(i['artifacts_count'] for i in actions.get('runs', []))} |",
            f"| Logs de CI recuperados | {sum(bool(i.get('saved')) for i in logs)}/{len(logs)} |",
            "", "## Branches", "",
            "| Branch | SHA | Arquivos | Mídias |", "|---|---|---:|---:|",
        ]
        for x in branch_checks:
            lines.append(f"| {x['branch']} | \`{x['head'][:12]}\` | {x['files']} | {x['media']} |")
        lines += ["", f"Release: https://github.com/{ARCHIVE}/releases/tag/{TAG}",
                  "", "O relatório JSON contém detalhes e limitações.", ""]
        Path("reports/EXAMS-APP-VERIFY.md").write_text("\n".join(lines))
        print(json.dumps({"ok": True, "branches": len(branch_checks),
                          "refs": len(backed_up_refs), "lfs": lfs["lfs_pointers_found"],
                          "actions_runs": actions.get("total_runs"),
                          "logs_saved": sum(bool(x.get("saved")) for x in logs)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
