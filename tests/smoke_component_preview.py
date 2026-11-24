"""End-to-end reviewed build, interaction and SQLite screenshot persistence."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import json

ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/"plugins/exams-archive/scripts/archive_query.py"


def main():
    deps=Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory() as home:
        env={**os.environ,"HOME":home,"USERPROFILE":home}
        def run(*args):
            r=subprocess.run([sys.executable,str(CLI),"components",*args],env=env,cwd=ROOT,capture_output=True,text=True,check=True)
            return json.loads(r.stdout)
        assert run("list")[0]["id"]=="error-boundary"
        result=run("render","error-boundary","--deps",str(deps))
        assert result["interactive"]
        photo=run("capture","error-boundary","--state","retry","--theme","dark","--width","390","--height","844")
        assert photo["state"]=="retry" and photo["width"]==390
        assert run("screenshots","--component","error-boundary")[0]["id"]==photo["id"]
        output=Path(home)/"export.png"
        assert run("export",photo["id"],"--output",str(output))["sha256"]==photo["png_sha256"]
        assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        print("Interactive React retry, dark theme, mobile screenshot, SQLite and PNG export passed")


if __name__=="__main__":main()
