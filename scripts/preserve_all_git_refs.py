#!/usr/bin/env python3
"""Create a truly all-refs archival release from public source mirrors.

Includes PR refs, not only heads/tags. Deliberately drops two known temporary
branches in exams-app from the temporary MIRROR ONLY (never from upstream).
All refs in the resulting bundles must match the refs in the temporary mirrors.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE="ianmaciel7/exams-app-archive"
TAG="archive-2026-11-23-all-refs"
PUBLIC=[
    "exams-app","exams-app-old","exams-app-antigo-2",
    "shadcn-template","shadcn-firebase-template",
    "fcc-responsive-web-design","ianmaciel7"
]
EXCLUDE={
    "exams-app":[
        "refs/heads/chore/consolidate-legacy-sources-20261123",
        "refs/heads/claude/project-thread-o4dym1",
    ]
}
OUT=Path("manifests")

def run(*cmd,stdout=None,timeout=1800):
    p=subprocess.run(cmd,stdout=stdout if stdout is not None else subprocess.PIPE,
                     stderr=subprocess.PIPE,timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{cmd[:4]} ({p.returncode}): {p.stderr.decode(errors='replace')[-1100:]}")
    return p.stdout.decode(errors="replace") if stdout is None else ""

def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as inp:
        for chunk in iter(lambda:inp.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def all_refs(repo):
    txt=run("git",f"--git-dir={repo}","for-each-ref",
            "--format=%(objectname) %(refname)")
    return {name:sha for sha,name in (l.split(" ",1) for l in txt.splitlines())}

def bundle_refs(path):
    v=run("git","bundle","list-heads",str(path))
    return {name:sha for sha,name in (l.split(" ",1) for l in v.splitlines()) if name.startswith("refs/")}

def main():
    if not os.environ.get("GH_TOKEN"):
        raise RuntimeError("GH_TOKEN is required")
    if run("gh","repo","view",ARCHIVE,"--json","visibility","--jq",".visibility").strip()!="PRIVATE":
        raise RuntimeError("Refusing to store source snapshots outside private archive")
    if subprocess.run(["gh","release","view",TAG,"--repo",ARCHIVE],capture_output=True).returncode==0:
        print("Immutable all-refs release already exists. No overwrite.")
        return
    manifest={
        "tag":TAG,"generated_utc":datetime.now(timezone.utc).isoformat(),
        "archive":ARCHIVE,
        "method":"git clone --mirror; bundle create --all; bundle verify; compare every advertised ref SHA; release download roundtrip",
        "assets":[],
        "limitations":[
            "Full notes-app private remote not included: archive GITHUB_TOKEN has no cross-private read permission.",
            "Only refs GitHub advertises to git clone --mirror are captured; unreachable and pruned objects are not guaranteed.",
            "Git LFS payloads and GitHub Issues/PR metadata/comments are not Git objects.",
            "Two unneeded branches created or superseded in exams-app were excluded intentionally."
        ]
    }
    with tempfile.TemporaryDirectory(prefix="exam-all-refs-") as folder:
        tmp=Path(folder)
        assets=tmp/"assets";assets.mkdir()
        for name in PUBLIC:
            mirror=tmp/(name+".git")
            run("git","clone","--mirror","--quiet",
                f"https://github.com/ianmaciel7/{name}.git",str(mirror),timeout=1800)
            original=all_refs(mirror)
            removed={}
            for ref in EXCLUDE.get(name,[]):
                if ref in original:
                    removed[ref]=original[ref]
                    run("git",f"--git-dir={mirror}","update-ref","-d",ref)
            expected=all_refs(mirror)
            if not expected:
                raise RuntimeError(f"Empty mirror refs: {name}")
            file=assets/(name+".bundle")
            run("git",f"--git-dir={mirror}","bundle","create",str(file),"--all",timeout=1800)
            check=tmp/(name+".verify.git")
            run("git","init","--bare","-q",str(check))
            run("git",f"--git-dir={check}","bundle","verify",str(file))
            actual=bundle_refs(file)
            if expected!=actual:
                missing=set(expected)-set(actual)
                extra=set(actual)-set(expected)
                changed=[k for k in expected.keys()&actual.keys() if expected[k]!=actual[k]]
                raise RuntimeError(f"Ref completeness mismatch {name}: missing={list(missing)[:8]},extra={list(extra)[:8]},changed={changed[:8]}")
            manifest["assets"].append({
                "asset":file.name,"repository":f"ianmaciel7/{name}",
                "sha256":digest(file),"bytes":file.stat().st_size,
                "original_ref_count":len(original),
                "preserved_ref_count":len(expected),
                "ref_categories": {
                    "branch":sum(r.startswith("refs/heads/") for r in expected),
                    "pull":sum(r.startswith("refs/pull/") for r in expected),
                    "tag":sum(r.startswith("refs/tags/") for r in expected),
                    "other":sum(not r.startswith(("refs/heads/","refs/pull/","refs/tags/")) for r in expected),
                },
                "excluded_refs":removed,"refs":expected,"verified":True
            })
            print(f"{name}: preserved {len(expected)} of {len(original)} advertised refs; {file.stat().st_size:,} bytes",flush=True)
        (assets/"MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
        (assets/"SHA256SUMS.txt").write_text("".join(f"{a['sha256']}  {a['asset']}\n" for a in manifest["assets"]))
        run("gh","release","create",TAG,"--repo",ARCHIVE,"--draft",
            "--title","All-refs Git history snapshot (including PR refs), 2026-11-23",
            "--notes","Authoritative public history backup: mirrors all advertised refs, including pull request refs, with two intentional temporary ref exclusions in exams-app.")
        for file in sorted(assets.iterdir()):
            run("gh","release","upload",TAG,str(file),"--repo",ARCHIVE,timeout=1200)
        check_dir=tmp/"recheck";check_dir.mkdir()
        run("gh","release","download",TAG,"--repo",ARCHIVE,
            "--pattern","exams-app-old.bundle","--dir",str(check_dir),timeout=900)
        downloaded=check_dir/"exams-app-old.bundle"
        expected=next(x for x in manifest["assets"] if x["asset"]=="exams-app-old.bundle")
        if digest(downloaded)!=expected["sha256"] or bundle_refs(downloaded)!=expected["refs"]:
            raise RuntimeError("Release roundtrip failed on PR-ref-rich exams-app-old bundle")
        manifest["roundtrip_verified_asset"]="exams-app-old.bundle"
        run("gh","release","edit",TAG,"--repo",ARCHIVE,"--draft=false")
        OUT.mkdir(exist_ok=True)
        (OUT/"release-2026-11-23-all-refs.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
        lines=["# Backup completo das referências Git públicas","",
               "Esta release inclui refs/pull/* antes omitidas pelos bundles de branches.",
               "A fonte é o espelho Git, sem alterações nos repositórios originais.","",
               "| Origem | Refs originais | Refs preservadas | Refs de PR | Excluídas |",
               "|---|---:|---:|---:|---:|"]
        for x in manifest["assets"]:
            lines.append(f"| {x['repository']} | {x['original_ref_count']} | {x['preserved_ref_count']} | {x['ref_categories']['pull']} | {len(x['excluded_refs'])} |")
        lines+=["","Release: https://github.com/"+ARCHIVE+"/releases/tag/"+TAG,
                "","Hashes e mapeamento de ref->SHA: release-2026-11-23-all-refs.json.",
                "Nenhuma branch foi criada no repositorio de arquivo.",
                "Ainda falta o histórico completo do notes-app privado.",""]
        (OUT/"ALL-REFS.md").write_text("\n".join(lines))
        print(json.dumps({"ok":True,"total_refs":sum(x["preserved_ref_count"] for x in manifest["assets"]),"pull_refs":sum(x["ref_categories"]["pull"] for x in manifest["assets"])}),flush=True)

if __name__=="__main__":
    main()
