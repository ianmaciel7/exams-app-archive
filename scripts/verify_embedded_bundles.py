#!/usr/bin/env python3
"""Verify all 15 historical bundles from an already-preserved private release."""
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ARCHIVE = "ianmaciel7/exams-app-archive"
RELEASE = "archive-2026-11-23-initial"
FILENAME = "exams-app-antigo-2.bundle"

def run(*argv, output=None, timeout=1600):
    p = subprocess.run(argv, stdout=output if output is not None else subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout)
    if p.returncode:
        raise RuntimeError(str(argv[:3]) + ": " + p.stderr.decode(errors="replace")[-600:])
    return p.stdout.decode(errors="replace") if output is None else ""

def digest(p):
    sha = hashlib.sha256()
    with p.open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            sha.update(block)
    return sha.hexdigest()

def main():
    assert os.environ.get("GH_TOKEN"), "Missing token"
    inventory = json.loads(Path("inventory/source-refs-2026-11-23.json").read_text())
    references = {i["name"]:i["branches"] for i in inventory["repositories"]}
    manifest = json.loads(Path("manifests/release-2026-11-23.json").read_text())
    source_sha = next(x["sha256"] for x in manifest["assets"] if x["asset"]==FILENAME)
    with tempfile.TemporaryDirectory(prefix="historical-bundle-check-") as d:
        temp = Path(d)
        run("gh","release","download",RELEASE,"--repo",ARCHIVE,
            "--pattern",FILENAME,"--dir",str(temp),timeout=900)
        bundle=temp/FILENAME
        if digest(bundle)!=source_sha:
            raise RuntimeError("Original release hash mismatch")
        bare=temp/"repo.git"
        run("git","clone","--mirror",str(bundle),str(bare))
        names = run("git",f"--git-dir={bare}","ls-tree","-r","--name-only",
                    "refs/heads/dev").splitlines()
        names=sorted(n for n in names if n.startswith("prototype/") and n.endswith(".bundle"))
        if len(names)!=15:
            raise RuntimeError(f"Expected 15 bundles but discovered {len(names)}")
        output=[]
        for idx,name in enumerate(names):
            embedded=temp/f"{idx:02}.bundle"
            with embedded.open("wb") as handle:
                run("git",f"--git-dir={bare}","cat-file","blob",
                    f"refs/heads/dev:{name}",output=handle)
            isolated=temp/f"validate-{idx}.git"
            run("git","init","--bare","-q",str(isolated))
            run("git",f"--git-dir={isolated}","bundle","verify",str(embedded))
            heads=[]
            for line in run("git","bundle","list-heads",str(embedded)).splitlines():
                split=line.split(" ",1)
                if len(split)==2:
                    heads.append({"sha":split[0],"ref":split[1]})
            if not heads: raise RuntimeError(f"No refs: {name}")
            if name.startswith("prototype/notes-app-"):
                repo="notes-app"
                branch=name.removeprefix("prototype/notes-app-").removesuffix(".bundle")
            else:
                repo="exams-app-old"
                branch=name.removeprefix("prototype/exams-app-old-").removesuffix(".bundle")
                branch=branch.replace("backup-","backup/",1)
            expected=references[repo].get(branch)
            matching=bool(expected and expected in {x["sha"] for x in heads})
            output.append({"path":name,"source_repository":repo,"branch":branch,
                           "expected_source_sha":expected,"bundle_heads":heads,
                           "matches_source_branch_sha":matching,
                           "size_bytes":embedded.stat().st_size,
                           "sha256":digest(embedded),"verified":True})
            print(f"OK: {name}, current SHA match: {matching}",flush=True)
        report={"generated_utc":datetime.now(timezone.utc).isoformat(),
                "release":RELEASE,"verified_bundles":len(output),
                "matching_current_source_heads":sum(x["matches_source_branch_sha"] for x in output),
                "contents_recovered_independently_of_sources":True,
                "items":output}
        Path("reports").mkdir(exist_ok=True)
        Path("reports/embedded-bundles-audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
        lines=["# Verificacao dos 15 Git Bundles historicos","","Testados a partir da release privada sem acesso aos repositorios de origem.","",
               "Bundles verificados: "+str(len(output))+"/15",
               "HEADs coincidentes com as branches atuais: "+str(report["matching_current_source_heads"])+"/15","",
               "| Repositorio | Branch historica | Mesmo SHA atual? | Bytes |",
               "|---|---|---|---:|"]
        lines.extend(f"| {x['source_repository']} | {x['branch']} | {'Sim' if x['matches_source_branch_sha'] else 'Nao'} | {x['size_bytes']} |" for x in output)
        lines+=["","Os resultados completos com os hashes SHA-256 estao em embedded-bundles-audit.json.",
                "Um SHA diferente pode significar versao anterior ou posterior; exige verificacao, nao prova perda.",""]
        Path("reports/embedded-bundles-audit.md").write_text("\n".join(lines))
        print(json.dumps({"verified":len(output),"matched":report["matching_current_source_heads"]}),flush=True)

if __name__=="__main__":
    main()
