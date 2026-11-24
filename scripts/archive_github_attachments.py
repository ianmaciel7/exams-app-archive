#!/usr/bin/env python3
"""Inventory GitHub-hosted issue/PR attachment URLs in archived metadata.
Fetch only explicit GitHub attachment hosts, no auth headers or arbitrary external sites.
Output bytes/manifests must remain private; console output is aggregate-only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
import urllib.parse
import urllib.request
import urllib.error
import zipfile
from audit_release_bytes import META, NOTES, BUNDLES, download

URL = re.compile(r'https://[^\s"<>\\\]\)]+')
HOSTS = {"github.com","user-images.githubusercontent.com","private-user-images.githubusercontent.com",
         "objects.githubusercontent.com","release-assets.githubusercontent.com","github-production-user-asset-6210df.s3.amazonaws.com"}
MAX = 50 * 1024 * 1024

def classify(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or p.username or p.password or p.port not in (None,443):
        return False
    if p.hostname in {"user-images.githubusercontent.com","private-user-images.githubusercontent.com"}:
        return True
    return p.hostname=="github.com" and bool(re.match(r"^/(?:user-attachments/assets/|[^/]+/[^/]+/(?:assets|files)/)",p.path))

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p=urllib.parse.urlsplit(newurl)
        if p.scheme!="https" or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):
            raise urllib.error.HTTPError(newurl,403,"disallowed redirect",headers,fp)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def strings(value):
    if isinstance(value,str):
        yield value
    elif isinstance(value,list):
        for x in value: yield from strings(x)
    elif isinstance(value,dict):
        for x in value.values(): yield from strings(x)

def collect(root,source):
    tag,name=(NOTES,"notes-app-github-metadata.zip") if source=="notes-app" else (META,source+".platform.zip")
    path=download(root,tag,name)
    found={}
    with zipfile.ZipFile(path) as z:
        for entry in z.namelist():
            if not entry.endswith(".json"):
                continue
            data=json.loads(z.read(entry))
            for s in strings(data):
                for match in URL.finditer(s):
                    url=match.group(0).rstrip(".,;")
                    try:
                        if classify(url):
                            p=urllib.parse.urlsplit(url)
                            key=urllib.parse.urlunsplit((p.scheme,p.netloc,p.path,"",""))
                            found.setdefault(key,url)
                    except ValueError:
                        continue
    return found

def capture(opener, url, destination):
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"ExamsArchive/1.0"})
        with opener.open(req,timeout=20) as response:
            mime=response.headers.get_content_type()
            if mime=="text/html":
                return {"status":"html_or_login"}
            if int(response.headers.get("Content-Length","0"))>MAX:
                return {"status":"too_large"}
            h=hashlib.sha256(); total=0
            with destination.open("wb") as f:
                while chunk:=response.read(1024*1024):
                    total+=len(chunk)
                    if total>MAX:
                        raise ValueError("too large")
                    h.update(chunk); f.write(chunk)
        return {"status":"saved","bytes":total,"sha256":h.hexdigest(),"mime":mime}
    except urllib.error.HTTPError as exc:
        return {"status":"unavailable","http_status":exc.code}
    except (OSError,ValueError,TimeoutError):
        return {"status":"unavailable"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",choices=sorted(BUNDLES),required=True)
    p.add_argument("--offset",type=int,default=0)
    p.add_argument("--limit",type=int,default=20)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.offset<0 or not 1<=a.limit<=100: p.error("invalid batch")
    a.output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory() as tmp:
        found=collect(Path(tmp),a.source)
    opener=urllib.request.build_opener(SafeRedirect())
    records=[]
    for base in sorted(found)[a.offset:a.offset+a.limit]:
        key=hashlib.sha256(base.encode()).hexdigest()
        dest=a.output/(key+".bin")
        rec=capture(opener,found[base],dest)
        if rec["status"]!="saved": dest.unlink(missing_ok=True)
        records.append({"attachment_id":key,"url_without_query":base,**rec})
    (a.output/"MANIFEST.json").write_text(json.dumps({"source":a.source,"total_known_github_attachment_urls":len(found),"offset":a.offset,"records":records},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"source":a.source,"total_known_github_attachment_urls":len(found),"requested":len(records),"saved":sum(r["status"]=="saved" for r in records),"unavailable":sum(r["status"]!="saved" for r in records)}))
if __name__=="__main__":
    main()
