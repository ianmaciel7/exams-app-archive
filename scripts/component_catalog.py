"""Reviewed component builds and reproducible screenshots, stored locally in SQLite."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / ".cache" / "exams-app-archive" / "component-previews"
REGISTRY = {
    "error-boundary": {
        "repository": "exams-app-old",
        "commit": "b86b70c304e574022416e8e2ecdc3816f1b386f1",
        "path": "src/app/error.tsx",
        "blob": "936e638aa231a2533e866c12e4d97a429c524d6c",
        "states": ["default", "retry"],
        "fidelity": "original React source; fixture props and equivalent CSS; not pixel verified",
        "builder": "build_error_preview.mjs",
    }
}
SCHEMA = """
CREATE TABLE IF NOT EXISTS builds(
    component_id TEXT PRIMARY KEY, repository TEXT NOT NULL, commit_sha TEXT NOT NULL,
    source_path TEXT NOT NULL, blob_sha TEXT NOT NULL, html_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS screenshots(
    id TEXT PRIMARY KEY, component_id TEXT NOT NULL, repository TEXT NOT NULL,
    commit_sha TEXT NOT NULL, source_path TEXT NOT NULL, blob_sha TEXT NOT NULL,
    html_sha256 TEXT NOT NULL, state TEXT NOT NULL, theme TEXT NOT NULL,
    width INTEGER NOT NULL, height INTEGER NOT NULL, png_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL, png BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS screenshots_component ON screenshots(component_id,created_at);
"""
COLUMNS = "id,component_id,repository,commit_sha,source_path,blob_sha,html_sha256,state,theme,width,height,png_sha256,created_at"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def connect():
    CACHE.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(CACHE / "components.sqlite")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def entry(component):
    if component not in REGISTRY:
        raise ValueError("Unknown or unreviewed component: " + component)
    return REGISTRY[component]


def list_components():
    with connect() as db:
        built = {r["component_id"]: r["html_sha256"] for r in db.execute("SELECT * FROM builds")}
        counts = {r[0]:r[1] for r in db.execute("SELECT component_id,COUNT(*) FROM screenshots GROUP BY component_id")}
    return [{"id":k, **{a:b for a,b in v.items() if a!="builder"},
             "built": k in built, "screenshots":counts.get(k,0)} for k,v in REGISTRY.items()]


def render(component, deps=None):
    item=entry(component)
    CACHE.mkdir(parents=True,exist_ok=True)
    deps=Path(deps) if deps else CACHE / "preview-deps"
    if not (deps / "node_modules" / "esbuild").is_dir():
        raise ValueError("Missing local preview dependencies; see docs/COMPONENT-EXPLORER.md")
    output=CACHE / (component+".html")
    temp=CACHE / (component+"-"+uuid4().hex+".tmp.html")
    try:
        proc=subprocess.run(["node",str(ROOT/"scripts"/item["builder"]),str(deps.resolve()),str(temp)],capture_output=True,text=True,timeout=90)
        if proc.returncode:
            raise RuntimeError("Reviewed build failed: "+proc.stderr[-500:])
        sha=digest(temp.read_bytes())
        os.replace(temp,output)
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO builds VALUES (?,?,?,?,?,?,?)",
                       (component,item["repository"],item["commit"],item["path"],item["blob"],sha,now()))
        return {"component":component,"html":str(output),"sha256":sha,"interactive":True,"fidelity":item["fidelity"]}
    finally:
        temp.unlink(missing_ok=True)


def capture(component, state="default", theme="light", width=1280, height=800):
    from playwright.sync_api import sync_playwright
    item=entry(component)
    if state not in item["states"] or theme not in {"light","dark"}:
        raise ValueError("Unsupported reviewed state or theme")
    if not 320<=width<=1920 or not 240<=height<=1440:
        raise ValueError("Viewport outside supported range")
    output=CACHE / (component+".html")
    with connect() as db:
        build=db.execute("SELECT * FROM builds WHERE component_id=?",(component,)).fetchone()
    if not build or not output.is_file() or digest(output.read_bytes())!=build["html_sha256"] or build["blob_sha"]!=item["blob"]:
        raise ValueError("Build is missing or modified; render first")
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1,
                                  color_scheme=theme, reduced_motion="reduce")
            # Reviewed standalone build only, no network requests.
            page.route("**/*",lambda route:route.continue_() if route.request.url==output.as_uri() else route.abort())
            errors=[]
            page.on("pageerror",lambda err:errors.append(str(err)))
            page.goto(output.as_uri(),wait_until="load")
            page.get_by_role("button",name="Try again",exact=True).wait_for(timeout=10000)
            if theme=="dark":
                page.get_by_role("button",name="Dark theme").click()
            if state=="retry":
                page.get_by_role("button",name="Try again",exact=True).click()
                page.wait_for_function("document.querySelector('#retry-status').textContent.includes('1')")
            if errors:
                raise RuntimeError("Preview JS errors: "+str(errors[:1]))
            png=page.screenshot(animations="disabled",timeout=15000)
        finally:
            browser.close()
    sid=uuid4().hex
    row=(sid,component,item["repository"],item["commit"],item["path"],item["blob"],build["html_sha256"],
         state,theme,width,height,digest(png),now(),png)
    with connect() as db:
        db.execute("INSERT INTO screenshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",row)
    return dict(zip(COLUMNS.split(","),row[:-1]))


def screenshots(component=None,limit=20):
    if component: entry(component)
    with connect() as db:
        sql="SELECT "+COLUMNS+" FROM screenshots"
        args=[]
        if component:sql+=" WHERE component_id=?";args.append(component)
        sql+=" ORDER BY created_at DESC LIMIT ?";args.append(max(1,min(int(limit),100)))
        return [dict(r) for r in db.execute(sql,args)]


def screenshot_bytes(screenshot_id):
    if not re.fullmatch("[0-9a-f]{32}",screenshot_id):
        raise ValueError("Invalid screenshot id")
    with connect() as db:
        row=db.execute("SELECT png,png_sha256 FROM screenshots WHERE id=?",(screenshot_id,)).fetchone()
    if not row or digest(row["png"])!=row["png_sha256"]:
        raise ValueError("Screenshot not found or checksum mismatch")
    return row["png"]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="operation",required=True)
    sub.add_parser("list")
    p=sub.add_parser("render");p.add_argument("component");p.add_argument("--deps",type=Path)
    p=sub.add_parser("capture");p.add_argument("component");p.add_argument("--state",default="default");p.add_argument("--theme",default="light");p.add_argument("--width",type=int,default=1280);p.add_argument("--height",type=int,default=800)
    p=sub.add_parser("screenshots");p.add_argument("--component");p.add_argument("--limit",type=int,default=20)
    p=sub.add_parser("export");p.add_argument("id");p.add_argument("--output",required=True,type=Path)
    a=parser.parse_args(argv)
    if a.operation=="list":result=list_components()
    elif a.operation=="render":result=render(a.component,a.deps)
    elif a.operation=="capture":result=capture(a.component,a.state,a.theme,a.width,a.height)
    elif a.operation=="screenshots":result=screenshots(a.component,a.limit)
    else:
        png=screenshot_bytes(a.id)
        with a.output.open("xb") as f:f.write(png)
        result={"id":a.id,"path":str(a.output),"sha256":digest(png)}
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(json.dumps({"error":str(exc)},ensure_ascii=False),file=sys.stderr)
        sys.exit(2)
