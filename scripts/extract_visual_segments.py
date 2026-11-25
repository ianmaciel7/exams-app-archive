#!/usr/bin/env python3
"""Generate lightweight, explicitly non-semantic timeline evidence from approved local media."""
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from visual_reference_index import LIB, load, verify

SAFE_ID = re.compile(r"[a-z0-9_-]+", re.I)
SEGMENTS = "media/segments"

def run(*args):
    return subprocess.check_output(args, stderr=subprocess.PIPE, timeout=60)

def probe(path):
    meta = json.loads(run("ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)))
    video = next(s for s in meta["streams"] if s["codec_type"] == "video")
    duration = float(meta["format"].get("duration") or video.get("duration") or 0)
    if not math.isfinite(duration) or duration <= 0 or duration > 600:
        raise ValueError("unsupported duration")
    return duration, video

def sample_times(duration):
    end = max(0., duration - min(.15, duration / 10))
    return [end * i / 12 for i in range(13)]

def gray(path, t):
    raw = run("ffmpeg", "-v", "error", "-ss", str(t), "-i", str(path), "-map", "0:v:0",
              "-frames:v", "1", "-vf", "scale=64:36,format=gray", "-threads", "1",
              "-f", "rawvideo", "-")
    if len(raw) != 64 * 36:
        raise ValueError("frame unavailable")
    return raw

def fingerprint(path, t=None):
    result = {"path": str(path.relative_to(LIB)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
    if t is not None:
        result["timestamp_seconds"] = round(t, 3)
    return result

def extract(row):
    ident = row["id"]
    if not SAFE_ID.fullmatch(ident) or row["license"] != "MIT":
        raise ValueError("unapproved input")
    path = LIB / row["path"]
    duration, video = probe(path)
    samples = []
    for t in sample_times(duration):
        try:
            samples.append((t, gray(path, t)))
        except (subprocess.SubprocessError, ValueError):
            continue
    if len(samples) < 3:
        raise ValueError("insufficient decoded frames")
    # Highest sampled pixel-change interval is only a candidate, not an action label.
    changes = [(sum(abs(x-y) for x,y in zip(a[1],b[1]))/len(a[1]), a[0], b[0])
               for a,b in zip(samples, samples[1:])]
    score, left, right = max(changes)
    if duration > 8 and score > 0:
        start = max(0., min(duration - 4., (left + right)/2 - 2.))
        end = min(duration, start + 4.)
    else:
        start, end = 0., duration
    folder = LIB / SEGMENTS
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, target in enumerate([start, (start+end)/2, max(start,end-min(.15,duration/10))]):
        t = min(samples, key=lambda s: abs(s[0]-target))[0]
        if frames and abs(frames[-1]["timestamp_seconds"]-t) < .001:
            continue
        out = folder / f"{ident}-{i+1}.jpg"
        run("ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", str(path), "-map", "0:v:0",
            "-frames:v", "1", "-vf", "scale='min(640,iw)':-2", "-q:v", "5", "-threads", "1", str(out))
        if out.stat().st_size == 0:
            raise ValueError("empty frame")
        frames.append(fingerprint(out, t))
    clip = None
    # Only create an excerpt for a long source; avoid duplicating an already short demo.
    if duration > 8 and score > 0:
        out = folder / f"{ident}-excerpt.mp4"
        run("ffmpeg", "-y", "-v", "error", "-ss", str(start), "-i", str(path),
            "-t", str(end-start), "-map", "0:v:0", "-an",
            "-vf", "scale='min(640,iw)':-2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-preset", "fast", "-crf", "25", "-threads", "1", "-movflags", "+faststart", str(out))
        actual, _ = probe(out)
        if actual > 8.1:
            raise ValueError("excerpt too long")
        clip = dict(fingerprint(out), duration_seconds=round(actual,3), audio=False)
    return {"schema_version":1, "source_blob_sha":row["blob_sha"],
            "duration_seconds":round(duration,3),
            "source_dimensions":[video["width"],video["height"]],
            "classification":"short-upstream-demo" if duration <= 8 else "longer-upstream-demo",
            "selection_method":"13 evenly spaced grayscale samples; maximum adjacent pixel change",
            "segment":{"start_seconds":round(start,3),"end_seconds":round(end,3)},
            "candidate_change_interval":{"start_seconds":round(left,3),"end_seconds":round(right,3),"mean_pixel_difference":round(score,3)},
            "keyframes":frames,"clip":clip,
            "semantic_review":"not-inspected","states":[],"observations":[],
            "verification":"decoded-frames-and-probed-duration",
            "limits":"Sampled pixel change does not establish a semantic event or exact motion timing."}

def main():
    manifest = LIB / "manifest.json"
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    errors = verify(doc["records"])
    if errors:
        raise ValueError(str(errors))
    rows = [r for r in doc["records"] if r["status"]=="archived-blob-verified" and r["kind"] in {"video","gif"}]
    failures = []
    for row in rows:
        try:
            row["segment_evidence"] = extract(row)
            row["duration_seconds"] = row["segment_evidence"]["duration_seconds"]
            row["playback"] = "decoded-sampled-frames"
        except Exception as exc:
            failures.append({"id":row["id"],"error":str(exc)})
    if failures:
        raise RuntimeError(json.dumps(failures))
    manifest.write_text(json.dumps(doc, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    errors = verify(doc["records"])
    if errors:
        raise ValueError(str(errors))
    print(json.dumps({"sources":len(rows),"frames":sum(len(r["segment_evidence"]["keyframes"]) for r in rows),
          "clips":sum(bool(r["segment_evidence"]["clip"]) for r in rows),
          "semantic_review":"pending","durations":{r["id"]:r["duration_seconds"] for r in rows}}))

if __name__ == "__main__":
    main()
