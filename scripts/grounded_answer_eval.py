#!/usr/bin/env python3
"""Tripartite Grounded Answer Evaluation suite (#88).

Inspired by LlamaIndex retriever + response evaluation concepts (pure Python
stdlib, zero mandatory LlamaIndex installation, zero network calls, zero emojis):

Separates three evaluation layers over the multidomain Gold Set (#78) plus
dedicated adversarial grounding scenarios:
  1. Intent Resolution Layer (`resolution`):
     - Canonical ID resolution, bilingual PT<->EN mapping, disambiguation,
       or explicit abstention when evidence is absent or private/unavailable.
  2. Evidence Ranking Layer (`ranking`):
     - Recall@20, Precision@10, MRR, nDCG@10, and exact origin/hash availability.
  3. Grounded Answer Layer (`grounding` / Claim Support):
     - Deterministic verification of every generated claim against retrieved
       evidence snippets, SHA/version/path citations, requirement completeness,
       preservation of historical contradictions/supersessions (e.g. ADR-0002
       superseded by ADR-0005, `domain.space` vs `domain.workspace`,
       `ui.tabs.pin_tab` vs `ui.sidebar.pinned_entity`), and strict abstention
       when proof is missing or inaccessible.
     - Detects and penalizes hallucinations EVEN WHEN retrieval succeeded 100%
       (e.g. ungrounded claims, wrong SHA/version citations, erased historical
       conflicts, or answering instead of abstaining on unavailable data).

Generates:
  - `reports/GROUNDED-ANSWER-EVAL.json`
  - `reports/GROUNDED-ANSWER-EVAL.md`
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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

import domain_ontology  # noqa: E402
import gold_set_benchmark as gsb  # noqa: E402
import knowledge_indexer  # noqa: E402

SCHEMA_VERSION = 1
EVAL_VERSION = "1.0.0"
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

DEFAULT_JSON_REPORT = ROOT_DIR / "reports" / "GROUNDED-ANSWER-EVAL.json"
DEFAULT_MD_REPORT = ROOT_DIR / "reports" / "GROUNDED-ANSWER-EVAL.md"

CLAIM_SUPPORT_THRESHOLD = 0.90


@dataclass(frozen=True)
class GroundingEvidence:
    """Authoritative retrieved evidence item with provenance, revision, and conflict metadata."""

    evidence_id: str
    domain: str
    modality: str
    scope: str
    title: str
    statement: str
    origin_ref: str
    version_or_sha: str
    status: str = "accepted"  # "accepted" | "superseded" | "not-recovered" | "documented"
    superseded_by: str | None = None
    conflicts_with: tuple[str, ...] = ()
    accessible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "domain": self.domain,
            "modality": self.modality,
            "scope": self.scope,
            "title": self.title,
            "statement": self.statement,
            "origin_ref": self.origin_ref,
            "version_or_sha": self.version_or_sha,
            "status": self.status,
            "superseded_by": self.superseded_by,
            "conflicts_with": list(self.conflicts_with),
            "accessible": self.accessible,
        }


def _build_evidence_store(ctx: dict[str, Any]) -> dict[str, GroundingEvidence]:
    """Build unified grounded evidence index from ontology, public catalogs, ADRs, and code/media anchors."""
    store: dict[str, GroundingEvidence] = {}
    ont: domain_ontology.DomainOntology = ctx["ontology"]
    anchors = ctx["anchors"]

    # 1. Ontology concepts (including conflicts & verified historical pointers)
    for cid, spec in ont.concepts.items():
        eid = f"ontology:{cid}"
        sha = hashlib.sha256(f"{cid}|{spec.domain}|{spec.en}|{spec.pt}".encode("utf-8")).hexdigest()[:16]
        origin = spec.evidence_pointers[0] if spec.evidence_pointers else "config/knowledge-concepts.json"
        store[eid] = GroundingEvidence(
            evidence_id=eid,
            domain=spec.domain,
            modality="concept",
            scope="authenticated_archive" if spec.scope == "authenticated-archive" else "public",
            title=f"{spec.en} / {spec.pt}",
            statement=f"Conceito {cid} ({spec.en} / {spec.pt}) no dominio {spec.domain}: " + " ".join(spec.behaviors),
            origin_ref=origin,
            version_or_sha=sha,
            status="accepted" if spec.evidence_level in {"verified-code", "accepted-adr"} else "documented",
            conflicts_with=tuple(dict.fromkeys([*spec.conflicts_with, *spec.ambiguous_with])),
            accessible=True,
        )

    # 2. Public research catalog records
    for rid, rec in ctx["records_by_id"].items():
        r_body = rec.get("record", {})
        stmt = "; ".join(
            f"{k}: {r_body[k]}"
            for k in ("definition", "purpose", "behavior", "guardrail", "classification")
            if isinstance(r_body.get(k), str) and r_body[k]
        ) or rec.get("title", rid)
        sha = rec.get("record_sha256", "")[:16] or hashlib.sha256(rid.encode("utf-8")).hexdigest()[:16]
        store[rid] = GroundingEvidence(
            evidence_id=rid,
            domain="referencias-externas",
            modality="media" if rec["kind"] == "visual" else "document",
            scope="public",
            title=rec.get("title", rid),
            statement=stmt,
            origin_ref=rec.get("catalog_path", "docs/references"),
            version_or_sha=r_body.get("blob_sha", "")[:16] or sha,
            status="documented",
            accessible=True,
        )

    # 3. Multidomain authenticated decisions & code symbols (including ADR-0002 -> ADR-0005 supersession)
    seed_by_id = {d["decision_id"]: d for d in knowledge_indexer.SEED_DECISIONS}
    for doc in ctx["auth_docs"]:
        did = doc["id"]
        if did.startswith("decision:"):
            raw_dec_id = did.split(":", 1)[1]
            seed = seed_by_id.get(raw_dec_id)
            if seed:
                store[did] = GroundingEvidence(
                    evidence_id=did,
                    domain=doc["domain"],
                    modality="decision",
                    scope=doc["scope"],
                    title=seed["title"],
                    statement=f"{seed['title']}: {seed['motivation']} | {seed['consequences']}",
                    origin_ref=seed["path"],
                    version_or_sha=seed["blob_sha"][:16],
                    status=seed["status"],
                    superseded_by=seed.get("superseded_by_id"),
                    accessible=True,
                )
                continue
        store[did] = GroundingEvidence(
            evidence_id=did,
            domain=doc["domain"],
            modality=doc["evidence_type"],
            scope=doc["scope"],
            title=doc["title"],
            statement=doc["text"],
            origin_ref=doc["origin"],
            version_or_sha=doc["sha"][:16],
            status="accepted",
            accessible=True,
        )

    # Ensure canonical SEED_DECISIONS (including ADR-0002 superseded by ADR-0005) are always indexed
    for dec_id, seed in seed_by_id.items():
        did = f"decision:{dec_id}"
        if did not in store:
            store[did] = GroundingEvidence(
                evidence_id=did,
                domain="arquitetura-tecnica",
                modality="decision",
                scope="authenticated_archive",
                title=seed["title"],
                statement=f"{seed['title']}: {seed['motivation']} | {seed['consequences']}",
                origin_ref=seed["path"],
                version_or_sha=seed["blob_sha"][:16],
                status=seed["status"],
                superseded_by=seed.get("superseded_by_id"),
                accessible=True,
            )

    return store


def synthesize_grounded_answer(
    eval_case: dict[str, Any],
    retrieved_ids: list[str],
    evidence_store: dict[str, GroundingEvidence],
    *,
    abstained: bool,
    negative_reason: str | None = None,
) -> dict[str, Any]:
    """Deterministically compose a structured, citation-pinned answer from retrieved evidence only.

    Never fabricates facts or citations outside `retrieved_ids`.
    """
    expected_status = eval_case.get("expected_status", "resolved")
    if abstained or not retrieved_ids:
        reason = negative_reason or eval_case.get("negative_reason") or "insufficient_verified_evidence"
        return {
            "status": "abstained",
            "abstention_reason": reason,
            "claims": [],
            "citations": [],
            "preserved_conflicts": [],
            "preserved_supersessions": [],
            "text": f"Abstencao fundamentada ({reason}): nenhuma evidencia verificada autoriza a resposta.",
        }

    claims: list[dict[str, Any]] = []
    citations: list[dict[str, str]] = []
    preserved_conflicts: list[dict[str, str]] = []
    preserved_supersessions: list[dict[str, str]] = []
    seen_cites: set[str] = set()

    # Select relevant retrieved evidences present in store (preserving rank order)
    selected: list[GroundingEvidence] = []
    for rid in retrieved_ids:
        ev = evidence_store.get(rid)
        if ev and ev.accessible:
            selected.append(ev)
        if len(selected) >= 6:
            break

    if not selected:
        return {
            "status": "abstained",
            "abstention_reason": "retrieved_evidence_inaccessible",
            "claims": [],
            "citations": [],
            "preserved_conflicts": [],
            "preserved_supersessions": [],
            "text": "Abstencao fundamentada: evidencias recuperadas indisponiveis ou sem acesso.",
        }

    for ev in selected:
        cite = {
            "evidence_id": ev.evidence_id,
            "origin_ref": ev.origin_ref,
            "version_or_sha": ev.version_or_sha,
            "status": ev.status,
        }
        if ev.evidence_id not in seen_cites:
            seen_cites.add(ev.evidence_id)
            citations.append(cite)

        claim_text = f"[{ev.evidence_id}] ({ev.origin_ref}@{ev.version_or_sha}, status={ev.status}): {ev.statement}"
        claims.append({
            "claim_id": f"claim:{len(claims) + 1}",
            "text": claim_text,
            "cited_evidence_id": ev.evidence_id,
            "cited_origin": ev.origin_ref,
            "cited_version_or_sha": ev.version_or_sha,
            "claim_kind": "conflict_disambiguation" if ev.conflicts_with else (
                "historical_supersession" if ev.superseded_by else "factual_evidence"
            ),
        })

        for conflict_id in ev.conflicts_with:
            preserved_conflicts.append({
                "source_id": ev.evidence_id,
                "conflicts_with": f"ontology:{conflict_id}" if not conflict_id.startswith("ontology:") else conflict_id,
                "note": f"Conflito/distincao preservada entre {ev.evidence_id} e {conflict_id}.",
            })
        if ev.superseded_by:
            preserved_supersessions.append({
                "superseded_id": ev.evidence_id,
                "superseded_by": f"decision:{ev.superseded_by}" if not ev.superseded_by.startswith("decision:") else ev.superseded_by,
                "status": ev.status,
            })

    if expected_status == "disambiguate" or preserved_conflicts:
        status = "disambiguated" if expected_status == "disambiguate" else "answered_with_conflicts"
    else:
        status = "answered"

    return {
        "status": status,
        "abstention_reason": None,
        "claims": claims,
        "citations": citations,
        "preserved_conflicts": preserved_conflicts,
        "preserved_supersessions": preserved_supersessions,
        "text": " ".join(c["text"] for c in claims),
    }


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_.:-]+", text.lower()))


def evaluate_grounded_answer(
    eval_case: dict[str, Any],
    retrieval_result: dict[str, Any],
    answer: dict[str, Any],
    evidence_store: dict[str, GroundingEvidence],
) -> dict[str, Any]:
    """Tripartite deterministic evaluation of (1) resolution, (2) ranking, and (3) answer grounding.

    Penalizes hallucinations EVEN WHEN retrieval succeeded 100%:
      - Unsupported claims whose statements/tokens are not backed by the cited retrieved evidence.
      - Incorrect or fabricated citations (wrong evidence_id, wrong origin_ref, or wrong version/SHA).
      - Answering when expected_status == 'abstain' (absence or inaccessible source).
      - Dropping required historical conflicts/supersessions when present in evidence or required by case.
    """
    expected_status = eval_case.get("expected_status", "resolved")
    retrieved_ids = list(retrieval_result.get("retrieved_ids", []))
    retrieved_set = set(retrieved_ids)

    # Layer 1: Intent Resolution
    resolution_ok = bool(retrieval_result.get("resolved_ok", False))

    # Layer 2: Ranking Metrics
    recall_at_20 = float(retrieval_result.get("recall_at_20", 0.0))
    precision_at_10 = float(retrieval_result.get("precision_at_10", 0.0))
    mrr = float(retrieval_result.get("mrr", 0.0))

    # Layer 3: Answer Grounding (Claim Support, Citation Accuracy, Completeness, Conflict Preservation, Abstention)
    claims = answer.get("claims", [])
    citations = answer.get("citations", [])
    ans_status = answer.get("status", "")

    hallucination_flags: list[str] = []
    supported_claims = 0
    citation_correct_count = 0

    if expected_status == "abstain":
        abstention_correct = ans_status == "abstained" and len(claims) == 0
        if not abstention_correct:
            hallucination_flags.append("answered_on_abstention_case")
            claim_support_rate = 0.0
            citation_accuracy = 0.0
            requirement_completeness = 0.0
        else:
            claim_support_rate = 1.0
            citation_accuracy = 1.0
            requirement_completeness = 1.0
    else:
        abstention_correct = ans_status != "abstained"
        if not claims:
            hallucination_flags.append("empty_claims_on_answerable_case")
            claim_support_rate = 0.0
        else:
            for cl in claims:
                cid = cl.get("cited_evidence_id", "")
                c_origin = cl.get("cited_origin", "")
                c_sha = cl.get("cited_version_or_sha", "")
                ev = evidence_store.get(cid)
                if cid not in retrieved_set or ev is None or not ev.accessible:
                    hallucination_flags.append(f"unretrieved_or_fabricated_evidence:{cid}")
                    continue
                # Verify origin & hash/version pinning
                if c_origin != ev.origin_ref or c_sha != ev.version_or_sha:
                    hallucination_flags.append(f"citation_pin_mismatch:{cid}")
                    continue
                # Verify lexical containment / support between claim text and authoritative evidence
                ev_tokens = _tokens(f"{ev.evidence_id} {ev.title} {ev.statement} {ev.origin_ref} {ev.version_or_sha} {ev.status}")
                cl_tokens = _tokens(cl.get("text", "")) - {"status", "no", "em", "de", "da", "do", "e"}
                if not cl_tokens:
                    hallucination_flags.append(f"empty_claim_tokens:{cid}")
                    continue
                overlap_ratio = len(cl_tokens & ev_tokens) / float(len(cl_tokens))
                if overlap_ratio < 0.65:
                    hallucination_flags.append(f"unsupported_claim_content:{cid}({overlap_ratio:.2f})")
                    continue
                supported_claims += 1

            claim_support_rate = supported_claims / float(len(claims))

        # Citation accuracy over all emitted citations
        if not citations:
            citation_accuracy = 0.0
            hallucination_flags.append("missing_citations")
        else:
            for ct in citations:
                cid = ct.get("evidence_id", "")
                ev = evidence_store.get(cid)
                if (
                    cid in retrieved_set
                    and ev is not None
                    and ev.accessible
                    and ct.get("origin_ref") == ev.origin_ref
                    and ct.get("version_or_sha") == ev.version_or_sha
                    and ct.get("status") == ev.status
                ):
                    citation_correct_count += 1
                else:
                    hallucination_flags.append(f"bad_citation:{cid}")
            citation_accuracy = citation_correct_count / float(len(citations))

        # Requirement completeness: check required expected evidence IDs are cited in answer
        req_ids = list(eval_case.get("required_evidence_ids") or eval_case.get("expected_evidence_ids") or [])
        cited_ids = {ct.get("evidence_id") for ct in citations}
        if req_ids:
            requirement_completeness = len(set(req_ids) & cited_ids) / float(len(set(req_ids)))
        else:
            requirement_completeness = 1.0 if citations else 0.0

    # Conflict / supersession preservation check
    required_conflicts = list(eval_case.get("required_conflicts", []))
    required_supersessions = list(eval_case.get("required_supersessions", []))
    preserved_conflict_targets = {
        (c.get("source_id"), c.get("conflicts_with"))
        for c in answer.get("preserved_conflicts", [])
    }
    preserved_sup_targets = {
        (s.get("superseded_id"), s.get("superseded_by"))
        for s in answer.get("preserved_supersessions", [])
    }

    conflicts_ok = True
    for src_id, dst_id in required_conflicts:
        if (src_id, dst_id) not in preserved_conflict_targets and (dst_id, src_id) not in preserved_conflict_targets:
            conflicts_ok = False
            hallucination_flags.append(f"erased_conflict:{src_id}<->{dst_id}")
    for old_id, new_id in required_supersessions:
        if (old_id, new_id) not in preserved_sup_targets:
            conflicts_ok = False
            hallucination_flags.append(f"erased_supersession:{old_id}->{new_id}")

    hallucination_detected = len(hallucination_flags) > 0
    grounded_pass = (
        claim_support_rate >= CLAIM_SUPPORT_THRESHOLD
        and citation_accuracy >= 0.90
        and abstention_correct
        and conflicts_ok
        and not hallucination_detected
    )

    return {
        "case_id": eval_case.get("query_id") or eval_case.get("case_id"),
        "domain": eval_case.get("domain"),
        "split": eval_case.get("split", "adversarial"),
        "case_type": eval_case.get("case_type") or eval_case.get("query_type"),
        "layer_1_resolution_ok": resolution_ok,
        "layer_2_ranking": {
            "recall_at_20": recall_at_20,
            "precision_at_10": precision_at_10,
            "mrr": mrr,
        },
        "layer_3_grounding": {
            "claim_support_rate": round(claim_support_rate, 4),
            "citation_accuracy": round(citation_accuracy, 4),
            "requirement_completeness": round(requirement_completeness, 4),
            "abstention_correct": abstention_correct,
            "conflicts_preserved": conflicts_ok,
            "hallucination_detected": hallucination_detected,
            "hallucination_flags": hallucination_flags,
            "grounded_pass": grounded_pass,
        },
    }


def build_adversarial_grounding_cases() -> list[dict[str, Any]]:
    """Build dedicated adversarial scenarios for conflicts, supersessions, multi-hop, and inaccessible data."""
    return [
        {
            "case_id": "adv-supersession-adr0002",
            "domain": "arquitetura-tecnica",
            "case_type": "historical_supersession",
            "query": "Qual o status historico de ADR-0002 e sua substituicao por ADR-0005?",
            "scope": "authenticated_archive",
            "expected_status": "resolved",
            "retrieved_ids": ["decision:ADR-0002", "decision:ADR-0005"],
            "required_evidence_ids": ["decision:ADR-0002", "decision:ADR-0005"],
            "required_supersessions": [("decision:ADR-0002", "decision:ADR-0005")],
            "required_conflicts": [],
            "negative_reason": None,
        },
        {
            "case_id": "adv-conflict-space-vs-workspace",
            "domain": "workspace",
            "case_type": "contradictory_concepts",
            "query": "Diferenca e conflito entre domain.space e domain.workspace",
            "scope": "authenticated_archive",
            "expected_status": "disambiguate",
            "retrieved_ids": ["ontology:domain.space", "ontology:domain.workspace"],
            "required_evidence_ids": ["ontology:domain.space", "ontology:domain.workspace"],
            "required_conflicts": [("ontology:domain.space", "ontology:domain.workspace")],
            "required_supersessions": [],
            "negative_reason": None,
        },
        {
            "case_id": "adv-conflict-pin-tab-vs-sidebar",
            "domain": "workspace",
            "case_type": "contradictory_concepts",
            "query": "Distincao entre fixar aba (ui.tabs.pin_tab) e entidade fixada na sidebar (ui.sidebar.pinned_entity)",
            "scope": "authenticated_archive",
            "expected_status": "disambiguate",
            "retrieved_ids": ["ontology:ui.tabs.pin_tab", "ontology:ui.sidebar.pinned_entity"],
            "required_evidence_ids": ["ontology:ui.tabs.pin_tab", "ontology:ui.sidebar.pinned_entity"],
            "required_conflicts": [("ontology:ui.tabs.pin_tab", "ontology:ui.sidebar.pinned_entity")],
            "required_supersessions": [],
            "negative_reason": None,
        },
        {
            "case_id": "adv-inaccessible-private-bundle",
            "domain": "historico",
            "case_type": "inaccessible_source",
            "query": "Conteudo bruto de bundle privado sem autorizacao no canal publico",
            "scope": "public",
            "expected_status": "abstain",
            "retrieved_ids": [],
            "required_evidence_ids": [],
            "required_conflicts": [],
            "required_supersessions": [],
            "negative_reason": "inaccessible_authenticated_bundle",
        },
        {
            "case_id": "adv-multihop-design-auth",
            "domain": "design-system",
            "case_type": "multi_hop",
            "query": "Relacao entre ADR-0008, SemanticThemeTokens e design-system",
            "scope": "authenticated_archive",
            "expected_status": "resolved",
            "retrieved_ids": ["ontology:domain.design-system", "decision:ADR-0008", "code:design-system:SemanticThemeTokens"],
            "required_evidence_ids": ["ontology:domain.design-system", "decision:ADR-0008", "code:design-system:SemanticThemeTokens"],
            "required_conflicts": [],
            "required_supersessions": [],
            "negative_reason": None,
        },
    ]


def evaluate_all_grounded_answers(
    config_path: Path = gsb.DEFAULT_CONFIG_PATH,
    *,
    write_reports: bool = True,
    json_report_path: Path = DEFAULT_JSON_REPORT,
    md_report_path: Path = DEFAULT_MD_REPORT,
) -> dict[str, Any]:
    """Run tripartite evaluation across all 460 Gold Set queries + adversarial grounding suite + hallucination probe."""
    dataset = gsb.load_gold_set(config_path)
    queries = dataset["queries"]
    ctx = gsb._build_corpus_indices()
    try:
        evidence_store = _build_evidence_store(ctx)
        gold_evaluations: list[dict[str, Any]] = []

        for q in queries:
            ret = gsb.run_single_benchmark_query(q, ctx, mode="full_federated")
            abstained = ret["actual_status"] == "abstain"
            ans = synthesize_grounded_answer(
                q,
                ret["retrieved_ids"],
                evidence_store,
                abstained=abstained,
                negative_reason=ret.get("negative_reason"),
            )
            ev_res = evaluate_grounded_answer(q, ret, ans, evidence_store)
            gold_evaluations.append(ev_res)

        # Evaluate dedicated adversarial cases (supersessions, conflicts, inaccessible, multi-hop)
        adversarial_evaluations: list[dict[str, Any]] = []
        for adv in build_adversarial_grounding_cases():
            ret = {
                "resolved_ok": True,
                "recall_at_20": 1.0,
                "precision_at_10": 1.0,
                "mrr": 1.0,
                "retrieved_ids": adv["retrieved_ids"],
            }
            ans = synthesize_grounded_answer(
                adv,
                adv["retrieved_ids"],
                evidence_store,
                abstained=(adv["expected_status"] == "abstain"),
                negative_reason=adv.get("negative_reason"),
            )
            adversarial_evaluations.append(evaluate_grounded_answer(adv, ret, ans, evidence_store))

        # Run hallucination sensitivity probe (proves detector penalizes hallucinations despite 100% retrieval)
        probe_case = {
            "case_id": "probe-hallucination-despite-perfect-retrieval",
            "domain": "design-system",
            "case_type": "hallucination_probe",
            "expected_status": "resolved",
            "required_evidence_ids": ["decision:ADR-0008"],
        }
        perfect_retrieval = {
            "resolved_ok": True,
            "recall_at_20": 1.0,
            "precision_at_10": 1.0,
            "mrr": 1.0,
            "retrieved_ids": ["decision:ADR-0008"],
        }
        hallucinated_answer = {
            "status": "answered",
            "claims": [
                {
                    "claim_id": "claim:1",
                    "text": "Fabricated statement claiming PostgreSQL cluster runs on port 9999 without citation support.",
                    "cited_evidence_id": "decision:ADR-0008",
                    "cited_origin": "docs/adr/0008-install-firebase-ui-registry.md",
                    "cited_version_or_sha": "0000000000000000",  # corrupted SHA
                }
            ],
            "citations": [
                {
                    "evidence_id": "decision:ADR-0008",
                    "origin_ref": "docs/adr/0008-install-firebase-ui-registry.md",
                    "version_or_sha": "0000000000000000",
                    "status": "accepted",
                }
            ],
            "preserved_conflicts": [],
            "preserved_supersessions": [],
        }
        probe_res = evaluate_grounded_answer(probe_case, perfect_retrieval, hallucinated_answer, evidence_store)

        all_evals = gold_evaluations + adversarial_evaluations
        n = float(len(all_evals))
        res_rate = round(sum(1 for e in all_evals if e["layer_1_resolution_ok"]) / n, 4)
        mean_rec = round(sum(e["layer_2_ranking"]["recall_at_20"] for e in all_evals) / n, 4)
        mean_prec = round(sum(e["layer_2_ranking"]["precision_at_10"] for e in all_evals) / n, 4)
        mean_mrr = round(sum(e["layer_2_ranking"]["mrr"] for e in all_evals) / n, 4)

        mean_claim_support = round(sum(e["layer_3_grounding"]["claim_support_rate"] for e in all_evals) / n, 4)
        mean_cite_acc = round(sum(e["layer_3_grounding"]["citation_accuracy"] for e in all_evals) / n, 4)
        mean_completeness = round(sum(e["layer_3_grounding"]["requirement_completeness"] for e in all_evals) / n, 4)
        abstention_cases = [e for e in all_evals if e["case_type"] in {"negative_absent", "negative_unavailable", "inaccessible_source"}]
        abstention_rate = round(
            sum(1 for e in abstention_cases if e["layer_3_grounding"]["abstention_correct"]) / float(len(abstention_cases)),
            4,
        ) if abstention_cases else 1.0
        conflicts_preserved_rate = round(
            sum(1 for e in all_evals if e["layer_3_grounding"]["conflicts_preserved"]) / n, 4
        )
        hallucination_rate = round(
            sum(1 for e in all_evals if e["layer_3_grounding"]["hallucination_detected"]) / n, 4
        )
        grounded_pass_rate = round(
            sum(1 for e in all_evals if e["layer_3_grounding"]["grounded_pass"]) / n, 4
        )

        by_domain: dict[str, dict[str, Any]] = {}
        for dom in gsb.REQUIRED_23_DOMAINS:
            sub = [e for e in all_evals if e["domain"] == dom]
            dn = float(len(sub)) or 1.0
            by_domain[dom] = {
                "count": len(sub),
                "resolution_rate": round(sum(1 for e in sub if e["layer_1_resolution_ok"]) / dn, 4),
                "recall_at_20": round(sum(e["layer_2_ranking"]["recall_at_20"] for e in sub) / dn, 4),
                "precision_at_10": round(sum(e["layer_2_ranking"]["precision_at_10"] for e in sub) / dn, 4),
                "claim_support_rate": round(sum(e["layer_3_grounding"]["claim_support_rate"] for e in sub) / dn, 4),
                "citation_accuracy": round(sum(e["layer_3_grounding"]["citation_accuracy"] for e in sub) / dn, 4),
                "requirement_completeness": round(sum(e["layer_3_grounding"]["requirement_completeness"] for e in sub) / dn, 4),
                "grounded_pass_rate": round(sum(1 for e in sub if e["layer_3_grounding"]["grounded_pass"]) / dn, 4),
            }

        failures = [e for e in all_evals if not e["layer_3_grounding"]["grounded_pass"]]
        gate_passed = (
            mean_claim_support >= CLAIM_SUPPORT_THRESHOLD
            and mean_cite_acc >= 0.90
            and abstention_rate >= 0.95
            and conflicts_preserved_rate == 1.0
            and probe_res["layer_3_grounding"]["hallucination_detected"] is True
        )

        report = {
            "schema_version": SCHEMA_VERSION,
            "eval_version": EVAL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_cases": len(all_evals),
            "gold_cases": len(gold_evaluations),
            "adversarial_cases": len(adversarial_evaluations),
            "tripartite_summary": {
                "layer_1_resolution": {
                    "resolution_rate": res_rate,
                },
                "layer_2_ranking": {
                    "recall_at_20": mean_rec,
                    "precision_at_10": mean_prec,
                    "mrr": mean_mrr,
                },
                "layer_3_grounding": {
                    "claim_support_rate": mean_claim_support,
                    "citation_accuracy": mean_cite_acc,
                    "requirement_completeness": mean_completeness,
                    "abstention_accuracy": abstention_rate,
                    "conflicts_preserved_rate": conflicts_preserved_rate,
                    "hallucination_rate": hallucination_rate,
                    "grounded_pass_rate": grounded_pass_rate,
                },
            },
            "hallucination_detector_probe": {
                "retrieval_recall_at_20": 1.0,
                "hallucination_detected": probe_res["layer_3_grounding"]["hallucination_detected"],
                "claim_support_rate": probe_res["layer_3_grounding"]["claim_support_rate"],
                "citation_accuracy": probe_res["layer_3_grounding"]["citation_accuracy"],
                "flags": probe_res["layer_3_grounding"]["hallucination_flags"],
            },
            "thresholds": {
                "claim_support_min": CLAIM_SUPPORT_THRESHOLD,
                "citation_accuracy_min": 0.90,
                "abstention_accuracy_min": 0.95,
            },
            "gate_passed": gate_passed,
            "by_domain": by_domain,
            "adversarial_results": adversarial_evaluations,
            "failures_count": len(failures),
            "failures_sample": failures[:20],
        }

        if write_reports:
            json_report_path.parent.mkdir(parents=True, exist_ok=True)
            json_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            md_report_path.parent.mkdir(parents=True, exist_ok=True)
            md_report_path.write_text(render_markdown_report(report), encoding="utf-8")

        return report
    finally:
        ctx["research_db"].close()


def render_markdown_report(report: dict[str, Any]) -> str:
    tri = report["tripartite_summary"]
    l1 = tri["layer_1_resolution"]
    l2 = tri["layer_2_ranking"]
    l3 = tri["layer_3_grounding"]
    probe = report["hallucination_detector_probe"]

    lines = [
        "**Synthetic/label-aware regression only (#94). Production evaluation: NOT RUN.**",
        "# Avaliacao Tripartite de Fundamentacao e Resposta (#88)",
        "",
        f"- **Data:** {report['generated_at']}",
        f"- **Total de Casos:** {report['total_cases']} ({report['gold_cases']} gold set + {report['adversarial_cases']} adversariais)",
        f"- **Gate de Fundamentacao:** `{'PASS' if report['gate_passed'] else 'FAIL'}` (Claim Support >= 90%)",
        "",
        "## Camada 1, 2 e 3 (Separacao Estrita: Resolucao vs Ranking vs Fundamentacao)",
        "",
        "| Camada | Metrica | Valor |",
        "|---|---|---:|",
        f"| 1. Resolucao da Intencao | `resolution_rate` | {l1['resolution_rate']:.2%} |",
        f"| 2. Ranking de Evidencias | `recall@20` | {l2['recall_at_20']:.2%} |",
        f"| 2. Ranking de Evidencias | `precision@10` | {l2['precision_at_10']:.2%} |",
        f"| 2. Ranking de Evidencias | `mrr` | {l2['mrr']:.4f} |",
        f"| 3. Fundamentacao (Claim Support) | `claim_support_rate` | {l3['claim_support_rate']:.2%} |",
        f"| 3. Fundamentacao (Citações/Hashes) | `citation_accuracy` | {l3['citation_accuracy']:.2%} |",
        f"| 3. Fundamentacao (Completude) | `requirement_completeness` | {l3['requirement_completeness']:.2%} |",
        f"| 3. Fundamentacao (Abstencao) | `abstention_accuracy` | {l3['abstention_accuracy']:.2%} |",
        f"| 3. Fundamentacao (Conflitos/Supersessoes) | `conflicts_preserved_rate` | {l3['conflicts_preserved_rate']:.2%} |",
        f"| 3. Fundamentacao (Taxa de Alucinacao) | `hallucination_rate` | {l3['hallucination_rate']:.2%} |",
        "",
        "## Sonda de Deteccao de Alucinacao com Retrieval 100% Correto",
        "",
        f"- **Retrieval Recall@20:** {probe['retrieval_recall_at_20']:.2%}",
        f"- **Alucinacao Detectada:** `{probe['hallucination_detected']}`",
        f"- **Claim Support na Sonda:** {probe['claim_support_rate']:.2%}",
        f"- **Citation Accuracy na Sonda:** {probe['citation_accuracy']:.2%}",
        f"- **Flags:** `{', '.join(probe['flags'])}`",
        "",
        "## Resultados por Dominio (23 Dominios)",
        "",
        "| Dominio | Casos | Resolucao | Recall@20 | Precision@10 | Claim Support | Citation Acc | Completeness |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dom in gsb.REQUIRED_23_DOMAINS:
        m = report["by_domain"][dom]
        lines.append(
            f"| `{dom}` | {m['count']} | {m['resolution_rate']:.2%} | {m['recall_at_20']:.2%} | "
            f"{m['precision_at_10']:.2%} | {m['claim_support_rate']:.2%} | {m['citation_accuracy']:.2%} | "
            f"{m['requirement_completeness']:.2%} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=gsb.DEFAULT_CONFIG_PATH)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_REPORT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    rep = evaluate_all_grounded_answers(
        config_path=args.config,
        write_reports=not args.no_write,
        json_report_path=args.json_out,
        md_report_path=args.md_out,
    )
    print(json.dumps({
        "total_cases": rep["total_cases"],
        "gate_passed": rep["gate_passed"],
        "tripartite_summary": rep["tripartite_summary"],
        "hallucination_detector_probe": rep["hallucination_detector_probe"],
    }, ensure_ascii=False, indent=2))
    return 0 if rep["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
