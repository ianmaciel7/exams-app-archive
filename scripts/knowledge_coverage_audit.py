"""Audit explicit public concept/record/source links and missing evidence dimensions.
No network, private index, inferred visual states, or fabricated coverage scores.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit
import research_index
import concept_packs
from domain_ontology import REQUIRED_23_DOMAINS, PUBLIC_ID_TO_DOMAIN

# Curated mapping of the issue scopes, not a claim that every topic is covered.
ISSUE_DOMAINS = {
    95: ("concursos", "produto"), 96: ("aprendizagem", "conhecimento-humano"),
    97: ("avaliacao",), 98: ("objetos", "ia-informacao", "workspace"),
    99: ("midia", "interacao"), 100: ("design-system", "acessibilidade"),
    101: ("visualizacoes", "acessibilidade"), 104: ("design-system", "interacao"),
    105: ("interacao", "motion"),
}

def canonical_url(value):
    p = urlsplit(value)
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("Only public HTTPS catalog URLs without credentials are accepted")
    # Do not collapse query parameters, fragments, paths or redirects: they can
    # identify distinct pages/sections. This only normalizes scheme/host/port.
    host = p.hostname.lower()
    if ":" in host:
        host = "[" + host + "]"
    if p.port and p.port != 443:
        host += ":" + str(p.port)
    return urlunsplit(("https", host, p.path or "/", p.query, p.fragment))

def audit(records, taxonomy):
    ids = {r["id"] for r in records}
    if len(ids) != len(records):
        raise ValueError("Duplicate record IDs")
    by_id = {r["id"]: r for r in records}
    source_by_url = defaultdict(list)
    for r in records:
        if r["kind"] == "source":
            for url in r.get("sources", []):
                source_by_url[canonical_url(url)].append(r)
    memberships = defaultdict(set)
    source_memberships = defaultdict(set)
    concepts = []
    dangling = []
    for c in taxonomy["concepts"]:
        domain = c.get("domain") or PUBLIC_ID_TO_DOMAIN.get(c["id"])
        members = set(c.get("members", []))
        missing = sorted(members - ids)
        dangling.extend({"concept":c["id"],"record":i} for i in missing)
        for i in members & ids:
            if domain in REQUIRED_23_DOMAINS:
                if by_id[i]["kind"] == "source":
                    source_memberships[domain].add(i)
                else:
                    memberships[i].add(domain)
        concepts.append({"concept":c["id"],"domain":domain,"explicit_members":len(members & ids),
                         "missing_members":missing,
                         "unlinked":not bool(members & ids)})
    domain_matrix = {d: {"patterns":0,"visual_records":0,"source_urls":set(),
                          "declared_tests":0,"declared_states":0,"explicit_code_links":0,
                          "inspected_visual_records":0,"record_ids":[],"explicit_source_record_ids":[]} for d in REQUIRED_23_DOMAINS}
    referenced = set()
    unresolved = []
    record_rows = []
    for r in records:
        if r["kind"] == "source":
            continue
        item = r.get("record", {})
        urls = sorted({canonical_url(u) for u in r.get("sources", [])})
        referenced.update(urls)
        for u in urls:
            if u not in source_by_url:
                unresolved.append({"record":r["id"],"url":u})
        domains = memberships[r["id"]] | set(ISSUE_DOMAINS.get(item.get("issue"),()))
        explicit = item.get("domain")
        if explicit in REQUIRED_23_DOMAINS:
            domains.add(explicit)
        segment = item.get("segment_evidence") or {}
        reviewed = r["kind"] == "visual" and segment.get("semantic_review") == "sampled-frames-reviewed"
        row = {"record":r["id"],"kind":r["kind"],"domains":sorted(domains),
               "source_urls":urls,"source_count":len(urls),
               "declared_tests":bool(item.get("tests") or item.get("acceptance_tests") or item.get("acceptance")),
               "declared_states":bool(item.get("states") or (reviewed and segment.get("states"))),
               "explicit_code_links":bool(item.get("source_repo") and item.get("source_commit") and item.get("source_path")),
               "visual_inspection":"declared_sampled_review" if reviewed else ("not_established" if r["kind"]=="visual" else "not_applicable"),
               "runtime_validation":"not_assessed"}
        record_rows.append(row)
        for d in domains:
            m=domain_matrix[d]
            m["patterns"] += r["kind"] == "pattern"
            m["visual_records"] += r["kind"] == "visual"
            m["source_urls"].update(urls)
            for k in ("declared_tests","declared_states","explicit_code_links"):
                m[k]+=row[k]
            m["inspected_visual_records"] += reviewed
            m["record_ids"].append(r["id"])
    for d,m in domain_matrix.items():
        m["explicit_source_record_ids"] = sorted(source_memberships[d])
        for ident in m["explicit_source_record_ids"]:
            m["source_urls"].update(canonical_url(u) for u in by_id[ident].get("sources", []))
        m["source_urls"] = len(m["source_urls"])
        m["record_ids"].sort()
        m["coverage_status"] = "linked_records_only" if m["record_ids"] else ("source_links_only" if m["explicit_source_record_ids"] else "no_explicit_catalog_links")
    sources = [{"url":u,"source_ids":[r["id"] for r in rs],
                "status_values":sorted({r["record"].get("status") or "unknown" for r in rs}),
                "metadata_missing":sorted({k for r in rs for k in ("license","author","checked_on","status") if not r["record"].get(k)}),
                "linked_records":sum(u in row["source_urls"] for row in record_rows),
                "live_access":"not_checked"} for u,rs in sorted(source_by_url.items())]
    gaps = [{"type":"dangling_concept_member",**x} for x in dangling]
    gaps += [{"type":"unregistered_reference_url",**x} for x in unresolved]
    gaps += [{"type":"unlinked_source","url":u} for u in sorted(set(source_by_url)-referenced)]
    gaps += [{"type":"domain_without_explicit_links","domain":d} for d,m in domain_matrix.items() if not m["record_ids"] and not m["explicit_source_record_ids"]]
    gaps += [{"type":"domain_with_source_links_only","domain":d} for d,m in domain_matrix.items() if not m["record_ids"] and m["explicit_source_record_ids"]]
    return {"schema":1,"status":"PUBLIC_CATALOG_AUDITED_ONLY",
            "domains":domain_matrix,"concepts":concepts,"sources":sources,"records":record_rows,
            "gaps":gaps,"gap_counts":dict(Counter(x["type"] for x in gaps)),
            "integrity_passed":not dangling,
            "scope_limits":["No private history, source reachability, independent relevance or runtime verification.",
                            "Source metadata, states and tests are declarations, not verified behavior.",
                            "Explicit domain links can overlap; do not sum as unique evidence.",
                            "Unregistered reference URLs may be legitimate upstream links; triage, not automatic corruption."]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    records=research_index.load_records()
    result=audit(records, concept_packs.load_taxonomy())
    result["record_provenance"]=research_index.verify_record_provenance(records)
    result["motion_source_integrity"]=research_index.verify_motion_source_copies()
    result["integrity_passed"] = (result["integrity_passed"] and result["record_provenance"]["integrity_passed"]
                                  and result["motion_source_integrity"]["integrity_passed"])
    serialized=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        args.output.write_text(serialized,encoding="utf-8")
    print(json.dumps({"status":result["status"],"integrity_passed":result["integrity_passed"],
                      "gap_counts":result["gap_counts"],"domain_record_counts":{d:len(m["record_ids"]) for d,m in result["domains"].items()}},indent=2))
    return 0 if result["integrity_passed"] else 1

if __name__=="__main__":
    raise SystemExit(main())
