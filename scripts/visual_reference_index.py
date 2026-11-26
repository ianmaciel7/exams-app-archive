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
            ev = r.get("segment_evidence")
            if ev:
                if ev["source_blob_sha"] != r["blob_sha"] or not 0 <= ev["segment"]["start_seconds"] < ev["segment"]["end_seconds"] <= ev["duration_seconds"]:
                    errors.append(f"invalid segment: {ident}")
                for asset in ev["keyframes"] + ([ev["clip"]] if ev.get("clip") else []):
                    rel = asset["path"]
                    if not re.fullmatch(r"media/segments/[a-zA-Z0-9_.-]+", rel):
                        errors.append(f"unsafe derivative: {ident}"); continue
                    file = (LIB / rel).resolve()
                    if not file.is_relative_to(LIB.resolve()) or not file.is_file():
                        errors.append(f"missing derivative: {ident}"); continue
                    data = file.read_bytes()
                    if len(data) != asset["bytes"] or hashlib.sha256(data).hexdigest() != asset["sha256"]:
                        errors.append(f"derivative mismatch: {ident}")
                    if "timestamp_seconds" in asset and not 0 <= asset["timestamp_seconds"] <= ev["duration_seconds"]:
                        errors.append(f"invalid timestamp: {ident}")
        elif r["status"] == "link-only":
            if "path" in r: errors.append(f"link-only has local path: {ident}")
        else: errors.append(f"unknown status: {ident}")
    return errors

def reconcile_legacy_assets(records, *, root=ROOT):
    """Validate public legacy copies against the canonical catalog and actual bytes.

    Hash equality establishes byte identity only. It does not establish visual
    semantics, playback, interaction states, or current upstream behavior.
    """
    root = Path(root).resolve()
    legacy = root / "docs/references/visual-library"
    canonical = root / "docs/references/visual-evidence-library"
    by_sha = {}
    for rec in records:
        if rec.get("status") == "archived-blob-verified" and rec.get("blob_sha"):
            by_sha.setdefault(rec["blob_sha"], []).append(rec)
    results, errors = [], []
    for product in ("excalidraw", "shadcn", "storybook"):
        manifest = legacy / (product + ".json")
        if not manifest.is_file():
            errors.append("missing legacy manifest: " + product)
            continue
        for item in json.loads(manifest.read_text(encoding="utf-8"))["assets"]:
            rel = item.get("path", "")
            ident = product + ":" + rel
            entry = {"legacy_id":ident,"canonical_ids":[],"bytes_verified":False,
                     "visual_inspection":"not_assessed","source_match":False}
            results.append(entry)
            if not re.fullmatch(r"media/" + product + r"/[a-zA-Z0-9_.-]+", rel):
                errors.append("unsafe legacy path: " + ident)
                continue
            path = (legacy / rel).resolve()
            if not path.is_relative_to(legacy.resolve()) or not path.is_file():
                errors.append("missing or unsafe legacy asset: " + ident)
                continue
            size = path.stat().st_size
            if size != item.get("bytes") or size > 16_000_000:
                errors.append("legacy byte size mismatch: " + ident)
                continue
            data = path.read_bytes()
            sha = hashlib.sha1(f"blob {size}\0".encode() + data).hexdigest()
            if sha != item.get("blob_sha"):
                errors.append("legacy blob mismatch: " + ident)
                continue
            entry["bytes_verified"] = True
            matches = by_sha.get(sha, [])
            entry["canonical_ids"] = sorted(r["id"] for r in matches)
            fields = ("source_repo","source_commit","source_path","source_url","license")
            matched = [r for r in matches if all(r.get(k) and r.get(k) == item.get(k) for k in fields)]
            if not matched:
                errors.append("canonical source mismatch or missing: " + ident)
                continue
            entry["source_match"] = True
            # Both copies and the license text must exist. Existing canonical
            # verification independently checks the blob and its derivatives.
            legacy_lic = (legacy / item.get("license_path", "")).resolve()
            if not legacy_lic.is_relative_to(legacy.resolve()) or not legacy_lic.is_file():
                errors.append("missing or unsafe legacy license: " + ident)
                continue
            valid_copy = False
            for rec in matched:
                cp = (canonical / rec.get("path", "")).resolve()
                cl = (canonical / rec.get("license_path", "")).resolve()
                if (cp.is_relative_to(canonical.resolve()) and cl.is_relative_to(canonical.resolve())
                    and cp.is_file() and cl.is_file() and cp.stat().st_size == size
                    and cp.read_bytes() == data and cl.read_bytes() == legacy_lic.read_bytes()):
                    valid_copy = True
                    break
            entry["canonical_copy_verified"] = valid_copy
            if not valid_copy:
                errors.append("canonical copy or license mismatch: " + ident)
    return {"scope":"public archived visual copies only","legacy_records":len(results),
            "byte_verified":sum(r["bytes_verified"] for r in results),
            "source_matched":sum(r["source_match"] for r in results),
            "canonical_copy_verified":sum(bool(r.get("canonical_copy_verified")) for r in results),
            "records":results,"errors":errors,"integrity_passed":not errors,
            "semantic_inspection":"not_assessed"}


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
            if key != "path" or not row.get("segment_evidence"):
                paths.add(rel)
        ev = row.get("segment_evidence")
        if ev:
            for asset in ev["keyframes"] + ([ev["clip"]] if ev.get("clip") else []):
                paths.add(asset["path"])
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
