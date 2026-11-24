"""Build a public metadata catalog from approved GitHub repositories, never from private bundles."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/public-catalog-sources.json"
SHA = re.compile(r"[0-9a-f]{40}")
EXCLUDED = re.compile(r"(?:^|/)(?:node_modules|\.git|\.cache|\.env[^/]*|secrets?|credentials?|private)(?:/|$)|(?:password|api[_-]?key|credential|token)[-_.]", re.I)
EXTENSIONS = {".tsx",".jsx",".ts",".js",".mjs",".cjs",".css",".scss",".html",".md",".mdx",".png",".jpg",".jpeg",".webp",".gif",".svg",".pdf",".json",".yaml",".yml",".py",".cs",".sql"}

def api(path, paginate=False):
    cmd = ["gh","api",path]
    if paginate: cmd.extend(["--paginate","--slurp"])
    value = json.loads(subprocess.check_output(cmd, text=True, timeout=120))
    return [item for page in value for item in page] if paginate else value

def eligible(entry):
    path=entry.get("path","")
    return (entry.get("type")=="blob" and entry.get("mode")!="120000"
            and not EXCLUDED.search(path) and Path(path).suffix.lower() in EXTENSIONS
            and not any(ord(ch)<32 for ch in path)
            and SHA.fullmatch(entry.get("sha","")) is not None)

def build(policy, request=api):
    snapshots=[]
    coverage=[]
    for repo in policy["repositories"]:
        if not re.fullmatch(r"ianmaciel7/[A-Za-z0-9_.-]+",repo):
            raise ValueError("Unapproved repository")
        base="repos/"+repo
        meta=request(base)
        if meta.get("private") is not False or meta.get("visibility")!="public":
            raise ValueError("Public catalog refuses non-public source: "+repo)
        refs={}
        for branch in request(base+"/branches?per_page=100",True):
            sha=branch["commit"]["sha"]
            if not SHA.fullmatch(sha): raise ValueError("Invalid SHA")
            refs.setdefault(sha,[]).append("branch:"+branch["name"])
        for tag in request(base+"/tags?per_page=100",True):
            sha=tag["commit"]["sha"]
            if not SHA.fullmatch(sha): raise ValueError("Invalid SHA")
            refs.setdefault(sha,[]).append("tag:"+tag["name"])
        trees={}
        for sha, aliases in sorted(refs.items()):
            commit=request(base+"/commits/"+sha)
            tree=commit["commit"]["tree"]["sha"]
            if not SHA.fullmatch(tree): raise ValueError("Invalid tree SHA")
            if tree not in trees:
                data=request(base+"/git/trees/"+tree+"?recursive=1")
                if data.get("truncated"): raise ValueError("Truncated tree: "+repo)
                trees[tree]=[{"path":e["path"],"blob":e["sha"],"size":e.get("size",0)} for e in data["tree"] if eligible(e)]
            snapshots.append({"repo":repo.split("/")[1],"sha":sha,"refs":sorted(aliases),"files":trees[tree]})
        coverage.append({"repo":repo,"refs":sum(map(len,refs.values())),"commits":len(refs),"trees":len(trees)})
    return {"version":2,"generated_at":datetime.now(timezone.utc).isoformat(),"coverage":coverage,"snapshots":snapshots}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    data=build(json.loads(POLICY.read_text(encoding="utf-8")))
    payload=json.dumps(data,ensure_ascii=False,separators=(",",":"))
    if len(payload.encode("utf-8"))>30*1024*1024:
        raise ValueError("Catalog exceeded 30 MiB; partition before publication")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.output.with_suffix(".tmp")
    tmp.write_text(payload,encoding="utf-8")
    tmp.replace(args.output)
    print(json.dumps({"coverage":data["coverage"],"snapshots":len(data["snapshots"]),"bytes":len(payload.encode("utf-8"))}))

if __name__=="__main__":
    main()
