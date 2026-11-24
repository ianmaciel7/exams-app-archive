#!/usr/bin/env python3
"""Build authenticated content and evidence indexes from verified original bundles.

The output contains source-derived data; store only in an authorized private location.
Never print source content, secret values, raw tracebacks, or private query hits in CI.
"""
from __future__ import annotations
import argparse
import gzip
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from audit_release_bytes import BUNDLES, META, NOTES, download, command, expected_refs
import content_index
import context_linker

def supplemental_bundle(folder):
    repo="ianmaciel7/notes-app"
    tag="notes-worktrees-2026-11-24"
    from audit_release_bytes import digest
    assets=json.loads(command("gh","api",f"repos/{repo}/releases/tags/{tag}"))["assets"]
    expected=next(a for a in assets if a["name"]=="worktree-history.bundle")
    command("gh","release","download",tag,"-R",repo,"--pattern","worktree-history.bundle","--dir",str(folder))
    path=folder/"worktree-history.bundle"
    if path.stat().st_size!=expected["size"] or "sha256:"+digest(path)!=expected["digest"]:
        raise ValueError("supplement checksum mismatch")
    return path

def add_metadata(root, conn, source):
    tag, name=(NOTES,"notes-app-github-metadata.zip") if source=="notes-app" else (META,source+".platform.zip")
    file=download(root,tag,name)
    inv=root/"inventory"/source
    inv.mkdir(parents=True)
    with zipfile.ZipFile(file) as z:
        for key, label in [("pulls","pulls"),("issues","issues"),("releases","releases"),("tags","tags"),("workflow_runs","workflow-runs")]:
            entry=key+".json"
            if entry not in z.namelist():
                continue
            rows=json.loads(z.read(entry))
            if isinstance(rows,dict):
                rows=rows.get(key,[])
            if not isinstance(rows,list):
                continue
            payload={"repository":"ianmaciel7/"+source,"endpoint":key,"entries":rows}
            if key=="workflow_runs":
                payload["records"]=rows
            (inv/(label+".json")).write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
    if source=="exams-app-old":
        from pathlib import Path
        original=Path(__file__).resolve().parents[1]/"inventory"/source/"pr-supplement"
        if original.exists():
            for file in sorted(original.glob("*.json")):
                raw=json.loads(file.read_text(encoding="utf-8"))
                n=raw["number"]
                row=raw["data"][f"pulls/{n}"]
                (inv/f"pulls-supplement-{n}.json").write_text(json.dumps({"repository":"ianmaciel7/"+source,"entries":[row]}),encoding="utf-8")
    return context_linker.import_inventory(inv,conn,repo_override=source)

def build(out):
    out.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        content=content_index.open_db(out/"content.sqlite")
        links=context_linker.open_db(out/"links.sqlite")
        results=[]
        for source in [*BUNDLES,"notes-app@worktrees"]:
            folder=root/source
            folder.mkdir()
            if source=="notes-app@worktrees":
                bundle=supplemental_bundle(folder)
                label="release://ianmaciel7/notes-app/notes-worktrees-2026-11-24/worktree-history.bundle"
                refs={"refs/heads/archive/worktree-object-studio-20261124":"786e519c135269600f534a52fe95a9436164f2d8","refs/heads/archive/worktree-capacities-sidebar-20261124":"ef0bda5cc8ca1a75418671da00ecac2cbfcdeef7"}
            else:
                tag,asset=BUNDLES[source]
                bundle=download(folder,tag,asset)
                label=f"release://ianmaciel7/exams-app-archive/{tag}/{asset}"
                refs=expected_refs(source)
            bare=folder/"restored.git"
            command("git","clone","--mirror",str(bundle),str(bare))
            actual={x.split()[1]:x.split()[0] for x in command("git",f"--git-dir={bare}","show-ref").decode().splitlines()}
            if actual!=refs:
                raise ValueError("ref mismatch")
            content_index.ingest_repo(bare,source,content,source_label=label,all_commits=True,include_deleted=True)
            summary=context_linker.ingest_git_repo(bare,source,links)
            if source in BUNDLES:
                summary["metadata"]=add_metadata(folder,links,source)
            results.append({"source":source,"refs":len(refs),"git_links":summary})
            print(json.dumps({"source":source,"refs":len(refs),"stage":"indexed"}),flush=True)
            shutil.rmtree(folder)
        for db in (content,links):
            db.commit()
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("database integrity")
        stats=content_index.stats(content)
        test_hits=content_index.search(content,"sidebar",limit=10)
        if not test_hits:
            raise ValueError("real corpus smoke test returned no content")
        stats["smoke_query_hits"]=len(test_hits)
        content.close()
        links.close()
        summary={"sources":results,"content":stats,"coverage":"all-commits mode; supported text extensions and configured max file bytes, secret paths and matches skipped; Git bundles remain authoritative","integrity":True}
        (out/"MANIFEST.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
        for path in [out/"content.sqlite",out/"links.sqlite"]:
            with path.open("rb") as src,gzip.open(str(path)+".gz","wb") as dest:
                shutil.copyfileobj(src,dest)
            path.unlink()
        print(json.dumps({"ok":True,"sources":len(results),"refs":sum(x["refs"] for x in results),"unique_blobs":stats["unique_blobs"],"chunks":stats["total_chunks"],"occurrences":stats["total_occurrences"],"smoke_hits":stats["smoke_query_hits"]}),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        build(a.output)
    except Exception as exc:
        print(json.dumps({"ok":False,"category":type(exc).__name__}),flush=True)
        raise SystemExit(1) from None

if __name__=="__main__":
    main()
