#!/usr/bin/env python3
"""Verify external dependencies in every preserved public Git bundle.

Verifies bundle SHA-256 and all objects, checks all branch trees for gitlinks,
scans all reachable/unreachable saved blob objects for Git LFS pointers, and
checks whether GitHub Wiki has an independent Git history.
No source repository is written to. GitHub Wiki remains report-only here.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone

ARCHIVE="ianmaciel7/exams-app-archive"
PUBLIC=["exams-app","exams-app-old","exams-app-antigo-2","shadcn-template",
        "shadcn-firebase-template","fcc-responsive-web-design","ianmaciel7"]
TAG="archive-2026-11-23-all-refs"
EXAMS_TAG="exams-app-2026-11-23-complete"

def run(*args, input=None, timeout=1800):
    p=subprocess.run(args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
    if p.returncode:
        raise RuntimeError(str(args[:4])+": "+p.stderr.decode(errors="replace")[-550:])
    return p.stdout

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as inp:
        for b in iter(lambda:inp.read(1048576),b""):h.update(b)
    return h.hexdigest()

def inspect(repo):
    cmd=["git",f"--git-dir={repo}"]
    run(*cmd,"fsck","--full","--no-reflogs",timeout=1800)
    raw=run(*cmd,"cat-file","--batch-all-objects","--batch-check=%(objectname) %(objecttype) %(objectsize)",timeout=600)
    all_objects=raw.decode().splitlines()
    cands=[]
    for entry in all_objects:
        sha,kind,size=entry.split()
        if kind=="blob" and 68<=int(size)<=1500:
            cands.append(sha)
    pointers=[]
    for start in range(0,len(cands),800):
        chunk=cands[start:start+800]
        output=run(*cmd,"cat-file","--batch",input=("\n".join(chunk)+"\n").encode(),timeout=600)
        stream=io.BytesIO(output)
        for expected in chunk:
            line=stream.readline().decode()
            parts=line.strip().split()
            if len(parts)!=3 or parts[0]!=expected or parts[1]!="blob":
                raise RuntimeError("Incorrect Git batch response")
            data=stream.read(int(parts[2]))
            if stream.read(1)!=b"\n":
                raise RuntimeError("Broken batch blob terminator")
            if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
                pointers.append({"blob":expected,"pointer":data.decode(errors="replace")[:400]})
    refs=run(*cmd,"for-each-ref","--format=%(refname)","refs/heads").decode().splitlines()
    submodules=[]
    attr=[]
    for ref in refs:
        files=run(*cmd,"ls-tree","-r","-z","--long",ref,timeout=600).split(b"\x00")
        for val in files:
            if not val or b"\t" not in val:continue
            meta,path=val.split(b"\t",1)
            p=meta.decode().split()
            name=path.decode(errors="replace")
            if p[0]=="160000":
                submodules.append({"ref":ref,"path":name,"object_sha":p[2]})
            if name.endswith(".gitattributes"):
                attr.append({"ref":ref,"path":name,"object_sha":p[2]})
    return {"git_fsck":True,"refs":len(refs),"object_count":len(all_objects),
            "small_blobs_scanned":len(cands),"lfs_pointer_count":len(pointers),
            "lfs_pointers":pointers[:100],"pointers_truncated":len(pointers)>100,
            "submodules":submodules,"gitattributes":attr}

def main():
    if not os.getenv("GH_TOKEN"):raise RuntimeError("GH_TOKEN required")
    m=json.loads(Path("manifests/release-2026-11-23-all-refs.json").read_text())
    e=json.loads(Path("manifests/exams-app-complete-2026-11-23.json").read_text())
    hashes={v["asset"]:v["sha256"] for v in m["assets"]}
    exams_hash=next(v["sha256"] for v in e["assets"] if v["name"]=="exams-app-all-refs.bundle")
    result={"date_utc":datetime.now(timezone.utc).isoformat(),"archive":ARCHIVE,
            "source_tag":TAG,"exams_tag":EXAMS_TAG,"sources":[]}
    with tempfile.TemporaryDirectory(prefix="exam-external-audit-") as d:
        tmp=Path(d)
        for name in PUBLIC:
            dl=tmp/name;dl.mkdir()
            tag=EXAMS_TAG if name=="exams-app" else TAG
            filename="exams-app-all-refs.bundle" if name=="exams-app" else name+".bundle"
            run("gh","release","download",tag,"--repo",ARCHIVE,
                "--pattern",filename,"--dir",str(dl),timeout=800)
            file=dl/filename
            expected=exams_hash if name=="exams-app" else hashes[filename]
            if digest(file)!=expected:raise RuntimeError("Source bundle checksum mismatch "+filename)
            bare=tmp/(name+".git")
            run("git","clone","--mirror","--quiet",str(file),str(bare),timeout=1800)
            d=inspect(bare)
            d.update({"repository":"ianmaciel7/"+name,"bundle_sha256_verified":True})
            w=subprocess.run(["git","ls-remote",f"https://github.com/ianmaciel7/{name}.wiki.git"],
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=40)
            d["wiki"]={"accessible":w.returncode==0,"reported_refs":len(w.stdout.splitlines()) if w.returncode==0 else 0,
                       "status":"accessible" if w.returncode==0 else "not found / inaccessible / empty"}
            result["sources"].append(d)
            print(f"{name}: {d['object_count']} objects; LFS pointers={d['lfs_pointer_count']}; "
                  f"gitlinks={len(d['submodules'])}; wiki={d['wiki']['status']}",flush=True)
    total_lfs=sum(v["lfs_pointer_count"] for v in result["sources"])
    total_modules=sum(len(v["submodules"]) for v in result["sources"])
    Path("reports").mkdir(exist_ok=True)
    (Path("reports")/"PUBLIC-GIT-EXTERNALS.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    table=["# Auditoria Git LFS, submodulos e wikis","",
           "Todos os dados Git foram recuperados **das releases privadas**, não dos repositorios de origem.",
           "Validação: SHA-256 dos bundles, restauração, git fsck --full e inspeção dos objetos.",
           "","| Origem | Objetos Git | Ponteiros LFS | Gitlinks | Wiki |",
           "|---|---:|---:|---:|---|"]
    for r in result["sources"]:
        table.append(f"| {r['repository']} | {r['object_count']} | {r['lfs_pointer_count']} | "
                     f"{len(r['submodules'])} | {r['wiki']['status']} |")
    table+=["",
        "Ponteiros Git LFS indicam conteúdo armazenado fora dos objetos Git; é necessária exportação dos binários.",
        "Gitlinks indicam submodulos cujo repositório deve ser arquivado separadamente.",
        "Wikis são Git separado e exigem exportação se existirem e estiverem acessíveis.",
        "",
        "**Esta validação não cobre objetos deletados do upstream, metadados das issues ou",
        "arquivos externos incluídos por URLs em documentos.**",""]
    (Path("reports")/"PUBLIC-GIT-EXTERNALS.md").write_text("\n".join(table))
    print(json.dumps({"success":True,"repositories":len(result["sources"]),
                      "lfs_pointers":total_lfs,"submodules":total_modules}),flush=True)

if __name__=="__main__":
    main()
