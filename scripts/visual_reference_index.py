#!/usr/bin/env python3
"""Search and verify public visual research records; no network or private data."""
import argparse
import hashlib
import json
import shutil
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "docs/references/visual-evidence-library"

def load():
    return json.loads((LIB / "manifest.json").read_text(encoding="utf-8"))["records"]

def search(records, query="", kind=None, status=None):
    terms = query.casefold().split()
    return [r for r in records if (not kind or r["kind"] == kind)
            and (not status or r["status"] == status)
            and all(t in json.dumps(r, ensure_ascii=False).casefold() for t in terms)]

def verify(records):
    errors, ids = [], set()
    for r in records:
        ident = r["id"]
        if ident in ids: errors.append(f"duplicate id: {ident}")
        ids.add(ident)
        if not r["source_url"].startswith("https://"): errors.append(f"invalid source: {ident}")
        if r["status"] == "archived-blob-verified":
            p = (LIB / r["path"]).resolve()
            lic = (LIB / r["license_path"]).resolve()
            if not p.is_relative_to(LIB.resolve()) or not lic.is_relative_to(LIB.resolve()):
                errors.append(f"unsafe path: {ident}"); continue
            if not p.is_file() or not lic.is_file():
                errors.append(f"missing file or license: {ident}"); continue
            data = p.read_bytes()
            sha = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
            if sha != r["blob_sha"] or len(data) != r["bytes"]:
                errors.append(f"blob mismatch: {ident}")
        elif r["status"] == "link-only":
            if "path" in r: errors.append(f"link-only has local path: {ident}")
        else: errors.append(f"unknown status: {ident}")
    return errors

def export_public(records, output):
    """Copy only manifest-verified, explicitly approved public assets."""
    errors = verify(records)
    if errors:
        raise ValueError(str(errors))
    paths = {"manifest.json", "gallery.html"}
    for row in records:
        if row["status"] != "archived-blob-verified":
            continue
        if row["license"] != "MIT":
            raise ValueError("unapproved license")
        for key in ("path", "license_path"):
            rel = row[key]
            if not re.fullmatch(r"media/[a-z0-9-]+/[a-zA-Z0-9_.-]+", rel):
                raise ValueError("unapproved public path")
            paths.add(rel)
    if output.exists() and any(output.iterdir()):
        raise ValueError("output must be empty")
    for rel in sorted(paths):
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(LIB / rel, target)
    return len(paths)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--kind", choices=["image","gif","video","demo","documentation"])
    parser.add_argument("--status", choices=["archived-blob-verified","link-only"])
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--export-public", type=Path)
    args = parser.parse_args()
    rows = load()
    if args.export_public:
        print(json.dumps({"exported": export_public(rows, args.export_public)}))
        return 0
    if args.verify:
        errors = verify(rows)
        print(json.dumps({"ok":not errors,"records":len(rows),"errors":errors}, ensure_ascii=False))
        return bool(errors)
    print(json.dumps(search(rows,args.query,args.kind,args.status),ensure_ascii=False,indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
