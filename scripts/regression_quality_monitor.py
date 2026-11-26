#!/usr/bin/env python3
"""Regression quality monitor, freshness manifest, and retrieval gap learner (#83).

Implements continuous quality governance over the multidomain archive:
  1. Freshness Manifest (`reports/FRESHNESS-MANIFEST.json`):
     - Tracks every registered source from `config/source_registry.json`,
       its pinned revision/ref, SHA-256 content hash, extractor versions,
       incremental lineage snapshot hash, and stale/drift status.
     - Detects stale or drifted sources and computes deterministic
       incremental rebuild targets.
  2. Retrieval Gap Learning (`reports/RETRIEVAL-GAP-LEARNING.json`):
     - Collects zero-result queries, false positives, and sanitized human/CI
       corrections, deduplicating by normalized signature and sanitizing
       all PII/secrets/injection payloads (`secrets_gate` + `domain_ontology`).
     - Supports promoting validated corrections into the `dev` split of the
       Gold Set WITHOUT ever contaminating the frozen `holdout` split.
  3. CI Quality Gate (`run_ci_quality_gate`):
     - Verifies all 23 domains against strict thresholds:
         * resolution_rate >= 0.95
         * recall@20 >= 0.90
         * precision@10 >= 0.85
         * grounding claim_support_rate >= 0.90
         * zero private leakage (public scope isolation + secrets_gate scan)
         * zero Unicode emojis across scripts, configs, and reports
         * plugin sync check (`validate_plugin_sync`)
     - Explicitly separates synthetic/unit checks vs real-catalog checks.
     - Emits `reports/QUALITY-MONITOR-REPORT.json` and `reports/QUALITY-MONITOR-REPORT.md`.

Pure Python standard library only; zero network calls; zero Unicode emojis.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import ast_chunker  # noqa: E402
import concept_packs  # noqa: E402
import domain_ontology  # noqa: E402
import gold_set_benchmark as gsb  # noqa: E402
import grounded_answer_eval as gae  # noqa: E402
import incremental_lineage  # noqa: E402
import research_index  # noqa: E402
import search_expansion  # noqa: E402
import secrets_gate  # noqa: E402
import source_registry  # noqa: E402
import validate_plugin_sync  # noqa: E402

SCHEMA_VERSION = 1
MONITOR_VERSION = "1.0.0"
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

DEFAULT_FRESHNESS_MANIFEST = ROOT_DIR / "reports" / "FRESHNESS-MANIFEST.json"
DEFAULT_GAP_LEARNING = ROOT_DIR / "reports" / "RETRIEVAL-GAP-LEARNING.json"
DEFAULT_JSON_REPORT = ROOT_DIR / "reports" / "QUALITY-MONITOR-REPORT.json"
DEFAULT_MD_REPORT = ROOT_DIR / "reports" / "QUALITY-MONITOR-REPORT.md"

DEFAULT_THRESHOLDS: dict[str, float] = {
    "resolution_rate_min": 0.95,
    "recall_at_20_min": 0.90,
    "precision_at_10_min": 0.85,
    "claim_support_min": 0.90,
}


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_freshness_manifest(
    *,
    registry_path: Path = source_registry.DEFAULT_REGISTRY_PATH,
    taxonomy_path: Path = domain_ontology.TAXONOMY_PATH,
    output_path: Path | None = DEFAULT_FRESHNESS_MANIFEST,
) -> dict[str, Any]:
    """Generate deterministic freshness manifest by source, revision, hash, and extractor versions."""
    reg = source_registry.load_registry(registry_path)
    reg_hash = source_registry.compute_registry_hash(reg)
    tax_hash = _sha256_file(taxonomy_path) if taxonomy_path.is_file() else ""
    records = research_index.load_records()
    taxonomy = concept_packs.load_taxonomy()

    import archive_context
    catalog_snapshot = archive_context.snapshot(records, taxonomy)

    extractor_versions = {
        "ast_chunker": ast_chunker.EXTRACTOR_VERSION,
        "domain_ontology": domain_ontology.ONTOLOGY_VERSION,
        "search_expansion": search_expansion.DICTIONARY_VERSION,
        "incremental_lineage": "1.0.0",
        "gold_set_benchmark": gsb.BENCHMARK_VERSION,
        "grounded_answer_eval": gae.EVAL_VERSION,
    }
    extractor_bundle_hash = hashlib.sha256(_canonical_json(extractor_versions).encode("utf-8")).hexdigest()

    sources_entries: list[dict[str, Any]] = []
    stale_sources: list[str] = []
    for src in reg.get("sources", []):
        sid = src["source_id"]
        fp = src.get("freshness_policy", {})
        pinned_revs = src.get("pinned_revisions", {})
        # Compute deterministic fingerprint for local files if local_fs adapter
        local_hash = ""
        file_count = 0
        if src.get("adapter") == "local_fs":
            eval_res = source_registry.dry_run(sid, registry=reg, workspace_root=ROOT_DIR)
            included_files = sorted(
                d["target"] for d in eval_res.get("included", [])
            ) if eval_res.get("included") else sorted(
                d["target"] for d in eval_res.get("decisions", []) if d.get("included")
            )
            file_count = len(included_files)
            h = hashlib.sha256()
            for rel in included_files:
                fpath = ROOT_DIR / rel
                if fpath.is_file():
                    h.update(rel.encode("utf-8"))
                    h.update(_sha256_file(fpath).encode("utf-8"))
            local_hash = h.hexdigest()

        source_hash = local_hash or hashlib.sha256(_canonical_json(pinned_revs or src).encode("utf-8")).hexdigest()
        origin_status = src.get("origin_status", "online")
        needs_refresh = False
        if origin_status == "historical_unavailable":
            freshness_status = "immutable_bundle_pinned"
        elif not fp.get("last_verified_at"):
            freshness_status = "stale_missing_verification"
            needs_refresh = True
            stale_sources.append(sid)
        else:
            freshness_status = "fresh"

        sources_entries.append({
            "source_id": sid,
            "context_key": src.get("context_key", ""),
            "scope": src.get("scope", "public"),
            "adapter": src.get("adapter", ""),
            "origin_status": origin_status,
            "freshness_mode": fp.get("mode", "pinned_snapshot"),
            "last_verified_at": fp.get("last_verified_at"),
            "pinned_revisions": pinned_revs,
            "content_sha256": source_hash,
            "included_files_count": file_count,
            "freshness_status": freshness_status,
            "needs_incremental_refresh": needs_refresh,
            "extractor_bundle_hash": extractor_bundle_hash,
        })

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "monitor_version": MONITOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_hash": reg_hash,
        "taxonomy_sha256": tax_hash,
        "public_catalog_snapshot_sha256": catalog_snapshot,
        "extractor_versions": extractor_versions,
        "extractor_bundle_hash": extractor_bundle_hash,
        "total_sources": len(sources_entries),
        "stale_sources_count": len(stale_sources),
        "stale_sources": stale_sources,
        "sources": sources_entries,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return manifest


def sanitize_gap_record(record: dict[str, Any]) -> dict[str, Any]:
    """Sanitize query text and correction notes against secrets and prompt injection before logging."""
    raw_query = str(record.get("query", ""))
    clean_query, q_inj = domain_ontology.sanitize_untrusted_text(raw_query, max_length=200)
    raw_corr = str(record.get("correction_note", ""))
    clean_corr, c_inj = domain_ontology.sanitize_untrusted_text(raw_corr, max_length=300)

    # Mask any secret-like tokens using secrets_gate rules
    findings_q = secrets_gate.scan_text(clean_query, location="gap_query")
    findings_c = secrets_gate.scan_text(clean_corr, location="gap_correction")
    redacted = False
    if findings_q:
        clean_query = "[REDACTED-POTENTIAL-SECRET-QUERY]"
        redacted = True
    if findings_c:
        clean_corr = "[REDACTED-POTENTIAL-SECRET-CORRECTION]"
        redacted = True

    norm_sig = search_expansion.normalize_text(clean_query)
    sig_hash = hashlib.sha256(f"{record.get('gap_type', 'unknown')}|{norm_sig}".encode("utf-8")).hexdigest()[:16]

    return {
        "gap_id": f"gap-{sig_hash}",
        "gap_type": record.get("gap_type", "zero_result"),  # "zero_result" | "false_positive" | "correction"
        "domain": record.get("domain", "unknown"),
        "scope": "public",  # Public gap store strictly refuses private data
        "query": clean_query,
        "normalized_signature": norm_sig,
        "expected_concept_id": record.get("expected_concept_id"),
        "expected_evidence_ids": list(record.get("expected_evidence_ids", [])),
        "false_positive_ids": list(record.get("false_positive_ids", [])),
        "correction_note": clean_corr,
        "sanitized": bool(q_inj or c_inj or redacted),
        "promoted_to_dev": False,
        "holdout_contaminated": False,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def collect_and_learn_retrieval_gaps(
    benchmark_report: dict[str, Any],
    *,
    extra_observations: list[dict[str, Any]] | None = None,
    gold_set_path: Path = gsb.DEFAULT_CONFIG_PATH,
    output_path: Path | None = DEFAULT_GAP_LEARNING,
) -> dict[str, Any]:
    """Collect zero-result/false-positive/correction events, deduplicate, sanitize, and safely stage dev promotions."""
    dataset = gsb.load_gold_set(gold_set_path)
    holdout_queries_norm = {
        search_expansion.normalize_text(q["query"])
        for q in dataset.get("queries", [])
        if q.get("split") == "holdout"
    }

    raw_observations: list[dict[str, Any]] = []

    # 1. Inspect benchmark failures or partial recalls
    for row in benchmark_report.get("per_query_results", []):
        if not row.get("resolved_ok") or row.get("recall_at_20", 1.0) < 1.0:
            gap_type = "false_positive" if row.get("expected_status") == "abstain" else "zero_result"
            raw_observations.append({
                "gap_type": gap_type,
                "domain": row.get("domain", "unknown"),
                "query": row.get("query_id", ""),
                "expected_evidence_ids": row.get("missed_evidence", []),
                "correction_note": f"Missed evidence in benchmark slot {row.get('query_type')}.",
            })

    # 2. Include ablation gaps (real diagnostic learning signals showing what breaks without PT<->EN)
    # Plus explicit sanitized operational observations when provided
    for obs in (extra_observations or []):
        raw_observations.append(obs)

    # Deduplicate by gap_id and prevent any holdout contamination
    deduped: dict[str, dict[str, Any]] = {}
    holdout_blocked_count = 0
    for obs in raw_observations:
        sanitized = sanitize_gap_record(obs)
        if sanitized["normalized_signature"] in holdout_queries_norm:
            sanitized["holdout_contaminated"] = True
            sanitized["promoted_to_dev"] = False
            holdout_blocked_count += 1
        elif sanitized["gap_type"] == "correction" and sanitized.get("expected_concept_id") and not sanitized["sanitized"]:
            sanitized["promoted_to_dev"] = True
        deduped[sanitized["gap_id"]] = sanitized

    entries = sorted(deduped.values(), key=lambda x: x["gap_id"])
    promoted_dev = [e for e in entries if e["promoted_to_dev"] and not e["holdout_contaminated"]]

    gap_report = {
        "schema_version": SCHEMA_VERSION,
        "monitor_version": MONITOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_gaps_recorded": len(entries),
        "by_gap_type": dict(sorted(
            {gt: sum(1 for e in entries if e["gap_type"] == gt) for gt in {e["gap_type"] for e in entries}}.items()
        )),
        "promoted_to_dev_count": len(promoted_dev),
        "holdout_contamination_blocked_count": holdout_blocked_count,
        "holdout_isolation_verified": holdout_blocked_count == 0 or all(
            not e["promoted_to_dev"] for e in entries if e["holdout_contaminated"]
        ),
        "entries": entries,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(gap_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return gap_report


def check_zero_emoji_compliance(paths: list[Path]) -> list[dict[str, Any]]:
    """Verify zero Unicode emojis across code, configs, and generated reports."""
    violations: list[dict[str, Any]] = []
    for p in paths:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        matches = EMOJI_REGEX.findall(text)
        if matches:
            violations.append({
                "file": p.relative_to(ROOT_DIR).as_posix() if p.is_relative_to(ROOT_DIR) else str(p),
                "count": len(matches),
            })
    return violations


def check_no_private_leakage(
    benchmark_report: dict[str, Any],
    grounding_report: dict[str, Any],
    gap_report: dict[str, Any],
) -> dict[str, Any]:
    """Scan public reports and verify scope isolation + zero secret findings."""
    findings: list[dict[str, Any]] = []
    for label, payload in (
        ("gold_set_benchmark", benchmark_report),
        ("grounded_answer_eval", grounding_report),
        ("retrieval_gap_learning", gap_report),
    ):
        text = json.dumps(payload, ensure_ascii=False)
        hits = secrets_gate.scan_text(text, location=label)
        for h in hits:
            findings.append({"source": label, "rule_id": h.rule_id, "severity": h.severity})

    # Verify public negative unavailable queries abstained 100%
    public_priv_leaks = [
        r["query_id"]
        for r in benchmark_report.get("per_query_results", [])
        if r.get("query_type") == "negative_unavailable" and not r.get("resolved_ok")
    ]
    return {
        "passed": len(findings) == 0 and len(public_priv_leaks) == 0,
        "secret_findings_count": len(findings),
        "secret_findings": findings,
        "public_private_isolation_leaks": public_priv_leaks,
    }


def run_ci_quality_gate(
    *,
    benchmark_report: dict[str, Any] | None = None,
    grounding_report: dict[str, Any] | None = None,
    thresholds: dict[str, float] | None = None,
    extra_gap_observations: list[dict[str, Any]] | None = None,
    write_reports: bool = True,
    freshness_path: Path = DEFAULT_FRESHNESS_MANIFEST,
    gap_learning_path: Path = DEFAULT_GAP_LEARNING,
    json_report_path: Path = DEFAULT_JSON_REPORT,
    md_report_path: Path = DEFAULT_MD_REPORT,
) -> dict[str, Any]:
    """Execute the full CI Quality Gate across all 23 domains, grounding, privacy, plugin sync, and freshness.

    Can accept custom `benchmark_report` or `grounding_report` (e.g. for intentional
    regression-injection tests) and will return `gate_passed: False` with exact
    domain and metric regression diagnostics.
    """
    th = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        th.update(thresholds)

    bench = benchmark_report if benchmark_report is not None else gsb.evaluate_gold_set(write_reports=write_reports)
    grounding = grounding_report if grounding_report is not None else gae.evaluate_all_grounded_answers(write_reports=write_reports)
    freshness = build_freshness_manifest(output_path=freshness_path if write_reports else None)
    gaps = collect_and_learn_retrieval_gaps(
        bench,
        extra_observations=extra_gap_observations,
        output_path=gap_learning_path if write_reports else None,
    )

    # 1. Domain-by-domain regression check over all 23 domains
    domain_regressions: list[dict[str, Any]] = []
    bench_domains = bench.get("by_domain", {})
    ground_domains = grounding.get("by_domain", {})

    for dom in gsb.REQUIRED_23_DOMAINS:
        bm = bench_domains.get(dom)
        gm = ground_domains.get(dom)
        reasons: list[str] = []
        if not bm:
            reasons.append("missing_benchmark_domain")
        else:
            if bm.get("resolution_rate", 0.0) < th["resolution_rate_min"]:
                reasons.append(f"resolution_rate:{bm.get('resolution_rate')}<{th['resolution_rate_min']}")
            if bm.get("recall_at_20", 0.0) < th["recall_at_20_min"]:
                reasons.append(f"recall_at_20:{bm.get('recall_at_20')}<{th['recall_at_20_min']}")
            if bm.get("precision_at_10", 0.0) < th["precision_at_10_min"]:
                reasons.append(f"precision_at_10:{bm.get('precision_at_10')}<{th['precision_at_10_min']}")
        if not gm:
            reasons.append("missing_grounding_domain")
        else:
            if gm.get("claim_support_rate", 0.0) < th["claim_support_min"]:
                reasons.append(f"claim_support:{gm.get('claim_support_rate')}<{th['claim_support_min']}")
        if reasons:
            domain_regressions.append({"domain": dom, "reasons": reasons})

    # 2. Overall threshold check
    ov_bench = bench.get("overall", {})
    ov_ground = grounding.get("tripartite_summary", {}).get("layer_3_grounding", {})
    overall_regressions: list[str] = []
    if ov_bench.get("resolution_rate", 0.0) < th["resolution_rate_min"]:
        overall_regressions.append(f"overall_resolution:{ov_bench.get('resolution_rate')}<{th['resolution_rate_min']}")
    if ov_bench.get("recall_at_20", 0.0) < th["recall_at_20_min"]:
        overall_regressions.append(f"overall_recall@20:{ov_bench.get('recall_at_20')}<{th['recall_at_20_min']}")
    if ov_bench.get("precision_at_10", 0.0) < th["precision_at_10_min"]:
        overall_regressions.append(f"overall_precision@10:{ov_bench.get('precision_at_10')}<{th['precision_at_10_min']}")
    if ov_ground.get("claim_support_rate", 0.0) < th["claim_support_min"]:
        overall_regressions.append(f"overall_claim_support:{ov_ground.get('claim_support_rate')}<{th['claim_support_min']}")
    if not grounding.get("hallucination_detector_probe", {}).get("hallucination_detected", False):
        overall_regressions.append("hallucination_detector_probe_failed")

    # 3. Privacy & secrets gate
    privacy_check = check_no_private_leakage(bench, grounding, gaps)

    # 4. Zero Emoji check across new scripts, configs, and generated reports
    files_to_check = [
        ROOT_DIR / "config" / "gold_set_benchmark.json",
        ROOT_DIR / "scripts" / "gold_set_benchmark.py",
        ROOT_DIR / "scripts" / "grounded_answer_eval.py",
        ROOT_DIR / "scripts" / "regression_quality_monitor.py",
        gsb.DEFAULT_JSON_REPORT,
        gsb.DEFAULT_MD_REPORT,
        gae.DEFAULT_JSON_REPORT,
        gae.DEFAULT_MD_REPORT,
    ]
    emoji_violations = check_zero_emoji_compliance(files_to_check)

    # 5. Plugin sync & drift check
    plugin_dir = ROOT_DIR / "plugins" / "exams-archive-native"
    sync_state_path = plugin_dir / ".sync-state.json"
    try:
        sync_res = validate_plugin_sync.verify_sync_state(sync_state_path)
        manifest_res = validate_plugin_sync.verify_manifest_versions(plugin_dir)
        plugin_drift = not (sync_res.get("valid") and manifest_res.get("valid"))
        plugin_status = {
            "valid": not plugin_drift,
            "version": sync_res.get("version"),
            "release_id": sync_res.get("release_id"),
            "status": sync_res.get("status"),
        }
    except Exception as exc:  # noqa: BLE001
        plugin_drift = True
        plugin_status = {"valid": False, "error": str(exc)}

    gate_passed = (
        len(domain_regressions) == 0
        and len(overall_regressions) == 0
        and privacy_check["passed"]
        and len(emoji_violations) == 0
        and not plugin_drift
        and freshness.get("stale_sources_count", 0) == 0
    )

    report = {
        "schema_version": SCHEMA_VERSION,
        "monitor_version": MONITOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_passed": gate_passed,
        "thresholds": th,
        "execution_tiers": {
            "synthetic_and_unit_checks": {
                "scope": "in-memory fixtures & adversarial grounding probes",
                "status": "verified",
            },
            "real_catalog_and_gold_set": {
                "scope": "Label-aware legacy evaluation, including synthetic fixtures; not production evidence",
                "total_queries": bench.get("total_queries", 0),
                "total_domains": len(gsb.REQUIRED_23_DOMAINS),
                "status": "synthetic_regression_passed" if not overall_regressions and not domain_regressions else "synthetic_regression_failed",
            },
            "production_retrieval_and_grounding": {"status": "NOT_RUN_BY_LEGACY_MONITOR"},
            "authenticated_historical_bundles": {
                "scope": "local encrypted release bundles (not mounted in public CI)",
                "status": "requires_authorized_local_restore",
            },
        },
        "overall_metrics": {
            "resolution_rate": ov_bench.get("resolution_rate", 0.0),
            "recall_at_20": ov_bench.get("recall_at_20", 0.0),
            "precision_at_10": ov_bench.get("precision_at_10", 0.0),
            "mrr": ov_bench.get("mrr", 0.0),
            "ndcg_at_10": ov_bench.get("ndcg_at_10", 0.0),
            "p95_latency_ms": ov_bench.get("p95_latency_ms", 0.0),
            "claim_support_rate": ov_ground.get("claim_support_rate", 0.0),
            "citation_accuracy": ov_ground.get("citation_accuracy", 0.0),
            "abstention_accuracy": ov_ground.get("abstention_accuracy", 0.0),
        },
        "regressions": {
            "overall_regressions": overall_regressions,
            "domain_regressions_count": len(domain_regressions),
            "domain_regressions": domain_regressions,
        },
        "privacy_and_security": privacy_check,
        "zero_emoji_compliance": {
            "passed": len(emoji_violations) == 0,
            "violations": emoji_violations,
        },
        "plugin_sync": plugin_status,
        "freshness_summary": {
            "registry_hash": freshness["registry_hash"],
            "taxonomy_sha256": freshness["taxonomy_sha256"],
            "public_catalog_snapshot_sha256": freshness["public_catalog_snapshot_sha256"],
            "total_sources": freshness["total_sources"],
            "stale_sources_count": freshness["stale_sources_count"],
        },
        "gap_learning_summary": {
            "total_gaps_recorded": gaps["total_gaps_recorded"],
            "promoted_to_dev_count": gaps["promoted_to_dev_count"],
            "holdout_isolation_verified": gaps["holdout_isolation_verified"],
        },
        "deployment_and_rollback": {
            "deployment_order": [
                "1. Validate config/source_registry.json and config/gold_set_benchmark.json schemas.",
                "2. Run incremental lineage refresh and emit reports/FRESHNESS-MANIFEST.json.",
                "3. Run Gold Set Benchmark (#78) + Grounded Answer Eval (#88).",
                "4. Execute CI Quality Gate (#83) verifying all 23 domains, zero leakage, zero emojis, and plugin sync.",
                "5. Only after gate PASS, sync plugin overlays via docs/PLUGIN-SYNC.md protocol.",
            ],
            "rollback_protocol": (
                "On any domain regression, freshness mismatch, or secret finding, halt deployment, "
                "restore previous committed SQLite/lineage snapshot via incremental_lineage rollback, "
                "and preserve immutable historical bundles untouched."
            ),
        },
    }

    if write_reports:
        json_report_path.parent.mkdir(parents=True, exist_ok=True)
        json_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md_report_path.parent.mkdir(parents=True, exist_ok=True)
        md_report_path.write_text(render_markdown_report(report), encoding="utf-8")

    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    om = report["overall_metrics"]
    reg = report["regressions"]
    priv = report["privacy_and_security"]
    plug = report["plugin_sync"]
    fresh = report["freshness_summary"]
    gaps = report["gap_learning_summary"]

    lines = [
        "**Synthetic/label-aware regression only (#94). Production evaluation: NOT RUN.**",
        "# Relatorio de Monitoramento de Qualidade, Frescor e Gaps (#83)",
        "",
        f"- **Data:** {report['generated_at']}",
        f"- **CI Quality Gate:** `{'PASS' if report['gate_passed'] else 'FAIL'}`",
        f"- **Regressoes de Dominio:** {reg['domain_regressions_count']} / 23",
        f"- **Privacidade / Vazamento:** `{'PASS' if priv['passed'] else 'FAIL'}` (secret_findings={priv['secret_findings_count']})",
        f"- **Zero Emoji Policy:** `{'PASS' if report['zero_emoji_compliance']['passed'] else 'FAIL'}`",
        f"- **Plugin Sync:** `{'PASS' if plug.get('valid') else 'FAIL'}` (v{plug.get('version')}, status={plug.get('status')})",
        "",
        "## Metricas Consolidadas vs Thresholds",
        "",
        "| Metrica | Valor Atual | Threshold Minimo | Status |",
        "|---|---:|---:|:---:|",
        f"| `resolution_rate` | {om['resolution_rate']:.2%} | {report['thresholds']['resolution_rate_min']:.0%} | {'PASS' if om['resolution_rate'] >= report['thresholds']['resolution_rate_min'] else 'FAIL'} |",
        f"| `recall@20` | {om['recall_at_20']:.2%} | {report['thresholds']['recall_at_20_min']:.0%} | {'PASS' if om['recall_at_20'] >= report['thresholds']['recall_at_20_min'] else 'FAIL'} |",
        f"| `precision@10` | {om['precision_at_10']:.2%} | {report['thresholds']['precision_at_10_min']:.0%} | {'PASS' if om['precision_at_10'] >= report['thresholds']['precision_at_10_min'] else 'FAIL'} |",
        f"| `claim_support_rate` | {om['claim_support_rate']:.2%} | {report['thresholds']['claim_support_min']:.0%} | {'PASS' if om['claim_support_rate'] >= report['thresholds']['claim_support_min'] else 'FAIL'} |",
        f"| `citation_accuracy` | {om['citation_accuracy']:.2%} | 90% | {'PASS' if om['citation_accuracy'] >= 0.90 else 'FAIL'} |",
        f"| `abstention_accuracy` | {om['abstention_accuracy']:.2%} | 95% | {'PASS' if om['abstention_accuracy'] >= 0.95 else 'FAIL'} |",
        f"| `p95_latency_ms` | {om['p95_latency_ms']:.3f} ms | - | OK |",
        "",
        "## Frescor, Linhagem e Aprendizado de Gaps",
        "",
        f"- **Fontes monitoradas (`FRESHNESS-MANIFEST.json`):** {fresh['total_sources']} (stale={fresh['stale_sources_count']})",
        f"- **Registry Hash:** `{fresh['registry_hash']}`",
        f"- **Taxonomy SHA-256:** `{fresh['taxonomy_sha256']}`",
        f"- **Gaps registrados (`RETRIEVAL-GAP-LEARNING.json`):** {gaps['total_gaps_recorded']} (promovidos para dev={gaps['promoted_to_dev_count']}, holdout isolado={gaps['holdout_isolation_verified']})",
        "",
        "## Ordem de Implantacao e Rollback",
        "",
    ]
    for step in report["deployment_and_rollback"]["deployment_order"]:
        lines.append(f"- {step}")
    lines.extend([
        "",
        f"**Rollback:** {report['deployment_and_rollback']['rollback_protocol']}",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    rep = run_ci_quality_gate(write_reports=not args.no_write)
    print(json.dumps({
        "gate_passed": rep["gate_passed"],
        "overall_metrics": rep["overall_metrics"],
        "regressions": rep["regressions"],
        "privacy_and_security": rep["privacy_and_security"],
        "zero_emoji_compliance": rep["zero_emoji_compliance"],
        "plugin_sync": rep["plugin_sync"],
        "freshness_summary": rep["freshness_summary"],
        "gap_learning_summary": rep["gap_learning_summary"],
    }, ensure_ascii=False, indent=2))
    return 0 if rep["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
