"""Check opaque canonical token pairs from the actual Markdown specification."""
import math
import re
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1] / "docs/UI-DESIGN-TOKENS.md"

def linear_rgb(value):
    if value.startswith("#"):
        def channel(n):
            x = n / 255
            return x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4
        return tuple(channel(n) for n in bytes.fromhex(value[1:]))
    L, C, h = map(float, re.fullmatch(r"oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)", value).groups())
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l = (L + .3963377774*a + .2158037573*b)**3
    m = (L - .1055613458*a - .0638541728*b)**3
    s = (L - .0894841775*a - 1.291485548*b)**3
    rgb = (4.0767416621*l - 3.3077115913*m + .2309699292*s,
           -1.2684380046*l + 2.6097574011*m - .3413193965*s,
           -.0041960863*l - .7034186147*m + 1.707614701*s)
    if min(rgb) < -1e-6 or max(rgb) > 1 + 1e-6:
        raise ValueError(f"Out-of-sRGB token requires explicit gamut mapping: {value}")
    return rgb

def contrast(a, b):
    def luminance(v):
        return sum(x*y for x,y in zip(linear_rgb(v), (.2126,.7152,.0722)))
    lo, hi = sorted((luminance(a), luminance(b)))
    return (hi + .05) / (lo + .05)

def parse_rows(markdown):
    rows = {}
    for line in markdown.splitlines():
        if not line.startswith("| `"):
            continue
        columns = [c.strip().strip("`") for c in line.split("|")[1:-1]]
        if len(columns) >= 3:
            rows[columns[0]] = columns[1:3]
    return rows

def evaluate(markdown):
    rows = parse_rows(markdown)
    canvas = next(key for key in rows if "--surface-canvas" in key)
    pairs = []
    for i, theme in enumerate(("light","dark")):
        for bg in (canvas, "--surface-panel", "--surface-panel-muted", "--surface-hover", "--surface-active"):
            # Ring needs contrast against surrounding surfaces; text tokens are normal-sized.
            for fg, minimum in (("--content-primary",4.5),("--content-secondary",4.5),("--content-tertiary",4.5),("--ring",3)):
                pairs.append((f"{theme}:{fg}/{bg}", contrast(rows[fg][i],rows[bg][i]),minimum))
    for key in ("blue-file","amber-folder","rose-citation","emerald-verified","violet-graph","slate-meta"):
        bg, fg = rows[key]
        pairs.append((key,contrast(fg,bg),4.5))
    return pairs

def main():
    results = evaluate(SPEC.read_text(encoding="utf-8"))
    for name, ratio, minimum in results:
        print(f"{name}: {ratio:.3f}:1 >= {minimum}:1 {'PASS' if ratio >= minimum else 'FAIL'}")
    return int(any(ratio < minimum for _,ratio,minimum in results))

if __name__ == "__main__":
    raise SystemExit(main())
