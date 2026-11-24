#!/usr/bin/env python3
"""Bounded authenticated query adapter for verified private release indexes.
No arbitrary input paths, no public request/result branches, no raw CI output.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
import subprocess
import time
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
import graph_linker
import secrets_gate

OWNER = "ianmaciel7/notes-app"
HISTORY = "archive-index-private-2026-11-24"
ADVANCED = "archive-content-private-2026-11-24"
ALLOWED = set(BUNDLES) | {"notes-app@worktrees"}
OPS = {"search", "images", "stats", "content_search", "linked_context", "context_pack", "get_evidence", "coverage", "graph_neighbors"}

def open_asset(root, tag, name):
    # The private job supplies a runner-local manifest of independently verified,
    # immutable release assets. One authenticated API download, not three per query.
    pins=json.loads(Path(os.environ["ARCHIVE_INDEX_PINS"]).read_text(encoding="utf-8"))
    expected=pins[tag][name]
    cache=Path(os.environ.get("ARCHIVE_QUERY_CACHE",str(root)))
    cache.mkdir(parents=True,exist_ok=True)
    path=cache/name
    if not path.exists():
        tmp=cache/(name+".part")
        for attempt in range(3):
            try:
                with tmp.open("wb") as out:
                    p=subprocess.run(["gh","api","-H","Accept: application/octet-stream",f"repos/{OWNER}/releases/assets/{int(expected['id'])}"],stdout=out,stderr=subprocess.PIPE,timeout=240)
                if p.returncode==0:
                    if tmp.stat().st_size!=expected["size"] or digest(tmp)!=expected["sha256"]:
                        raise ValueError("index_digest_mismatch")
                    tmp.replace(path)
                    break
                err=p.stderr.decode("utf-8","replace").lower()
                if "rate limit" in err or "http 429" in err:
                    raise RuntimeError("api_rate_limited")
                if "http 401" in err or "http 403" in err or "http 404" in err:
                    raise RuntimeError("asset_access_denied")
            except subprocess.TimeoutExpired:
                pass
            finally:
                tmp.unlink(missing_ok=True)
            if attempt<2: time.sleep(5*(attempt+1))
        if not path.exists():
            raise RuntimeError("asset_download_failed")
    sha=digest(path)
    if path.stat().st_size!=expected["size"] or sha!=expected["sha256"]:
        raise ValueError("index_digest_mismatch")
    db=root/Path(name).with_suffix("").name
    with gzip.open(path,"rb") as src, db.open("wb") as dst:
        shutil.copyfileobj(src,dst)
    conn=sqlite3.connect(db.resolve().as_uri()+"?mode=ro",uri=True)
    conn.row_factory=sqlite3.Row
    if conn.execute("PRAGMA quick_check").fetchone()[0]!="ok":
        raise ValueError("index integrity")
    return conn, {"index_release":tag,"index_checksum":sha,"asset":name}

def validate(req):
    if not isinstance(req,dict) or set(req)-{"version","id","operation","query","repo","ref","path","sha","start_line","end_line","limit","kind","language","concept_id","entity_type","edge_type","hops","source_sha","token_budget"}:
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
    for key, size in [("query",160),("ref",200),("path",500),("language",50),("concept_id",160),("entity_type",80),("edge_type",80)]:
        if key in req and (not isinstance(req[key],str) or len(req[key])>size or any(ord(c)<32 for c in req[key])):
            raise ValueError("invalid text")
    if "path" in req:
        path=archive_flow.validate_path(req["path"])
        if secrets_gate.is_sensitive_path(path)[0]:
            raise ValueError("sensitive path")
    if "hops" in req and (type(req["hops"]) is not int or not 1<=req["hops"]<=2):
        raise ValueError("invalid hops")
    if "token_budget" in req and (type(req["token_budget"]) is not int or not 256<=req["token_budget"]<=8000):
        raise ValueError("invalid token budget")
    if "source_sha" in req and not re.fullmatch(r"[a-f0-9]{40}",req["source_sha"]):
        raise ValueError("invalid source_sha")
    if req["operation"]=="graph_neighbors" and not (req.get("concept_id") or req.get("query","").strip()):
        raise ValueError("concept required")
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

def compact_history(history, limit):
    """Bound nested timelines without pretending omitted records were inspected."""
    files=[]
    for file in history.get("files", [])[:limit]:
        commits=file.get("commits", [])
        kept=[]
        for c in commits[-6:]:
            item={k:c[k] for k in ("commit_sha","date","ref","status","pr_number","blob_sha","blob_url","justification_status","has_cited_justification") if k in c}
            for k in ("subject","snippet"):
                if k in c: item[k]=str(c[k])[:300]
            for k in ("objective_links","associated_images","cited_justifications"):
                if k in c:
                    item[k]=[{a:(str(b)[:300] if isinstance(b,str) else b) for a,b in x.items() if not isinstance(b,(dict,list))} for x in c[k][:3] if isinstance(x,dict)]
                    item[k+"_total"]=len(c[k])
            kept.append(item)
        row={k:file[k] for k in ("repository","repo","path","first_sha","last_sha","first_date","last_date") if k in file}
        row.update({"commits":kept,"total_commits":len(commits),"omitted_commits":max(0,len(commits)-len(kept))})
        files.append(row)
    return {"query":history.get("query"),"files":files,"gaps":history.get("gaps",[])[:10],"mode":"bounded history; recent commits only","total_matched_files":len(history.get("files",[]))}

def execute(root, req):
    op=req["operation"];limit=req.get("limit",10);repo=req.get("repo");q=req.get("query","")
    if op=="graph_neighbors":
        history,prov=open_asset(root,HISTORY,"full-index.sqlite.gz")
        history.close()
        graph=graph_linker.open_db(root/"graph.sqlite")
        graph_linker.ingest_archive_sqlite(graph,root/"full-index.sqlite")
        graph_linker.link_temporal_supersession(graph)
        out=graph_linker.query_neighborhood(graph,req.get("concept_id") or q,hops=req.get("hops",1),repo=repo,edge_types=(req["edge_type"],) if req.get("edge_type") else None,target_types=(req["entity_type"],) if req.get("entity_type") else None,limit=limit)
        graph.close()
        out["coverage_note"]="Graph derived from historical Git paths, commits, and images; inferred edges are not proof of decisions."
    elif op in {"search","images","stats","coverage"}:
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
            out=compact_history(context_linker.query_history(conn,q,repo=repo,limit=limit),min(limit,5))
        else:
            terms=[q]
            if q.casefold().strip() in {"fixar aba","pin tab","fixar abas"}:
                terms=["togglePin","Fixados"]
            hits=[]
            seen=set()
            for term in terms:
                for h in content_index.search(conn,term,repo=repo,ref=req.get("ref"),path=req.get("path"),language=req.get("language"),limit=min(100,limit*5),snippet_lines=8):
                    if req.get("source_sha") and h.get("commit_sha")!=req["source_sha"]:
                        continue
                    key=(h.get("repository"),h.get("path"),h.get("blob_sha"),h.get("start_line"))
                    if key not in seen:
                        seen.add(key); hits.append(h)
            # Prefer distinct paths before filling remaining slots with historical variants.
            preferred=[]
            paths=set()
            for h in hits:
                key=(h.get("repository"),h.get("path"))
                if key not in paths:
                    paths.add(key);preferred.append(h)
            preferred.extend(h for h in hits if h not in preferred)
            hits=preferred[:limit]
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
    if op=="context_pack" and req.get("token_budget"):
        items=clean.get("items",[])
        while items and len(serialized)>req["token_budget"]*3:
            items.pop()
            serialized=json.dumps(clean,ensure_ascii=False,sort_keys=True).encode()
        clean["budget_note"]="Conservative character/byte heuristic, not exact tokenizer count."
        serialized=json.dumps(clean,ensure_ascii=False,sort_keys=True).encode()
    if len(serialized)>96*1024:
        raise ValueError("response_too_large")
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
        response={"ok":False,"id":req.get("id"),"category":type(e).__name__,"reason":str(e) if str(e) in {"response_too_large","api_rate_limited","asset_access_denied","asset_download_failed","index_digest_mismatch"} else "query_failed"}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(response,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"ok":response["ok"],"operation":req.get("operation"),"id":req.get("id")}),flush=True)
    if not response["ok"]: raise SystemExit(1)
if __name__=="__main__":
    main()
