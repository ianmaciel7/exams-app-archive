#!/usr/bin/env python3
"""Build a portable, compressed FTS5 index exclusively from private archive releases.

No source repository checkout, paid inference, embedding service or extra MCP.
The full SQLite DB is distributed as a private release asset, not a Git blob.
"""
from __future__ import annotations
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from archive_index import git, ingest, images, open_db, recover, search

ARCHIVE="ianmaciel7/exams-app-archive"
TAG_SOURCE="archive-2026-11-23-all-refs"
TAG_EXAMS="exams-app-2026-11-23-complete"
TAG_NOTES="notes-app-2026-11-23-private-full"
TAG_INDEX="index-2026-11-24-six-sources-complete"
REPORTS=Path("reports")
SOURCES=[
    "exams-app","exams-app-old","exams-app-antigo-2",
    "shadcn-template","shadcn-firebase-template",
]

def cmd(*args, output=None, timeout=1800):
    p=subprocess.run(args,stdout=output if output is not None else subprocess.PIPE,
                     stderr=subprocess.PIPE,timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{args[:3]} failed: {p.stderr.decode(errors='replace')[-850:]}")
    return p.stdout.decode(errors="replace") if output is None else ""

def sha256(p):
    d=hashlib.sha256()
    with p.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            d.update(block)
    return d.hexdigest()

def main():
    if not os.environ.get("GH_TOKEN"):raise RuntimeError("GH_TOKEN missing")
    if cmd("gh","repo","view",ARCHIVE,"--json","visibility","--jq",".visibility").strip()!="PRIVATE":
        raise RuntimeError("Destination visibility is not PRIVATE")
    if subprocess.run(["gh","release","view",TAG_INDEX,"--repo",ARCHIVE],capture_output=True).returncode==0:
        print("Full index snapshot already exists; refusing to overwrite")
        return

    manifest=json.loads((Path("manifests")/"release-2026-11-23-all-refs.json").read_text())
    provenance={item["asset"]:item["sha256"] for item in manifest["assets"]}
    complete_manifest=json.loads((Path("manifests")/"exams-app-complete-2026-11-23.json").read_text())
    complete_hash=next(i["sha256"] for i in complete_manifest["assets"] if i["name"]=="exams-app-all-refs.bundle")
    provenance["exams-app.bundle"]=complete_hash
    notes_manifest=json.loads((Path("manifests")/"notes-app-private-full.json").read_text())
    notes_asset=next(i for i in notes_manifest["assets"] if i["asset"]=="notes-app-all-refs.bundle")
    if not all(notes_manifest["verified"].get(k) is True for k in ("bundle","git_fsck","ref_comparison","restore","release_download")):
        raise RuntimeError("Notes backup verification evidence missing")
    with tempfile.TemporaryDirectory(prefix="full-allrefs-archive-") as folder:
        temp=Path(folder)
        downloaded=temp/"downloaded";downloaded.mkdir()
        cmd("gh","release","download",TAG_SOURCE,"--repo",ARCHIVE,
            "--pattern","*.bundle","--dir",str(downloaded),timeout=1800)
        all_bundles={p.name:p for p in downloaded.glob("*.bundle")}
        exams_dir=temp/"complete-exams";exams_dir.mkdir()
        cmd("gh","release","download",TAG_EXAMS,"--repo",ARCHIVE,
            "--pattern","exams-app-all-refs.bundle","--dir",str(exams_dir),timeout=900)
        all_bundles["exams-app.bundle"]=exams_dir/"exams-app-all-refs.bundle"
        for name in SOURCES:
            file=all_bundles.get(name+".bundle")
            if not file:raise RuntimeError("Missing saved source bundle: "+name)
            if sha256(file)!=provenance[name+".bundle"]:raise RuntimeError("SHA mismatch "+str(file))
        notes_dir=temp/"complete-notes";notes_dir.mkdir()
        cmd("gh","release","download",TAG_NOTES,"--repo",ARCHIVE,
            "--pattern","notes-app-all-refs.bundle","--dir",str(notes_dir),timeout=900)
        notes_file=notes_dir/"notes-app-all-refs.bundle"
        if sha256(notes_file)!=notes_asset["sha256"] or notes_file.stat().st_size!=notes_asset["bytes"]:
            raise RuntimeError("Notes bundle checksum or size mismatch")
        bare_repos=temp/"repos";bare_repos.mkdir()
        db=REPORTS/"full-index.sqlite"
        REPORTS.mkdir(exist_ok=True)
        if db.exists():db.unlink()
        conn=open_db(db)
        results=[]
        repos={}
        start=time.perf_counter()

        def import_bundle(file,name,source):
            bare=bare_repos/(name+".git")
            cmd("git","clone","--mirror","--quiet",str(file),str(bare),timeout=1500)
            t=time.perf_counter()
            data=ingest(bare,name,conn)
            conn.execute("UPDATE repositories SET source=? WHERE name=?",(source,name))
            conn.commit()
            data.update({"elapsed_seconds":round(time.perf_counter()-t,2),
                         "source":source,"head_count":len(git(bare,"for-each-ref","--format=%(refname)","refs/heads").splitlines())})
            results.append(data)
            repos[name]=bare
            print(f"Indexed {name}: {data['commits']} commits, {data['changes']} changes, {data['images']} images",flush=True)

        for name in SOURCES:
            file=all_bundles[name+".bundle"]
            source_tag=TAG_EXAMS if name=="exams-app" else TAG_SOURCE
            import_bundle(file,name,"release://"+source_tag+"/"+file.name)
        import_bundle(notes_file,"notes-app","release://"+TAG_NOTES+"/"+notes_file.name)
        actual={line.split(" ",1)[1]:line.split(" ",1)[0] for line in git(repos["notes-app"],"show-ref").splitlines()}
        if actual!=notes_manifest["all_refs"]:
            raise RuntimeError("Notes restored refs differ from verified manifest")
        cmd("git",f"--git-dir={repos['notes-app']}","fsck","--full",timeout=900)
        exams=next(x for x in results if x["repository"]=="exams-app")
        if exams["head_count"]!=4 or exams["refs"]<5 or exams["commits"]<45 or exams["images"]<900:
            raise RuntimeError("The four exams-app branches have not been fully indexed")
        if next(x for x in results if x["repository"]=="exams-app-old")["commits"] < 700:
            raise RuntimeError("Old exams PR history disappeared from index")
        if next(x for x in results if x["repository"]=="exams-app-antigo-2")["commits"] < 1000:
            raise RuntimeError("Old2 PR history disappeared from index")

        # Extra historical Git bundles are original files under dev inside old2.
        old2=repos["exams-app-antigo-2"]
        paths=git(old2,"ls-tree","-r","--name-only","refs/heads/dev").splitlines()
        old_paths=sorted(p for p in paths if p.startswith("prototype/notes-app-") and p.endswith(".bundle"))
        if len(old_paths)!=12:
            raise RuntimeError("Expected 12 notes-app history bundles but found "+str(len(old_paths)))
        for num,p in enumerate(old_paths):
            file=temp/(f"notes-{num:02}.bundle")
            with file.open("wb") as handle:
                cmd("git",f"--git-dir={old2}","cat-file","blob",f"refs/heads/dev:{p}",output=handle)
            branch=p.removeprefix("prototype/notes-app-").removesuffix(".bundle")
            name="notes-app@"+branch
            import_bundle(file,name,"embedded://"+TAG_SOURCE+"/"+p)

        # Cross-source search; return compact data without reading all file contents into context.
        tests=[]
        for term in ("firebase","grafo","qconcursos","recall","capacit","fsrs","sidebar","exam","simulado"):
            t=time.perf_counter()
            found=search(conn,term,limit=12)
            tests.append({"query":term,"count":len(found),
                          "ms":round((time.perf_counter()-t)*1000,2),
                          "sample":found[:4]})
        if not all(t["count"] for t in tests[:4]):
            raise RuntimeError("Basic expected text search yielded empty results")
        source=next(x for x in results if x["repository"]=="notes-app@old-10")
        if not source["commits"]:raise RuntimeError("Historical notes-app-old-10 was not indexed")
        proof={}
        known_sha="cabcec2e8227fc7f06aa5c9c5afcc0e8944802c6"
        out=temp/"recall.ts"
        metadata=recover(repos["notes-app@old-10"],known_sha,"src/domain/recall.ts",out)
        proof["code"]={"repository":"notes-app@old-10","sha":known_sha,
                       "sha256":metadata["sha256"],"bytes":metadata["bytes"],"verified":True}
        selected=next((i for i in images(conn,deleted_only=True,limit=50) if i["repository"]=="exams-app-antigo-2"),None)
        if selected:
            dest=temp/("image"+Path(selected["path"]).suffix)
            data=recover(repos[selected["repository"]],selected["commit_sha"],selected["path"],dest)
            if git(repos[selected["repository"]],"hash-object",str(dest)).strip()!=selected["blob"]:
                raise RuntimeError("Retrieved deleted image Git SHA mismatch")
            proof["deleted_image"]={"repository":selected["repository"],"path":selected["path"],
                                   "sha256":data["sha256"],"sha":selected["commit_sha"],"verified":True}
        else:raise RuntimeError("No historical deleted image available")

        conn.commit();conn.close()
        packed=temp/"full-index.sqlite.gz"
        with db.open("rb") as inp,gzip.open(packed,"wb",compresslevel=6) as output:
            shutil.copyfileobj(inp,output)
        elapsed=round(time.perf_counter()-start,2)
        report={"date_utc":datetime.now(timezone.utc).isoformat(),
                "source":"all-refs and complete exams-app/notes-app releases; six primary repositories only; originals not accessed",
                "sources":results,"queries":tests,"proofs":proof,
                "source_count":len(results),"elapsed_seconds":elapsed,
                "sqlite_bytes":db.stat().st_size,"gzip_bytes":packed.stat().st_size,
                "gzip_sha256":sha256(packed),"release_tag":TAG_INDEX,
                "limitations":[
                    "Full Notes Git refs indexed; old aliases retained for historical source compatibility",
                    "FTS covers commit subjects and historical paths, not full text of every blob",
                    "Historical GitHub issue and PR metadata are separately preserved in exams-app complete release, not indexed in this FTS",
                    "Other project issues and PR metadata and LFS payloads are not included in this FTS",
                ]}
        manifest_file=temp/"FULL-INDEX-MANIFEST.json"
        manifest_file.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        cmd("gh","release","create",TAG_INDEX,"--repo",ARCHIVE,"--draft",
            "--title","Portable historical FTS5 index — complete exams-app and all other preserved sources",
            "--notes","Searchable SQLite FTS5 (gzip) rebuilt from the six in-scope Git bundles, including complete Notes. Contains Git metadata, no raw code duplication.")
        for f in (packed,manifest_file):
            cmd("gh","release","upload",TAG_INDEX,str(f),"--repo",ARCHIVE,timeout=900)
        check=temp/"download";check.mkdir()
        cmd("gh","release","download",TAG_INDEX,"--repo",ARCHIVE,
            "--pattern","full-index.sqlite.gz","--dir",str(check),timeout=600)
        if sha256(check/"full-index.sqlite.gz")!=report["gzip_sha256"]:
            raise RuntimeError("Download roundtrip SHA256 mismatch")
        cmd("gh","release","edit",TAG_INDEX,"--repo",ARCHIVE,"--draft=false")
        (REPORTS/"FULL-INDEX.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        summary=["# Índice pesquisável das seis origens completas","",
                 "Índice criado exclusivamente das releases privadas, incluindo exams-app e notes-app completos; sem clonar origens.",
                 "","- Fontes históricas indexadas: "+str(len(results)),
                 "- Commits processados (somados, podem ter ancestrais comuns): "+str(sum(x["commits"] for x in results)),
                 "- Alterações de arquivos processadas: "+str(sum(x["changes"] for x in results)),
                 "- Registros de imagens: "+str(sum(x["images"] for x in results)),
                 "- Tempo: "+str(elapsed)+" segundos",
                 "- SQLite: "+str(round(db.stat().st_size/2**20,2))+" MiB",
                 "- Download comprimido: "+str(round(packed.stat().st_size/2**20,2))+" MiB",
                 "","Release: https://github.com/"+ARCHIVE+"/releases/tag/"+TAG_INDEX,
                 "","| Fonte | Refs | Commits | Alterações | Imagens |","|---|---:|---:|---:|---:|"]
        for i in results:
            summary.append(f"| {i['repository']} | {i['refs']} | {i['commits']} | {i['changes']} | {i['images']} |")
        summary+=["","## Buscas com evidência","","| Consulta | Resultados | Latência |","|---|---:|---:|"]
        for t in tests:
            summary.append(f"| {t['query']} | {t['count']} | {t['ms']} ms |")
        summary+=["","## Limitações","","Todas as refs de Notes no manifesto foram comparadas; índices de conteúdo e metadados de plataforma são separados.",
                  "A busca FTS não é semântica e não indexa o conteúdo completo de cada versão.",
                  "É possível recuperar os blobs originais por SHA e caminho usando os Git bundles.",
                  "",""]
        (REPORTS/"FULL-INDEX.md").write_text("\n".join(summary))
        db.unlink()  # keep only the compressed, published index
        print(json.dumps({"ok":True,"sources":len(results),"total_seconds":elapsed,
                          "gzip_bytes":packed.stat().st_size,"proofs":proof}),flush=True)

if __name__=="__main__":
    main()
