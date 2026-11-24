#!/usr/bin/env python3
"""Preserve original CI run-log ZIPs in a private destination, never print log bytes.
Batch offsets are based on the immutable archived run list, not the live run order.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import zipfile
from audit_release_bytes import META, NOTES, BUNDLES, ROOT, ARCHIVE

def run_list(root: Path, source: str):
    tag, name = (NOTES, "notes-app-github-metadata.zip") if source == "notes-app" else (META, source+".platform.zip")
    # These snapshots were already independently verified. Use their pinned
    # digest and public release asset URL without spending API rate quota.
    if source=="notes-app":
        entry=next(a for a in json.loads((ROOT/"manifests/notes-app-private-full.json").read_text())["assets"] if a["asset"]==name)
        size=entry["bytes"]
    else:
        entry=next(a for a in json.loads((ROOT/"manifests/public-platform-metadata-2026-11-23.json").read_text())["sources"] if a["asset"]==name)
        size=entry["size_bytes"]
    path=root/name
    subprocess.run(["curl","--fail","--silent","--show-error","--location","--retry","3","--max-time","180","--output",str(path),f"https://github.com/{ARCHIVE}/releases/download/{tag}/{name}"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if path.stat().st_size!=size or sha(path)!=entry["sha256"]:
        raise ValueError("snapshot_integrity_failed")
    with zipfile.ZipFile(path) as z:
        data = json.loads(z.read("workflow_runs.json"))
    if isinstance(data, dict):
        data = data["workflow_runs"]
    return sorted({int(r["id"]) for r in data}, reverse=True)

def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def capture(source, ids, folder):
    records=[]
    for id in ids:
        dest=folder/f"{id}.zip"
        status=None
        succeeded=False
        for attempt in range(4):
            try:
                with dest.open("wb") as out:
                    p=subprocess.run(["gh","api","--allow-escape-sequences",f"repos/ianmaciel7/{source}/actions/runs/{id}/logs"],
                                     stdout=out,stderr=subprocess.PIPE,timeout=120)
                if p.returncode==0:
                    succeeded=True
                    break
                err=p.stderr.decode("utf-8","replace")
                match=re.search(r"HTTP\s+(\d{3})",err)
                status=int(match.group(1)) if match else None
                if status in (404,410):
                    break
                if status in (403,429) and ('rate limit' in err.lower() or status==429):
                    # Stop a throttled shard promptly. Do not mislabel it as missing.
                    status=429
                    break
            except subprocess.TimeoutExpired:
                status=None
            if attempt<3:
                time.sleep(2**attempt * 5)
        if not succeeded:
            dest.unlink(missing_ok=True)
            records.append({"run_id":id,"status":"unavailable" if status in (404,410) else "retry_required","http_status":status})
            if status==429:
                records.extend({"run_id":remaining,"status":"retry_required","http_status":429} for remaining in ids[len(records):])
                break
            continue
        try:
            with zipfile.ZipFile(dest) as z:
                if z.testzip() is not None: raise ValueError("crc")
        except (ValueError,zipfile.BadZipFile):
            dest.unlink(missing_ok=True)
            records.append({"run_id":id,"status":"invalid_zip"})
            continue
        records.append({"run_id":id,"status":"saved","bytes":dest.stat().st_size,"sha256":sha(dest)})
    return records

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",choices=sorted(BUNDLES),required=True)
    p.add_argument("--offset",type=int,default=0)
    p.add_argument("--limit",type=int,default=20)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.offset<0 or not 1<=a.limit<=500: p.error("invalid batch")
    a.output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp:
        ids=run_list(Path(tmp),a.source)
        records=capture(a.source,ids[a.offset:a.offset+a.limit],a.output)
    report={"source":a.source,"snapshot_run_count":len(ids),"offset":a.offset,"requested":len(records),"records":records}
    (a.output/"MANIFEST.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"source":a.source,"total":len(ids),"requested":len(records),"saved":sum(r["status"]=="saved" for r in records),"unavailable":sum(r["status"]=="unavailable" for r in records),"retry_required":sum(r["status"] not in ("saved","unavailable") for r in records)}))
if __name__=="__main__":
    main()
