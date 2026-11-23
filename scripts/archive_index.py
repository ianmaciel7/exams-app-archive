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


def search(conn:sqlite3.Connection, q:str, limit:int=8) -> list[dict]:
    tokens=re.findall(r'\w+',q,flags=re.UNICODE)[:6]
    if not tokens:
        return []
    matcher=' OR '.join('"'+t.replace('"','')+'"' for t in tokens)
    limit=max(1,min(int(limit),50))
    # Separate FTS queries keep memory use and result size bounded.
    result=[]
    for kind,query in [
        ('commit','''SELECT r.name,c.sha,c.subject FROM commit_fts f JOIN repositories r ON r.id=CAST(f.repo_id AS INTEGER) JOIN commits c ON c.repo_id=r.id AND c.sha=f.sha WHERE commit_fts MATCH ? LIMIT ?'''),
        ('file','''SELECT r.name,f.sha,f.path FROM change_fts f JOIN repositories r ON r.id=CAST(f.repo_id AS INTEGER) WHERE change_fts MATCH ? LIMIT ?''')]:
        try:
            rows=conn.execute(query,(matcher,limit)).fetchall()
        except sqlite3.OperationalError:
            rows=[]
        for repo,sha,val in rows:
            result.append({'repository':repo,'kind':kind,'sha':sha,'path':val if kind=='file' else '', 'summary':val[:160] if kind=='commit' else ''})
    return result[:limit]


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
    ap.add_argument('--db',default='reports/archive-index.sqlite')
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('ingest');p.add_argument('--repo',required=True);p.add_argument('--name',required=True)
    p=sub.add_parser('search');p.add_argument('query');p.add_argument('--limit',type=int,default=10)
    p=sub.add_parser('images');p.add_argument('--deleted-only',action='store_true');p.add_argument('--limit',type=int,default=10)
    p=sub.add_parser('recover');p.add_argument('--repo',required=True);p.add_argument('--sha',required=True);p.add_argument('--path',required=True);p.add_argument('--output',required=True)
    p=sub.add_parser('stats')
    args=ap.parse_args()
    if args.command=='recover':
        value=recover(Path(args.repo),args.sha,args.path,Path(args.output))
    else:
        conn=open_db(Path(args.db))
        if args.command=='ingest': value=ingest(Path(args.repo),args.name,conn)
        elif args.command=='search':value=search(conn,args.query,args.limit)
        elif args.command=='images':value=images(conn,args.deleted_only,args.limit)
        else:value=[dict(name=r[0],commits=conn.execute('SELECT COUNT(*) FROM commits WHERE repo_id=?',(r[1],)).fetchone()[0],images=conn.execute('SELECT COUNT(*) FROM images WHERE repo_id=?',(r[1],)).fetchone()[0]) for r in conn.execute('SELECT name,id FROM repositories')]
        conn.close()
    print(json.dumps(value,ensure_ascii=False,indent=2))


if __name__=='__main__':main()