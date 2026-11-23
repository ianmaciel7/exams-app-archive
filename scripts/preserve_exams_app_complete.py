#!/usr/bin/env python3
"""Back up ALL advertised refs and current branch files from the public exams-app.

Preserves public GitHub issue/PR metadata, a browseable file inventory, and a
convenience snapshot of dev. Does NOT modify the source repository.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "ianmaciel7/exams-app"
DEST = "ianmaciel7/exams-app-archive"
TAG = "exams-app-2026-11-23-complete"
EXPECTED_BRANCHES = {
    "main", "dev", "claude/project-thread-o4dym1",
    "chore/consolidate-legacy-sources-20261123",
}

def command(*cmd: str, timeout: int = 1200, stdout=None) -> str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE if stdout is None else stdout,
                       stderr=subprocess.PIPE, timeout=timeout, check=False)
    if p.returncode:
        raise RuntimeError(f"{cmd[:4]} returned {p.returncode}: {p.stderr.decode(errors='replace')[-1000:]}")
    return p.stdout.decode("utf-8", "replace") if stdout is None else ""

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def git(git_dir: Path, *args: str) -> str:
    return command("git", f"--git-dir={git_dir}", *args)

def all_refs(git_dir: Path) -> dict[str, str]:
    raw = git(git_dir, "for-each-ref", "--format=%(objectname) %(refname)")
    return {ref: sha for sha, ref in (line.split(" ", 1) for line in raw.splitlines())}

def bundle_refs(path: Path) -> dict[str, str]:
    return {ref: sha for sha, ref in
            (line.split(" ", 1) for line in command("git", "bundle", "list-heads", str(path)).splitlines())
            if ref.startswith("refs/")}

def api(relative: str, paginated: bool = False):
    # This accesses only the PUBLIC SOURCE, and does not use any private source credentials.
    if paginated:
        pages = json.loads(command("gh", "api", "--paginate", "--slurp", relative, timeout=600))
        return [row for page in pages for row in (page if isinstance(page, list) else [page])]
    return json.loads(command("gh", "api", relative, timeout=180))

def source_metadata():
    issue_path = "repos/" + SOURCE + "/issues"
    pr_path = "repos/" + SOURCE + "/pulls"
    issues = api(issue_path + "?state=all&per_page=100", True)
    pull_requests = api(pr_path + "?state=all&per_page=100", True)
    releases = api("repos/" + SOURCE + "/releases?per_page=100", True)
    issue_data = []
    for i in issues:
        number = i["number"]
        issue_data.append({
            "issue": i, "comments": api(issue_path + f"/{number}/comments?per_page=100", True),
            "events": api(issue_path + f"/{number}/events?per_page=100", True),
        })
    pr_data = []
    for p in pull_requests:
        number = p["number"]
        pr_data.append({
            "pull_request": api(pr_path + f"/{number}"),
            "changed_files": api(pr_path + f"/{number}/files?per_page=100", True),
            "reviews": api(pr_path + f"/{number}/reviews?per_page=100", True),
            "review_comments": api(pr_path + f"/{number}/comments?per_page=100", True),
            "commits": api(pr_path + f"/{number}/commits?per_page=100", True),
        })
    return {
        "source": SOURCE, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "issues": issue_data, "pull_requests": pr_data, "releases": releases,
        "counts": {"issues_including_prs": len(issues), "prs": len(pull_requests),
                   "releases": len(releases)},
    }

def file_inventory(git_dir: Path, refs: dict[str,str]):
    result = []
    for branch in sorted(EXPECTED_BRANCHES):
        ref = "refs/heads/" + branch
        lines = subprocess.run(
            ["git", f"--git-dir={git_dir}", "ls-tree", "-r", "-z", "--long", ref],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        files = []
        for line in lines.split(b"\x00"):
            if not line or b"\t" not in line: continue
            meta, name = line.split(b"\t", 1)
            p = meta.decode("ascii", "replace").split()
            if len(p) < 4: continue
            files.append({
                "path": name.decode("utf-8", "replace"), "mode": p[0],
                "object_type": p[1], "sha": p[2],
                "size": int(p[3]) if p[3].isdigit() else None,
            })
        image_files = [x for x in files if x["path"].lower().endswith((".png",".webp",".jpg",".jpeg",".gif",".svg",".pdf"))]
        result.append({
            "branch": branch, "ref": ref, "sha": refs[ref],
            "files": files, "file_count": len(files),
            "media_file_count": len(image_files),
            "total_blob_bytes": sum(x["size"] or 0 for x in files),
        })
    return result

def main():
    if not os.environ.get("GH_TOKEN"): raise RuntimeError("GH_TOKEN is required")
    if command("gh","repo","view",DEST,"--json","visibility","--jq",".visibility").strip() != "PRIVATE":
        raise RuntimeError("Destination archive must be private")
    if subprocess.run(["gh","release","view",TAG,"--repo",DEST],capture_output=True).returncode == 0:
        raise RuntimeError("Release tag already exists; do not overwrite an immutable snapshot")

    with tempfile.TemporaryDirectory(prefix="exams-complete-") as folder:
        tmp = Path(folder)
        bare = tmp/"source.git"
        command("git","clone","--mirror","--quiet",f"https://github.com/{SOURCE}.git",str(bare),timeout=1500)
        refs = all_refs(bare)
        branch_refs = set(r for r in refs if r.startswith("refs/heads/"))
        missing = {"refs/heads/"+b for b in EXPECTED_BRANCHES} - branch_refs
        if missing: raise RuntimeError("Not all four source branches available: "+repr(missing))
        if len(branch_refs) != 4:
            raise RuntimeError(f"Source branches changed, expected four but got {sorted(branch_refs)}")

        files = file_inventory(bare, refs)
        content = source_metadata()
        assets = tmp/"assets"; assets.mkdir()
        bundle = assets/"exams-app-all-refs.bundle"
        command("git",f"--git-dir={bare}","bundle","create",str(bundle),"--all",timeout=1500)

        isolated = tmp/"check.git"
        command("git","init","--bare","-q",str(isolated))
        command("git",f"--git-dir={isolated}","bundle","verify",str(bundle))
        actual = bundle_refs(bundle)
        if refs != actual: raise RuntimeError("Advertised refs missing or SHA mismatch in bundle")

        restored = tmp/"restored.git"
        command("git","clone","--mirror","--quiet",str(bundle),str(restored),timeout=1500)
        for item in files:
            branch=item["branch"]
            if git(restored,"rev-parse","refs/heads/"+branch).strip() != item["sha"]:
                raise RuntimeError("Restored branch HEAD mismatch: "+branch)
            restored_paths=command("git",f"--git-dir={restored}","ls-tree","-r","--name-only",
                                    "refs/heads/"+branch).splitlines()
            if len(restored_paths) != item["file_count"]:
                raise RuntimeError("Restored branch file count mismatch: "+branch)

        # Convenience view: current dev snapshot can be opened without using Git.
        dev_archive=assets/"exams-app-dev-snapshot.tar.gz"
        command("git",f"--git-dir={bare}","archive","--format=tar.gz",
                f"--output={dev_archive}","refs/heads/dev",timeout=900)
        file_json=assets/"BRANCH-FILES.json"
        file_json.write_text(json.dumps({
            "source":SOURCE, "branch_inventories":files,
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        metadata=assets/"GITHUB-METADATA.json"
        metadata.write_text(json.dumps(content,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

        lfs_status="not independently verified"
        attributes = [f for f in files if any(x["path"]==".gitattributes" for x in f["files"])]
        if not attributes:
            lfs_status="no root .gitattributes found on the four branch heads; other pointers not exhaustively checked"

        wiki = {"status": "not checked"}
        wiki_addr=f"https://github.com/{SOURCE}.wiki.git"
        wiki_check=subprocess.run(["git","ls-remote",wiki_addr],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
        if wiki_check.returncode==0:
            wiki={"status":"accessible", "ref_count":len(wiki_check.stdout.splitlines())}
            wb=tmp/"wiki.git"
            command("git","clone","--mirror","--quiet",wiki_addr,str(wb),timeout=900)
            wiki_bundle=assets/"exams-app-wiki.bundle"
            command("git",f"--git-dir={wb}","bundle","create",str(wiki_bundle),"--all",timeout=900)
            wc=tmp/"wiki-check.git"
            command("git","init","--bare","-q",str(wc))
            command("git",f"--git-dir={wc}","bundle","verify",str(wiki_bundle))
            wiki["sha256"]=digest(wiki_bundle)
        else:
            wiki={"status":"wiki repository is empty, absent or inaccessible", "reason":wiki_check.stderr.decode(errors="replace")[-200:]}

        assets_detail=[{"name":p.name,"size_bytes":p.stat().st_size,"sha256":digest(p)}
                       for p in sorted(assets.iterdir())]
        manifest={
            "archive":DEST,"source":SOURCE,"tag":TAG,
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "all_advertised_refs":refs, "ref_count":len(refs),
            "branch_count":len(branch_refs),"refs_pull_count":sum(r.startswith("refs/pull/") for r in refs),
            "branch_summaries":[{k:item[k] for k in ("branch","sha","file_count","media_file_count","total_blob_bytes")} for item in files],
            "github_metadata_counts":content["counts"],"wiki":wiki,
            "git_lfs":lfs_status,"assets":assets_detail,
            "integrity":{"bundle_verify":True,"all_refs_equal":True,
                         "roundtrip_branch_restore":True},
            "notes":["Source repository is public; archive is private.",
                     "Includes all four branches, including previously excluded temporary branches.",
                     "Other Github platform metadata such as older workflow artifacts or LFS payloads may require additional exports.",
                     "Git unreferenced/pruned objects are not recoverable solely from a mirror clone."],
        }
        (assets/"MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
        (assets/"SHA256SUMS.txt").write_text("".join(f"{p['sha256']}  {p['name']}\n" for p in assets_detail))
        command("gh","release","create",TAG,"--repo",DEST,"--draft",
                "--title","Complete exams-app archive: all four branches and metadata",
                "--notes","All advertised Git refs, all four original branches, a browseable file inventory, current dev tar.gz snapshot, and GitHub issue/PR metadata.")
        for asset in sorted(assets.iterdir()):
            command("gh","release","upload",TAG,str(asset),"--repo",DEST,timeout=1200)
        downloaded=tmp/"downloaded";downloaded.mkdir()
        command("gh","release","download",TAG,"--repo",DEST,"--pattern","exams-app-all-refs.bundle",
                "--dir",str(downloaded),timeout=900)
        fetched=downloaded/"exams-app-all-refs.bundle"
        if digest(fetched)!=digest(bundle) or bundle_refs(fetched)!=refs:
            raise RuntimeError("Downloaded release bundle digest or ref validation failed")
        manifest["integrity"]["release_download_roundtrip"]=True
        command("gh","release","edit",TAG,"--repo",DEST,"--draft=false")
        output=Path("manifests");output.mkdir(exist_ok=True)
        (output/"exams-app-complete-2026-11-23.json").write_text(
            json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

        inv=Path("inventory"); inv.mkdir(exist_ok=True)
        (inv/"exams-app-branch-files.json").write_text(
            file_json.read_text(encoding="utf-8"),encoding="utf-8")
        docs=Path("docs");docs.mkdir(exist_ok=True)
        md=["# Exams App — verificação de preservação completa","",
            "Fonte: https://github.com/"+SOURCE,
            "Destino (privado): https://github.com/"+DEST,
            "",
            "**Todas as quatro branches e todos os objetos alcançáveis pelas refs anunciadas no Git foram exportados.**",
            "As refs originais permanecem no bundle; não foram criadas branches no repositório de arquivo.",
            "",
            "| Branch | HEAD | Arquivos | Imagens/PDF |",
            "|---|---|---:|---:|"]
        for item in files:
            md.append(f"| \u0060{item['branch']}\u0060 | \u0060{item['sha'][:12]}\u0060 | {item['file_count']} | {item['media_file_count']} |")
        md+=["",
             f"- Referências Git no backup: **{len(refs)}**, incluindo {sum(r.startswith('refs/pull/') for r in refs)} refs de PR.",
             f"- Issues (incluindo PR): {len(content['issues'])}; PRs: {len(content['pull_requests'])}; releases de origem: {len(content['releases'])}.",
             f"- Wiki: {wiki['status']}.",
             f"- LFS: {lfs_status}.","",
             "## Como recuperar",
             "",
             "Acesse a [release privada](https://github.com/"+DEST+"/releases/tag/"+TAG+").",
             "",
             "- \u0060exams-app-all-refs.bundle\u0060 — backup Git com todas as branches, histórico e refs de PR.",
             "- \u0060exams-app-dev-snapshot.tar.gz\u0060 — arquivos da branch dev em arquivo extraível.",
             "- \u0060BRANCH-FILES.json\u0060 — todos os caminhos, tamanhos e hashes por branch.",
             "- \u0060GITHUB-METADATA.json\u0060 — issues, PRs, comentários, eventos, revisões e arquivos alterados.",
             "- \u0060MANIFEST.json\u0060 e \u0060SHA256SUMS.txt\u0060 — rastreabilidade e checksums.",
             "",
             "## Integridade",
             "",
             "- \u0060git bundle verify\u0060 aprovado.",
             "- Todas as refs e seus commits no bundle conferem com o espelho.",
             "- As quatro branches foram restauradas e tiveram heads e quantidade de arquivos comparados.",
             "- O asset publicado foi baixado novamente e validado por SHA-256 e refs.",
             "",
             "Arquivos grandes são armazenados em releases, e não duplicados no histórico Git do arquivo.",
             "A presença de todos os arquivos dentro de Git Bundle não significa que cada arquivo",
             "apareça individualmente na árvore do GitHub; consulte a lista em \u0060inventory/\u0060",
             "ou extraia o snapshot para navegar pelos arquivos.",
             "",
             "Metadados GitHub fora do Git, LFS remoto e objetos já eliminados do upstream podem",
             "exigir preservação separada e não estão incluídos na garantia de Git Bundle.",""]
        (docs/"EXAMS-APP-COMPLETE.md").write_text("\n".join(md),encoding="utf-8")
        print(json.dumps({"success":True,"release":TAG,"heads":len(branch_refs),
                          "refs":len(refs),"pr_refs":sum(r.startswith("refs/pull/") for r in refs),
                          "branch_files":{x["branch"]:x["file_count"] for x in files},
                          "pr_count":len(content["pull_requests"]),
                          "roundtrip":True},ensure_ascii=False),flush=True)

if __name__=="__main__": main()
