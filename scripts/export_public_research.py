#!/usr/bin/env python3
"""Export an explicit public projection; never read historical or private indexes."""
import json
from pathlib import Path
import sys
from research_index import load_records, audit

def projection(records):
    fields = ("id", "title", "kind", "product", "availability", "date",
              "license", "confidence", "catalog_path", "catalog_sha256", "record_sha256", "sources")
    return {"version": 1, "scope": "public research metadata only",
            "records": [{**{k: r.get(k) for k in fields},
                         "keywords": r["record"].get("keywords", []),
                         "description": r["record"].get("definition") or r["record"].get("purpose") or ""}
                        for r in records],
            "audit": audit(records)}

if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(projection(load_records()), ensure_ascii=False, indent=2), encoding="utf-8")
