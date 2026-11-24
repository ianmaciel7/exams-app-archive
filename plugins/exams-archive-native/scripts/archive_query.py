#!/usr/bin/env python3
"""Read-only, authenticated local search of Exams App archive (stdlib only)."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ARCHIVE = "ianmaciel7/exams-app-archive"
REPORT_PATH = "reports/FULL-INDEX.json"
DEFAULT_TAG = "index-2026-11-23-exams-complete"
CACHE = Path.home() / ".cache" / "exams-app-archive"
DEFAULT_DB = CACHE / "full-index.sqlite"
DEFAULT_GRAPH_DB = CACHE / "graph-linker.sqlite"
DEFAULT_CONTEXT_DB = CACHE / "context-linker.sqlite"
COLUMNS = ("repository", "kind", "sha", "path", "summary", "blob", "bytes", "deleted")


def run(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, check=True).stdout
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing executable: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{cmd[0]} exited with {exc.returncode}: {exc.stderr.strip()[:400]}") from exc


def read_db(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise RuntimeError(f"Index not found: {path}. Run 'sync' first.")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def sync(path: Path, force: bool = False) -> dict:
    if path.exists() and not force:
        with read_db(path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM repositories").fetchone()[0]
        return {"index": str(path), "sources": count, "cached": True}
    report = json.loads(run("gh", "api", "-H", "Accept: application/vnd.github.raw",
                            f"repos/{ARCHIVE}/contents/{REPORT_PATH}"))
    tag, expected = report.get("release_tag", DEFAULT_TAG), report.get("gzip_sha256")
    if not isinstance(tag, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", tag):
        raise RuntimeError("Invalid release tag")
    if not isinstance(expected, str) or not re.fullmatch("[0-9a-f]{64}", expected):
        raise RuntimeError("Archive checksum missing or invalid")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="archive-", dir=path.parent) as temp:
        folder = Path(temp)
        run("gh", "release", "download", tag, "--repo", ARCHIVE,
            "--pattern", "full-index.sqlite.gz", "--dir", str(folder))
        packed = folder / "full-index.sqlite.gz"
        actual = hashlib.sha256(packed.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError("Archive checksum mismatch; index was not installed")
        unpacked = folder / "full-index.sqlite"
        with gzip.open(packed, "rb") as src, unpacked.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        with read_db(unpacked) as conn:
            check = conn.execute("PRAGMA quick_check").fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM repositories").fetchone()[0]
        if check != "ok" or not count:
            raise RuntimeError("Downloaded SQLite failed integrity check")
        os.replace(unpacked, path)
    return {"index": str(path), "release": tag, "sources": count, "sha256_gzip": actual, "cached": False}


def _fts_matchers(tokens: list[str]) -> list[str]:
    clean = [t.replace('"', "") for t in tokens if t.replace('"', "")]
    if not clean:
        return []
    prefix_terms = [f'"{t}"*' for t in clean]
    if len(clean) == 1:
        return [prefix_terms[0]]
    phrase = '"' + " ".join(clean) + '"'
    and_expr = " AND ".join(prefix_terms)
    or_expr = " OR ".join(prefix_terms)
    return [f"({phrase} OR ({and_expr}))", or_expr]


def _type_quotas(limit: int, kinds: tuple[str, ...]) -> dict[str, int]:
    n = len(kinds)
    base, rem = divmod(limit, n)
    return {k: base + (1 if i < rem else 0) for i, k in enumerate(kinds)}


def _interleave_by_kind(buckets: dict[str, list[dict]], kinds: tuple[str, ...], limit: int) -> list[dict]:
    quotas = _type_quotas(limit, kinds)
    selected: list[dict] = []
    positions: dict[str, int] = {k: 0 for k in kinds}

    for k in kinds:
        rows = buckets.get(k, [])
        take = min(quotas[k], len(rows))
        selected.extend(rows[:take])
        positions[k] = take

    if len(selected) < limit:
        progressed = True
        while len(selected) < limit and progressed:
            progressed = False
            for k in kinds:
                rows = buckets.get(k, [])
                idx = positions[k]
                if idx < len(rows):
                    selected.append(rows[idx])
                    positions[k] = idx + 1
                    progressed = True
                    if len(selected) >= limit:
                        break
    return selected[:limit]


def _query_commits(conn: sqlite3.Connection, tokens: list[str],
                   repo: str | None, limit: int) -> list[dict]:
    matchers = _fts_matchers(tokens)
    if not matchers:
        return []
    for matcher in matchers:
        sql = """SELECT r.name AS repository,'commit' AS kind,c.sha AS sha,'' AS path,
                 c.subject AS summary,'' AS blob,0 AS bytes,0 AS deleted,
                 c.date AS commit_date,bm25(commit_fts) AS rank
                 FROM commit_fts f JOIN repositories r ON r.id=CAST(f.repo_id AS INTEGER)
                 JOIN commits c ON c.repo_id=r.id AND c.sha=f.sha
                 WHERE commit_fts MATCH ?"""
        params: list = [matcher]
        if repo:
            sql += " AND r.name=?"
            params.append(repo)
        sql += " ORDER BY rank ASC, c.date DESC, r.name ASC, c.sha ASC LIMIT ?"
        params.append(limit)
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if rows:
            out: list[dict] = []
            for row in rows:
                item = dict(row)
                item.pop("commit_date", None)
                item["rank"] = round(float(item["rank"]), 6)
                out.append(item)
            return out
    return []


def _date_sort_key(value: str, sha: str, *, missing_last: bool) -> tuple[str, str]:
    if not value:
        return ("9999-99-99", sha) if missing_last else ("", sha)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            return (dt.astimezone(timezone.utc).isoformat(), sha)
    except ValueError:
        pass
    return (value, sha)


def _query_files(conn: sqlite3.Connection, tokens: list[str],
                 repo: str | None, limit: int) -> list[dict]:
    matchers = _fts_matchers(tokens)
    if not matchers:
        return []
    for matcher in matchers:
        repo_filter = (
            " AND CAST(f.repo_id AS INTEGER) = (SELECT id FROM repositories WHERE name=?)"
            if repo
            else ""
        )
        sql = f"""WITH matched AS MATERIALIZED (
                      SELECT CAST(f.repo_id AS INTEGER) AS repo_id, f.sha AS sha,
                             f.path AS path, bm25(change_fts) AS rank
                      FROM change_fts f
                      WHERE change_fts MATCH ?{repo_filter}
                  ),
                  grouped AS (
                      SELECT m.repo_id, r.name AS repository, m.path,
                             MIN(m.rank) AS best_rank, COUNT(DISTINCT m.sha) AS commits
                      FROM matched m JOIN repositories r ON r.id=m.repo_id
                      GROUP BY m.repo_id, m.path
                      ORDER BY best_rank ASC, commits DESC, repository ASC, m.path ASC
                      LIMIT ?
                  )
                  SELECT g.repo_id AS repo_id, g.repository AS repository, g.path AS path,
                         g.best_rank AS best_rank, g.commits AS commits,
                         m.sha AS sha, COALESCE(c.date,'') AS commit_date
                  FROM grouped g
                  JOIN matched m ON m.repo_id=g.repo_id AND m.path=g.path
                  LEFT JOIN commits c ON c.repo_id=g.repo_id AND c.sha=m.sha
                  ORDER BY g.best_rank ASC, g.commits DESC, g.repository ASC, g.path ASC, m.sha ASC"""
        params: list = [matcher]
        if repo:
            params.append(repo)
        params.append(limit)
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows:
            continue

        grouped: dict[tuple[int, str], dict] = {}
        for row in rows:
            repo_id = row["repo_id"]
            repo_name = row["repository"]
            fpath = row["path"]
            best_rank = float(row["best_rank"])
            commit_count = int(row["commits"])
            sha = row["sha"]
            cdate = row["commit_date"]
            key = (repo_id, fpath)
            fkey = _date_sort_key(cdate, sha, missing_last=True)
            lkey = _date_sort_key(cdate, sha, missing_last=False)
            entry = grouped.get(key)
            if entry is None:
                grouped[key] = {
                    "repository": repo_name,
                    "path": fpath,
                    "best_rank": best_rank,
                    "commits": commit_count,
                    "first_key": fkey,
                    "first_sha": sha,
                    "last_key": lkey,
                    "last_sha": sha,
                }
            else:
                if fkey < entry["first_key"]:
                    entry["first_key"] = fkey
                    entry["first_sha"] = sha
                if lkey > entry["last_key"]:
                    entry["last_key"] = lkey
                    entry["last_sha"] = sha

        return [
            {
                "repository": e["repository"],
                "kind": "file",
                "sha": e["last_sha"],
                "path": e["path"],
                "summary": "",
                "blob": "",
                "bytes": 0,
                "deleted": 0,
                "commits": e["commits"],
                "first_sha": e["first_sha"],
                "last_sha": e["last_sha"],
                "rank": round(e["best_rank"], 6),
            }
            for e in grouped.values()
        ]
    return []


def _query_images(conn: sqlite3.Connection, tokens: list[str],
                  repo: str | None, limit: int) -> list[dict]:
    if not tokens:
        return []
    lowered = [t.lower() for t in tokens]
    escaped = [
        "%" + t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        for t in lowered
    ]
    attempts = [(" OR ", escaped)] if len(escaped) == 1 else [(" AND ", escaped), (" OR ", escaped)]
    for joiner, patterns in attempts:
        sql = """SELECT r.name AS repository,i.path AS path,i.blob AS blob,
                 i.commit_sha AS sha,i.kind AS ikind,i.bytes AS bytes
                 FROM images i JOIN repositories r ON r.id=i.repo_id WHERE (""" + (
            joiner.join("lower(i.path) LIKE ? ESCAPE '\\'" for _ in patterns)
        ) + ")"
        params: list = list(patterns)
        if repo:
            sql += " AND r.name=?"
            params.append(repo)
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows:
            continue

        deduped: dict[str, dict] = {}
        for row in rows:
            repo_name = row["repository"]
            ipath = row["path"]
            blob = row["blob"]
            commit_sha = row["sha"]
            ikind = row["ikind"]
            ibytes = int(row["bytes"])
            low_path = ipath.lower()
            basename = Path(low_path).name
            tok_hits = sum(1 for t in lowered if t in low_path)
            base_hits = sum(1 for t in lowered if t in basename)
            deleted_flag = 1 if ikind == "deleted" else 0
            score_key = (-base_hits, -tok_hits, -deleted_flag, -ibytes, repo_name, ipath)
            existing = deduped.get(blob)
            if existing is None or score_key < existing["score_key"]:
                deduped[blob] = {
                    "repository": repo_name,
                    "kind": "image",
                    "sha": commit_sha,
                    "path": ipath,
                    "summary": ikind,
                    "blob": blob,
                    "bytes": ibytes,
                    "deleted": deleted_flag,
                    "score_key": score_key,
                    "occurrences": (existing["occurrences"] + 1) if existing else 1,
                }
            else:
                existing["occurrences"] += 1

        ranked = sorted(deduped.values(), key=lambda e: e["score_key"])[:limit]
        for item in ranked:
            item.pop("score_key", None)
        return ranked
    return []


def build_results(conn: sqlite3.Connection, query: str, repo: str | None,
                  kind: str, limit: int) -> list[dict]:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)[:6]
    if not tokens:
        return []
    limit = max(1, min(int(limit), 100))
    kinds = ("commit", "file", "image") if kind == "all" else (kind,)
    buckets: dict[str, list[dict]] = {}
    for current in kinds:
        if current == "commit":
            buckets["commit"] = _query_commits(conn, tokens, repo, limit)
        elif current == "file":
            buckets["file"] = _query_files(conn, tokens, repo, limit)
        else:
            buckets["image"] = _query_images(conn, tokens, repo, limit)
    if len(kinds) == 1:
        return buckets.get(kinds[0], [])[:limit]
    return _interleave_by_kind(buckets, kinds, limit)


def list_images(conn: sqlite3.Connection, repo: str | None,
                deleted_only: bool, limit: int) -> list[dict]:
    sql = """SELECT r.name AS repository,'image' AS kind,i.commit_sha AS sha,i.path AS path,
             i.kind AS summary,i.blob AS blob,i.bytes AS bytes,(i.kind='deleted') AS deleted
             FROM images i JOIN repositories r ON r.id=i.repo_id WHERE 1=1"""
    params: list = []
    if repo:
        sql += " AND r.name=?"
        params.append(repo)
    if deleted_only:
        sql += " AND i.kind='deleted'"
    sql += " ORDER BY i.bytes DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


def export_pages(conn: sqlite3.Connection, destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    queries = [
        """SELECT r.name AS repository,'commit' AS kind,c.sha AS sha,'' AS path,
           c.subject AS summary,'' AS blob,0 AS bytes,0 AS deleted
           FROM commits c JOIN repositories r ON r.id=c.repo_id""",
        """SELECT r.name AS repository,'file' AS kind,x.sha AS sha,x.path AS path,
           '' AS summary,'' AS blob,0 AS bytes,(x.status='D') AS deleted
           FROM changes x JOIN repositories r ON r.id=x.repo_id""",
        """SELECT r.name AS repository,'image' AS kind,i.commit_sha AS sha,i.path AS path,
           i.kind AS summary,i.blob AS blob,i.bytes AS bytes,(i.kind='deleted') AS deleted
           FROM images i JOIN repositories r ON r.id=i.repo_id"""
    ]
    count = 0
    output_stream = destination.open("x", encoding="utf-8")
    try:
        with output_stream as out:
            out.write(json.dumps({"version": 1, "generated_at": datetime.now(timezone.utc).isoformat()})[:-1])
            out.write(',"records":[')
            for query in queries:
                for row in conn.execute(query):
                    if count:
                        out.write(",")
                    out.write(json.dumps(dict(row), ensure_ascii=False, separators=(",", ":")))
                    count += 1
            out.write("]}\n")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"output": str(destination), "records": count, "private": True}


def recover(bare: Path, sha: str, path: str, output: Path) -> dict:
    if not re.fullmatch("[0-9a-f]{40,64}", sha):
        raise ValueError("A full commit SHA is required")
    if not path or path.startswith(("/", "-")) or "\\" in path or ":" in path or \
            ".." in Path(path).parts or "\0" in path:
        raise ValueError("Unsafe historical path")
    if not (bare / "HEAD").is_file():
        raise ValueError("Use the path to a bare Git mirror of the downloaded bundle")
    output.parent.mkdir(parents=True, exist_ok=True)
    output_stream = output.open("xb")
    try:
        with output_stream as target:
            subprocess.run(["git", f"--git-dir={bare}", "show", f"{sha}:{path}"],
                           stdout=target, stderr=subprocess.PIPE, check=True)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {"output": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "bytes": output.stat().st_size, "sha": sha, "path": path}


def _find_scripts_dir() -> Path:
    """Locate the repository scripts/ directory containing core integration modules."""
    here = Path(__file__).resolve()
    env_root = os.environ.get("EXAMS_ARCHIVE_ROOT")
    candidates: list[Path] = []
    if env_root:
        candidates.append(Path(env_root) / "scripts")
    for parent in here.parents:
        candidates.append(parent / "scripts")
    candidates.append(Path.cwd() / "scripts")
    for candidate in candidates:
        if (candidate / "ast_chunker.py").is_file():
            return candidate
    raise RuntimeError(
        "Core archive scripts directory not found. Run inside the exams-app-archive "
        "repository or set EXAMS_ARCHIVE_ROOT."
    )


def _load_core_module(name: str):
    scripts_dir = _find_scripts_dir()
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    return importlib.import_module(name)


def run_ast_command(path: Path, lang: str | None = None, summary_only: bool = False) -> dict:
    if not path.is_file():
        raise RuntimeError(f"Source file not found: {path}")
    ast_chunker = _load_core_module("ast_chunker")
    text = path.read_text(encoding="utf-8", errors="replace")
    effective_lang = lang or path.suffix.lower() or "text"
    chunks = ast_chunker.chunk_code(text, language=effective_lang)
    motion_contracts = [m.to_dict() for c in chunks for m in c.motion_contracts]
    payload: dict = {
        "path": str(path),
        "language": ast_chunker.normalize_language(effective_lang),
        "extractor_version": ast_chunker.EXTRACTOR_VERSION,
        "blob_sha": ast_chunker.compute_git_blob_sha(text.replace("\r\n", "\n").replace("\r", "\n")),
        "chunk_count": len(chunks),
        "motion_contract_count": len(motion_contracts),
    }
    if summary_only:
        payload["chunks"] = [
            {
                "chunk_index": c.chunk_index,
                "node_type": c.node_type,
                "name": c.name,
                "parent_context": c.parent_context,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "symbol_id": c.symbol_id,
                "status": c.status,
                "motion_contracts": [m.to_dict() for m in c.motion_contracts],
            }
            for c in chunks
        ]
    else:
        payload["chunks"] = [c.to_dict() for c in chunks]
    return payload


def run_graph_command(
    *,
    entity: str | None = None,
    graph_db: Path = DEFAULT_GRAPH_DB,
    inventory_dir: Path | None = None,
    archive_db: Path | None = None,
    hops: int = 2,
    repo: str | None = None,
    since: str | None = None,
    until: str | None = None,
    confidence: str | None = None,
    limit: int = 50,
    stats_only: bool = False,
) -> dict:
    graph_linker = _load_core_module("graph_linker")
    if not graph_db.exists() and not inventory_dir and not archive_db:
        raise RuntimeError(
            f"Graph DB not found: {graph_db}. Pass --inventory-dir, --archive-db, or --graph-db."
        )
    conn = graph_linker.open_db(graph_db)
    try:
        build_info: dict = {}
        if inventory_dir is not None:
            if not inventory_dir.is_dir():
                raise RuntimeError(f"Inventory directory not found: {inventory_dir}")
            exams_inv = inventory_dir / "exams-app-branch-files.json"
            notes_inv = inventory_dir / "notes-app"
            if exams_inv.is_file():
                build_info["exams_app"] = graph_linker.ingest_branch_inventory(
                    conn, exams_inv, repo_override="exams-app"
                )
            if notes_inv.is_dir():
                build_info["notes_app"] = graph_linker.ingest_notes_platform_inventory(
                    conn, notes_inv, repo_name="notes-app"
                )
            build_info["supersedes_edges"] = graph_linker.link_temporal_supersession(conn)
        if archive_db is not None:
            if not archive_db.is_file():
                raise RuntimeError(f"Archive SQLite not found: {archive_db}")
            build_info["archive_ingest"] = graph_linker.ingest_archive_sqlite(conn, archive_db)
            build_info["supersedes_edges"] = graph_linker.link_temporal_supersession(conn)

        if stats_only or not entity:
            out = graph_linker.graph_stats(conn)
            if build_info:
                out["build"] = build_info
            return out

        out = graph_linker.query_neighborhood(
            conn,
            entity,
            hops=hops,
            repo=repo,
            since=since,
            until=until,
            confidence=confidence,
            limit=max(1, min(int(limit), 500)),
        )
        if build_info:
            out["build"] = build_info
        return out
    finally:
        conn.close()


def run_context_command(
    *,
    query: str | None = None,
    context_db: Path = DEFAULT_CONTEXT_DB,
    inventory_dir: Path | None = None,
    git_source: Path | None = None,
    repo: str | None = None,
    limit: int = 20,
    stats_only: bool = False,
) -> dict:
    context_linker = _load_core_module("context_linker")
    if not context_db.exists() and not inventory_dir and not git_source:
        raise RuntimeError(
            f"Context DB not found: {context_db}. Pass --inventory-dir, --git-source, or --context-db."
        )
    conn = context_linker.open_db(context_db)
    try:
        build_info: dict = {}
        if inventory_dir is not None:
            if not inventory_dir.is_dir():
                raise RuntimeError(f"Inventory directory not found: {inventory_dir}")
            build_info["inventory"] = context_linker.import_inventory(
                inventory_dir, conn, repo_override=repo
            )
        if git_source is not None:
            if not repo:
                raise RuntimeError("--repo is required when using --git-source")
            build_info["git"] = context_linker.ingest_git_repo(git_source, repo, conn)

        if stats_only or not query:
            out = {
                "sources": conn.execute("SELECT COUNT(*) FROM ctx_sources").fetchone()[0],
                "items": conn.execute("SELECT COUNT(*) FROM ctx_items").fetchone()[0],
                "commits": conn.execute("SELECT COUNT(*) FROM ctx_commits").fetchone()[0],
                "commit_files": conn.execute("SELECT COUNT(*) FROM ctx_commit_files").fetchone()[0],
                "comments": conn.execute("SELECT COUNT(*) FROM ctx_comments").fetchone()[0],
                "events": conn.execute("SELECT COUNT(*) FROM ctx_events").fetchone()[0],
                "images": conn.execute("SELECT COUNT(*) FROM ctx_images").fetchone()[0],
                "links": conn.execute("SELECT COUNT(*) FROM ctx_links").fetchone()[0],
                "releases": conn.execute("SELECT COUNT(*) FROM ctx_releases").fetchone()[0],
                "workflow_runs": conn.execute("SELECT COUNT(*) FROM ctx_workflow_runs").fetchone()[0],
                "gaps": conn.execute("SELECT COUNT(*) FROM ctx_gaps").fetchone()[0],
            }
            if build_info:
                out["build"] = build_info
            return out

        out = context_linker.query_history(
            conn,
            query,
            repo=repo,
            limit=max(1, min(int(limit), 100)),
        )
        if build_info:
            out["build"] = build_info
        return out
    finally:
        conn.close()


def run_secrets_check_command(
    target: Path,
    *,
    allowlist: Path | None = None,
    use_gitleaks: bool = False,
) -> dict:
    secrets_gate = _load_core_module("secrets_gate")
    if not target.exists():
        raise RuntimeError(f"Secrets check target does not exist: {target}")
    gate_allowlist = secrets_gate._load_allowlist(allowlist) if allowlist else None
    return secrets_gate.scan_target(target, allowlist=gate_allowlist, use_gitleaks=use_gitleaks)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "components":
        _load_core_module("component_catalog").main(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("components", help="Reviewed component previews, capture and screenshot catalog")
    p = sub.add_parser("sync", help="Download and verify private release index")
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--repo")
    p.add_argument("--kind", choices=("all", "file", "commit", "image"), default="all")
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("images")
    p.add_argument("--repo")
    p.add_argument("--deleted-only", action="store_true")
    p.add_argument("--limit", type=int, default=20)
    sub.add_parser("stats")
    p = sub.add_parser("export-pages")
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("recover")
    p.add_argument("--git-dir", type=Path, required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--output", type=Path, required=True)

    p_ast = sub.add_parser("ast", help="Extract structural AST chunks and motion contracts")
    p_ast.add_argument("path", type=Path)
    p_ast.add_argument("--lang", default=None)
    p_ast.add_argument("--summary-only", action="store_true")

    p_graph = sub.add_parser("graph", help="Query or build multi-repo relation graph")
    p_graph.add_argument("entity", nargs="?", default=None)
    p_graph.add_argument("--graph-db", type=Path, default=DEFAULT_GRAPH_DB)
    p_graph.add_argument("--inventory-dir", type=Path, default=None)
    p_graph.add_argument("--archive-db", type=Path, default=None)
    p_graph.add_argument("--hops", type=int, default=2)
    p_graph.add_argument("--repo", default=None)
    p_graph.add_argument("--since", default=None)
    p_graph.add_argument("--until", default=None)
    p_graph.add_argument("--confidence", choices=("EXTRACTED", "INFERRED"), default=None)
    p_graph.add_argument("--limit", type=int, default=50)
    p_graph.add_argument("--stats", action="store_true")

    p_ctx = sub.add_parser("context", help="Query chronological file/PR/review/image context")
    p_ctx.add_argument("query", nargs="?", default=None)
    p_ctx.add_argument("--context-db", type=Path, default=DEFAULT_CONTEXT_DB)
    p_ctx.add_argument("--inventory-dir", type=Path, default=None)
    p_ctx.add_argument("--git-source", type=Path, default=None)
    p_ctx.add_argument("--repo", default=None)
    p_ctx.add_argument("--limit", type=int, default=20)
    p_ctx.add_argument("--stats", action="store_true")

    p_sec = sub.add_parser("secrets-check", help="Scan file, directory, SQLite, JSON, or Git bundle for secrets")
    p_sec.add_argument("target", type=Path)
    p_sec.add_argument("--allowlist", type=Path, default=None)
    p_sec.add_argument("--use-gitleaks", action="store_true")

    args = parser.parse_args()
    exit_code = 0
    if args.command == "sync":
        result = sync(args.db, args.force)
    elif args.command == "recover":
        result = recover(args.git_dir, args.sha, args.path, args.output)
    elif args.command == "ast":
        result = run_ast_command(args.path, lang=args.lang, summary_only=args.summary_only)
    elif args.command == "graph":
        result = run_graph_command(
            entity=args.entity,
            graph_db=args.graph_db,
            inventory_dir=args.inventory_dir,
            archive_db=args.archive_db,
            hops=args.hops,
            repo=args.repo,
            since=args.since,
            until=args.until,
            confidence=args.confidence,
            limit=args.limit,
            stats_only=args.stats,
        )
    elif args.command == "context":
        result = run_context_command(
            query=args.query,
            context_db=args.context_db,
            inventory_dir=args.inventory_dir,
            git_source=args.git_source,
            repo=args.repo,
            limit=args.limit,
            stats_only=args.stats,
        )
    elif args.command == "secrets-check":
        result = run_secrets_check_command(
            args.target,
            allowlist=args.allowlist,
            use_gitleaks=args.use_gitleaks,
        )
        if result.get("blocked"):
            exit_code = 2
    else:
        with read_db(args.db) as conn:
            if args.command == "search":
                result = build_results(conn, args.query, args.repo, args.kind,
                                       max(1, min(args.limit, 100)))
            elif args.command == "images":
                result = list_images(conn, args.repo, args.deleted_only, max(1, min(args.limit, 100)))
            elif args.command == "stats":
                result = [dict(row) for row in conn.execute(
                    """SELECT r.name AS repository,COUNT(DISTINCT c.sha) AS commits
                       FROM repositories r LEFT JOIN commits c ON c.repo_id=r.id
                       GROUP BY r.id ORDER BY r.name""")]
            else:
                result = export_pages(conn, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if exit_code:
        sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, FileExistsError, sqlite3.Error, OSError,
            subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
