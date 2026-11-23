#!/usr/bin/env python3
"""Reproducible search benchmark comparing FTS5 strategies, PT<->EN expansion,
and optional semantic/QMD/picoqmd-style embeddings on archive fixtures.

Standard library only. Can evaluate both:
1. A deterministic synthetic ground-truth benchmark (default, CI-safe, zero external deps).
2. An optional real local SQLite archive DB (e.g., .cache/benchmark/full-index.sqlite)
   to measure cross-lingual hit expansion, latency, and token footprint on live data.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import archive_index  # noqa: E402
import search_expansion  # noqa: E402


@dataclass(frozen=True)
class BenchmarkDoc:
    doc_id: str
    repository: str
    kind: str  # "commit" | "file" | "image"
    sha: str
    path: str
    subject: str
    date: str
    blob: str = ""
    bytes: int = 0
    image_kind: str = "branch-head"


@dataclass(frozen=True)
class BenchmarkQuery:
    query_id: str
    query: str
    category: str
    relevant_ids: tuple[str, ...]
    notes: str = ""


def build_synthetic_corpus() -> tuple[list[BenchmarkDoc], list[BenchmarkQuery]]:
    """Create a realistic bilingual (PT commits <-> EN paths) synthetic corpus with explicit ground truth."""
    docs: list[BenchmarkDoc] = [
        # --- Graph / Grafo domain (PT commits + EN paths + images) ---
        BenchmarkDoc(
            doc_id="c_grafo_1",
            repository="exams-app-antigo-2",
            kind="commit",
            sha="1111111111111111111111111111111111111111",
            path="",
            subject="feat(grafo): exporta PNG via capability downloads",
            date="2026-08-10T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_graph_2",
            repository="notes-app@old-4",
            kind="commit",
            sha="1111111111111111111111111111111111111112",
            path="",
            subject="feat(graph): contextual canvas graph physics and node filter",
            date="2026-08-11T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_graph_canvas",
            repository="exams-app-antigo-2",
            kind="file",
            sha="1111111111111111111111111111111111111113",
            path="src/components/graph/graph-canvas.tsx",
            subject="",
            date="2026-08-12T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_grafo_mjs",
            repository="exams-app",
            kind="file",
            sha="1111111111111111111111111111111111111114",
            path="docs/05-ferramentas/repo-grafo/grafo.mjs",
            subject="",
            date="2026-08-13T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="i_graph_toolbar",
            repository="exams-app-antigo-2",
            kind="image",
            sha="1111111111111111111111111111111111111115",
            path="prototypes/assets/issue68_graph_toolbar_1366.png",
            subject="",
            date="2026-08-14T10:00:00Z",
            blob="aa11" * 10,
            bytes=92400,
            image_kind="deleted",
        ),
        # --- Sidebar / Barra lateral domain ---
        BenchmarkDoc(
            doc_id="c_sidebar_1",
            repository="notes-app@old-2",
            kind="commit",
            sha="2222222222222222222222222222222222222221",
            path="",
            subject="Implement workspace sidebar shell and collapsible drawer",
            date="2026-07-01T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_sidebar_pt",
            repository="exams-app",
            kind="commit",
            sha="2222222222222222222222222222222222222222",
            path="",
            subject="docs: prototipo da barra lateral com gaveta responsiva",
            date="2026-07-02T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_sidebar_tsx",
            repository="notes-app@old-2",
            kind="file",
            sha="2222222222222222222222222222222222222223",
            path="src/components/workspace/sidebar.tsx",
            subject="",
            date="2026-07-03T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="i_sidebar_gaveta",
            repository="exams-app",
            kind="image",
            sha="2222222222222222222222222222222222222224",
            path="docs/revisao/sidebar-prototipo/capturas/m-dark-2-gaveta.png",
            subject="",
            date="2026-07-04T10:00:00Z",
            blob="bb22" * 10,
            bytes=64200,
            image_kind="branch-head",
        ),
        # --- Simulado / Exam / Mock / Questao domain ---
        BenchmarkDoc(
            doc_id="c_simulado_1",
            repository="exams-app-antigo-2",
            kind="commit",
            sha="3333333333333333333333333333333333333331",
            path="",
            subject="feat(novo): modelos de Questao e Simulado no menu principal",
            date="2026-07-10T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_exam_ts",
            repository="notes-app@old-9",
            kind="file",
            sha="3333333333333333333333333333333333333332",
            path="src/domain/exams/exam.ts",
            subject="",
            date="2026-07-11T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_mock_runner",
            repository="exams-app-antigo-2",
            kind="file",
            sha="3333333333333333333333333333333333333333",
            path="src/features/mock-exam-runner.ts",
            subject="",
            date="2026-07-12T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_question_ts",
            repository="notes-app@old-9",
            kind="file",
            sha="3333333333333333333333333333333333333334",
            path="src/domain/questions/question.ts",
            subject="",
            date="2026-07-13T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="i_questao_img",
            repository="exams-app-antigo-2",
            kind="image",
            sha="3333333333333333333333333333333333333335",
            path="prototypes/audit2026_questao_expanded.png",
            subject="",
            date="2026-07-14T10:00:00Z",
            blob="cc33" * 10,
            bytes=51200,
            image_kind="branch-head",
        ),
        # --- Capacities & QConcursos & FSRS/Recall domain ---
        BenchmarkDoc(
            doc_id="c_capacities_1",
            repository="notes-app@old-5",
            kind="commit",
            sha="4444444444444444444444444444444444444441",
            path="",
            subject="Polish Capacities workspace parity and object tabs",
            date="2026-07-20T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_capacities_map",
            repository="notes-app@old-5",
            kind="file",
            sha="4444444444444444444444444444444444444442",
            path="CAPACITIES_COMPONENT_MAP.md",
            subject="",
            date="2026-07-21T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_qconcursos_1",
            repository="exams-app-antigo-2",
            kind="commit",
            sha="5555555555555555555555555555555555555551",
            path="",
            subject="Add QConcursos inventory and verified research for issue 31",
            date="2026-07-22T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_qconcursos_md",
            repository="exams-app-antigo-2",
            kind="file",
            sha="5555555555555555555555555555555555555552",
            path="prototypes/analise-qconcursos.md",
            subject="",
            date="2026-07-23T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_fsrs_1",
            repository="notes-app@old-10",
            kind="commit",
            sha="6666666666666666666666666666666666666661",
            path="",
            subject="feat: add spaced repetition study mode with FSRS scheduler",
            date="2026-07-24T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_fsrs_ts",
            repository="notes-app@old-5",
            kind="file",
            sha="6666666666666666666666666666666666666662",
            path="src/lib/srs/fsrs.ts",
            subject="",
            date="2026-07-25T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_recall_ts",
            repository="notes-app@old-10",
            kind="file",
            sha="6666666666666666666666666666666666666663",
            path="src/domain/recall.ts",
            subject="",
            date="2026-07-26T10:00:00Z",
        ),
        # --- Code with divergent identifiers & non-descriptive screenshot ---
        BenchmarkDoc(
            doc_id="f_spaced_code",
            repository="notes-app@old-11",
            kind="file",
            sha="7777777777777777777777777777777777777771",
            path="src/lib/memory/interval_scheduler_v2.ts",
            subject="",
            date="2026-07-27T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_spaced_code",
            repository="notes-app@old-11",
            kind="commit",
            sha="7777777777777777777777777777777777777772",
            path="",
            subject="feat: implement interval scheduler for daily review queue",
            date="2026-07-27T10:05:00Z",
        ),
        BenchmarkDoc(
            doc_id="i_nondescriptive_shot",
            repository="exams-app",
            kind="image",
            sha="8888888888888888888888888888888888888881",
            path="docs/captures/IMG_20260801_0042.png",
            subject="",
            date="2026-08-01T10:00:00Z",
            blob="dd44" * 10,
            bytes=118000,
            image_kind="deleted",
        ),
        BenchmarkDoc(
            doc_id="c_nondescriptive_shot",
            repository="exams-app",
            kind="commit",
            sha="8888888888888888888888888888888888888882",
            path="",
            subject="docs: captura visual da tela inicial do app",
            date="2026-08-01T10:05:00Z",
        ),
        # --- Noise / Distractor documents (to test ranking, quotas, and precision) ---
        BenchmarkDoc(
            doc_id="c_noise_1",
            repository="shadcn-template",
            kind="commit",
            sha="9999999999999999999999999999999999999991",
            path="",
            subject="chore: bump tailwind and eslint dependencies",
            date="2026-06-01T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_noise_2",
            repository="shadcn-template",
            kind="file",
            sha="9999999999999999999999999999999999999992",
            path="package.json",
            subject="",
            date="2026-06-02T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="f_noise_3",
            repository="exams-app-old",
            kind="file",
            sha="9999999999999999999999999999999999999993",
            path="src/components/ui/button.tsx",
            subject="",
            date="2026-06-03T10:00:00Z",
        ),
        # Many recent low-relevance long commit messages mentioning 'sidebar' incidentally;
        # FTS5 legacy (ORDER BY date DESC) floods top-k commits with these, hiding older relevant
        # files/images and shorter exact-focus commits, whereas BM25 + kind quotas (#16) recovers them.
        BenchmarkDoc(
            doc_id="c_noise_sidebar_long_1",
            repository="exams-app-old",
            kind="commit",
            sha="9999999999999999999999999999999999999994",
            path="",
            subject="chore: adjust unrelated footer spacing typography badges and borders near sidebar wrapper",
            date="2026-09-04T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_noise_sidebar_long_2",
            repository="exams-app-old",
            kind="commit",
            sha="9999999999999999999999999999999999999995",
            path="",
            subject="chore: refactor header dropdown menu alignment without touching sidebar behavior or state",
            date="2026-09-05T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_noise_sidebar_long_3",
            repository="exams-app-old",
            kind="commit",
            sha="9999999999999999999999999999999999999996",
            path="",
            subject="chore: cleanup unused css tokens across cards modals dialogs and legacy sidebar container",
            date="2026-09-06T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_noise_sidebar_long_4",
            repository="exams-app-old",
            kind="commit",
            sha="9999999999999999999999999999999999999997",
            path="",
            subject="chore: update dark theme color contrast variables around main container and sidebar edge",
            date="2026-09-07T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_noise_sidebar_long_5",
            repository="exams-app-old",
            kind="commit",
            sha="9999999999999999999999999999999999999998",
            path="",
            subject="chore: polish responsive padding breakpoints across mobile tablet and desktop sidebar area",
            date="2026-09-08T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_noise_sidebar_long_6",
            repository="exams-app-old",
            kind="commit",
            sha="9999999999999999999999999999999999999999",
            path="",
            subject="chore: align scrollbar width inside nested list containers adjacent to sidebar frame",
            date="2026-09-09T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_noise_sidebar_long_7",
            repository="exams-app-old",
            kind="commit",
            sha="999999999999999999999999999999999999999a",
            path="",
            subject="chore: document lint rule exceptions for legacy styles near secondary sidebar slot",
            date="2026-09-10T10:00:00Z",
        ),
        BenchmarkDoc(
            doc_id="c_noise_sidebar_long_8",
            repository="exams-app-old",
            kind="commit",
            sha="999999999999999999999999999999999999999b",
            path="",
            subject="chore: bump icon sprite bundle and verify aria labels outside sidebar region",
            date="2026-09-11T10:00:00Z",
        ),
        # Unannotated screenshot whose path has zero domain terms ('assets/opaque/img_0042.png'),
        # demonstrating why pure filename/commit search misses visual-only content without CLIP/OCR.
        BenchmarkDoc(
            doc_id="i_opaque_home",
            repository="exams-app",
            kind="image",
            sha="8888888888888888888888888888888888888889",
            path="assets/opaque/img_0042.png",
            subject="",
            date="2026-08-02T10:00:00Z",
            blob="ee55" * 10,
            bytes=78402,
            image_kind="deleted",
        ),
    ]

    queries: list[BenchmarkQuery] = [
        BenchmarkQuery(
            query_id="q_sidebar",
            query="sidebar",
            category="direct_en",
            relevant_ids=("c_sidebar_1", "c_sidebar_pt", "f_sidebar_tsx", "i_sidebar_gaveta"),
            notes="Direct English term plus Portuguese drawer/barra lateral evidence",
        ),
        BenchmarkQuery(
            query_id="q_barra_lateral",
            query="barra lateral",
            category="cross_lingual_pt_en",
            relevant_ids=("c_sidebar_pt", "c_sidebar_1", "f_sidebar_tsx", "i_sidebar_gaveta"),
            notes="Portuguese query targeting English sidebar code and commits",
        ),
        BenchmarkQuery(
            query_id="q_grafo",
            query="grafo",
            category="cross_lingual_pt_en",
            relevant_ids=("c_grafo_1", "c_graph_2", "f_grafo_mjs", "f_graph_canvas", "i_graph_toolbar"),
            notes="Portuguese 'grafo' must retrieve English 'graph' code & screenshots",
        ),
        BenchmarkQuery(
            query_id="q_simulado",
            query="simulado",
            category="cross_lingual_pt_en",
            relevant_ids=("c_simulado_1", "f_exam_ts", "f_mock_runner"),
            notes="Portuguese 'simulado' must retrieve exam.ts and mock-exam-runner.ts",
        ),
        BenchmarkQuery(
            query_id="q_questao",
            query="questao",
            category="cross_lingual_pt_en",
            relevant_ids=("c_simulado_1", "f_question_ts", "i_questao_img"),
            notes="Portuguese 'questao' must retrieve question.ts and screenshot",
        ),
        BenchmarkQuery(
            query_id="q_capacities",
            query="Capacities",
            category="entity_exact",
            relevant_ids=("c_capacities_1", "f_capacities_map"),
            notes="Named reference system",
        ),
        BenchmarkQuery(
            query_id="q_qconcursos",
            query="QConcursos",
            category="entity_exact",
            relevant_ids=("c_qconcursos_1", "f_qconcursos_md"),
            notes="Named reference platform",
        ),
        BenchmarkQuery(
            query_id="q_divergent_code",
            query="repeticao espacada",
            category="divergent_identifier",
            relevant_ids=("c_fsrs_1", "f_fsrs_ts"),
            notes="Query about spaced repetition where code file is named fsrs.ts",
        ),
        BenchmarkQuery(
            query_id="q_nondescriptive_img",
            query="captura tela inicial",
            category="nondescriptive_image",
            relevant_ids=("c_nondescriptive_shot", "i_nondescriptive_shot", "i_opaque_home"),
            notes="Includes opaque screenshot filename old-10-home.png (no lexical overlap with query)",
        ),
    ]
    return docs, queries


def populate_synthetic_db(db_path: Path, docs: list[BenchmarkDoc]) -> tuple[sqlite3.Connection, dict[tuple[str, str], str]]:
    """Populate a standard archive_index SQLite database with the benchmark corpus."""
    if db_path.exists():
        db_path.unlink()
    conn = archive_index.open_db(db_path)
    repo_ids: dict[str, int] = {}
    id_lookup: dict[tuple[str, str], str] = {}

    with conn:
        for doc in docs:
            if doc.repository not in repo_ids:
                conn.execute(
                    "INSERT INTO repositories (name, source, indexed_at) VALUES (?, ?, ?)",
                    (doc.repository, "synthetic://benchmark", "2026-11-23T00:00:00+00:00"),
                )
                repo_ids[doc.repository] = conn.execute(
                    "SELECT id FROM repositories WHERE name = ?", (doc.repository,)
                ).fetchone()[0]
            rid = repo_ids[doc.repository]
            if doc.kind == "commit":
                conn.execute(
                    "INSERT OR IGNORE INTO commits (repo_id, sha, date, subject) VALUES (?, ?, ?, ?)",
                    (rid, doc.sha, doc.date, doc.subject),
                )
                conn.execute(
                    "INSERT INTO commit_fts (subject, repo_id, sha) VALUES (?, ?, ?)",
                    (doc.subject, rid, doc.sha),
                )
                id_lookup[("commit", doc.sha)] = doc.doc_id
            elif doc.kind == "file":
                conn.execute(
                    "INSERT OR IGNORE INTO commits (repo_id, sha, date, subject) VALUES (?, ?, ?, ?)",
                    (rid, doc.sha, doc.date, f"touch {doc.path}"),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO changes (repo_id, sha, status, path, previous_path) VALUES (?, ?, ?, ?, ?)",
                    (rid, doc.sha, "M", doc.path, ""),
                )
                conn.execute(
                    "INSERT INTO change_fts (path, repo_id, sha, status) VALUES (?, ?, ?, ?)",
                    (doc.path, rid, doc.sha, "M"),
                )
                id_lookup[("file", doc.path)] = doc.doc_id
            elif doc.kind == "image":
                conn.execute(
                    "INSERT OR IGNORE INTO commits (repo_id, sha, date, subject) VALUES (?, ?, ?, ?)",
                    (rid, doc.sha, doc.date, f"asset {doc.path}"),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO images (repo_id, path, blob, commit_sha, kind, bytes) VALUES (?, ?, ?, ?, ?, ?)",
                    (rid, doc.path, doc.blob, doc.sha, doc.image_kind, doc.bytes),
                )
                id_lookup[("image", doc.blob)] = doc.doc_id
    return conn, id_lookup


def _result_to_doc_id(item: dict, id_lookup: dict[tuple[str, str], str]) -> str:
    kind = item.get("kind", "")
    if kind == "commit":
        return id_lookup.get(("commit", item.get("sha", "")), f"commit:{item.get('sha', '')}")
    if kind == "file":
        return id_lookup.get(("file", item.get("path", "")), f"file:{item.get('path', '')}")
    if kind == "image":
        return id_lookup.get(("image", item.get("blob", "")), f"image:{item.get('blob', '')}")
    return f"unknown:{item}"


def search_fts5_legacy(conn: sqlite3.Connection, query: str, limit: int = 8) -> list[dict]:
    """Pre-#16 baseline: simple FTS5 MATCH ordered by commit date / row order without BM25 or quotas."""
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)[:6]
    if not tokens:
        return []
    matcher = " AND ".join(f'"{t}"*' for t in tokens)
    out: list[dict] = []

    try:
        commits = conn.execute(
            "SELECT r.name, c.sha, c.subject "
            "FROM commit_fts f "
            "JOIN repositories r ON r.id = CAST(f.repo_id AS INTEGER) "
            "JOIN commits c ON c.repo_id = r.id AND c.sha = f.sha "
            "WHERE commit_fts MATCH ? ORDER BY c.date DESC LIMIT ?",
            (matcher, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        commits = []
    for r_name, sha, subj in commits:
        out.append({"repository": r_name, "kind": "commit", "sha": sha, "path": "", "summary": subj[:160]})

    try:
        files = conn.execute(
            "SELECT r.name, f.sha, f.path "
            "FROM change_fts f JOIN repositories r ON r.id = CAST(f.repo_id AS INTEGER) "
            "WHERE change_fts MATCH ? LIMIT ?",
            (matcher, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        files = []
    for r_name, sha, fpath in files:
        out.append({"repository": r_name, "kind": "file", "sha": sha, "path": fpath, "summary": ""})

    if len(tokens) == 1:
        pat = f"%{tokens[0].lower()}%"
        imgs = conn.execute(
            "SELECT r.name, i.commit_sha, i.path, i.blob "
            "FROM images i JOIN repositories r ON r.id = i.repo_id "
            "WHERE lower(i.path) LIKE ? LIMIT ?",
            (pat, limit),
        ).fetchall()
        for r_name, sha, ipath, blob in imgs:
            out.append({"repository": r_name, "kind": "image", "sha": sha, "path": ipath, "blob": blob, "summary": ""})

    return out[:limit]


def _char_ngram_vector(text: str, n: int = 3) -> dict[str, float]:
    norm = f" {search_expansion.normalize_text(text)} "
    vec: dict[str, float] = {}
    if len(norm) < n:
        return {norm: 1.0} if norm.strip() else {}
    for i in range(len(norm) - n + 1):
        gram = norm[i : i + n]
        vec[gram] = vec.get(gram, 0.0) + 1.0
    # Add word unigrams for hybrid lexical-dense simulation
    for tok in search_expansion.tokenize(text):
        key = f"w:{tok}"
        vec[key] = vec.get(key, 0.0) + 2.0
    norm_val = math.sqrt(sum(v * v for v in vec.values()))
    if norm_val > 0:
        for k in vec:
            vec[k] /= norm_val
    return vec


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(val * b[k] for k, val in a.items() if k in b)


class SemanticProxyIndex:
    """In-memory char-ngram + TF hybrid vector proxy simulating QMD/picoqmd dense retrieval latency & behavior."""

    def __init__(self, docs: list[BenchmarkDoc]) -> None:
        self.docs = docs
        self.vectors: list[tuple[BenchmarkDoc, dict[str, float]]] = []
        for doc in docs:
            text = f"{doc.kind} {doc.repository} {doc.path} {doc.subject}"
            self.vectors.append((doc, _char_ngram_vector(text)))

    def search(self, query: str, limit: int = 8) -> list[dict]:
        qvec = _char_ngram_vector(query)
        scored: list[tuple[float, BenchmarkDoc]] = []
        for doc, dvec in self.vectors:
            sim = _cosine(qvec, dvec)
            if sim > 0.05:
                scored.append((sim, doc))
        scored.sort(key=lambda pair: (-pair[0], pair[1].doc_id))
        results: list[dict] = []
        for sim, doc in scored[:limit]:
            results.append(
                {
                    "repository": doc.repository,
                    "kind": doc.kind,
                    "sha": doc.sha,
                    "path": doc.path,
                    "summary": doc.subject[:160],
                    "blob": doc.blob,
                    "score": round(sim, 6),
                }
            )
        return results


def estimate_tokens(payload: object) -> int:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (len(raw) + 3) // 4 if raw else 0


def compute_ir_metrics(retrieved_ids: list[str], relevant_ids: tuple[str, ...], k: int = 8) -> dict[str, float]:
    rel_set = set(relevant_ids)
    top_k = retrieved_ids[:k]
    if not rel_set:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0}
    hits = sum(1 for doc_id in top_k if doc_id in rel_set)
    precision = hits / float(k)
    recall = hits / float(len(rel_set))
    mrr = 0.0
    for rank, doc_id in enumerate(top_k, start=1):
        if doc_id in rel_set:
            mrr = 1.0 / float(rank)
            break
    return {
        "precision_at_k": round(precision, 4),
        "recall_at_k": round(recall, 4),
        "mrr": round(mrr, 4),
    }


def detect_external_tools() -> dict[str, dict]:
    """Check whether external tools (qmd, picoqmd, sentence-transformers) exist locally."""
    tools: dict[str, dict] = {}
    for cmd in ("qmd", "picoqmd"):
        proc = subprocess.run(["which", cmd], capture_output=True, text=True)
        tools[cmd] = {
            "installed": proc.returncode == 0,
            "path": proc.stdout.strip() if proc.returncode == 0 else None,
        }
    for mod in ("numpy", "sentence_transformers", "fastembed", "torch"):
        try:
            __import__(mod)
            tools[mod] = {"installed": True}
        except ImportError:
            tools[mod] = {"installed": False}
    return tools


def run_synthetic_benchmark(*, k: int = 8, repetitions: int = 5) -> dict:
    docs, queries = build_synthetic_corpus()
    with tempfile.TemporaryDirectory(prefix="search-bench-") as tmp:
        db_path = Path(tmp) / "bench.sqlite"
        conn, id_lookup = populate_synthetic_db(db_path, docs)
        db_bytes = db_path.stat().st_size

        tracemalloc.start()
        t_sem_start = time.perf_counter()
        sem_index = SemanticProxyIndex(docs)
        sem_build_ms = (time.perf_counter() - t_sem_start) * 1000.0
        _, sem_peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        strategies = {
            "fts5_legacy": lambda q: search_fts5_legacy(conn, q, limit=k),
            "fts5_bm25_16": lambda q: archive_index.search(conn, q, limit=k, expand_pt_en=False),
            "fts5_bm25_pt_en": lambda q: archive_index.search(conn, q, limit=k, expand_pt_en=True),
            "semantic_proxy_local": lambda q: sem_index.search(q, limit=k),
        }

        summary: dict[str, dict] = {}
        per_query: dict[str, list[dict]] = {}

        for name, fn in strategies.items():
            latencies_ms: list[float] = []
            precisions: list[float] = []
            recalls: list[float] = []
            mrrs: list[float] = []
            tokens_list: list[int] = []
            q_details: list[dict] = []

            for bq in queries:
                t0 = time.perf_counter()
                results: list[dict] = []
                for _ in range(repetitions):
                    results = fn(bq.query)
                elapsed_ms = ((time.perf_counter() - t0) * 1000.0) / repetitions

                retrieved_ids = [_result_to_doc_id(r, id_lookup) for r in results]
                ir = compute_ir_metrics(retrieved_ids, bq.relevant_ids, k=k)
                toks = estimate_tokens(results)

                latencies_ms.append(elapsed_ms)
                precisions.append(ir["precision_at_k"])
                recalls.append(ir["recall_at_k"])
                mrrs.append(ir["mrr"])
                tokens_list.append(toks)
                q_details.append(
                    {
                        "query_id": bq.query_id,
                        "query": bq.query,
                        "category": bq.category,
                        "retrieved_count": len(results),
                        "retrieved_ids": retrieved_ids,
                        "relevant_ids": list(bq.relevant_ids),
                        "precision_at_k": ir["precision_at_k"],
                        "recall_at_k": ir["recall_at_k"],
                        "mrr": ir["mrr"],
                        "latency_ms": round(elapsed_ms, 3),
                        "response_tokens": toks,
                    }
                )

            n_q = float(len(queries))
            summary[name] = {
                "k": k,
                "queries": len(queries),
                "mean_precision_at_k": round(sum(precisions) / n_q, 4),
                "mean_recall_at_k": round(sum(recalls) / n_q, 4),
                "mrr": round(sum(mrrs) / n_q, 4),
                "mean_latency_ms": round(sum(latencies_ms) / n_q, 3),
                "p95_latency_ms": round(sorted(latencies_ms)[min(len(latencies_ms) - 1, int(0.95 * len(latencies_ms)))], 3),
                "mean_response_tokens": round(sum(tokens_list) / n_q, 1),
            }
            per_query[name] = q_details

        conn.close()

    return {
        "mode": "synthetic_ground_truth",
        "dictionary": search_expansion.dictionary_stats(),
        "corpus": {
            "documents": len(docs),
            "queries": len(queries),
            "sqlite_bytes": db_bytes,
            "semantic_proxy_build_ms": round(sem_build_ms, 3),
            "semantic_proxy_ram_bytes": sem_peak_bytes,
        },
        "external_tools": detect_external_tools(),
        "summary": summary,
        "per_query": per_query,
    }


def run_live_db_benchmark(db_path: Path, *, limit: int = 12) -> dict:
    """Measure real-index behavior comparing FTS5+BM25 (#16) with and without PT<->EN expansion."""
    if not db_path.is_file():
        raise FileNotFoundError(f"Live SQLite DB not found: {db_path}")

    queries = [
        ("sidebar", "direct_en"),
        ("barra lateral", "cross_lingual_pt_en"),
        ("grafo", "cross_lingual_pt_en"),
        ("graph", "direct_en"),
        ("simulado", "cross_lingual_pt_en"),
        ("questao", "cross_lingual_pt_en"),
        ("prova", "cross_lingual_pt_en"),
        ("Capacities", "entity_exact"),
        ("QConcursos", "entity_exact"),
        ("fsrs", "domain_acronym"),
        ("recall", "domain_exact"),
        ("captura de tela", "cross_lingual_pt_en"),
    ]

    conn = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)
    rows: list[dict] = []
    try:
        for q, category in queries:
            t0 = time.perf_counter()
            res_base = archive_index.search(conn, q, limit=limit, expand_pt_en=False)
            ms_base = (time.perf_counter() - t0) * 1000.0

            t1 = time.perf_counter()
            res_exp = archive_index.search(conn, q, limit=limit, expand_pt_en=True)
            ms_exp = (time.perf_counter() - t1) * 1000.0

            expansion = search_expansion.expand_query(q)
            matchers_exp = expansion["fts_matchers"]
            matchers_base = archive_index._fts_matchers(re.findall(r"\w+", q, flags=re.UNICODE)[:6])

            commit_hits_base = conn.execute(
                "SELECT COUNT(*) FROM commit_fts WHERE commit_fts MATCH ?",
                (matchers_base[0],),
            ).fetchone()[0] if matchers_base else 0
            commit_hits_exp = conn.execute(
                "SELECT COUNT(*) FROM commit_fts WHERE commit_fts MATCH ?",
                (matchers_exp[0],),
            ).fetchone()[0] if matchers_exp else 0

            path_hits_base = conn.execute(
                "SELECT COUNT(DISTINCT path) FROM change_fts WHERE change_fts MATCH ?",
                (matchers_base[0],),
            ).fetchone()[0] if matchers_base else 0
            path_hits_exp = conn.execute(
                "SELECT COUNT(DISTINCT path) FROM change_fts WHERE change_fts MATCH ?",
                (matchers_exp[0],),
            ).fetchone()[0] if matchers_exp else 0

            rows.append(
                {
                    "query": q,
                    "category": category,
                    "base_returned": len(res_base),
                    "exp_returned": len(res_exp),
                    "base_latency_ms": round(ms_base, 3),
                    "exp_latency_ms": round(ms_exp, 3),
                    "base_tokens": estimate_tokens(res_base),
                    "exp_tokens": estimate_tokens(res_exp),
                    "commit_hits_base": commit_hits_base,
                    "commit_hits_exp": commit_hits_exp,
                    "distinct_path_hits_base": path_hits_base,
                    "distinct_path_hits_exp": path_hits_exp,
                    "sample_exp_paths": [r["path"] for r in res_exp if r.get("path")][:3],
                }
            )
    finally:
        conn.close()

    return {
        "mode": "live_archive_db",
        "db_path": str(db_path),
        "db_bytes": db_path.stat().st_size,
        "limit": limit,
        "queries": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=8, help="Cutoff k for precision@k / recall@k / MRR")
    parser.add_argument("--repetitions", type=int, default=5, help="Timing repetitions per query")
    parser.add_argument(
        "--live-db",
        type=Path,
        default=None,
        help="Optional path to a local archive SQLite DB (e.g. .cache/benchmark/full-index.sqlite)",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output file path")
    args = parser.parse_args()

    result = run_synthetic_benchmark(k=args.k, repetitions=args.repetitions)
    if args.live_db is not None:
        result["live_archive"] = run_live_db_benchmark(args.live_db, limit=max(args.k, 12))

    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
