#!/usr/bin/env python3
"""Archive public exams-app GitHub Actions job logs into a PRIVATE release.

All archived logs originate from public source CI runs. Release assets are
compressed and SHA-256 verified. No source repo or branches are modified.
"""
from __future__ import annotations
import gzip
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE="ianmaciel7/exams-app"
DEST="ianmaciel7/exams-app-archive"
TAG="exams-app-2026-11-23-ci-logs"
REPORT=Path("reports/EXAMS-APP-ACTIONS-LOGS.json")


def cmd(*args, timeout=180):
    r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     timeout=timeout)
    if r.returncode:
        raise RuntimeError(str(args[:4])+": "+r.stderr.decode(errors="replace")[-500:])
    return r.stdout

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):
            h.update(block)
    return h.hexdigest()

def api(endpoint):
    return json.loads(cmd("gh","api",endpoint).decode("utf-8"))

def main():
    if not os.getenv("GH_TOKEN"):
        raise RuntimeError("GH_TOKEN required")
    if cmd("gh","repo","view",DEST,"--json","visibility","--jq",".visibility").decode().strip()!="PRIVATE":
        raise RuntimeError("Archive must be PRIVATE")
    if subprocess.run(["gh","release","view",TAG,"--repo",DEST],capture_output=True).returncode==0:
        print("Release already created, no changes")
        return
    runs=api(f"repos/{SOURCE}/actions/runs?per_page=100")
    if runs.get("total_count",0)>100:
        raise RuntimeError("Pagination needed for >100 runs")
    with tempfile.TemporaryDirectory(prefix="exams-ci-archive-") as tmp:
        directory=Path(tmp)
        assets=directory/"assets";assets.mkdir()
        result={"source":SOURCE,"destination":DEST,"tag":TAG,
                "captured_at_utc":datetime.now(timezone.utc).isoformat(),
                "total_runs":runs["total_count"],"jobs":[]}
        for run in runs.get("workflow_runs",[]):
            jobs=api(f"repos/{SOURCE}/actions/runs/{run['id']}/jobs?per_page=100")
            if jobs.get("total_count",0)>100:
                raise RuntimeError("Pagination needed for >100 jobs")
            artifacts=api(f"repos/{SOURCE}/actions/runs/{run['id']}/artifacts?per_page=100")
            for job in jobs["jobs"]:
                # Required: GitHub CLI rejects ANSI control sequences in log output
                # unless explicitly enabled. Logs are written as bytes, never executed.
                raw=cmd("gh","api","--allow-escape-sequences",
                        f"repos/{SOURCE}/actions/jobs/{job['id']}/logs",timeout=300)
                if len(raw)<2000:
                    raise RuntimeError(f"Unexpectedly short CI log: {job['id']}")
                asset=assets/f"exams-app-job-{job['id']}.log.gz"
                with gzip.open(asset,"wb",compresslevel=6) as out:
                    out.write(raw)
                result["jobs"].append({"run_id":run["id"],"job_id":job["id"],
                                       "run_name":run.get("name"),
                                       "run_url":run.get("html_url"),
                                       "archive_file":asset.name,
                                       "uncompressed_bytes":len(raw),
                                       "compressed_bytes":asset.stat().st_size,
                                       "sha256":sha256(asset),"verified":True,
                                       "source_artifacts_count":artifacts.get("total_count",0)})
        manifest=assets/"MANIFEST.json"
        manifest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
        cmd("gh","release","create",TAG,"--repo",DEST,"--draft",
            "--title","Exams App — original GitHub Actions logs",
            "--notes","Historical Actions job logs for public exams-app CI. Compressed, checksummed, published into the private archive.")
        for asset in sorted(assets.iterdir()):
            cmd("gh","release","upload",TAG,str(asset),"--repo",DEST,timeout=300)
        check=directory/"check";check.mkdir()
        for job in result["jobs"]:
            cmd("gh","release","download",TAG,"--repo",DEST,
                "--pattern",job["archive_file"],"--dir",str(check))
            asset=check/job["archive_file"]
            if sha256(asset)!=job["sha256"]:
                raise RuntimeError("Log download hash differs")
            with gzip.open(asset,"rb") as inp:
                if len(inp.read())!=job["uncompressed_bytes"]:
                    raise RuntimeError("Log decompression check failed")
        cmd("gh","release","edit",TAG,"--repo",DEST,"--draft=false")
        REPORT.parent.mkdir(exist_ok=True)
        REPORT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
        print(json.dumps({"saved_jobs":len(result["jobs"]),
                          "runs":result["total_runs"],
                          "total_bytes":sum(x["uncompressed_bytes"] for x in result["jobs"]),
                          "verified":True}),flush=True)

if __name__=="__main__":
    main()
