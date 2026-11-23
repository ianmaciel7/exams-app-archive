#!/usr/bin/env python3
"""Historical Git archive index: Git remains authoritative; SQLite is rebuildable.

Standard library only. No embeddings, no model inference, no shell interpolation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

MEDIA = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}
DB_SCHEMA = '''
PRAGMA journal_mode=DELETE;
CREATE TABLE IF NOT EXISTS repositories (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, source TEXT NOT NULL, indexed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS refs (repo_id INTEGER NOT NULL, name TEXT NOT NULL, sha TEXT NOT NULL, PRIMARY KEY(repo_id,name));
CREATE TABLE IF NOT EXISTS commits (repo_id INTEGER NOT NULL, sha TEXT NOT NULL, date TEXT NOT NULL, subject TEXT NOT NULL, PRIMARY KEY(repo_id,sha));
CREATE TABLE IF NOT EXISTS changes (repo_id INTEGER NOT NULL, sha TEXT NOT NULL, status TEXT NOT NULL, path TEXT NOT NULL, previous_path TEXT NOT NULL DEFAULT '', PRIMARY KEY(repo_id,sha,status,path));
CREATE TABLE IF NOT EXISTS images (repo_id INTEGER NOT NULL, path TEXT NOT NULL, blob TEXT NOT NULL, commit_sha TEXT NOT NULL, kind TEXT NOT NULL, bytes INTEGER NOT NULL, PRIMARY KEY(repo_id,path,blob,kind));
CREATE VIRTUAL TABLE IF NOT EXISTS commit_fts USING fts5(subject, repo_id UNINDEXED, sha UNINDEXED, tokenize='unicode61');
CREATE VIRTUAL TABLE IF NOT EXISTS change_fts USING fts5(path, repo_id UNINDEXED, sha UNINDEXED, status UNINDEXED, tokenize='unicode61');
CREATE INDEX IF NOT EXISTS changes_path ON changes(repo_id,path);
CREATE INDEX IF NOT EXISTS changes_status ON changes(repo_id,status);
'''


def git(repo: Path, *args: str, binary: bool = False) -> str | bytes:
    # caller-controlled paths are never interpolated into a shell.
    result = subprocess.run(['git', f'--git-dir={repo}', *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout if binary else result.stdout.decode('utf-8', 'replace')


def git_stream(repo: Path, *args: str):
    p = subprocess.Popen(['git', f'--git-dir={repo}', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
    assert p.stdout is not None and p.stderr is not None
    try:
        for line in p.stdout:
            yield line.rstrip('\n')
        err = p.stderr.read()
    finally:
        p.stdout.close()
        p.stderr.close()
    code = p.wait()
    if code:
        raise RuntimeError(f'git returned {code}: {err[:1200]}')


def safe_ref(value: str) -> str:
    if not re.fullmatch(r'[0-9a-f]{40,64}', value):
        raise ValueError('commit SHA must be full-length hexadecimal')
    return value


def safe_path(path: str) -> str:
    parts = Path(path).parts
    if not path or path.startswith('/') or '\\' in path or '..' in parts or path.startswith('-') or '\x00' in path or ':' in path:
        raise ValueError('unsafe path')
    return path


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(DB_SCHEMA)
    return conn


def ingest(repo: Path, repo_name: str, conn: sqlite3.Connection) -> dict:
    if not repo.is_dir() or not (repo / 'HEAD').exists():
        raise ValueError(f'Expected a bare Git repository: {repo}')
    with conn:
        conn.execute('INSERT OR REPLACE INTO repositories (name,source,indexed_at) VALUES (?,?,?)',
                     (repo_name, str(repo), datetime.now(timezone.utc).isoformat()))
        repo_id = conn.execute('SELECT id FROM repositories WHERE name=?', (repo_name,)).fetchone()[0]
        for table in ('refs','commits','changes','images','commit_fts','change_fts'):
            conn.execute(f'DELETE FROM {table} WHERE repo_id=?', (repo_id,))
        refs = []
        for line in git_stream(repo,'for-each-ref','--format=%(refname)%09%(objectname)'):
            if '\t' not in line:
                continue
            name,sha = line.split('\t',1)
            refs.append((repo_id,name,sha))
        conn.executemany('INSERT INTO refs VALUES (?,?,?)', refs)
        last_sha = None
        commit_count, change_count, deleted_images = 0,0,0
        # One streaming git invocation instead of one git process per commit.
        for line in git_stream(repo,'log','--all','--root','--no-renames','--name-status', '--format=%x1e%H%x1f%aI%x1f%s'):
            if line.startswith('\x1e'):
                fields = line[1:].split('\x1f',2)
                if len(fields) != 3:
                    raise ValueError(f'Cannot parse commit: {line[:100]}')
                last_sha,date,subject = fields
                conn.execute('INSERT OR IGNORE INTO commits VALUES (?,?,?,?)',(repo_id,last_sha,date,subject))
                conn.execute('INSERT INTO commit_fts(subject,repo_id,sha) VALUES (?,?,?)',(subject,repo_id,last_sha))
                commit_count += 1
                continue
            if not last_sha or '\t' not in line:
                continue
            fields=line.split('\t')
            status=fields[0][:1]
            if status not in {'A','M','D','T','R','C'}:
                continue
            current=fields[-1]
            original=fields[1] if len(fields)>2 else ''
            if not current or current.startswith('/'):
                continue
            conn.execute('INSERT OR IGNORE INTO changes VALUES (?,?,?,?,?)', (repo_id,last_sha,status,current,original))
            conn.execute('INSERT INTO change_fts(path,repo_id,sha,status) VALUES (?,?,?,?)', (current,repo_id,last_sha,status))
            change_count+=1
            if status=='D' and Path(current).suffix.lower() in MEDIA:
                # Git stores the pre-delete blob in the first parent if available.
                try:
                    parent=git(repo,'rev-parse',last_sha+'^').strip()
                    blob=git(repo,'rev-parse',f'{parent}:{current}').strip()
                    size=int(git(repo,'cat-file','-s',blob))
                    conn.execute('INSERT OR IGNORE INTO images VALUES (?,?,?,?,?,?)', (repo_id,current,blob,parent,'deleted',size))
                    deleted_images+=1
                except (subprocess.CalledProcessError,ValueError):
                    pass
        # Catalog latest images, not duplicates from every branch and commit.
        for _rid,refname,_sha in refs:
            if not refname.startswith('refs/heads/'):
                continue
            try:
                for line in git_stream(repo,'ls-tree','-r','-l',refname):
                    # 100644 blob sha size\tpath
                    if '\t' not in line:
                        continue
                    meta,path=line.split('\t',1)
                    if Path(path).suffix.lower() not in MEDIA:
                        continue
                    fields=meta.split()
                    if len(fields)<4 or fields[1]!='blob':
                        continue
                    blob, size=fields[2],int(fields[3])
                    conn.execute('INSERT OR IGNORE INTO images VALUES (?,?,?,?,?,?)',
                                 (repo_id,path,blob,_sha,'branch-head',size))
            except (ValueError,subprocess.CalledProcessError):
                continue
    return {'repository': repo_name, 'refs':len(refs), 'commits':commit_count, 'changes':change_count, 'deleted_image_evidence':deleted_images,
            'images':conn.execute('SELECT COUNT(*) FROM images WHERE repo_id=?',(repo_id,)).fetchone()[0]}


def _fts_matchers(tokens: list[str]) -> list[str]:
    clean = [t.replace('"', '') for t in tokens if t.replace('"', '')]
    if not clean:
        return []
    prefix_terms = [f'"{t}"*' for t in clean]
    if len(clean) == 1:
        return [prefix_terms[0]]
    phrase = '"' + ' '.join(clean) + '"'
    and_expr = ' AND '.join(prefix_terms)
    or_expr = ' OR '.join(prefix_terms)
    return [f'({phrase} OR ({and_expr}))', or_expr]


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


def _query_commits(
    conn: sqlite3.Connection,
    tokens: list[str],
    repo: str | None,
    limit: int,
) -> list[dict]:
    matchers = _fts_matchers(tokens)
    if not matchers:
        return []
    for matcher in matchers:
        sql = (
            "SELECT r.name, c.sha, c.subject, c.date, bm25(commit_fts) AS rank "
            "FROM commit_fts f "
            "JOIN repositories r ON r.id = CAST(f.repo_id AS INTEGER) "
            "JOIN commits c ON c.repo_id = r.id AND c.sha = f.sha "
            "WHERE commit_fts MATCH ?"
        )
        params: list = [matcher]
        if repo:
            sql += " AND r.name = ?"
            params.append(repo)
        sql += " ORDER BY rank ASC, c.date DESC, r.name ASC, c.sha ASC LIMIT ?"
        params.append(limit)
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if rows:
            return [
                {
                    'repository': r_name,
                    'kind': 'commit',
                    'sha': sha,
                    'path': '',
                    'summary': subject[:160],
                    'rank': round(float(rank), 6),
                }
                for r_name, sha, subject, _date, rank in rows
            ]
    return []


def _date_sort_key(value: str, sha: str, *, missing_last: bool) -> tuple[str, str]:
    if not value:
        return ('9999-99-99', sha) if missing_last else ('', sha)
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is not None:
            return (dt.astimezone(timezone.utc).isoformat(), sha)
    except ValueError:
        pass
    return (value, sha)


def _query_files(
    conn: sqlite3.Connection,
    tokens: list[str],
    repo: str | None,
    limit: int,
) -> list[dict]:
    matchers = _fts_matchers(tokens)
    if not matchers:
        return []
    for matcher in matchers:
        repo_filter = (
            ' AND CAST(f.repo_id AS INTEGER) = (SELECT id FROM repositories WHERE name = ?)'
            if repo
            else ''
        )
        sql = (
            'WITH matched AS MATERIALIZED ('
            'SELECT CAST(f.repo_id AS INTEGER) AS repo_id, f.sha AS sha, f.path AS path, '
            'bm25(change_fts) AS rank '
            f'FROM change_fts f WHERE change_fts MATCH ?{repo_filter}'
            '), grouped AS ('
            'SELECT m.repo_id, r.name AS repository, m.path, '
            'MIN(m.rank) AS best_rank, COUNT(DISTINCT m.sha) AS commits '
            'FROM matched m JOIN repositories r ON r.id = m.repo_id '
            'GROUP BY m.repo_id, m.path '
            'ORDER BY best_rank ASC, commits DESC, repository ASC, m.path ASC '
            'LIMIT ?'
            ') '
            'SELECT g.repo_id, g.repository, g.path, g.best_rank, g.commits, '
            'm.sha, COALESCE(c.date, \'\') '
            'FROM grouped g '
            'JOIN matched m ON m.repo_id = g.repo_id AND m.path = g.path '
            'LEFT JOIN commits c ON c.repo_id = g.repo_id AND c.sha = m.sha '
            'ORDER BY g.best_rank ASC, g.commits DESC, g.repository ASC, g.path ASC, m.sha ASC'
        )
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
        for repo_id, repo_name, fpath, best_rank, commit_count, sha, date in rows:
            key = (repo_id, fpath)
            entry = grouped.get(key)
            fkey = _date_sort_key(date, sha, missing_last=True)
            lkey = _date_sort_key(date, sha, missing_last=False)
            if entry is None:
                grouped[key] = {
                    'repository': repo_name,
                    'path': fpath,
                    'best_rank': float(best_rank),
                    'commits': int(commit_count),
                    'first_key': fkey,
                    'first_sha': sha,
                    'last_key': lkey,
                    'last_sha': sha,
                }
            else:
                if fkey < entry['first_key']:
                    entry['first_key'] = fkey
                    entry['first_sha'] = sha
                if lkey > entry['last_key']:
                    entry['last_key'] = lkey
                    entry['last_sha'] = sha

        return [
            {
                'repository': e['repository'],
                'kind': 'file',
                'sha': e['last_sha'],
                'path': e['path'],
                'summary': '',
                'commits': e['commits'],
                'first_sha': e['first_sha'],
                'last_sha': e['last_sha'],
                'rank': round(e['best_rank'], 6),
            }
            for e in grouped.values()
        ]
    return []


def _query_images(
    conn: sqlite3.Connection,
    tokens: list[str],
    repo: str | None,
    limit: int,
) -> list[dict]:
    if not tokens:
        return []
    lowered = [t.lower() for t in tokens]
    escaped = [
        '%' + t.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        for t in lowered
    ]
    if len(escaped) == 1:
        attempts = [(' OR ', escaped)]
    else:
        attempts = [(' AND ', escaped), (' OR ', escaped)]

    for joiner, patterns in attempts:
        sql = (
            "SELECT r.name, i.path, i.blob, i.commit_sha, i.kind, i.bytes "
            "FROM images i JOIN repositories r ON r.id = i.repo_id WHERE ("
            + joiner.join("lower(i.path) LIKE ? ESCAPE '\\'" for _ in patterns)
            + ")"
        )
        params: list = list(patterns)
        if repo:
            sql += " AND r.name = ?"
            params.append(repo)
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows:
            continue

        deduped: dict[str, dict] = {}
        for repo_name, ipath, blob, commit_sha, ikind, ibytes in rows:
            low_path = ipath.lower()
            basename = Path(low_path).name
            tok_hits = sum(1 for t in lowered if t in low_path)
            base_hits = sum(1 for t in lowered if t in basename)
            deleted_flag = 1 if ikind == 'deleted' else 0
            # Lower score tuple is better (mirrors bm25 ascending convention).
            score_key = (-base_hits, -tok_hits, -deleted_flag, -int(ibytes), repo_name, ipath)
            existing = deduped.get(blob)
            if existing is None or score_key < existing['score_key']:
                deduped[blob] = {
                    'repository': repo_name,
                    'kind': 'image',
                    'sha': commit_sha,
                    'path': ipath,
                    'summary': ikind,
                    'blob': blob,
                    'bytes': int(ibytes),
                    'deleted': deleted_flag,
                    'score_key': score_key,
                    'occurrences': (existing['occurrences'] + 1) if existing else 1,
                }
            else:
                existing['occurrences'] += 1

        ranked = sorted(deduped.values(), key=lambda e: e['score_key'])[:limit]
        for item in ranked:
            item.pop('score_key', None)
        return ranked
    return []


def search(
    conn: sqlite3.Connection,
    q: str,
    limit: int = 8,
    *,
    kind: str = 'all',
    repo: str | None = None,
) -> list[dict]:
    tokens = re.findall(r'\w+', q, flags=re.UNICODE)[:6]
    if not tokens:
        return []
    limit = max(1, min(int(limit), 100))
    kinds = ('commit', 'file', 'image') if kind == 'all' else (kind,)
    buckets: dict[str, list[dict]] = {}
    for current in kinds:
        if current == 'commit':
            buckets['commit'] = _query_commits(conn, tokens, repo, limit)
        elif current == 'file':
            buckets['file'] = _query_files(conn, tokens, repo, limit)
        elif current == 'image':
            buckets['image'] = _query_images(conn, tokens, repo, limit)
    if len(kinds) == 1:
        return buckets.get(kinds[0], [])[:limit]
    return _interleave_by_kind(buckets, kinds, limit)


def images(conn:sqlite3.Connection, deleted_only:bool=False,limit:int=10)->list[dict]:
    sql='''SELECT r.name,i.path,i.blob,i.commit_sha,i.kind,i.bytes FROM images i JOIN repositories r ON r.id=i.repo_id'''
    if deleted_only:
        sql+=" WHERE i.kind='deleted'"
    sql+=' ORDER BY i.kind DESC, i.bytes DESC LIMIT ?'
    return [dict(zip(['repository','path','blob','commit_sha','kind','bytes'],row)) for row in conn.execute(sql,(limit,))]


def recover(repo:Path, sha:str,path:str,out:Path)->dict:
    sha=safe_ref(sha);path=safe_path(path)
    # git show works for text and binary, including paths absent at HEAD.
    content=git(repo,'show',f'{sha}:{path}',binary=True)
    if out.exists():
        raise FileExistsError(f'Destination exists: {out}')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(content)
    return {'commit':sha,'path':path,'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest(),'output':str(out)}


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db',default='.cache/archive/archive-index.sqlite')
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('ingest');p.add_argument('--repo',required=True);p.add_argument('--name',required=True)
    p=sub.add_parser('search');p.add_argument('query');p.add_argument('--repo');p.add_argument('--kind',choices=('all','commit','file','image'),default='all');p.add_argument('--limit',type=int,default=10)
    p=sub.add_parser('images');p.add_argument('--deleted-only',action='store_true');p.add_argument('--limit',type=int,default=10)
    p=sub.add_parser('recover');p.add_argument('--repo',required=True);p.add_argument('--sha',required=True);p.add_argument('--path',required=True);p.add_argument('--output',required=True)
    p=sub.add_parser('stats')
    args=ap.parse_args()
    if args.command=='recover':
        value=recover(Path(args.repo),args.sha,args.path,Path(args.output))
    else:
        conn=open_db(Path(args.db))
        if args.command=='ingest': value=ingest(Path(args.repo),args.name,conn)
        elif args.command=='search':value=search(conn,args.query,args.limit,kind=args.kind,repo=args.repo)
        elif args.command=='images':value=images(conn,args.deleted_only,args.limit)
        else:value=[dict(name=r[0],commits=conn.execute('SELECT COUNT(*) FROM commits WHERE repo_id=?',(r[1],)).fetchone()[0],images=conn.execute('SELECT COUNT(*) FROM images WHERE repo_id=?',(r[1],)).fetchone()[0]) for r in conn.execute('SELECT name,id FROM repositories')]
        conn.close()
    print(json.dumps(value,ensure_ascii=False,indent=2))


if __name__=='__main__':main()