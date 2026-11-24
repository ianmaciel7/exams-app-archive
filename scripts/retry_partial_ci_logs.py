#!/usr/bin/env python3
"""Recover only transient failures in an immutable private CI-log shard."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import tarfile
from archive_ci_log_batch import capture

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tar",type=Path,required=True)
    p.add_argument("--source",choices=["exams-app-antigo-2"],required=True)
    p.add_argument("--offset",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    with tarfile.open(a.tar,"r:*") as t:
        m=t.getmember("MANIFEST.json")
        if not m.isfile() or m.size>2*1024*1024:
            raise ValueError("invalid manifest")
        data=json.load(t.extractfile(m))
    if data["source"]!=a.source or data["offset"]!=a.offset:
        raise ValueError("shard mismatch")
    ids=[int(r["run_id"]) for r in data["records"] if r["status"] not in ("saved","unavailable")]
    if len(ids)!=len(set(ids)) or len(ids)>500:
        raise ValueError("invalid IDs")
    a.output.mkdir(parents=True,exist_ok=False)
    records=capture(a.source,ids,a.output)
    out={"source":a.source,"offset":a.offset,"requested":len(ids),"records":records,"parent_shard":a.tar.name}
    (a.output/"MANIFEST.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    summary={"source":a.source,"offset":a.offset,"requested":len(ids),"saved":sum(r["status"]=="saved" for r in records),"unavailable":sum(r["status"]=="unavailable" for r in records),"retry_required":sum(r["status"] not in ("saved","unavailable") for r in records)}
    print(json.dumps(summary))
if __name__=="__main__":
    main()
