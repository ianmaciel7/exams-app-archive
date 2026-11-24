#!/usr/bin/env python3
"""Bounded authenticated query adapter for verified private release indexes.
No arbitrary input paths, no public request/result branches, no raw CI output.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from audit_release_bytes import command, BUNDLES, download, digest
from build_authenticated_content_index import supplemental_bundle
import archive_index
import archive_flow
import content_index
import context_linker
import secrets_gate

OWNER = "ianmaciel7/notes-app"
HISTORY = "archive-index-private-2026-11-24"
ADVANCED = "archive-content-private-2026-11-24"
ALLOWED = set(BUNDLES) | {"notes-app@worktrees"}
OPS = {"search", "images", "stats", "content_search", "linked_context", "context_pack", "get_evidence", "coverage"}

def open_asset(root, tag, name):
    assets=json.loads(command("gh","api",f"repos/{OWNER}/releases/tags/{tag}"))["assets"]
    expected=next(a for a in assets if a["name"]==name)
    command("gh","release","download",tag,"-R",OWNER,"--pattern",name,"--dir",str(root))
    path=root/name
    sha=digest(path)
    if path.stat().st_size!=expected["size"] or "sha256:"+sha!=expected["digest"]:
        raise ValueError("index digest mismatch")
    db=path.with_suffix("")
    with gzip.open(path,"rb") as src, db.open("wb") as dst:
        shutil.copyfileobj(src,dst)
    conn=sqlite3.connect(db.resolve().as_uri()+"?mode=ro",uri=True)
    conn.row_factory=sqlite3.Row
    if conn.execute("PRAGMA quick_check").fetchone()[0]!="ok":
        raise ValueError("index integrity")
    return conn, {"index_release":tag,"index_checksum":sha,"asset":name}

def validate(req):
    if not isinstance(req,dict) or set(req)-{"version","id","operation","query","repo","ref","path","sha","start_line","end_line","limit","kind"}:
        raise ValueError("unsupported fields")
    if req.get("version")!=1 or req.get("operation") not in OPS:
        raise ValueError("invalid contract")
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}",req.get("id","")):
        raise ValueError("invalid request id")
    if req.get("repo") is not None and req["repo"] not in ALLOWED:
        raise ValueError("invalid source")
    if type(req.get("limit",10)) is not int or not 1<=req.get("limit",10)<=20:
        raise ValueError("invalid limit")
    if req.get("kind","all") not in {"all","commit","file","image"}:
        raise ValueError("invalid kind")
    for key, size in [("query",160),("ref",200),("path",500)]:
        if key in req and (not isinstance(req[key],str) or len(req[key])>size or any(ord(c)<32 for c in req[key])):
            raise ValueError("invalid text")
    if "path" in req:
        path=archive_flow.validate_path(req["path"])
        if secrets_gate.is_sensitive_path(path)[0]:
            raise ValueError("sensitive path")
    if "sha" in req and not re.fullmatch(r"[a-f0-9]{40}",req["sha"]):
        raise ValueError("full SHA required")
    if req["operation"] in {"search","content_search","linked_context","context_pack"} and not req.get("query","").strip():
        raise ValueError("query required")
    if req["operation"]=="get_evidence":
        if not all(req.get(k) for k in ("repo","sha","path")):
            raise ValueError("exact provenance required")
        start,end=req.get("start_line",1),req.get("end_line",40)
        if type(start)is not int or type(end)is not int or not 1<=start<=end<=start+99:
            raise ValueError("line range")

def execute(root, req):
    op=req["operation"];limit=req.get("limit",10);repo=req.get("repo");q=req.get("query","")
    if op in {"search","images","stats","coverage"}:
        conn,prov=open_asset(root,HISTORY,"full-index.sqlite.gz")
        with conn:
            if op=="search":
                out=archive_index.search(conn,q,limit,kind=req.get("kind","all"),repo=repo)
            elif op=="images":
                sql="SELECT r.name repository,i.path,i.blob,i.commit_sha,i.kind,i.bytes FROM images i JOIN repositories r ON r.id=i.repo_id"
                params=[]
                if repo:
                    sql+=" WHERE r.name=?";params.append(repo)
                out=[dict(x) for x in conn.execute(sql+" ORDER BY i.bytes DESC LIMIT ?",[*params,limit])]
            else:
                out=[dict(x) for x in conn.execute("SELECT p.name repository,count(r.name) refs FROM repositories p LEFT JOIN refs r ON p.id=r.repo_id GROUP BY p.name ORDER BY p.name")]
        conn.close()
    elif op in {"content_search","context_pack","linked_context"}:
        conn,prov=open_asset(root,ADVANCED,"links.sqlite.gz" if op=="linked_context" else "content.sqlite.gz")
        if op=="linked_context":
            out=context_linker.query_history(conn,q,repo=repo,limit=limit)
        else:
            hits=content_index.search(conn,q,repo=repo,ref=req.get("ref"),path=req.get("path"),limit=limit,snippet_lines=8)
            if op=="context_pack":
                selected=[];seen=set()
                for h in hits:
                    key=(h.get("repository"),h.get("path"),h.get("blob_sha"))
                    if key in seen: continue
                    seen.add(key);selected.append(h)
                out={"items":selected,"mode":"bounded indexed snippets","not_full_file_recovery":True}
            else: out=hits
        conn.close()
    else:
        if repo=="notes-app@worktrees":
            source=supplemental_bundle(root)
            release="notes-worktrees-2026-11-24"
        else:
            release,asset=BUNDLES[repo]
            source=download(root,release,asset)
        prov={"index_release":release,"index_checksum":digest(source),"asset":source.name}
        out=archive_flow.flow_fetch(source=source,source_repo=repo,sha=req["sha"],ref=req.get("ref"),path=req["path"],start_line=req.get("start_line",1),end_line=req.get("end_line",40),max_bytes=1024*1024,max_payload_bytes=48*1024)
    clean,redactions=secrets_gate.sanitize_json_value(out)
    serialized=json.dumps(clean,ensure_ascii=False,sort_keys=True).encode()
    if len(serialized)>96*1024:
        raise ValueError("response too large; narrow query")
    return {"ok":True,"version":1,"id":req["id"],"operation":op,**prov,"result_checksum":hashlib.sha256(serialized).hexdigest(),"redactions":redactions,"results":clean}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--request",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    req=json.loads(a.request.read_text(encoding="utf-8"))
    try:
        validate(req)
        with tempfile.TemporaryDirectory() as folder:
            response=execute(Path(folder),req)
    except Exception as e:
        response={"ok":False,"id":req.get("id"),"category":type(e).__name__}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(response,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"ok":response["ok"],"operation":req.get("operation"),"id":req.get("id")}),flush=True)
    if not response["ok"]: raise SystemExit(1)
if __name__=="__main__":
    main()
