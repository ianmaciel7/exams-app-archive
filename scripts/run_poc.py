#!/usr/bin/env python3
"""Real Git source proof: clone public history, index, query, restore removed image.

Archives only metadata and a rebuildable SQLite file. Source Git objects remain
in the original repos; Git bundles are verified but not republished by this POC.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from archive_index import git, ingest, images, open_db, recover, search

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache' / 'poc'
REPORTS = ROOT / 'reports'
REPOS = ['exams-app-old', 'exams-app-antigo-2']
BUNDLE_REF = 'refs/heads/dev'
BUNDLE_PATH = 'prototype/notes-app-old-10.bundle'
OWNER = 'ianmaciel7'


def execute(*args: str, out: Path | None = None, timeout: int = 900) -> str:
    with (out.open('wb') if out else open(os.devnull, 'wb')) as sink:
        p = subprocess.run(args, stdout=sink, stderr=subprocess.PIPE, timeout=timeout)
    if p.returncode:
        raise RuntimeError(' '.join(args[:3]) + ' failed: ' + p.stderr.decode('utf-8','replace')[-1500:])
    return p.stderr.decode('utf-8','replace')


def checkout_public(name: str) -> Path:
    path = CACHE / (name + '.git')
    if not path.exists():
        execute('git','clone','--mirror','--quiet',f'https://github.com/{OWNER}/{name}.git',str(path))
    return path


def historical_bundle(src: Path) -> tuple[Path | None,dict]:
    temp = CACHE / 'notes-app-old-10.bundle'
    output = {'bundle':BUNDLE_PATH, 'source_repo':'exams-app-antigo-2', 'validated':False}
    try:
        cmd=['git',f'--git-dir={src}','show',f'{BUNDLE_REF}:{BUNDLE_PATH}']
        execute(*cmd,out=temp)
        output['size_bytes']=temp.stat().st_size
        output['sha256']=hashlib.sha256(temp.read_bytes()).hexdigest()
        init = CACHE / 'verify.git'
        if not init.exists():
            execute('git','init','--bare','--quiet',str(init))
        execute('git',f'--git-dir={init}','bundle','verify',str(temp))
        destination=CACHE/'notes-app-old-10.git'
        if not destination.exists():
            execute('git','clone','--mirror','--quiet',str(temp),str(destination))
        output['validated']=True
        output['heads']=git(destination,'for-each-ref','--format=%(refname)').splitlines()[:12]
        return destination,output
    except Exception as exc:
        output['error']=str(exc)[:500]
        return None,output


def sample_recovery(conn: sqlite3.Connection, sources: dict[str,Path]) -> dict:
    candidates=images(conn,deleted_only=True,limit=80)
    for item in candidates:
        if item['repository'] not in sources:
            continue
        dest = CACHE / 'retrieved-historical-media' / (hashlib.sha256((item['path']+item['blob']).encode()).hexdigest()[:16] + Path(item['path']).suffix)
        if dest.exists():
            dest.unlink()
        try:
            proof=recover(sources[item['repository']],item['commit_sha'],item['path'],dest)
            computed=git(sources[item['repository']],'hash-object',str(dest)).strip()
            # hash-object agrees with the SHA recorded by the original Git object.
            if computed != item['blob']:
                raise AssertionError(f'Git blob hash mismatch: {computed} != {item["blob"]}')
            proof.update({'repository':item['repository'],'git_blob_sha':item['blob'],'verified':True})
            # POC does not persist historical binary into GitHub automatically.
            dest.unlink()
            return proof
        except (subprocess.CalledProcessError,ValueError,OSError):
            continue
    return {'verified':False,'error':'No deleted image recoverable among top 80 indexed candidates'}


def sample_code(conn: sqlite3.Connection, sources:dict[str,Path]) -> dict:
    name='notes-app-old-10'
    if name not in sources:
        return {'verified':False,'reason':'notes-app historical bundle unavailable'}
    target='src/domain/recall.ts'
    repo=sources[name]
    for row in conn.execute("SELECT sha FROM refs WHERE repo_id=(SELECT id FROM repositories WHERE name=?) AND name LIKE 'refs/heads/%'",(name,)):
        sha=row[0]
        try:
            blob=git(repo,'rev-parse',f'{sha}:{target}').strip()
            data=git(repo,'show',f'{sha}:{target}',binary=True)
            return {'verified':True,'repository':name,'path':target,'commit':sha,'blob':blob,'bytes':len(data), 'mentions_recall':b'recall' in data.lower() or b'interval' in data.lower()}
        except subprocess.CalledProcessError:
            continue
    return {'verified':False,'reason':f'No accessible {target} in preserved refs'}


def compare_branches(repo:Path,a:str='main',b:str='dev') -> dict:
    try:
        text=git(repo,'rev-list','--left-right','--count',f'refs/heads/{a}...refs/heads/{b}').strip()
        left,right=map(int,text.split())
        return {'main_only':left,'dev_only':right,'divergent':bool(left and right)}
    except (subprocess.CalledProcessError,ValueError):
        return {'available':False}


def main() -> int:
    CACHE.mkdir(parents=True,exist_ok=True)
    REPORTS.mkdir(parents=True,exist_ok=True)
    db_file=REPORTS/'archive-index.sqlite'
    if db_file.exists(): db_file.unlink()
    conn=open_db(db_file)
    run={'generated_utc':datetime.now(timezone.utc).isoformat(), 'sources':[],'queries':[]}
    sources={}
    start=time.perf_counter()
    for name in REPOS:
        t=time.perf_counter()
        src=checkout_public(name)
        sources[name]=src
        result=ingest(src,name,conn)
        result['seconds']=round(time.perf_counter()-t,2)
        result['branch_compare']=compare_branches(src)
        run['sources'].append(result)
    bundle_src,proof=historical_bundle(sources['exams-app-antigo-2'])
    run['bundle_validation']=proof
    if bundle_src:
        t=time.perf_counter()
        sources['notes-app-old-10']=bundle_src
        result=ingest(bundle_src,'notes-app-old-10',conn)
        result['seconds']=round(time.perf_counter()-t,2)
        run['sources'].append(result)
    for word in ['firebase','grafo','qconcursos','recall','capacit']:
        t=time.perf_counter()
        found=search(conn,word,limit=8)
        run['queries'].append({'query':word,'results':found,'ms':round(1000*(time.perf_counter()-t),2),'count':len(found)})
    run['deleted_image_recovery']=sample_recovery(conn,sources)
    run['historical_code_recovery']=sample_code(conn,sources)
    run['elapsed_seconds']=round(time.perf_counter()-start,2)
    run['index_bytes']=db_file.stat().st_size
    run['sqlite_fts5']=True
    run['historical_sources_complete']=False
    run['limitations']=[
        'Only two public repos and one historical notes-app bundle are indexed in this POC.',
        'Other notes-app private refs are not accessible using the new repository GITHUB_TOKEN.',
        'Archive metadata is reproducible; original full Git histories are not yet copied into this repository.',
        'Deleted images are identified by deletion events, not necessarily absent from all current branches.',
        'Full contents of every historical file and semantic image descriptions are not indexed.',
        'GitHub Actions costs/limits are not measured by this proof.',
    ]
    (REPORTS/'POC.json').write_text(json.dumps(run,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    text=['# Prova de conceito real — Git histórico + SQLite FTS5','',
          f"Gerada em {run['generated_utc']} (UTC). Fonte: Git, sem LLM/embeddings.",'',
          '| Fonte | Refs | Commits | Alterações | Imagens | Tempo |','|---|---:|---:|---:|---:|---:|']
    for d in run['sources']:
        text.append(f"| {d['repository']} | {d['refs']} | {d['commits']} | {d['changes']} | {d['images']} | {d['seconds']} s |")
    text += ['','## Recuperação de evidências','',
            f"- Bundle histórico validado: **{proof.get('validated')}** — `{BUNDLE_PATH}`",
            f"- Imagem removida recuperada e hash Git verificado: **{run['deleted_image_recovery'].get('verified')}**",
            f"- Código histórico `src/domain/recall.ts` recuperado: **{run['historical_code_recovery'].get('verified')}**",
            f"- Tempo total: **{run['elapsed_seconds']} s**; índice SQLite: **{round(run['index_bytes']/1024/1024,2)} MiB**",'']
    if run['deleted_image_recovery'].get('verified'):
        x=run['deleted_image_recovery'];text.extend([f"- Evidência de imagem: `{x['repository']}` / `{x['path']}` / commit `{x['commit']}` / blob `{x['git_blob_sha']}`",''])
    if run['historical_code_recovery'].get('verified'):
        x=run['historical_code_recovery'];text.extend([f"- Evidência de código: `{x['repository']}` / `{x['path']}` / commit `{x['commit']}`",''])
    text.extend(['## Buscas reais','','| Busca | Resultados | Latência | Exemplo |','|---|---:|---:|---|'])
    for q in run['queries']:
        example=q['results'][0] if q['results'] else {}
        text.append(f"| {q['query']} | {q['count']} | {q['ms']} ms | `{example.get('path') or example.get('summary','nenhum')[:55]}` |")
    text+=['','## Limitações e próximos passos','','- Não é migração completa: esta prova indexa duas fontes públicas e um bundle histórico.','- Sem cópia dos objetos Git para este repositório, a recuperação ainda depende da disponibilidade das fontes originais.','- Não indexa automaticamente todo o `notes-app` privado; exige autorização de acesso entre repositórios ou importação controlada de bundles.','- Próximo passo: verificar demais bundles, integrar históricos aprovados e ampliar a cobertura de consultas/contratos.','',
           'Os dados estruturados, SHAs e hashes estão em `POC.json`. O SQLite pode ser regenerado usando `scripts/run_poc.py`.']
    (REPORTS/'POC.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    conn.close()
    print(json.dumps({'sources':run['sources'],'image':run['deleted_image_recovery'],'code':run['historical_code_recovery'],'bundle':proof,'elapsed_seconds':run['elapsed_seconds'],'sqlite_bytes':run['index_bytes']},ensure_ascii=False,indent=2))
    if not run['deleted_image_recovery'].get('verified'):
        print('WARNING: real deleted image was not recovered',file=sys.stderr)
    return 0

if __name__=='__main__':raise SystemExit(main())