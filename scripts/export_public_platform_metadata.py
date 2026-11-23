#!/usr/bin/env python3
"""Archive public GitHub PLATFORM metadata (not merely Git commits) to a private release.

Read-only against source repositories. Uses only the archive's GITHUB_TOKEN.
All API pagination and errors are explicitly recorded. PR text, reviews,
discussion comments, issues, releases, workflow runs and available artifact
metadata are exported as compressed JSON without inference or summarization.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

OWNER = "ianmaciel7"
ARCHIVE = OWNER + "/exams-app-archive"
TAG = "public-metadata-2026-11-23"
REPOSITORIES = (
    "exams-app", "exams-app-old", "exams-app-antigo-2",
    "shadcn-template", "shadcn-firebase-template",
    "fcc-responsive-web-design", "ianmaciel7",
)
BASE = "https://api.github.com/"
REPORT_DIR = Path("reports")
MANIFEST_DIR = Path("manifests")
TOKEN = os.environ.get("GH_TOKEN", "")
REQUIRED = {"repository", "issues", "pulls", "releases", "workflow_runs"}
ISSUES_LIMIT = 3000

def shell(*args: str, timeout: int = 300) -> bytes:
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"command {args[:4]} returned {p.returncode}: {p.stderr.decode(errors='replace')[-700:]}")
    return p.stdout

def digest(file: Path) -> str:
    h=hashlib.sha256()
    with file.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def api(path: str):
    if not path.startswith("repos/"):
        raise ValueError("Only approved GitHub repository paths allowed")
    url = urllib.parse.urljoin(BASE, path)
    headers = {"Accept": "application/vnd.github+json",
               "Authorization": "Bearer " + TOKEN,
               "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "exams-archive-metadata-exporter"}
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=40) as response:
                content=response.read()
                remain=int(response.headers.get("X-RateLimit-Remaining", "5000"))
                if remain < 40:
                    raise RuntimeError("GitHub API rate limit almost exhausted; stop without incomplete publication")
                return json.loads(content), response.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            error=e.read(280).decode("utf-8", "replace")
            raise RuntimeError(f"API {e.code}: {path} [{error}]") from e
    raise RuntimeError("Retry budget exceeded")

def collection(path: str):
    if "per_page=" not in path:
        sep="&" if "?" in path else "?"
        path += sep + "per_page=100"
    results=[]
    visited=set()
    page=0
    while path:
        if path in visited:
            raise RuntimeError("Pagination loop at "+path)
        visited.add(path)
        val,link=api(path)
        if isinstance(val,list):
            arr=val
        elif isinstance(val,dict) and isinstance(val.get("workflow_runs"),list):
            arr=val["workflow_runs"]
        elif isinstance(val,dict) and isinstance(val.get("artifacts"),list):
            arr=val["artifacts"]
        else:
            raise RuntimeError("Unexpected list payload at "+path)
        results.extend(arr)
        nxt=re.search(r'<(https://api.github.com/[^>]+)>;\s*rel="next"', link)
        path=nxt.group(1).replace(BASE, "", 1) if nxt else ""
        page += 1
        if page > 1000:
            raise RuntimeError("Too many paginated pages; abort")
    return results

def optional(result: dict, name: str, action):
    try:
        result[name]=action()
    except Exception as exc:
        result[name]=None
        result.setdefault("errors",[]).append({"section":name, "error":str(exc)[:400]})

def export(name: str):
    root=f"repos/{OWNER}/{name}"
    pack={"repository":f"{OWNER}/{name}","captured_at":datetime.now(timezone.utc).isoformat(),
          "errors":[],"data":{}}
    data=pack["data"]
    data["repository"],_=api(root)
    for label,path in [
        ("issues",root+"/issues?state=all&per_page=100"),
        ("pulls",root+"/pulls?state=all&per_page=100"),
        ("releases",root+"/releases?per_page=100"),
        ("workflow_runs",root+"/actions/runs?per_page=100"),
    ]:
        data[label]=collection(path)
        print(f"{name}: fetched {label} = {len(data[label])}",flush=True)
    # Requirements are strict: don't publish a collection known to be truncated.
    run_count, _=api(root+"/actions/runs?per_page=1")
    expected=run_count.get("total_count")
    pack["expected_run_count"]=expected
    if expected is not None and len(data["workflow_runs"]) != expected:
        raise RuntimeError(f"{name}: API workflow runs {len(data['workflow_runs'])} != total {expected}")
    for label,path in [
        ("branches",root+"/branches?per_page=100"),
        ("tags",root+"/tags?per_page=100"),
        ("labels",root+"/labels?per_page=100"),
        ("milestones",root+"/milestones?state=all&per_page=100"),
        ("contributors",root+"/contributors?per_page=100"),
        ("languages",root+"/languages"),
        ("topics",root+"/topics"),
        ("actions_artifacts",root+"/actions/artifacts?per_page=100"),
        ("rulesets",root+"/rulesets?per_page=100"),
    ]:
        if label in ("languages","topics"):
            optional(data,label,lambda path=path:api(path)[0])
        else:
            optional(data,label,lambda path=path:collection(path))
    if len(data["issues"]) > ISSUES_LIMIT:
        raise RuntimeError(f"{name}: issue count too high for single atomic export")
    # PR descriptions are provided by /pulls; nested pages include reviews,
    # inline comments, changed-file lists, merge histories and commits.
    pr_details=[]
    for idx,pr in enumerate(data["pulls"]):
        num=pr["number"]
        item={"number":num,"url":pr.get("html_url")}
        for label,path in [
            ("detail",f"{root}/pulls/{num}"),
            ("reviews",f"{root}/pulls/{num}/reviews?per_page=100"),
            ("review_comments",f"{root}/pulls/{num}/comments?per_page=100"),
            ("files",f"{root}/pulls/{num}/files?per_page=100"),
            ("commits",f"{root}/pulls/{num}/commits?per_page=100"),
        ]:
            if label=="detail":
                optional(item,label,lambda path=path:api(path)[0])
            else:
                optional(item,label,lambda path=path:collection(path))
        if item.get("detail") and item.get("files") is not None:
            expected_files=item["detail"].get("changed_files")
            if expected_files is not None and expected_files!=len(item["files"]):
                pack["errors"].append({"section":f"pr#{num}/files",
                    "error":f"Expected {expected_files} files, API returned {len(item['files'])}"})
        pr_details.append(item)
        if (idx+1)%25==0:
            print(f"{name}: PR details {idx+1}/{len(data['pulls'])}",flush=True)
    data["pull_request_details"]=pr_details
    # Issues endpoint includes PRs, and their conversation comments are separate
    # from inline code-review comments.
    issue_details=[]
    for entry in data["issues"]:
        num=entry["number"]
        item={"number":num}
        if entry.get("comments",0):
            optional(item,"comments",lambda num=num:collection(f"{root}/issues/{num}/comments?per_page=100"))
        optional(item,"events",lambda num=num:collection(f"{root}/issues/{num}/events?per_page=100"))
        issue_details.append(item)
    data["issue_conversations"]=issue_details
    pack["counts"]={
        "issues_including_prs":len(data["issues"]),
        "actual_issues":sum(not bool(i.get("pull_request")) for i in data["issues"]),
        "prs":len(data["pulls"]),
        "releases":len(data["releases"]),
        "workflow_runs":len(data["workflow_runs"]),
        "artifact_records":len(data.get("actions_artifacts") or []),
        "pr_details":len(pr_details),
        "issue_conversations":len(issue_details),
        "errors":len(pack["errors"])+sum(len(i.get("errors",[])) for i in pr_details+issue_details)
    }
    return pack

def main():
    if not TOKEN:
        raise RuntimeError("Archive GITHUB_TOKEN required")
    dest_visibility = json.loads(shell("gh","repo","view",ARCHIVE,"--json","visibility"))["visibility"]
    if dest_visibility!="PRIVATE":
        raise RuntimeError("Archive destination must be private")
    if subprocess.run(["gh","release","view",TAG,"--repo",ARCHIVE],
                      stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
        print("Immutable metadata release exists; not overwriting.")
        return
    with tempfile.TemporaryDirectory(prefix="archive-platform-") as d:
        tmp=Path(d); folder=tmp/"assets";folder.mkdir()
        manifest={"tag":TAG,"archive":ARCHIVE,
                  "captured_at":datetime.now(timezone.utc).isoformat(),
                  "sources":[],"limitations":[
                    "GitHub API only: expired CI logs/artifacts cannot be reconstructed",
                    "Secrets values, deleted/pruned source data and third-party assets are not exportable",
                    "GitHub Actions run JOB metadata, every log and artifact bytes need separate scalable processing",
                    "Code review threads and external issue attachment payloads need separate assessment",
                    "notes-app is PRIVATE and is intentionally excluded until least-privilege read access is granted"
                  ]}
        for name in REPOSITORIES:
            result=export(name)
            archive=folder/(name+".platform.zip")
            with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
                for key,value in result["data"].items():
                    z.writestr(key+".json",json.dumps(value,ensure_ascii=False,indent=2))
                z.writestr("_SUMMARY.json",json.dumps({
                    k:v for k,v in result.items() if k!="data"
                },ensure_ascii=False,indent=2))
            with zipfile.ZipFile(archive) as z:
                failed=z.testzip()
                if failed:raise RuntimeError("Corrupt zip entry: "+failed)
            entry={"repository":result["repository"],"asset":archive.name,
                   "size_bytes":archive.stat().st_size,"sha256":digest(archive),
                   "counts":result["counts"],"errors":result["errors"]}
            manifest["sources"].append(entry)
            print(f"{name}: ZIP {entry['size_bytes']:,} bytes, errors {entry['counts']['errors']}",flush=True)
        (folder/"MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
        (folder/"SHA256SUMS.txt").write_text("".join(
            f"{x['sha256']}  {x['asset']}\n" for x in manifest["sources"]
        ))
        shell("gh","release","create",TAG,"--repo",ARCHIVE,"--draft",
              "--title","Complete public GitHub platform metadata (issues/PRs/CI runs)",
              "--notes","All retrievable public repository GitHub API metadata: PR reviews/files, issue events/comments, releases and CI run lists. Known API gaps explicitly recorded.")
        for f in sorted(folder.iterdir()):
            shell("gh","release","upload",TAG,str(f),"--repo",ARCHIVE,timeout=800)
        for source in manifest["sources"]:
            check=tmp/"check";check.mkdir(exist_ok=True)
            shell("gh","release","download",TAG,"--repo",ARCHIVE,
                  "--pattern",source["asset"],"--dir",str(check),timeout=600)
            downloaded=check/source["asset"]
            if digest(downloaded)!=source["sha256"]:
                raise RuntimeError("Release download does not match original asset: "+source["asset"])
            with zipfile.ZipFile(downloaded) as z:
                if z.testzip():raise RuntimeError("Broken release archive")
        shell("gh","release","edit",TAG,"--repo",ARCHIVE,"--draft=false")
        REPORT_DIR.mkdir(exist_ok=True)
        MANIFEST_DIR.mkdir(exist_ok=True)
        (MANIFEST_DIR/"public-platform-metadata-2026-11-23.json").write_text(
            json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
        report=["# Metadados da plataforma GitHub exportados","",
                "Todas as páginas disponíveis de issues, PRs, revisões, arquivos alterados e",
                "execuções de CI foram solicitadas via API e guardadas em ZIPs na release privada.",
                "Os erros de acesso/cobertura são registrados separadamente.","",
                "| Repositório | PRs | Issues | CI runs | Erros registrados |",
                "|---|---:|---:|---:|---:|"]
        for s in manifest["sources"]:
            c=s["counts"]
            report.append(f"| {s['repository']} | {c['prs']} | {c['actual_issues']} | {c['workflow_runs']} | {c['errors']} |")
        report+=["","Release: https://github.com/"+ARCHIVE+"/releases/tag/"+TAG,
                 "","**Não é possível prometer 100% de informação histórica**: dados deletados",
                 "ou expirados, segredos, wikis inacessíveis e payloads externos exigem",
                 "verificação separada. Os erros detalhados estão no manifesto e ZIPs.",""]
        (REPORT_DIR/"PUBLIC-PLATFORM-METADATA.md").write_text("\n".join(report))
        print(json.dumps({"success":True,"sources":len(manifest["sources"]),
                          "total_errors":sum(s["counts"]["errors"] for s in manifest["sources"]),
                          "total_runs":sum(s["counts"]["workflow_runs"] for s in manifest["sources"])}),flush=True)

if __name__=="__main__":
    main()
