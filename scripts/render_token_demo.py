"""Generate an original, offline reference fixture from the canonical token spec."""
import argparse
from html import escape
from pathlib import Path
from check_token_contrast import SPEC, parse_rows

SURFACES = ("--surface-canvas","--surface-panel","--surface-panel-muted","--surface-hover","--surface-active")
TEXTS = ("--content-primary","--content-secondary","--content-tertiary")
CHIPS = ("blue-file","amber-folder","rose-citation","emerald-verified","violet-graph","slate-meta")

def render(markdown):
    rows = parse_rows(markdown)
    canvas = next(k for k in rows if "--surface-canvas" in k)
    rows["--surface-canvas"] = rows[canvas]
    keys = (*SURFACES,*TEXTS,"--ring","--content-active","--border-subtle")
    theme = []
    for index, name in enumerate(("light","dark")):
        theme.append(f'[data-theme="{name}"]'+"{"+ ";".join(f"{k}:{rows[k][index]}" for k in keys)+"}")
    sections = []
    for surface in (*SURFACES,"overlay"):
        color = "color-mix(in srgb, var(--content-primary) 8%, var(--surface-panel))" if surface=="overlay" else f"var({surface})"
        texts = "".join(f'<p data-token="{k}" style="color:var({k})">{escape(k)} - sample</p>' for k in TEXTS)
        sections.append(f'<section class="sample" data-surface="{surface}" style="background:{color}"><h2>{escape(surface)}</h2>{texts}<button class="state-control">Focus sample</button></section>')
    chips = "".join(f'<span class="chip" data-chip="{k}" style="background:{rows[k][0]};color:{rows[k][1]}">{escape(k)}</span>' for k in CHIPS)
    return """<!doctype html><html lang="en" data-theme="light"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Canonical color roles - original demo</title>
<style>
"""+"\n".join(theme)+"""
*{box-sizing:border-box}body{font:16px/1.5 system-ui;margin:0;background:var(--surface-canvas);color:var(--content-primary);padding:16px}
h1{font-size:1.3rem}h2{font-size:1rem;margin:0 0 8px}p{margin:4px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:12px}
.sample{padding:16px;border-radius:8px;color:var(--content-primary)}
button{background:var(--surface-panel);color:var(--content-primary);font:inherit;border:1px solid var(--ring);border-radius:5px;padding:6px 10px}
button:focus-visible{outline:3px solid var(--ring);outline-offset:3px}
.state-control{margin:5px 0}.state-control:hover{background:var(--surface-hover)}.state-control:active,.state-control[aria-pressed=true]{background:var(--surface-active)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.chip{padding:3px 8px;border-radius:4px}
@media(forced-colors:active){button:focus-visible{outline:3px solid Highlight}button{border:1px solid ButtonText}.chip{border:1px solid CanvasText}}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
<main><h1>Color roles, focus and interaction states</h1>
<p>Original test fixture, not an active Exam App screenshot. Text labels preserve meaning without color.</p>
<button id="theme" aria-label="Toggle light or dark theme">Toggle theme</button>
<button id="select" aria-pressed="false" class="state-control">Select item</button>
<p id="selection" role="status">Not selected</p>
<div class="grid">"""+ "".join(sections)+"""</div><h2>Object identity chips</h2><div class="chips">"""+chips+"""</div></main>
<script>
document.querySelector('#theme').addEventListener('click',()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='light'?'dark':'light';});
document.querySelector('#select').addEventListener('click',e=>{const v=e.currentTarget.getAttribute('aria-pressed')!=='true';e.currentTarget.setAttribute('aria-pressed',String(v));document.querySelector('#selection').textContent=v?'Selected':'Not selected';});
</script></html>"""

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    args.output.write_text(render(SPEC.read_text(encoding="utf-8")),encoding="utf-8")

if __name__=="__main__":
    main()
