#!/usr/bin/env python3
"""Create verified Git bundles for a private GitHub Release, not Git branches.

Usage: python3 scripts/create_release_archives.py
Requires git, gh (GitHub CLI), GH_TOKEN with contents:write in archive repo.

Original repositories are cloned read-only. No source refs are edited. Binary
snapshots are attached to the private archive Release rather than committed to
its Git history. No private notes-app credential or cookie is required.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE = 'ianmaciel7/exams-app-archive'
TAG = 'archive-2026-11-23-initial'
SOURCES = {
    'exams-app': ['main', 'dev'],
    'exams-app-old': ['*'],
    'exams-app-antigo-2': ['*'],
    'shadcn-template': ['main'],
    'shadcn-firebase-template': ['main'],
}
# These are the most useful stand-alone historical snapshots inside old2.
# All 15 original bundles remain reachable in the full old2 Git bundle.
EXTRACT = ['notes-app-old-5.bundle', 'notes-app-old-8.bundle',
           'notes-app-old-10.bundle', 'notes-app-old-11.bundle']
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'manifests'


def command(*argv: str, stdout_path: Path | None = None, capture: bool = False, timeout: int = 900) -> str:
    handle = stdout_path.open('wb') if stdout_path else None
    try:
        proc = subprocess.run(argv, stdout=subprocess.PIPE if capture else (handle if handle else subprocess.DEVNULL),
                              stderr=subprocess.PIPE, timeout=timeout)
    finally:
        if handle:
            handle.close()
    if proc.returncode:
        raise RuntimeError(f"{' '.join(argv[:4])}: {proc.stderr.decode('utf-8', 'replace')[-900:]}")
    return (proc.stdout or b'').decode('utf-8', 'replace') if capture else proc.stderr.decode('utf-8', 'replace')


def sha256(path: Path) -> str:
    value=hashlib.sha256()
    with path.open('rb') as inp:
        for block in iter(lambda: inp.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def verify(bundle: Path, tmp: Path) -> dict:
    probe = tmp / ('verify-'+bundle.stem+'.git')
    command('git','init','--bare','-q',str(probe))
    try:
        output=command('git',f'--git-dir={probe}','bundle','verify',str(bundle),capture=True)
        return {'verified':True,'message':output.strip()[:250]}
    except RuntimeError as exc:
        return {'verified':False,'message':str(exc)[:350]}


def mirror(name: str, root: Path) -> Path:
    directory=root/(name+'.git')
    command('git','clone','--mirror','--quiet',f'https://github.com/ianmaciel7/{name}.git',str(directory))
    return directory


def head_count(repo:Path)->int:
    return len(command('git',f'--git-dir={repo}','for-each-ref','--format=%(refname)','refs/heads/',capture=True).splitlines())


def manifest_item(out:Path,repo:str,ref_count:int,verification:dict,source:str)->dict:
    return {'asset':out.name,'repository':repo,'source':source,'size_bytes':out.stat().st_size,
            'sha256':sha256(out),'branch_refs_in_bundle':ref_count,**verification}


def main()->None:
    if not os.getenv('GH_TOKEN'):
        raise RuntimeError('GH_TOKEN missing; this program only publishes to the private archive')
    if command('gh','repo','view',ARCHIVE,'--json','visibility','--jq','.visibility',capture=True).strip()!='PRIVATE':
        raise RuntimeError('Refusing to upload histories to a non-private repository')
    # Never overwrite a prior immutable history snapshot.
    already=subprocess.run(['gh','release','view',TAG,'--repo',ARCHIVE],capture_output=True)
    if already.returncode==0:
        raise RuntimeError(f'Release {TAG} already exists; no replacement performed')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    manifest={'tag':TAG,'created_at':datetime.now(timezone.utc).isoformat(),'archive':ARCHIVE,'assets':[],
              'limitations':['Does not yet include complete private notes-app remote repository history.',
                             'Historical notes-app bundles are restored from exams-app-antigo-2, not its current private remote.',
                             'Full Git bundles preserve internal branch refs, but the archive repository itself has only main.',
                             'Release asset checksums prove bytes; no claim that unreachable Git objects survived upstream pruning.']}
    with tempfile.TemporaryDirectory(prefix='exam-archive-release-') as directory:
        temp=Path(directory)
        bundles=temp/'assets';bundles.mkdir()
        clones={}
        for name,selector in SOURCES.items():
            repo=mirror(name,temp)
            clones[name]=repo
            if selector==['*']:
                branches=['--branches','--tags']
                selected=head_count(repo)
            else:
                branches=[f'refs/heads/{x}' for x in selector]
                selected=len(branches)
                for ref in branches:
                    command('git',f'--git-dir={repo}','rev-parse','--verify',ref,capture=True)
            bundle=bundles/(name+'.bundle')
            command('git',f'--git-dir={repo}','bundle','create',str(bundle),*branches,timeout=1500)
            result=verify(bundle,temp)
            if not result['verified']:
                raise RuntimeError(f'New bundle not verified: {bundle}: {result}')
            manifest['assets'].append(manifest_item(bundle,name,selected,result,'Git branch/tag refs'))
            print(f'Verified {name}: {bundle.stat().st_size:,} bytes, {selected} branch refs',flush=True)

        old2=clones['exams-app-antigo-2']
        for filename in EXTRACT:
            git_path=f'prototype/{filename}'
            out=bundles/filename
            # Binary-safe extraction without checking out potentially executable code.
            with out.open('wb') as sink:
                result=subprocess.run(['git',f'--git-dir={old2}','show',f'refs/heads/dev:{git_path}'],stdout=sink,stderr=subprocess.PIPE,timeout=120)
            if result.returncode:
                raise RuntimeError('Historical bundle missing: '+git_path)
            result=verify(out,temp)
            manifest['assets'].append(manifest_item(out, 'notes-app',1,result,git_path))
            print(f'Historical snapshot {filename}: verified={result["verified"]}',flush=True)

        man_file=bundles/'SHA256SUMS.txt'
        man_file.write_text(''.join(f"{x['sha256']}  {x['asset']}\n" for x in manifest['assets']),encoding='utf-8')
        man_json=bundles/'MANIFEST.json'
        man_json.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        # gh creates a private draft Release, uploads checked assets, then publishes.
        command('gh','release','create',TAG,'--repo',ARCHIVE,'--draft',
                '--title','Historical Exam App sources (2026-11-23)',
                '--notes','Verified Git bundle archives; use MANIFEST.json / SHA256SUMS.txt to validate original histories.',
                timeout=120)
        for asset in sorted(bundles.iterdir()):
            command('gh','release','upload',TAG,str(asset),'--repo',ARCHIVE,timeout=900)
            print('Uploaded',asset.name,flush=True)
        # Read back a small bundle asset, verify byte hash, and ensure it can be restored.
        verify_download=temp/'verify-download';verify_download.mkdir()
        command('gh','release','download',TAG,'--repo',ARCHIVE,'--pattern','exams-app-old.bundle','--dir',str(verify_download),timeout=300)
        downloaded=verify_download/'exams-app-old.bundle'
        expected=next(x for x in manifest['assets'] if x['asset']=='exams-app-old.bundle')['sha256']
        if sha256(downloaded)!=expected or not verify(downloaded,verify_download)['verified']:
            raise RuntimeError('Release roundtrip integrity failed')
        manifest['roundtrip_verified_asset']='exams-app-old.bundle'
        command('gh','release','edit',TAG,'--repo',ARCHIVE,'--draft=false',timeout=120)
        (OUTPUT/'release-2026-11-23.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        report=['# Git bundles preservados em release privado','',f'Release: https://github.com/{ARCHIVE}/releases/tag/{TAG}','',
                'Foram preservados os objetos e refs incluídos em cada bundle. Nenhuma branch foi criada no repositório do arquivo.','',
                '| Asset | Origem | Tamanho (MiB) | Verificado |','|---|---|---:|---|']
        for item in manifest['assets']:
            report.append(f"| {item['asset']} | {item['repository']} | {item['size_bytes']/2**20:.2f} | {item['verified']} |")
        report+=['','Os 15 backups internos de `exams-app-antigo-2` também estão contidos no bundle completo desse repositório.',
                 'Quatro snapshots de maior valor foram disponibilizados individualmente para recuperação rápida.',
                 '', '**Pendente:** importar o histórico completo do repositório privado `notes-app` com autorização adequada.',
                 'Confira os hashes e a restauração antes de remover qualquer fonte original.','']
        (OUTPUT/'README.md').write_text('\n'.join(report),encoding='utf-8')
        print(json.dumps({'published':True,'assets':len(manifest['assets'])+2,'roundtrip':manifest['roundtrip_verified_asset']},indent=2),flush=True)


if __name__=='__main__':main()