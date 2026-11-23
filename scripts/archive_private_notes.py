#!/usr/bin/env python3
"""Complete PRIVATE notes-app backup into PRIVATE exams-app-archive release.

Requires NOTES_READ_TOKEN as a GitHub Actions secret on exams-app-archive.
Token must be a fine-grained, read-only credential restricted to notes-app.
Never writes to notes-app. Never prints secrets or embeds credentials in URLs.
"""
from __future__ import annotations
import gzip
import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE = "ianmaciel7/exams-app-archive"
SOURCE = "ianmaciel7/notes-app"
TAG = "notes-app-2026-11-23-private-full"
BRANCHES = {"main", "dev", "stag", "firebase/file", "old", *(f"old-{n}" for n in range(1, 12))}
TAGS = {"v0.1.0", "v0.2.0", "v0.3.0"}

def cmd(*args: str, env:dict|None=None, timeout:int=1200, output=None) -> bytes:
    p=subprocess.run(args, stdout=output if output is not None else subprocess.PIPE,
                     stderr=subprocess.PIPE, env=env,timeout=timeout)
    if p.returncode:
        raise RuntimeError("Operation failed ("+str(p.returncode)+"): "+
                           str(args[:3])+" "+p.stderr.decode(errors="replace")[-800:])
    return p.stdout if output is None else b""

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for buf in iter(lambda:f.read(1048576),b""):
            h.update(buf)
    return h.hexdigest()

def head_refs(repo:Path):
    raw=cmd("git",f"--git-dir={repo}","for-each-ref",
            "--format=%(objectname) %(refname)").decode()
    return {name:sha for sha,name in (line.split(" ",1) for line in raw.splitlines())}

def bundle_refs(file:Path):
    raw=cmd("git","bundle","list-heads",str(file)).decode()
    return {name:sha for sha,name in (line.split(" ",1) for line in raw.splitlines())
            if name.startswith("refs/")}

def github_api(repo_path:str):
    import urllib.request
    url="https://api.github.com/"+repo_path
    req=urllib.request.Request(url,headers={
        "Authorization":"Bearer "+os.environ["NOTES_READ_TOKEN"],
        "Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"exams-archive-notes-backup"})
    with urllib.request.urlopen(req,timeout=45) as res:
        return json.loads(res.read())

def main():
    if not os.environ.get("GH_TOKEN"):
        raise RuntimeError("Missing archive GH_TOKEN")
    if not os.environ.get("NOTES_READ_TOKEN"):
        raise RuntimeError("PENDING: Add NOTES_READ_TOKEN in the private archive Actions secrets. Use a read-only fine-grained PAT for notes-app only.")
    if json.loads(cmd("gh","repo","view",ARCHIVE,"--json","visibility"))["visibility"]!="PRIVATE":
        raise RuntimeError("Refusing to store notes-app history outside a private archive")
    if cmd("gh","release","list","--repo",ARCHIVE,"--limit","100").decode().find(TAG)>=0:
        print("Release already exists; not overwriting.",flush=True)
        return
    # Check actual authorization before fetching any large data.
    metadata=github_api("repos/"+SOURCE)
    if metadata.get("private") is not True:
        raise RuntimeError("Source repository must be private")

    with tempfile.TemporaryDirectory(prefix="private-notes-backup-") as d:
        root=Path(d)
        askpass=root/"askpass.sh"
        askpass.write_text(
            '#!/bin/sh\n'
            'case "$1" in\n'
            '  *Username*) printf "%s\\\\n" "x-access-token";;\n'
            '  *Password*) printf "%s\\\\n" "$NOTES_READ_TOKEN";;\n'
            '  *) exit 1;;\n'
            'esac\n')
        askpass.chmod(0o700)
        safe_env=os.environ.copy()
        safe_env.update({"GIT_ASKPASS":str(askpass),"GIT_TERMINAL_PROMPT":"0"})
        mirror=root/"notes.git"
        cmd("git","clone","--mirror","--quiet","https://github.com/"+SOURCE+".git",
            str(mirror),env=safe_env,timeout=1800)
        refs=head_refs(mirror)
        found_branches={x.removeprefix("refs/heads/") for x in refs if x.startswith("refs/heads/")}
        found_tags={x.removeprefix("refs/tags/") for x in refs if x.startswith("refs/tags/")}
        if not BRANCHES.issubset(found_branches):
            raise RuntimeError("Historical or current branches missing from private mirror: "+
                ", ".join(sorted(BRANCHES-found_branches)))
        if not TAGS.issubset(found_tags):
            raise RuntimeError("Required tags missing from private mirror: "+", ".join(sorted(TAGS-found_tags)))
        # An API HEAD comparison catches unexpected branch movement during cloning.
        api_branches=github_api("repos/"+SOURCE+"/branches?per_page=100")
        live={x["name"]:x["commit"]["sha"] for x in api_branches}
        for name, sha in live.items():
            if refs.get("refs/heads/"+name)!=sha:
                raise RuntimeError("Source branch moved or clone missed: "+name)

        assets=root/"assets";assets.mkdir()
        bundle=assets/"notes-app-all-refs.bundle"
        cmd("git",f"--git-dir={mirror}","bundle","create",str(bundle),"--all",timeout=1800)
        verify=root/"verify.git"
        cmd("git","init","--bare","-q",str(verify))
        cmd("git",f"--git-dir={verify}","bundle","verify",str(bundle))
        actual=bundle_refs(bundle)
        if actual!=refs:
            raise RuntimeError("Bundle refs differ from exact source Git mirror")
        restored=root/"restored.git"
        cmd("git","clone","--mirror","--quiet",str(bundle),str(restored),timeout=1200)
        cmd("git",f"--git-dir={restored}","fsck","--full","--no-reflogs",timeout=1200)
        if head_refs(restored)!=refs:
            raise RuntimeError("Roundtrip mirror ref mismatch")
        snap=assets/"notes-app-main-snapshot.tar.gz"
        cmd("git",f"--git-dir={mirror}","archive","--format=tar.gz",
            "--output="+str(snap),"refs/heads/main",timeout=900)
        with tarfile.open(snap,"r:gz") as tar:
            if not tar.getmembers():
                raise RuntimeError("main branch archive is empty")

        # Secondary platform metadata API: requires corresponding read permission;
        # keep a precise gap report rather than misrepresent inaccessible records.
        platform={"source":SOURCE,"exported":False}
        try:
            import export_public_platform_metadata as public
            public.TOKEN=os.environ["NOTES_READ_TOKEN"]
            platform=public.export("notes-app")
            platform["exported"]=True
        except Exception as e:
            platform={"source":SOURCE,"exported":False,"error":str(e)[:450]}
        pack=assets/"notes-app-github-metadata.zip"
        with zipfile.ZipFile(pack,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
            if platform.get("exported"):
                for key,value in platform["data"].items():
                    z.writestr(key+".json",json.dumps(value,ensure_ascii=False,indent=2))
            z.writestr("MANIFEST.json",json.dumps(
                {k:v for k,v in platform.items() if k!="data"},ensure_ascii=False,indent=2))
        with zipfile.ZipFile(pack) as z:
            if z.testzip():raise RuntimeError("Metadata ZIP corruption")

        source_releases=github_api("repos/"+SOURCE+"/releases?per_page=100")
        (assets/"notes-app-release-descriptions.json").write_text(
            json.dumps(source_releases,ensure_ascii=False,indent=2)+"\n")
        file_list=[]
        for name in sorted(found_branches):
            ref="refs/heads/"+name
            ls=cmd("git",f"--git-dir={mirror}","ls-tree","--long","-r","-z",ref)
            files=[]
            for entry in ls.split(b"\0"):
                if not entry or b"\t" not in entry:
                    continue
                meta,path=entry.split(b"\t",1)
                pieces=meta.decode().split()
                if len(pieces)!=4:continue
                files.append({"path":path.decode(errors="replace"),"mode":pieces[0],
                    "kind":pieces[1],"sha":pieces[2],"bytes":int(pieces[3]) if pieces[3].isdigit() else None})
            file_list.append({"branch":name,"head_sha":refs[ref],"file_count":len(files),"files":files})
        (assets/"notes-app-branch-file-inventory.json").write_text(
            json.dumps({"source":SOURCE,"branches":file_list},ensure_ascii=False,indent=2)+"\n")
        archive_assets=[{"asset":p.name,"bytes":p.stat().st_size,"sha256":sha256(p)}
                        for p in assets.iterdir()]
        manifest={"source":SOURCE,"archive":ARCHIVE,"tag":TAG,
            "snapshot_at_utc":datetime.now(timezone.utc).isoformat(),
            "private":True,"all_refs":refs,
            "branch_count":len(found_branches),"tag_count":len(found_tags),
            "pull_ref_count":sum(x.startswith("refs/pull/") for x in refs),
            "branch_heads_verified":len(live),"main_files":next(x["file_count"] for x in file_list if x["branch"]=="main"),
            "verified":{"bundle":True,"git_fsck":True,"ref_comparison":True,"restore":True,"main_tar":True},
            "platform_exported":platform.get("exported",False),
            "platform_error":platform.get("error"),
            "assets":archive_assets}
        (assets/"MANIFEST.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
        cmd("gh","release","create",TAG,"--repo",ARCHIVE,"--draft",
            "--title","Notes App: full private Git history and platform metadata",
            "--notes","Private-to-private backup of all advertised Git refs including branch heads, tags and PR refs. Contains release notes, branch file inventory and public-platform-style metadata when authorized.")
        for p in sorted(assets.iterdir()):
            cmd("gh","release","upload",TAG,str(p),"--repo",ARCHIVE,timeout=1000)
        downloaded=root/"download";downloaded.mkdir()
        cmd("gh","release","download",TAG,"--repo",ARCHIVE,
            "--pattern",bundle.name,"--dir",str(downloaded),timeout=900)
        if sha256(downloaded/bundle.name)!=sha256(bundle):
            raise RuntimeError("Release-download digest mismatch")
        if bundle_refs(downloaded/bundle.name)!=refs:
            raise RuntimeError("Release-download refs mismatch")
        cmd("gh","release","edit",TAG,"--repo",ARCHIVE,"--draft=false")
        manifest["verified"]["release_download"]=True
        Path("manifests").mkdir(exist_ok=True)
        (Path("manifests")/"notes-app-private-full.json").write_text(
            json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
        print(json.dumps({"success":True,"branch_count":len(found_branches),
            "tag_count":len(found_tags),"pr_refs":manifest["pull_ref_count"],
            "platform_exported":manifest["platform_exported"],
            "bundle_mib":round(bundle.stat().st_size/1048576,2)}),flush=True)

if __name__=="__main__":
    main()
