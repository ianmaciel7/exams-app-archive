"""Build a public metadata catalog from approved GitHub repositories, never from private bundles."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import re
import subprocess
from pathlib import Path

import tempfile

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/public-catalog-sources.json"
SHA = re.compile(r"[0-9a-f]{40}")
EXCLUDED = re.compile(r"(?:^|/)(?:node_modules|\.git|\.cache|\.env[^/]*|secrets?|credentials?|private)(?:/|$)|(?:password|api[_-]?key|credential|token)[-_.]", re.I)
SECRET_CONTENT = re.compile(rb"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|BEGIN [A-Z ]+PRIVATE KEY|sk-[A-Za-z0-9]{32,}|xox[baprs]-[A-Za-z0-9-]{10,})")
TEXT_EXTENSIONS = {".tsx",".jsx",".ts",".js",".mjs",".cjs",".css",".scss",".html",".md",".mdx",".json",".yaml",".yml",".py",".cs",".sql"}
IMAGE_EXTENSIONS = {".png",".jpg",".jpeg",".webp",".gif",".svg"}
EXTENSIONS = TEXT_EXTENSIONS | IMAGE_EXTENSIONS | {".pdf"}
MAX_TEXT_BLOB = 256 * 1024
MAX_IMAGE_BLOB = 1536 * 1024

def api(path, paginate=False):
    cmd = ["gh","api",path]
    if paginate: cmd.extend(["--paginate","--slurp"])
    value = json.loads(subprocess.check_output(cmd, text=True, timeout=120))
    return [item for page in value for item in page] if paginate else value

def eligible(entry):
    path=entry.get("path","")
    return (entry.get("type")=="blob" and entry.get("mode")!="120000"
            and not EXCLUDED.search(path) and Path(path).suffix.lower() in EXTENSIONS
            and not any(ord(ch)<32 for ch in path)
            and SHA.fullmatch(entry.get("sha","")) is not None)

def build(policy, request=api):
    snapshots=[]
    coverage=[]
    for repo in policy["repositories"]:
        if not re.fullmatch(r"ianmaciel7/[A-Za-z0-9_.-]+",repo):
            raise ValueError("Unapproved repository")
        base="repos/"+repo
        meta=request(base)
        if meta.get("private") is not False or meta.get("visibility")!="public":
            raise ValueError("Public catalog refuses non-public source: "+repo)
        refs={}
        for branch in request(base+"/branches?per_page=100",True):
            sha=branch["commit"]["sha"]
            if not SHA.fullmatch(sha): raise ValueError("Invalid SHA")
            refs.setdefault(sha,[]).append("branch:"+branch["name"])
        for tag in request(base+"/tags?per_page=100",True):
            sha=tag["commit"]["sha"]
            if not SHA.fullmatch(sha): raise ValueError("Invalid SHA")
            refs.setdefault(sha,[]).append("tag:"+tag["name"])
        trees={}
        for sha, aliases in sorted(refs.items()):
            commit=request(base+"/commits/"+sha)
            tree=commit["commit"]["tree"]["sha"]
            if not SHA.fullmatch(tree): raise ValueError("Invalid tree SHA")
            if tree not in trees:
                # Git defines this SHA as the canonical empty tree. The API may return 404 for it.
                data = {"truncated": False, "tree": []} if tree == "4b825dc642cb6eb9a060e54bf8d69288fbee4904" else request(base+"/git/trees/"+tree+"?recursive=1")
                if data.get("truncated"): raise ValueError("Truncated tree: "+repo)
                trees[tree]=[{"path":e["path"],"blob":e["sha"],"size":e.get("size",0)} for e in data["tree"] if eligible(e)]
            snapshots.append({"repo":repo.split("/")[1],"sha":sha,"refs":sorted(aliases),"files":trees[tree]})
        coverage.append({"repo":repo,"refs":sum(map(len,refs.values())),"commits":len(refs),"trees":len(trees)})
    # Explicit retired/unavailable origins are not queried or silently counted as covered.
    for repo in policy.get("historical_unavailable", []):
        if not re.fullmatch(r"ianmaciel7/[A-Za-z0-9_.-]+", repo) or repo in policy["repositories"]:
            raise ValueError("Invalid historical-only source")
        coverage.append({"repo":repo,"refs":0,"commits":0,"trees":0,
                         "status":"historical-only","reason":"origin unavailable; restore authorized archive locally"})
    return {"version":2,"generated_at":datetime.now(timezone.utc).isoformat(),"coverage":coverage,"snapshots":snapshots}


def _export_blob(git_dir: Path, blob_sha: str, ext: str, size: int, blobs_dir: Path, exported: set[str]) -> bool:
    if blob_sha in exported:
        return True
    is_text = ext in TEXT_EXTENSIONS
    is_img = ext in IMAGE_EXTENSIONS
    if is_text and size > MAX_TEXT_BLOB:
        return False
    if is_img and size > MAX_IMAGE_BLOB:
        return False
    if not (is_text or is_img):
        return False
    raw = subprocess.check_output(["git", "--git-dir", str(git_dir), "cat-file", "blob", blob_sha], timeout=30)
    if is_text and SECRET_CONTENT.search(raw):
        return False
    dest = blobs_dir / blob_sha[:2] / blob_sha
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    exported.add(blob_sha)
    return True


def build_from_bundles(policy, bundle_dir: Path, blobs_dir: Path | None = None):
    """Build catalog snapshots from verified public Git bundles (never private/Notes repos)."""
    approved_repos = list(policy.get("repositories", [])) + list(policy.get("historical_unavailable", []))
    snapshots = []
    coverage = []
    exported_blobs: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="catalog-git-") as tmp_root:
        tmp_path = Path(tmp_root)
        for full_repo in approved_repos:
            if not re.fullmatch(r"ianmaciel7/[A-Za-z0-9_.-]+", full_repo):
                raise ValueError("Unapproved repository: " + full_repo)
            name = full_repo.split("/")[1]
            if "notes" in name.lower():
                raise ValueError("Refusing private Notes repository in public catalog: " + full_repo)
            bundle = bundle_dir / f"{name}.bundle"
            if not bundle.is_file():
                coverage.append({"repo": full_repo, "refs": 0, "commits": 0, "trees": 0, "status": "bundle-missing"})
                continue
            git_dir = tmp_path / f"{name}.git"
            subprocess.run(["git", "clone", "--bare", "-q", str(bundle), str(git_dir)], check=True, timeout=180)
            refs_out = subprocess.check_output(
                ["git", "--git-dir", str(git_dir), "for-each-ref", "--format=%(objectname) %(refname)", "refs/heads/", "refs/tags/"],
                text=True, timeout=60
            )
            by_sha: dict[str, list[str]] = {}
            for line in refs_out.splitlines():
                if not line.strip():
                    continue
                sha, ref = line.split(" ", 1)
                if not SHA.fullmatch(sha):
                    continue
                if ref.startswith("refs/heads/"):
                    alias = "branch:" + ref[len("refs/heads/"):]
                elif ref.startswith("refs/tags/"):
                    alias = "tag:" + ref[len("refs/tags/"):]
                else:
                    continue
                by_sha.setdefault(sha, []).append(alias)
            trees_seen: set[str] = set()
            for sha, aliases in sorted(by_sha.items()):
                tree_out = subprocess.check_output(
                    ["git", "--git-dir", str(git_dir), "ls-tree", "-r", "-l", sha],
                    text=True, timeout=60
                )
                files = []
                for line in tree_out.splitlines():
                    if "\t" not in line:
                        continue
                    meta, path = line.split("\t", 1)
                    parts = meta.split()
                    if len(parts) < 4:
                        continue
                    mode, typ, blob, size_str = parts[0], parts[1], parts[2], parts[3]
                    if size_str == "-":
                        continue
                    size = int(size_str)
                    entry = {"type": typ, "mode": mode, "sha": blob, "path": path, "size": size}
                    if not eligible(entry):
                        continue
                    rec = {"path": path, "blob": blob, "size": size}
                    if blobs_dir is not None:
                        ext = Path(path).suffix.lower()
                        if _export_blob(git_dir, blob, ext, size, blobs_dir, exported_blobs):
                            rec["cached"] = True
                    files.append(rec)
                trees_seen.add(sha)
                snapshots.append({"repo": name, "sha": sha, "refs": sorted(aliases), "files": files})
            coverage.append({
                "repo": full_repo,
                "refs": sum(map(len, by_sha.values())),
                "commits": len(by_sha),
                "trees": len(trees_seen),
                "source": "public-archive-bundle",
            })
    result = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coverage": coverage,
        "snapshots": snapshots,
    }
    if blobs_dir is not None:
        result["blobs_base"] = "./blobs"
        result["exported_blobs"] = len(exported_blobs)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--from-release",type=str,default="",help="Public release tag containing .bundle assets (e.g. archive-2026-11-23-all-refs)")
    p.add_argument("--bundle-dir",type=Path,default=None,help="Local directory with pre-downloaded public .bundle assets")
    p.add_argument("--blobs-dir",type=Path,default=None,help="Optional output directory for deduplicated public text/image blobs")
    args=p.parse_args()
    policy=json.loads(POLICY.read_text(encoding="utf-8"))
    if args.bundle_dir:
        data=build_from_bundles(policy, args.bundle_dir, args.blobs_dir)
    elif args.from_release:
        approved = [r.split("/")[1] for r in list(policy.get("repositories", [])) + list(policy.get("historical_unavailable", []))]
        with tempfile.TemporaryDirectory(prefix="release-bundles-") as td:
            bdir = Path(td)
            cmd = ["gh", "release", "download", args.from_release, "-D", str(bdir), "--clobber"]
            for name in approved:
                if "notes" not in name.lower():
                    cmd.extend(["-p", f"{name}.bundle"])
            subprocess.run(cmd, check=True, timeout=300)
            data=build_from_bundles(policy, bdir, args.blobs_dir)
    else:
        data=build(policy)
    payload=json.dumps(data,ensure_ascii=False,separators=(",",":"))
    if len(payload.encode("utf-8"))>30*1024*1024:
        raise ValueError("Catalog exceeded 30 MiB; partition before publication")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.output.with_suffix(".tmp")
    tmp.write_text(payload,encoding="utf-8")
    tmp.replace(args.output)
    print(json.dumps({"coverage":data["coverage"],"snapshots":len(data["snapshots"]),"exported_blobs":data.get("exported_blobs",0),"bytes":len(payload.encode("utf-8"))}))

if __name__=="__main__":
    main()
