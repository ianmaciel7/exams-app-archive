#!/usr/bin/env python3
"""Private historical image catalog for bare Git repositories and Git bundles.

Reads image metadata and dimensions directly from raw bytes (PNG, JPG, GIF,
WEBP, SVG) using the Python standard library without executing scripts or
publishing data to site/ or GitHub Pages. Optional deterministic thumbnails are
generated when Pillow is installed; otherwise dimensions are recorded and
thumbnails are skipped cleanly.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import zlib

try:
    from PIL import Image, ImageOps
    HAS_PILLOW = True
except ImportError:  # pragma: no cover - exercised in stdlib-only environments
    Image = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    HAS_PILLOW = False

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"})
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOF_MARKERS = frozenset({
    0xC0, 0xC1, 0xC2, 0xC3,
    0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB,
    0xCD, 0xCE, 0xCF,
})
MAX_PAGE_SIZE = 200
MAX_LIMIT = 500
MAX_THUMB_SIZE = 512
MIN_THUMB_SIZE = 16
MAX_IMAGE_PIXELS = 50_000_000
REPO_ROOT = Path(__file__).resolve().parents[1]

SVG_TAG_RE = re.compile(r"<svg\b([^>]*)>", re.IGNORECASE | re.DOTALL)
SVG_ATTR_RE = re.compile(
    r"""(?:^|\s)(width|height|viewbox)\s*=\s*(?:"([^"]*)"|'([^']*)')""",
    re.IGNORECASE,
)
SVG_NUM_UNIT_RE = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*(px|pt|pc|in|cm|mm)?\s*$",
    re.IGNORECASE,
)
SVG_SCRIPT_RE = re.compile(
    r"<\s*script\b|javascript\s*:|\bon[a-z]+\s*=|<\s*foreignobject\b",
    re.IGNORECASE,
)
UNIT_FACTORS_96DPI = {
    "": 1.0,
    "px": 1.0,
    "in": 96.0,
    "pc": 16.0,
    "pt": 96.0 / 72.0,
    "cm": 96.0 / 2.54,
    "mm": 96.0 / 25.4,
}


def safe_ref(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise ValueError("commit SHA must be full-length hexadecimal")
    return value


def safe_path(path: str) -> str:
    parts = Path(path).parts
    if (
        not path
        or path.startswith(("/", "-"))
        or "\\" in path
        or ".." in parts
        or "\x00" in path
        or ":" in path
    ):
        raise ValueError(f"unsafe path: {path!r}")
    return path


def validate_private_output_path(path: Path, repo_root: Path | None = None) -> Path:
    """Reject any path targeting site/ or public GitHub Pages output."""
    root = (repo_root or REPO_ROOT).resolve()
    site_dir = root / "site"
    resolved = path.resolve()
    if resolved == site_dir or site_dir in resolved.parents:
        raise ValueError(f"Refusing to write private catalog data inside site/: {path}")
    cwd_site = (Path.cwd() / "site").resolve()
    if resolved == cwd_site or cwd_site in resolved.parents:
        raise ValueError(f"Refusing to write private catalog data inside site/: {path}")
    if not path.is_absolute() and path.parts and path.parts[0] == "site":
        raise ValueError(f"Refusing to write private catalog data inside site/: {path}")

    forbidden_names = frozenset({"site", "_site", "gh-pages"})
    parts_lower = [p.lower() for p in path.parts]
    if any(p in forbidden_names for p in parts_lower):
        raise ValueError(f"Refusing to write private catalog data inside public Pages directory: {path}")

    for parent in (resolved, *resolved.parents):
        if parent.name.lower() in forbidden_names:
            raise ValueError(f"Refusing to write private catalog data inside public Pages directory: {path}")
        if parent == (root / "public" / "pages") or (root / "public" / "pages") in parent.parents:
            raise ValueError(f"Refusing to write private catalog data inside public Pages directory: {path}")

    if len(parts_lower) >= 2 and parts_lower[0] == "public" and parts_lower[1] == "pages":
        raise ValueError(f"Refusing to write private catalog data inside public Pages directory: {path}")

    return path


def _git_run(git_dir: Path, *args: str, stdin_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(
        ["git", f"--git-dir={git_dir}", *args],
        input=stdin_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()[:600]
        raise RuntimeError(f"git {' '.join(args[:3])} failed ({proc.returncode}): {err}")
    return proc.stdout


def _git_stream(git_dir: Path, *args: str):
    proc = subprocess.Popen(
        ["git", f"--git-dir={git_dir}", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None and proc.stderr is not None
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
        err = proc.stderr.read()
    finally:
        proc.stdout.close()
        proc.stderr.close()
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"git {' '.join(args[:3])} returned {code}: {err[:600]}")


def _read_blobs_batch(git_dir: Path, blob_shas: list[str]) -> dict[str, bytes | None]:
    """Fetch multiple blobs from git in a single batch subprocess."""
    if not blob_shas:
        return {}
    unique = list(dict.fromkeys(blob_shas))
    payload = ("\n".join(unique) + "\n").encode("utf-8")
    proc = subprocess.run(
        ["git", f"--git-dir={git_dir}", "cat-file", "--batch"],
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()[:600]
        raise RuntimeError(f"git cat-file --batch failed: {err}")

    out = proc.stdout
    results: dict[str, bytes | None] = {}
    pos = 0
    total = len(out)
    for requested in unique:
        if pos >= total:
            results[requested] = None
            continue
        nl = out.find(b"\n", pos)
        if nl == -1:
            results[requested] = None
            break
        header = out[pos:nl].decode("utf-8", "replace")
        pos = nl + 1
        if header.endswith(" missing"):
            results[requested] = None
            continue
        parts = header.split(" ")
        if len(parts) < 3:
            results[requested] = None
            continue
        try:
            size = int(parts[2])
        except ValueError:
            results[requested] = None
            continue
        if pos + size > total:
            results[requested] = None
            break
        results[requested] = out[pos:pos + size]
        pos += size
        if pos < total and out[pos:pos + 1] == b"\n":
            pos += 1
    return results


def _parse_png_dimensions(data: bytes) -> tuple[int | None, int | None]:
    if len(data) < 24 or data[:8] != PNG_SIGNATURE or data[12:16] != b"IHDR":
        return (None, None)
    width, height = struct.unpack(">II", data[16:24])
    if width == 0 or height == 0:
        return (None, None)
    return (width, height)


def _parse_gif_dimensions(data: bytes) -> tuple[int | None, int | None]:
    if len(data) < 10 or data[:6] not in (b"GIF87a", b"GIF89a"):
        return (None, None)
    width, height = struct.unpack("<HH", data[6:10])
    if width == 0 or height == 0:
        return (None, None)
    return (width, height)


def _parse_jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    n = len(data)
    if n < 4 or data[:2] != b"\xff\xd8":
        return (None, None)
    pos = 2
    while pos < n:
        if data[pos] != 0xFF:
            break
        while pos < n and data[pos] == 0xFF:
            pos += 1
        if pos >= n:
            break
        marker = data[pos]
        pos += 1
        if marker == 0x00:
            continue
        if marker in (0xD9, 0xDA):
            break
        if marker == 0x01 or (0xD0 <= marker <= 0xD8):
            continue
        if pos + 2 > n:
            break
        seg_len = struct.unpack(">H", data[pos:pos + 2])[0]
        if seg_len < 2 or pos + seg_len > n:
            break
        if marker in JPEG_SOF_MARKERS:
            if seg_len < 7 or pos + 7 > n:
                break
            height, width = struct.unpack(">HH", data[pos + 3:pos + 7])
            if width > 0 and height > 0:
                return (width, height)
            return (None, None)
        pos += seg_len
    return (None, None)


def _parse_webp_dimensions(data: bytes) -> tuple[int | None, int | None]:
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return (None, None)
    chunk = data[12:16]
    if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
        w, h = struct.unpack("<HH", data[26:30])
        w &= 0x3FFF
        h &= 0x3FFF
        return (w, h) if w > 0 and h > 0 else (None, None)
    if chunk == b"VP8L" and data[20] == 0x2F:
        b0, b1, b2, b3 = data[21:25]
        w = 1 + (((b1 & 0x3F) << 8) | b0)
        h = 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
        return (w, h) if w > 0 and h > 0 else (None, None)
    if chunk == b"VP8X":
        w = 1 + int.from_bytes(data[24:27], "little")
        h = 1 + int.from_bytes(data[27:30], "little")
        return (w, h) if w > 0 and h > 0 else (None, None)
    return (None, None)


def _parse_svg_length(raw: str) -> int | None:
    match = SVG_NUM_UNIT_RE.match(raw)
    if not match:
        return None
    val = float(match.group(1))
    unit = (match.group(2) or "").lower()
    factor = UNIT_FACTORS_96DPI.get(unit)
    if factor is None or val <= 0:
        return None
    px = val * factor
    rounded = int(round(px))
    return rounded if rounded > 0 else None


def inspect_svg_inert(data: bytes) -> dict:
    """Parse SVG metadata as strictly inert text without executing scripts or XML."""
    text = data.decode("utf-8", "replace").lstrip("\ufeff")
    script_detected = bool(SVG_SCRIPT_RE.search(text))
    # Remove XML comments before inspecting root <svg ...> tag attributes.
    cleaned = re.sub(r"<!--.*?-->", " ", text[:65536], flags=re.DOTALL)
    tag_match = SVG_TAG_RE.search(cleaned)
    width: int | None = None
    height: int | None = None
    vb_width: int | None = None
    vb_height: int | None = None
    if tag_match:
        attrs_raw = tag_match.group(1)
        attrs: dict[str, str] = {}
        for attr_match in SVG_ATTR_RE.finditer(attrs_raw):
            key = attr_match.group(1).lower()
            val = attr_match.group(2) if attr_match.group(2) is not None else attr_match.group(3)
            if key not in attrs:
                attrs[key] = val
        if "width" in attrs:
            width = _parse_svg_length(attrs["width"])
        if "height" in attrs:
            height = _parse_svg_length(attrs["height"])
        if "viewbox" in attrs:
            parts = [p for p in re.split(r"[\s,]+", attrs["viewbox"].strip()) if p]
            if len(parts) == 4:
                try:
                    vw = float(parts[2])
                    vh = float(parts[3])
                    if vw > 0 and vh > 0:
                        vb_width = int(round(vw))
                        vb_height = int(round(vh))
                except ValueError:
                    pass
    if width is None and vb_width is not None:
        width = vb_width
    if height is None and vb_height is not None:
        height = vb_height
    return {
        "width": width,
        "height": height,
        "inert": True,
        "script_detected": script_detected,
    }


def sanitize_svg(data: bytes | str) -> str:
    """Sanitize SVG markup to ensure completely inert rendering without script execution."""
    if isinstance(data, bytes):
        text = data.decode("utf-8", "replace").lstrip("\ufeff")
    else:
        text = str(data)

    # Remove XML comments first to prevent hiding tricks
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # Remove script tags and content
    text = re.sub(r"<\s*script\b[^>]*>.*?<\s*/\s*script\s*>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<\s*script\b[^>]*/>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<\s*script\b[^>]*>", "", text, flags=re.IGNORECASE)

    # Remove foreignObject tags and content
    text = re.sub(r"<\s*foreignObject\b[^>]*>.*?<\s*/\s*foreignObject\s*>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<\s*foreignObject\b[^>]*/>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove dangerous container elements
    for tag in ("iframe", "object", "embed", "applet", "audio", "video", "meta", "link"):
        text = re.sub(rf"<\s*{tag}\b[^>]*>.*?<\s*/\s*{tag}\s*>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(rf"<\s*{tag}\b[^>]*/>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(rf"<\s*{tag}\b[^>]*>", "", text, flags=re.IGNORECASE)

    # Remove inline event handlers (onload, onclick, onerror, onmouseover, etc.)
    text = re.sub(r"""\s+on[a-z0-9_-]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", "", text, flags=re.IGNORECASE)

    # Block javascript:, vbscript:, and data:text/html in href, src, xlink:href
    text = re.sub(
        r"""(\b(?:href|xlink:href|src)\s*=\s*['"])\s*(?:javascript|vbscript|data\s*:\s*text/html):[^'"]*(['"])""",
        r"\1#blocked\2",
        text,
        flags=re.IGNORECASE,
    )

    # Strip entity declarations to avoid XML entity expansion
    text = re.sub(r"<!ENTITY\b[^>]*>", "", text, flags=re.IGNORECASE)

    return text.strip()


def extract_screen_name(path: str) -> str:
    """Extract a canonical screen or UI component name from an image path."""
    p = Path(path)
    stem = p.stem.lower()
    cleaned = re.sub(r"[-_](?:v\d+|\d+x|\d{4,}|old|new|dark|light)$", "", stem)
    cleaned = re.sub(r"^(?:screen[-_]|screenshot[-_]|img[-_])", "", cleaned)
    if cleaned in ("index", "view", "main", "screenshot", "screen", "preview") and len(p.parts) > 1:
        parent_name = p.parts[-2].lower()
        if parent_name not in ("assets", "images", "img", "static", "public", "screenshots"):
            return parent_name
    return cleaned or stem


def diff_image_versions(v1: dict, v2: dict) -> dict:
    """Compare two image versions and return detailed differences."""
    path = v1.get("path") or v2.get("path") or ""
    sha1 = v1.get("sha256")
    sha2 = v2.get("sha256")
    same_content = bool(sha1 and sha2 and sha1 == sha2)

    w1, h1 = v1.get("width"), v1.get("height")
    w2, h2 = v2.get("width"), v2.get("height")
    dimensions_changed = (w1 != w2 or h1 != h2)

    w_delta = (w2 - w1) if (w1 is not None and w2 is not None) else None
    h_delta = (h2 - h1) if (h1 is not None and h2 is not None) else None

    b1 = v1.get("bytes")
    b2 = v2.get("bytes")
    bytes_delta = (b2 - b1) if (b1 is not None and b2 is not None) else None

    status1 = v1.get("status", "unknown")
    status2 = v2.get("status", "unknown")
    status_changed = (status1 != status2)

    parts = []
    if same_content:
        parts.append("Content identical (same SHA-256)")
    else:
        parts.append("Content modified")

    if dimensions_changed:
        d1_str = f"{w1}x{h1}" if (w1 and h1) else "unknown"
        d2_str = f"{w2}x{h2}" if (w2 and h2) else "unknown"
        w_d_str = f"{w_delta:+d}" if w_delta is not None else "?"
        h_d_str = f"{h_delta:+d}" if h_delta is not None else "?"
        parts.append(f"dimensions: {d1_str} -> {d2_str} (delta: {w_d_str}w, {h_d_str}h)")
    else:
        parts.append(f"dimensions unchanged ({w1}x{h1})" if w1 and h1 else "dimensions unknown")

    if bytes_delta is not None and bytes_delta != 0:
        parts.append(f"size delta: {bytes_delta:+d} bytes")

    if status_changed:
        parts.append(f"status: {status1} -> {status2}")

    summary = "; ".join(parts)

    return {
        "path": path,
        "same_content": same_content,
        "dimensions_changed": dimensions_changed,
        "dimension_diff": {
            "width_a": w1,
            "height_a": h1,
            "width_b": w2,
            "height_b": h2,
            "width_delta": w_delta,
            "height_delta": h_delta,
        },
        "bytes_diff": bytes_delta,
        "status_changed": status_changed,
        "version_a": {
            "commit": v1.get("commit"),
            "ref": v1.get("ref") or (v1.get("refs")[0] if v1.get("refs") else None),
            "sha256": sha1,
            "width": w1,
            "height": h1,
            "bytes": b1,
            "status": status1,
        },
        "version_b": {
            "commit": v2.get("commit"),
            "ref": v2.get("ref") or (v2.get("refs")[0] if v2.get("refs") else None),
            "sha256": sha2,
            "width": w2,
            "height": h2,
            "bytes": b2,
            "status": status2,
        },
        "summary": summary,
    }


def compare_versions(
    catalog: dict,
    path: str,
    commit_a: str | None = None,
    commit_b: str | None = None,
) -> dict:
    """Find and compare two versions of an image file in the catalog."""
    items = catalog.get("items", [])
    matching_item = None
    for item in items:
        if item.get("path") == path:
            matching_item = item
            break
    if matching_item is None:
        raise ValueError(f"Path not found in catalog: {path}")

    versions = matching_item.get("versions", [])
    if not versions:
        v = {
            "commit": matching_item.get("commit"),
            "ref": matching_item.get("ref"),
            "sha256": matching_item.get("sha256"),
            "width": matching_item.get("width"),
            "height": matching_item.get("height"),
            "bytes": matching_item.get("bytes"),
            "status": matching_item.get("status"),
            "path": path,
        }
        return diff_image_versions(v, v)

    if commit_a and commit_b:
        va = next((v for v in versions if (v.get("commit") or "").startswith(commit_a)), None)
        vb = next((v for v in versions if (v.get("commit") or "").startswith(commit_b)), None)
        if not va:
            raise ValueError(f"Commit {commit_a} not found in versions for {path}")
        if not vb:
            raise ValueError(f"Commit {commit_b} not found in versions for {path}")
        return diff_image_versions(va, vb)

    if len(versions) >= 2:
        return diff_image_versions(versions[-1], versions[0])

    return diff_image_versions(versions[0], versions[0])


def filter_catalog(
    catalog: dict,
    repo: str | None = None,
    screen: str | None = None,
    commit: str | None = None,
    tag: str | None = None,
    extension: str | None = None,
    query: str | None = None,
    deleted_only: bool = False,
) -> dict:
    """Filter catalog items by repo, screen, commit, tag, extension, and query."""
    items = list(catalog.get("items", []))

    if repo:
        r_low = repo.lower()
        items = [
            i for i in items
            if r_low in (i.get("origin") or "").lower() or r_low in (i.get("repo") or "").lower()
        ]

    if screen:
        s_low = screen.lower()
        items = [
            i for i in items
            if s_low in (i.get("screen") or "").lower() or s_low in i.get("path", "").lower()
        ]

    if commit:
        c_low = commit.lower()
        items = [
            i for i in items
            if (i.get("commit") or "").lower().startswith(c_low)
            or any((v.get("commit") or "").lower().startswith(c_low) for v in i.get("versions", []))
        ]

    if tag:
        t_low = tag.lower()
        items = [
            i for i in items
            if any(t_low in t.lower() for t in i.get("tags", []))
            or any(t_low in t.lower() for v in i.get("versions", []) for t in v.get("tags", []))
        ]

    if extension:
        ext_clean = extension.lower().lstrip(".")
        if ext_clean in ("jpg", "jpeg"):
            allowed_exts = {".jpg", ".jpeg"}
        else:
            allowed_exts = {f".{ext_clean}"}
        items = [i for i in items if (i.get("extension") or "").lower() in allowed_exts]

    if deleted_only:
        items = [i for i in items if i.get("deleted")]

    if query:
        tokens = [t.lower() for t in query.split() if t.strip()]
        if tokens:
            items = [
                item
                for item in items
                if all(
                    tok in " ".join([
                        item.get("origin", ""),
                        item.get("ref", ""),
                        item.get("commit") or "",
                        item.get("path", ""),
                        item.get("extension", ""),
                        item.get("status", ""),
                        item.get("screen", ""),
                    ]).lower()
                    for tok in tokens
                )
            ]

    by_ext: dict[str, int] = {}
    for item in items:
        ext_key = item.get("extension") or "(none)"
        by_ext[ext_key] = by_ext.get(ext_key, 0) + 1

    filtered_catalog = dict(catalog)
    filtered_catalog["items"] = items
    filtered_catalog["summary"] = {
        "total_images": len(items),
        "active_images": sum(1 for i in items if not i.get("deleted") and not i.get("missing")),
        "deleted_images": sum(1 for i in items if i.get("deleted")),
        "missing_images": sum(1 for i in items if i.get("missing")),
        "thumbnails_generated": sum(1 for i in items if i.get("thumbnail_status") == "generated"),
        "thumbnails_skipped": sum(1 for i in items if i.get("thumbnail_status") != "generated"),
        "by_extension": dict(sorted(by_ext.items())),
    }
    return filtered_catalog


def detect_format(data: bytes, ext: str = "") -> str:
    ext_norm = ext.lower()
    if data.startswith(PNG_SIGNATURE):
        return "png"
    if data.startswith(b"\xff\xd8"):
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if ext_norm == ".svg":
        return "svg"
    head = data[:1024].decode("utf-8", "replace").lower()
    if "<svg" in head:
        return "svg"
    return "unknown"


def parse_image_dimensions(data: bytes, ext: str = "") -> tuple[int | None, int | None]:
    if not data:
        return (None, None)
    fmt = detect_format(data, ext)
    if fmt == "png":
        return _parse_png_dimensions(data)
    if fmt == "jpeg":
        return _parse_jpeg_dimensions(data)
    if fmt == "gif":
        return _parse_gif_dimensions(data)
    if fmt == "webp":
        return _parse_webp_dimensions(data)
    if fmt == "svg":
        meta = inspect_svg_inert(data)
        return (meta["width"], meta["height"])
    return (None, None)


def _encode_png_rgba(width: int, height: int, rgba_rows: list[bytes]) -> bytes:
    """Encode RGBA pixel rows into a deterministic PNG byte stream using stdlib."""
    def chunk(ctype: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(ctype + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + ctype + payload + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = b"".join(b"\x00" + row for row in rgba_rows)
    idat = zlib.compress(raw, level=6)
    return PNG_SIGNATURE + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _paeth_predictor(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _decode_png_to_rgba(data: bytes) -> tuple[int, int, list[bytes]] | None:
    """Minimal stdlib PNG decoder (8-bit RGB/RGBA/Grayscale/Grayscale+Alpha, non-interlaced)."""
    if len(data) < 24 or data[:8] != PNG_SIGNATURE:
        return None
    pos = 8
    width = height = bit_depth = color_type = interlace = 0
    idat_parts: list[bytes] = []
    seen_ihdr = False
    while pos + 8 <= len(data):
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        pos += 8
        if pos + length + 4 > len(data):
            return None
        payload = data[pos:pos + length]
        pos += length + 4
        if ctype == b"IHDR":
            if length != 13:
                return None
            width, height, bit_depth, color_type, comp, flt, interlace = struct.unpack(">IIBBBBB", payload)
            if comp != 0 or flt != 0 or interlace != 0 or bit_depth != 8:
                return None
            if color_type not in (0, 2, 4, 6) or width == 0 or height == 0:
                return None
            if width * height > MAX_IMAGE_PIXELS:
                return None
            seen_ihdr = True
        elif ctype == b"IDAT":
            idat_parts.append(payload)
        elif ctype == b"IEND":
            break
    if not seen_ihdr or not idat_parts:
        return None
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    try:
        raw = zlib.decompress(b"".join(idat_parts))
    except zlib.error:
        return None
    stride = width * channels
    if len(raw) < height * (stride + 1):
        return None

    rows: list[bytes] = []
    prev_row = bytes(stride)
    offset = 0
    for _ in range(height):
        ftype = raw[offset]
        offset += 1
        scan = bytearray(raw[offset:offset + stride])
        offset += stride
        if ftype == 1:
            for i in range(channels, stride):
                scan[i] = (scan[i] + scan[i - channels]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                scan[i] = (scan[i] + prev_row[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = scan[i - channels] if i >= channels else 0
                scan[i] = (scan[i] + ((left + prev_row[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                left = scan[i - channels] if i >= channels else 0
                up = prev_row[i]
                up_left = prev_row[i - channels] if i >= channels else 0
                scan[i] = (scan[i] + _paeth_predictor(left, up, up_left)) & 0xFF
        elif ftype != 0:
            return None
        prev_row = bytes(scan)
        if color_type == 6:
            rows.append(prev_row)
        elif color_type == 2:
            out = bytearray(width * 4)
            for x in range(width):
                s = x * 3
                d = x * 4
                out[d:d + 3] = prev_row[s:s + 3]
                out[d + 3] = 255
            rows.append(bytes(out))
        elif color_type == 0:
            out = bytearray(width * 4)
            for x in range(width):
                v = prev_row[x]
                d = x * 4
                out[d] = v
                out[d + 1] = v
                out[d + 2] = v
                out[d + 3] = 255
            rows.append(bytes(out))
        else:  # color_type == 4
            out = bytearray(width * 4)
            for x in range(width):
                v = prev_row[x * 2]
                a = prev_row[x * 2 + 1]
                d = x * 4
                out[d] = v
                out[d + 1] = v
                out[d + 2] = v
                out[d + 3] = a
            rows.append(bytes(out))
    return (width, height, rows)


def _stdlib_png_thumbnail(data: bytes, max_size: tuple[int, int]) -> tuple[bytes, int, int] | None:
    decoded = _decode_png_to_rgba(data)
    if decoded is None:
        return None
    w, h, rows = decoded
    max_w, max_h = max_size
    if w <= max_w and h <= max_h:
        return (_encode_png_rgba(w, h, rows), w, h)
    scale = min(max_w / w, max_h / h)
    tw = max(1, int(round(w * scale)))
    th = max(1, int(round(h * scale)))
    out_rows: list[bytes] = []
    for ty in range(th):
        sy = min(h - 1, (ty * h) // th)
        src_row = rows[sy]
        dst = bytearray(tw * 4)
        for tx in range(tw):
            sx = min(w - 1, (tx * w) // tw)
            s = sx * 4
            d = tx * 4
            dst[d:d + 4] = src_row[s:s + 4]
        out_rows.append(bytes(dst))
    return (_encode_png_rgba(tw, th, out_rows), tw, th)


def generate_thumbnail(
    data: bytes,
    ext: str,
    sha256_hex: str,
    thumb_dir: Path,
    max_size: tuple[int, int] = (160, 160),
    force_no_pillow: bool = False,
) -> dict:
    """Generate a deterministic PNG thumbnail.

    Uses Pillow when available; otherwise attempts a stdlib PNG thumbnail
    fallback and cleanly skips formats requiring external decoders (recording
    dimensions without failing). SVG files are always treated as inert.
    """
    validate_private_output_path(thumb_dir)
    fmt = detect_format(data, ext)
    if fmt == "svg" or ext.lower() == ".svg":
        return {
            "generated": False,
            "path": None,
            "status": "skipped_inert_svg",
            "width": None,
            "height": None,
            "sha256": None,
        }
    if not data or fmt == "unknown":
        return {
            "generated": False,
            "path": None,
            "status": "skipped_unsupported",
            "width": None,
            "height": None,
            "sha256": None,
        }

    thumb_bytes: bytes | None = None
    tw = th = 0
    if force_no_pillow or not HAS_PILLOW or Image is None:
        if fmt == "png":
            stdlib_res = _stdlib_png_thumbnail(data, max_size)
            if stdlib_res is not None:
                thumb_bytes, tw, th = stdlib_res
        if thumb_bytes is None:
            return {
                "generated": False,
                "path": None,
                "status": "skipped_no_pillow",
                "width": None,
                "height": None,
                "sha256": None,
            }
    else:
        previous_limit = getattr(Image, "MAX_IMAGE_PIXELS", None)
        try:
            Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
            with Image.open(io.BytesIO(data)) as img:
                if ImageOps is not None:
                    img = ImageOps.exif_transpose(img)
                else:
                    img.load()
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
                resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)
                img.thumbnail(max_size, resampling)
                buf = io.BytesIO()
                img.save(buf, format="PNG", compress_level=6)
                thumb_bytes = buf.getvalue()
                tw, th = img.size
        except Exception:
            return {
                "generated": False,
                "path": None,
                "status": "skipped_corrupt",
                "width": None,
                "height": None,
                "sha256": None,
            }
        finally:
            if previous_limit is not None:
                Image.MAX_IMAGE_PIXELS = previous_limit

    thumb_dir.mkdir(parents=True, exist_ok=True)
    target = thumb_dir / f"{sha256_hex[:16]}_{max_size[0]}x{max_size[1]}.png"
    tmp = target.with_suffix(".tmp")
    try:
        tmp.write_bytes(thumb_bytes)
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)

    return {
        "generated": True,
        "path": str(target),
        "status": "generated",
        "width": tw,
        "height": th,
        "sha256": hashlib.sha256(thumb_bytes).hexdigest(),
    }


def _make_data_uri(
    data: bytes,
    ext: str,
    fmt: str,
    thumb_size: int = 160,
    force_no_pillow: bool = False,
) -> str | None:
    """Generate an inert data URI for self-contained visual gallery embedding."""
    if not data:
        return None
    if fmt == "svg" or ext.lower() == ".svg":
        sanitized = sanitize_svg(data)
        b64 = base64.b64encode(sanitized.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{b64}"
    if fmt == "png":
        stdlib_res = _stdlib_png_thumbnail(data, (thumb_size, thumb_size))
        data_to_encode = stdlib_res[0] if stdlib_res is not None else data
        b64 = base64.b64encode(data_to_encode).decode("ascii")
        return f"data:image/png;base64,{b64}"
    if HAS_PILLOW and not force_no_pillow and Image is not None:
        try:
            with Image.open(io.BytesIO(data)) as img:
                if ImageOps is not None:
                    img = ImageOps.exif_transpose(img)
                else:
                    img.load()
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
                resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)
                img.thumbnail((thumb_size, thumb_size), resampling)
                buf = io.BytesIO()
                img.save(buf, format="PNG", compress_level=6)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                return f"data:image/png;base64,{b64}"
        except Exception:
            pass
    mime = f"image/{fmt}" if fmt in ("jpeg", "gif", "webp") else "image/png"
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _ref_sort_key(refname: str) -> tuple[int, str]:
    if refname == "refs/heads/main":
        return (0, refname)
    if refname.startswith("refs/heads/"):
        return (1, refname)
    if refname.startswith("refs/tags/"):
        return (2, refname)
    return (3, refname)


def _open_git_dir(source: Path, temp_root: Path) -> tuple[Path, str]:
    if not source.exists():
        raise FileNotFoundError(f"Source repository or bundle does not exist: {source}")
    if source.is_dir():
        if (source / "HEAD").is_file():
            return (source, "bare")
        if (source / ".git" / "HEAD").is_file():
            return (source / ".git", "workdir")
        raise ValueError(f"Directory is not a valid git repository: {source}")
    if source.is_file():
        bare = temp_root / "bundle-mirror.git"
        subprocess.run(
            ["git", "init", "--bare", "-q", str(bare)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        verify = subprocess.run(
            ["git", f"--git-dir={bare}", "bundle", "verify", "-q", str(source)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if verify.returncode != 0:
            err = verify.stderr.decode("utf-8", "replace").strip()[:400]
            raise ValueError(f"Invalid git bundle {source}: {err}")
        subprocess.run(
            ["git", f"--git-dir={bare}", "fetch", "-q", str(source), "refs/*:refs/*"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return (bare, "bundle")
    raise ValueError(f"Unsupported source path: {source}")


def _collect_refs(git_dir: Path) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    raw = _git_run(
        git_dir,
        "for-each-ref",
        "--format=%(refname)%09%(objectname)%09%(objecttype)%09%(*objectname)",
    ).decode("utf-8", "replace")
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        refname, obj_sha, obj_type = parts[0], parts[1], parts[2]
        peeled = parts[3] if len(parts) > 3 else ""
        commit_sha = peeled if obj_type == "tag" and peeled else obj_sha
        if re.fullmatch(r"[0-9a-f]{40,64}", commit_sha):
            refs.append((refname, commit_sha))
    refs.sort(key=lambda item: _ref_sort_key(item[0]))
    return refs


def _build_commit_ref_map(git_dir: Path, refs: list[tuple[str, str]]) -> dict[str, list[str]]:
    commit_refs: dict[str, list[str]] = {}
    for refname, _commit in refs:
        try:
            for sha in _git_stream(git_dir, "rev-list", refname):
                bucket = commit_refs.setdefault(sha, [])
                if refname not in bucket:
                    bucket.append(refname)
        except RuntimeError:
            continue
    return commit_refs


def catalog_git_source(
    source: Path,
    origin: str | None = None,
    thumb_dir: Path | None = None,
    thumb_size: int = 160,
    query: str | None = None,
    deleted_only: bool = False,
    check_paths: list[str] | None = None,
    page: int = 1,
    page_size: int = 50,
    offset: int | None = None,
    limit: int | None = None,
    force_no_pillow: bool = False,
    repo: str | None = None,
    screen: str | None = None,
    commit: str | None = None,
    tag: str | None = None,
    extension: str | None = None,
    gallery_output: Path | None = None,
    embed_thumbnails: bool = True,
) -> dict:
    """Catalog images from a local bare Git repo or Git bundle."""
    if page < 1:
        raise ValueError("page must be >= 1")
    if not 1 <= page_size <= MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")
    if offset is not None and offset < 0:
        raise ValueError("offset must be >= 0")
    if limit is not None and not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    if not MIN_THUMB_SIZE <= thumb_size <= MAX_THUMB_SIZE:
        raise ValueError(f"thumb_size must be between {MIN_THUMB_SIZE} and {MAX_THUMB_SIZE}")
    if thumb_dir is not None:
        validate_private_output_path(thumb_dir)
    if gallery_output is not None:
        validate_private_output_path(gallery_output)

    origin_label = origin or source.stem or source.name
    pillow_usable = HAS_PILLOW and not force_no_pillow

    with tempfile.TemporaryDirectory(prefix="image-catalog-") as tmp_str:
        git_dir, source_type = _open_git_dir(source, Path(tmp_str))
        refs = _collect_refs(git_dir)
        commit_ref_map = _build_commit_ref_map(git_dir, refs)

        # Key: (path, blob_sha, deleted)
        records_map: dict[tuple[str, str, bool], dict] = {}
        active_paths: set[str] = set()
        deleted_paths: set[str] = set()
        path_versions: dict[str, list[dict]] = {}

        for refname, commit_sha in refs:
            try:
                lines = list(_git_stream(git_dir, "ls-tree", "-r", "-l", commit_sha))
            except RuntimeError:
                continue
            for line in lines:
                if "\t" not in line:
                    continue
                meta, path = line.split("\t", 1)
                ext = Path(path).suffix.lower()
                if ext not in IMAGE_EXTENSIONS:
                    continue
                fields = meta.split()
                if len(fields) < 4 or fields[1] != "blob":
                    continue
                blob_sha = fields[2]
                active_paths.add(path)
                key = (path, blob_sha, False)
                if key not in records_map:
                    records_map[key] = {
                        "origin": origin_label,
                        "ref": refname,
                        "refs": [refname],
                        "commit": commit_sha,
                        "deleted_in_commit": None,
                        "blob_sha": blob_sha,
                        "path": path,
                        "extension": ext,
                        "deleted": False,
                        "missing": False,
                        "status": "present",
                    }
                elif refname not in records_map[key]["refs"]:
                    records_map[key]["refs"].append(refname)

        # Scan full commit history for revisions and deleted images
        last_sha: str | None = None
        last_date: str = ""
        last_subject: str = ""
        for line in _git_stream(
            git_dir,
            "log",
            "--all",
            "--root",
            "--no-renames",
            "--raw",
            "--abbrev=40",
            "--format=%x1e%H%x1f%aI%x1f%s",
        ):
            if line.startswith("\x1e"):
                parts = line[1:].split("\x1f", 2)
                last_sha = parts[0]
                last_date = parts[1] if len(parts) > 1 else ""
                last_subject = parts[2] if len(parts) > 2 else ""
                continue
            if not last_sha or not line.startswith(":") or "\t" not in line:
                continue
            raw_meta, path = line.split("\t", 1)
            ext = Path(path).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            fields = raw_meta.lstrip(":").split()
            if len(fields) < 5:
                continue
            old_blob = fields[2]
            new_blob = fields[3]
            status_code = fields[4][:1]

            containing_refs = commit_ref_map.get(last_sha, [])
            primary_ref = containing_refs[0] if containing_refs else ""
            tags_list = [
                r.split("refs/tags/", 1)[1]
                for r in containing_refs
                if r.startswith("refs/tags/")
            ]

            if status_code == "D":
                deleted_paths.add(path)
                parent_sha: str | None = None
                blob_sha: str | None = old_blob if old_blob != "0" * 40 else None
                try:
                    parent_sha = _git_run(git_dir, "rev-parse", f"{last_sha}^").decode("utf-8", "replace").strip()
                except RuntimeError:
                    parent_sha = None

                if blob_sha is None:
                    miss_key = (path, f"missing:{last_sha}", True)
                    if miss_key not in records_map:
                        records_map[miss_key] = {
                            "origin": origin_label,
                            "ref": primary_ref,
                            "refs": list(containing_refs),
                            "commit": parent_sha or last_sha,
                            "deleted_in_commit": last_sha,
                            "blob_sha": None,
                            "path": path,
                            "extension": ext,
                            "deleted": True,
                            "missing": True,
                            "status": "missing",
                        }
                    continue

                key = (path, blob_sha, True)
                if key not in records_map:
                    records_map[key] = {
                        "origin": origin_label,
                        "ref": primary_ref,
                        "refs": list(containing_refs),
                        "commit": parent_sha,
                        "deleted_in_commit": last_sha,
                        "blob_sha": blob_sha,
                        "path": path,
                        "extension": ext,
                        "deleted": True,
                        "missing": False,
                        "status": "deleted",
                    }

                path_versions.setdefault(path, []).append({
                    "commit": last_sha,
                    "commit_short": last_sha[:8],
                    "date": last_date,
                    "message": last_subject,
                    "blob_sha": blob_sha,
                    "action": "D",
                    "status": "deleted",
                    "deleted": True,
                    "path": path,
                    "refs": list(containing_refs),
                    "tags": tags_list,
                })
            else:
                active_paths.add(path)
                ver_blob = new_blob if new_blob != "0" * 40 else old_blob
                if ver_blob and ver_blob != "0" * 40:
                    action_code = "A" if status_code == "A" else "M"
                    path_versions.setdefault(path, []).append({
                        "commit": last_sha,
                        "commit_short": last_sha[:8],
                        "date": last_date,
                        "message": last_subject,
                        "blob_sha": ver_blob,
                        "action": action_code,
                        "status": "added" if action_code == "A" else "modified",
                        "deleted": False,
                        "path": path,
                        "refs": list(containing_refs),
                        "tags": tags_list,
                    })

        # Record any explicitly requested paths that are absent from the repository.
        if check_paths:
            for raw_p in check_paths:
                req_path = safe_path(raw_p)
                if req_path not in active_paths and req_path not in deleted_paths:
                    ext = Path(req_path).suffix.lower()
                    miss_key = (req_path, "missing:requested", False)
                    records_map[miss_key] = {
                        "origin": origin_label,
                        "ref": "",
                        "refs": [],
                        "commit": None,
                        "deleted_in_commit": None,
                        "blob_sha": None,
                        "path": req_path,
                        "extension": ext,
                        "deleted": False,
                        "missing": True,
                        "status": "missing",
                    }

        blob_shas = [
            rec["blob_sha"]
            for rec in records_map.values()
            if rec["blob_sha"] is not None
        ]
        for p_vers in path_versions.values():
            for v in p_vers:
                b = v.get("blob_sha")
                if b and b != "0" * 40:
                    blob_shas.append(b)
        blobs = _read_blobs_batch(git_dir, blob_shas)

        # Enrich version records with blob metadata and data URIs
        for p, vers in path_versions.items():
            p_ext = Path(p).suffix.lower()
            for v in vers:
                b_sha = v.get("blob_sha")
                raw_bytes = blobs.get(b_sha) if b_sha else None
                if raw_bytes is None:
                    v.update({
                        "format": "missing",
                        "bytes": None,
                        "sha256": None,
                        "width": None,
                        "height": None,
                        "inert": p_ext == ".svg",
                        "script_detected": False,
                        "data_uri": None,
                    })
                    continue
                v_fmt = detect_format(raw_bytes, p_ext)
                v_sha = hashlib.sha256(raw_bytes).hexdigest()
                if v_fmt == "svg" or p_ext == ".svg":
                    v_meta = inspect_svg_inert(raw_bytes)
                    v_w, v_h = v_meta["width"], v_meta["height"]
                    v_inert = True
                    v_script = v_meta["script_detected"]
                else:
                    v_w, v_h = parse_image_dimensions(raw_bytes, p_ext)
                    v_inert = False
                    v_script = False
                v_data_uri = (
                    _make_data_uri(raw_bytes, p_ext, v_fmt, thumb_size, force_no_pillow)
                    if embed_thumbnails
                    else None
                )
                v.update({
                    "format": v_fmt,
                    "bytes": len(raw_bytes),
                    "sha256": v_sha,
                    "width": v_w,
                    "height": v_h,
                    "inert": v_inert,
                    "script_detected": v_script,
                    "data_uri": v_data_uri,
                })

        all_items: list[dict] = []
        for rec in records_map.values():
            blob_sha = rec["blob_sha"]
            raw_bytes = blobs.get(blob_sha) if blob_sha is not None else None
            rec_tags = [
                r.split("refs/tags/", 1)[1]
                for r in rec.get("refs", [])
                if r.startswith("refs/tags/")
            ]
            rec_versions = path_versions.get(rec["path"], [])

            if raw_bytes is None:
                if not rec_versions and rec.get("commit"):
                    rec_versions = [{
                        "commit": rec["commit"],
                        "commit_short": (rec["commit"] or "")[:8],
                        "date": "",
                        "message": "",
                        "blob_sha": None,
                        "action": "D" if rec["deleted"] else "A",
                        "status": rec["status"],
                        "deleted": rec["deleted"],
                        "path": rec["path"],
                        "refs": rec.get("refs", []),
                        "tags": rec_tags,
                        "bytes": None,
                        "format": "missing",
                        "sha256": None,
                        "width": None,
                        "height": None,
                        "inert": rec["extension"] == ".svg",
                        "script_detected": False,
                        "data_uri": None,
                    }]
                rec.update({
                    "format": "missing",
                    "bytes": None,
                    "sha256": None,
                    "width": None,
                    "height": None,
                    "dimensions": None,
                    "missing": True,
                    "status": "missing",
                    "inert": rec["extension"] == ".svg",
                    "script_detected": False,
                    "thumbnail": None,
                    "thumbnail_status": "skipped_missing",
                    "screen": extract_screen_name(rec["path"]),
                    "repo": rec["origin"],
                    "tags": rec_tags,
                    "tag": rec_tags[0] if rec_tags else "",
                    "versions": rec_versions,
                    "version_count": len(rec_versions),
                    "data_uri": None,
                })
                all_items.append(rec)
                continue

            fmt = detect_format(raw_bytes, rec["extension"])
            sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
            is_svg = fmt == "svg" or rec["extension"] == ".svg"
            if is_svg:
                svg_meta = inspect_svg_inert(raw_bytes)
                width, height = svg_meta["width"], svg_meta["height"]
                inert = True
                script_detected = svg_meta["script_detected"]
            else:
                width, height = parse_image_dimensions(raw_bytes, rec["extension"])
                inert = False
                script_detected = False

            rec_data_uri = (
                _make_data_uri(raw_bytes, rec["extension"], fmt, thumb_size, force_no_pillow)
                if embed_thumbnails
                else None
            )

            if not rec_versions and rec.get("commit"):
                rec_versions = [{
                    "commit": rec["commit"],
                    "commit_short": (rec["commit"] or "")[:8],
                    "date": "",
                    "message": "",
                    "blob_sha": rec["blob_sha"],
                    "action": "D" if rec["deleted"] else "A",
                    "status": rec["status"],
                    "deleted": rec["deleted"],
                    "path": rec["path"],
                    "refs": rec.get("refs", []),
                    "tags": rec_tags,
                    "bytes": len(raw_bytes),
                    "format": fmt,
                    "sha256": sha256_hex,
                    "width": width,
                    "height": height,
                    "inert": inert,
                    "script_detected": script_detected,
                    "data_uri": rec_data_uri,
                }]

            rec.update({
                "format": fmt,
                "bytes": len(raw_bytes),
                "sha256": sha256_hex,
                "width": width,
                "height": height,
                "dimensions": (
                    {"width": width, "height": height}
                    if width is not None and height is not None
                    else None
                ),
                "inert": inert,
                "script_detected": script_detected,
                "thumbnail": None,
                "thumbnail_status": "not_requested",
                "screen": extract_screen_name(rec["path"]),
                "repo": rec["origin"],
                "tags": rec_tags,
                "tag": rec_tags[0] if rec_tags else "",
                "versions": rec_versions,
                "version_count": len(rec_versions),
                "data_uri": rec_data_uri,
                "_raw_bytes": raw_bytes,
            })
            all_items.append(rec)

    all_items.sort(
        key=lambda r: (
            r["origin"],
            r["path"],
            1 if r["deleted"] else 0,
            1 if r["missing"] else 0,
            r["commit"] or "",
            r["blob_sha"] or "",
        )
    )

    filtered = all_items
    if repo or screen or commit or tag or extension or deleted_only or query:
        filtered_cat = filter_catalog(
            {"items": all_items},
            repo=repo,
            screen=screen,
            commit=commit,
            tag=tag,
            extension=extension,
            query=query,
            deleted_only=deleted_only,
        )
        filtered = filtered_cat["items"]

    by_ext: dict[str, int] = {}
    for item in filtered:
        ext_key = item["extension"] or "(none)"
        by_ext[ext_key] = by_ext.get(ext_key, 0) + 1

    total_items = len(filtered)
    effective_offset = (page - 1) * page_size if offset is None else offset
    effective_limit = min(page_size, limit) if limit is not None else page_size
    effective_page = (effective_offset // effective_limit) + 1
    total_pages = ((total_items + effective_limit - 1) // effective_limit) if total_items else 0
    page_items = filtered[effective_offset:effective_offset + effective_limit]

    thumbs_generated = 0
    thumbs_skipped = 0
    for item in page_items:
        raw_bytes = item.pop("_raw_bytes", None)
        if item["missing"] or raw_bytes is None:
            item["thumbnail"] = None
            item["thumbnail_status"] = "skipped_missing"
            thumbs_skipped += 1
        elif thumb_dir is not None:
            thumb_info = generate_thumbnail(
                raw_bytes,
                item["extension"],
                item["sha256"],
                thumb_dir,
                max_size=(thumb_size, thumb_size),
                force_no_pillow=force_no_pillow,
            )
            item["thumbnail"] = thumb_info["path"]
            item["thumbnail_status"] = thumb_info["status"]
            if thumb_info["generated"]:
                item["thumbnail_dimensions"] = {
                    "width": thumb_info["width"],
                    "height": thumb_info["height"],
                }
                item["thumbnail_sha256"] = thumb_info["sha256"]
                thumbs_generated += 1
            else:
                thumbs_skipped += 1
        elif item["inert"]:
            item["thumbnail"] = None
            item["thumbnail_status"] = "skipped_inert_svg"
            thumbs_skipped += 1
        elif not pillow_usable:
            item["thumbnail"] = None
            item["thumbnail_status"] = "skipped_no_pillow"
            thumbs_skipped += 1
        else:
            item["thumbnail"] = None
            item["thumbnail_status"] = "not_requested"
            thumbs_skipped += 1

    for item in filtered:
        item.pop("_raw_bytes", None)

    catalog_dict = {
        "version": 1,
        "private": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "origin": origin_label,
        "source": str(source),
        "source_type": source_type,
        "pillow_available": pillow_usable,
        "pagination": {
            "page": effective_page,
            "page_size": effective_limit,
            "offset": effective_offset,
            "limit": effective_limit,
            "total_items": total_items,
            "total_pages": total_pages,
            "returned_items": len(page_items),
            "has_next": (effective_offset + len(page_items)) < total_items,
            "has_prev": effective_offset > 0,
        },
        "summary": {
            "total_images": total_items,
            "active_images": sum(1 for i in filtered if not i["deleted"] and not i["missing"]),
            "deleted_images": sum(1 for i in filtered if i["deleted"]),
            "missing_images": sum(1 for i in filtered if i["missing"]),
            "multi_version_images": sum(1 for i in filtered if len(i.get("versions", [])) > 1),
            "thumbnails_generated": thumbs_generated,
            "thumbnails_skipped": thumbs_skipped,
            "by_extension": dict(sorted(by_ext.items())),
        },
        "items": page_items,
        "limitations": [
            "Private catalog output only; never publish to site/ or GitHub Pages.",
            "SVG files are parsed as inert metadata without script or XML entity execution.",
            "Visual gallery UI and side-by-side version comparison enabled via offline self-contained HTML report.",
        ],
    }

    if gallery_output is not None:
        generate_visual_gallery(
            catalog_dict,
            output_path=gallery_output,
            embed_thumbnails=embed_thumbnails,
        )
        catalog_dict["gallery_path"] = str(gallery_output)

    return catalog_dict


def generate_visual_gallery(
    catalog: dict,
    output_path: Path | None = None,
    embed_thumbnails: bool = True,
    title: str = "Private Historical Image Catalog & Visual Gallery",
) -> str:
    """Generate an offline, self-contained HTML visual comparison gallery report."""
    if output_path is not None:
        validate_private_output_path(output_path)

    origin = catalog.get("origin", "archive")
    generated_at = catalog.get("generated_at", datetime.now(timezone.utc).isoformat())
    items = catalog.get("items", [])
    summary = catalog.get("summary", {})

    total_images = summary.get("total_images", len(items))
    active_images = summary.get("active_images", sum(1 for i in items if not i.get("deleted") and not i.get("missing")))
    deleted_images = summary.get("deleted_images", sum(1 for i in items if i.get("deleted")))
    by_ext = summary.get("by_extension", {})
    multi_version_count = sum(1 for i in items if len(i.get("versions", [])) > 1)

    repos = sorted({i.get("origin") or i.get("repo") or "unknown" for i in items if i.get("origin") or i.get("repo")})
    screens = sorted({i.get("screen") for i in items if i.get("screen")})
    tags = sorted({t for i in items for t in i.get("tags", []) if t})

    client_payload = {
        "title": title,
        "origin": origin,
        "generated_at": generated_at,
        "summary": summary,
        "items": items,
    }
    json_str = json.dumps(client_payload, ensure_ascii=False).replace("</", "<\\/")

    repo_options = "".join(f'<option value="{html.escape(r)}">{html.escape(r)}</option>' for r in repos)
    screen_options = "".join(f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in screens)
    tag_options = "".join(f'<option value="{html.escape(t)}">{html.escape(t)}</option>' for t in tags)

    ext_stats_html = "".join(
        f'<span class="stat-pill ext-{html.escape(ext.lstrip(".").lower())}">{html.escape(ext)}: {count}</span> '
        for ext, count in sorted(by_ext.items())
    )

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} - {html.escape(origin)}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --accent-bg: rgba(56, 189, 248, 0.15);
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
      --purple: #a855f7;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding: 1.5rem;
    }}
    .privacy-banner {{
      background: #450a0a;
      border: 1px solid #b91c1c;
      color: #fecaca;
      padding: 0.75rem 1rem;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      letter-spacing: 0.02em;
    }}
    .header {{
      margin-bottom: 1.5rem;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 1rem;
    }}
    .header h1 {{
      font-size: 1.6rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .header-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-top: 0.75rem;
      font-size: 0.85rem;
      color: var(--text-muted);
    }}
    .stat-pill {{
      display: inline-block;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      background: #334155;
      color: #e2e8f0;
      font-size: 0.75rem;
      font-family: var(--font-mono);
    }}
    .stat-pill.success {{ background: #064e3b; color: #a7f3d0; }}
    .stat-pill.danger {{ background: #7f1d1d; color: #fecaca; }}
    .stat-pill.warning {{ background: #78350f; color: #fde68a; }}
    .stat-pill.purple {{ background: #581c87; color: #e9d5ff; }}
    .controls {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1rem;
      margin-bottom: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }}
    .controls-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
    }}
    .search-input {{
      flex: 1;
      min-width: 240px;
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: #fff;
      padding: 0.5rem 0.75rem;
      font-size: 0.9rem;
      outline: none;
    }}
    .search-input:focus {{ border-color: var(--accent); }}
    .select-filter {{
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: #fff;
      padding: 0.5rem 0.75rem;
      font-size: 0.85rem;
      outline: none;
    }}
    .btn-group {{
      display: inline-flex;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      overflow: hidden;
    }}
    .btn {{
      background: #1e293b;
      color: #cbd5e1;
      border: none;
      padding: 0.45rem 0.8rem;
      font-size: 0.8rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }}
    .btn:hover {{ background: #334155; color: #fff; }}
    .btn.active {{ background: var(--accent); color: #0f172a; font-weight: 600; }}
    .view-switcher {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }}
    .count-indicator {{
      font-size: 0.85rem;
      color: var(--text-muted);
    }}
    .gallery-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 1.25rem;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.15s, border-color 0.15s;
    }}
    .card:hover {{
      transform: translateY(-2px);
      border-color: var(--accent);
    }}
    .card-thumb-container {{
      height: 180px;
      background: repeating-conic-gradient(#1e293b 0% 25%, #0f172a 0% 50%) 50% / 16px 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0.5rem;
      position: relative;
      border-bottom: 1px solid var(--card-border);
    }}
    .card-thumb {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      image-rendering: auto;
    }}
    .placeholder-box {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);
      font-size: 0.8rem;
      gap: 0.25rem;
      text-align: center;
      font-family: var(--font-mono);
    }}
    .card-body {{
      padding: 0.85rem;
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      flex: 1;
    }}
    .card-title {{
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 600;
      color: #f1f5f9;
      word-break: break-all;
    }}
    .card-badges {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      margin-top: 0.25rem;
    }}
    .badge {{
      display: inline-block;
      font-size: 0.7rem;
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-weight: 500;
    }}
    .badge-present {{ background: #064e3b; color: #a7f3d0; }}
    .badge-deleted {{ background: #7f1d1d; color: #fecaca; }}
    .badge-missing {{ background: #78350f; color: #fde68a; }}
    .badge-ext {{ background: #334155; color: #cbd5e1; }}
    .badge-screen {{ background: #1e1b4b; color: #c7d2fe; }}
    .badge-versions {{ background: #3b0764; color: #f5d0fe; }}
    .card-meta {{
      font-size: 0.75rem;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      margin-top: auto;
      padding-top: 0.5rem;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .card-actions {{
      margin-top: 0.5rem;
    }}
    .btn-diff {{
      width: 100%;
      background: #334155;
      color: #38bdf8;
      border: 1px solid #475569;
      padding: 0.35rem 0.6rem;
      border-radius: 4px;
      font-size: 0.75rem;
      cursor: pointer;
      font-weight: 600;
      text-align: center;
    }}
    .btn-diff:hover {{
      background: #0284c7;
      color: #fff;
    }}
    .diff-view-container {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}
    .diff-selector-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: center;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 1rem;
    }}
    .diff-summary-bar {{
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 0.75rem 1rem;
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: center;
      font-size: 0.85rem;
    }}
    .diff-summary-title {{
      font-weight: 700;
      color: #fff;
    }}
    .diff-side-by-side {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.25rem;
    }}
    @media (max-width: 768px) {{
      .diff-side-by-side {{ grid-template-columns: 1fr; }}
    }}
    .diff-panel {{
      background: #0f172a;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }}
    .diff-panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 0.5rem;
    }}
    .diff-panel-title {{
      font-weight: 600;
      color: #38bdf8;
      font-size: 0.9rem;
    }}
    .diff-img-container {{
      height: 280px;
      background: repeating-conic-gradient(#1e293b 0% 25%, #0f172a 0% 50%) 50% / 16px 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0.5rem;
      border: 1px solid var(--card-border);
      border-radius: 4px;
    }}
    .diff-img {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }}
    .diff-table {{
      width: 100%;
      font-size: 0.75rem;
      font-family: var(--font-mono);
      border-collapse: collapse;
    }}
    .diff-table td {{
      padding: 0.3rem 0.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .diff-table td:first-child {{
      color: var(--text-muted);
      width: 35%;
    }}
    .diff-delta-tag {{
      display: inline-block;
      padding: 0.1rem 0.4rem;
      border-radius: 3px;
      font-weight: 600;
      font-size: 0.75rem;
      font-family: var(--font-mono);
    }}
    .delta-plus {{ background: #064e3b; color: #a7f3d0; }}
    .delta-minus {{ background: #7f1d1d; color: #fecaca; }}
    .delta-zero {{ background: #334155; color: #cbd5e1; }}
    .modal-backdrop {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.8);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }}
    .modal-backdrop.open {{ display: flex; }}
    .modal-content {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      width: 100%;
      max-width: 1100px;
      max-height: 90vh;
      overflow-y: auto;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .modal-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 0.75rem;
    }}
    .modal-title {{
      font-size: 1.1rem;
      font-weight: 700;
      color: #fff;
      font-family: var(--font-mono);
      word-break: break-all;
    }}
    .btn-close {{
      background: #334155;
      color: #fff;
      border: none;
      border-radius: 4px;
      padding: 0.4rem 0.8rem;
      cursor: pointer;
      font-weight: 600;
    }}
    .btn-close:hover {{ background: #475569; }}
    .empty-state {{
      padding: 3rem;
      text-align: center;
      color: var(--text-muted);
      font-size: 0.95rem;
    }}
  </style>
</head>
<body>

  <div class="privacy-banner">
    <span>[CONFIDENTIAL] PRIVATE HISTORICAL ARCHIVE CATALOG - OFFLINE USE ONLY</span>
    <span>STRICT PRIVACY GATE: NEVER PUBLISH TO SITE/ OR GITHUB PAGES</span>
  </div>

  <header class="header">
    <h1>{html.escape(title)}</h1>
    <div class="header-meta">
      <span>Origin: <strong>{html.escape(origin)}</strong></span>
      <span>Total Images: <strong>{total_images}</strong></span>
      <span class="stat-pill success">Active: {active_images}</span>
      <span class="stat-pill danger">Deleted: {deleted_images}</span>
      <span class="stat-pill purple">Multi-Version: {multi_version_count}</span>
      <span>Generated: {html.escape(generated_at)}</span>
      <div style="margin-left: auto;">{ext_stats_html}</div>
    </div>
  </header>

  <div class="controls">
    <div class="controls-row">
      <input type="text" id="search-input" class="search-input" placeholder="Search by path, screen name, commit SHA, or keyword..." />
      <select id="filter-repo" class="select-filter">
        <option value="">All Repositories ({len(repos)})</option>
        {repo_options}
      </select>
      <select id="filter-screen" class="select-filter">
        <option value="">All Screens ({len(screens)})</option>
        {screen_options}
      </select>
      <select id="filter-tag" class="select-filter">
        <option value="">All Tags ({len(tags)})</option>
        {tag_options}
      </select>
    </div>
    <div class="controls-row">
      <span style="font-size: 0.8rem; color: var(--text-muted);">Extension:</span>
      <div class="btn-group" id="filter-ext-group">
        <button type="button" class="btn active" data-ext="">All</button>
        <button type="button" class="btn" data-ext=".png">PNG</button>
        <button type="button" class="btn" data-ext=".svg">SVG</button>
        <button type="button" class="btn" data-ext=".jpg">JPG</button>
        <button type="button" class="btn" data-ext=".gif">GIF</button>
        <button type="button" class="btn" data-ext=".webp">WEBP</button>
      </div>
      <span style="font-size: 0.8rem; color: var(--text-muted); margin-left: 0.5rem;">Status:</span>
      <div class="btn-group" id="filter-status-group">
        <button type="button" class="btn active" data-status="">All</button>
        <button type="button" class="btn" data-status="present">Active</button>
        <button type="button" class="btn" data-status="deleted">Deleted</button>
        <button type="button" class="btn" data-status="missing">Missing</button>
      </div>
      <div style="margin-left: auto;" class="btn-group" id="view-mode-group">
        <button type="button" class="btn active" id="btn-view-gallery">Gallery Grid</button>
        <button type="button" class="btn" id="btn-view-diff">Version Diff View ({multi_version_count})</button>
      </div>
    </div>
  </div>

  <div class="view-switcher">
    <div class="count-indicator" id="results-count">Showing {len(items)} of {total_images} images</div>
  </div>

  <!-- Main Views Container -->
  <main id="view-gallery" class="gallery-grid">
    <!-- Rendered via JS -->
  </main>

  <main id="view-diff" class="diff-view-container" style="display: none;">
    <div class="diff-selector-row">
      <label for="diff-file-select" style="font-size: 0.85rem; font-weight: 600;">Select Multi-Version Image:</label>
      <select id="diff-file-select" class="select-filter" style="flex: 1; max-width: 600px;">
        <!-- Populated via JS -->
      </select>
    </div>
    <div id="diff-content-area">
      <!-- Side by side diff rendered via JS -->
    </div>
  </main>

  <!-- Modal for side-by-side comparison from any card -->
  <div id="diff-modal" class="modal-backdrop">
    <div class="modal-content">
      <div class="modal-header">
        <div class="modal-title" id="modal-file-title">Compare Versions</div>
        <button type="button" class="btn-close" id="btn-modal-close">[Close X]</button>
      </div>
      <div id="modal-diff-content">
        <!-- Rendered via JS -->
      </div>
    </div>
  </div>

  <script type="application/json" id="catalog-data">
{json_str}
  </script>

  <script>
    (function() {{
      const rawData = JSON.parse(document.getElementById("catalog-data").textContent);
      const allItems = rawData.items || [];

      let state = {{
        search: "",
        repo: "",
        screen: "",
        tag: "",
        ext: "",
        status: "",
        viewMode: "gallery",
        diffSelectedPath: "",
        diffVerAIdx: 0,
        diffVerBIdx: 1
      }};

      const searchInput = document.getElementById("search-input");
      const filterRepo = document.getElementById("filter-repo");
      const filterScreen = document.getElementById("filter-screen");
      const filterTag = document.getElementById("filter-tag");
      const filterExtGroup = document.getElementById("filter-ext-group");
      const filterStatusGroup = document.getElementById("filter-status-group");
      const galleryView = document.getElementById("view-gallery");
      const diffView = document.getElementById("view-diff");
      const btnViewGallery = document.getElementById("btn-view-gallery");
      const btnViewDiff = document.getElementById("btn-view-diff");
      const resultsCount = document.getElementById("results-count");
      const diffFileSelect = document.getElementById("diff-file-select");
      const diffContentArea = document.getElementById("diff-content-area");
      const diffModal = document.getElementById("diff-modal");
      const btnModalClose = document.getElementById("btn-modal-close");
      const modalFileTitle = document.getElementById("modal-file-title");
      const modalDiffContent = document.getElementById("modal-diff-content");

      function escapeHtml(str) {{
        if (!str) return "";
        return String(str)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");
      }}

      function formatBytes(bytes) {{
        if (bytes == null || isNaN(bytes)) return "unknown size";
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / (1024 * 1024)).toFixed(2) + " MB";
      }}

      function getFilteredItems() {{
        const q = state.search.toLowerCase().trim();
        const r = state.repo.toLowerCase();
        const s = state.screen.toLowerCase();
        const t = state.tag.toLowerCase();
        const ext = state.ext.toLowerCase();
        const stat = state.status.toLowerCase();

        return allItems.filter(item => {{
          if (ext) {{
            const itemExt = (item.extension || "").toLowerCase();
            if (ext === ".jpg" || ext === ".jpeg") {{
              if (itemExt !== ".jpg" && itemExt !== ".jpeg") return false;
            }} else if (itemExt !== ext) {{
              return false;
            }}
          }}
          if (stat) {{
            if (stat === "present" && (item.deleted || item.missing)) return false;
            if (stat === "deleted" && !item.deleted) return false;
            if (stat === "missing" && !item.missing) return false;
          }}
          if (r) {{
            const itemRepo = (item.origin || item.repo || "").toLowerCase();
            if (itemRepo !== r) return false;
          }}
          if (s) {{
            const itemScreen = (item.screen || "").toLowerCase();
            if (itemScreen !== s && !item.path.toLowerCase().includes(s)) return false;
          }}
          if (t) {{
            const hasTag = (item.tags || []).some(tag => tag.toLowerCase() === t) ||
                           (item.versions || []).some(v => (v.tags || []).some(tag => tag.toLowerCase() === t));
            if (!hasTag) return false;
          }}
          if (q) {{
            const haystack = [
              item.path || "",
              item.screen || "",
              item.origin || "",
              item.commit || "",
              item.sha256 || "",
              item.status || "",
              item.extension || ""
            ].join(" ").toLowerCase();
            if (!haystack.includes(q)) return false;
          }}
          return true;
        }});
      }}

      function renderCard(item) {{
        const ext = (item.extension || "").toUpperCase().replace(".", "") || "BIN";
        const statusClass = item.deleted ? "badge-deleted" : (item.missing ? "badge-missing" : "badge-present");
        const statusLabel = item.deleted ? "[DELETED]" : (item.missing ? "[MISSING]" : "[ACTIVE]");
        const dims = (item.width && item.height) ? `${{item.width}}x${{item.height}} px` : "Dimensions N/A";
        const sizeStr = formatBytes(item.bytes);
        const versionsCount = (item.versions && item.versions.length) ? item.versions.length : 1;
        const commitShort = (item.commit || "none").slice(0, 8);
        const screenName = item.screen || "default";

        let previewHtml = "";
        if (item.data_uri) {{
          previewHtml = `<img src="${{item.data_uri}}" alt="${{escapeHtml(item.path)}}" class="card-thumb" loading="lazy" />`;
        }} else if (item.thumbnail) {{
          previewHtml = `<img src="${{escapeHtml(item.thumbnail)}}" alt="${{escapeHtml(item.path)}}" class="card-thumb" loading="lazy" />`;
        }} else {{
          previewHtml = `
            <div class="placeholder-box">
              <span>[${{escapeHtml(ext)}}]</span>
              <span>${{escapeHtml(dims)}}</span>
              <span>${{escapeHtml(statusLabel)}}</span>
            </div>`;
        }}

        const compareBtn = versionsCount > 1
          ? `<div class="card-actions">
               <button type="button" class="btn-diff" data-path="${{escapeHtml(item.path)}}">
                 Compare Versions (${{versionsCount}})
               </button>
             </div>`
          : "";

        return `
          <div class="card">
            <div class="card-thumb-container">
              ${{previewHtml}}
            </div>
            <div class="card-body">
              <div class="card-title" title="${{escapeHtml(item.path)}}">${{escapeHtml(item.path)}}</div>
              <div class="card-badges">
                <span class="badge badge-ext">${{escapeHtml(ext)}}</span>
                <span class="badge ${{statusClass}}">${{escapeHtml(statusLabel)}}</span>
                <span class="badge badge-screen">screen:${{escapeHtml(screenName)}}</span>
                ${{versionsCount > 1 ? `<span class="badge badge-versions">${{versionsCount}} versions</span>` : ""}}
              </div>
              <div class="card-meta">
                <span>${{escapeHtml(dims)}}</span>
                <span>${{escapeHtml(sizeStr)}}</span>
                <span>commit:${{escapeHtml(commitShort)}}</span>
              </div>
              ${{compareBtn}}
            </div>
          </div>
        `;
      }}

      function renderGallery() {{
        const filtered = getFilteredItems();
        resultsCount.textContent = `Showing ${{filtered.length}} of ${{allItems.length}} images`;
        if (filtered.length === 0) {{
          galleryView.innerHTML = '<div class="empty-state">No matching images found for the active filters.</div>';
          return;
        }}
        galleryView.innerHTML = filtered.map(renderCard).join("");

        galleryView.querySelectorAll(".btn-diff").forEach(btn => {{
          btn.addEventListener("click", () => {{
            const p = btn.getAttribute("data-path");
            openDiffModal(p);
          }});
        }});
      }}

      function renderDiffSideBySide(item, verAIdx, verBIdx) {{
        const versions = item.versions || [];
        if (versions.length === 0) {{
          return '<div class="empty-state">No version history available for this file.</div>';
        }}
        const vA = versions[verAIdx] || versions[0];
        const vB = versions[verBIdx] || (versions.length > 1 ? versions[1] : versions[0]);

        const sameContent = Boolean(vA.sha256 && vB.sha256 && vA.sha256 === vB.sha256);
        const dimsChanged = (vA.width !== vB.width || vA.height !== vB.height);
        const wDelta = (vA.width != null && vB.width != null) ? (vB.width - vA.width) : null;
        const hDelta = (vA.height != null && vB.height != null) ? (vB.height - vA.height) : null;
        const bytesDelta = (vA.bytes != null && vB.bytes != null) ? (vB.bytes - vA.bytes) : null;

        let deltaDimsTag = '<span class="diff-delta-tag delta-zero">Dimensions unchanged</span>';
        if (dimsChanged) {{
          const wdStr = wDelta != null ? (wDelta >= 0 ? "+" + wDelta : String(wDelta)) : "?";
          const hdStr = hDelta != null ? (hDelta >= 0 ? "+" + hDelta : String(hDelta)) : "?";
          deltaDimsTag = `<span class="diff-delta-tag delta-plus">Dims: ${{wdStr}}w, ${{hdStr}}h</span>`;
        }}

        let deltaBytesTag = '<span class="diff-delta-tag delta-zero">Size unchanged</span>';
        if (bytesDelta != null && bytesDelta !== 0) {{
          const bdStr = bytesDelta > 0 ? "+" + formatBytes(bytesDelta) : "-" + formatBytes(Math.abs(bytesDelta));
          const cls = bytesDelta > 0 ? "delta-plus" : "delta-minus";
          deltaBytesTag = `<span class="diff-delta-tag ${{cls}}">Size: ${{bdStr}}</span>`;
        }}

        const contentTag = sameContent
          ? '<span class="diff-delta-tag delta-zero">Content: Identical</span>'
          : '<span class="diff-delta-tag delta-plus">Content: Modified</span>';

        function renderPanel(ver, label, selectId, activeIdx) {{
          const preview = ver.data_uri
            ? `<img src="${{ver.data_uri}}" alt="version preview" class="diff-img" />`
            : `<div class="placeholder-box"><span>[NO PREVIEW]</span><span>${{escapeHtml(ver.status || "")}}</span></div>`;

          const options = versions.map((v, idx) => `
            <option value="${{idx}}" ${{idx === activeIdx ? "selected" : ""}}>
              v${{versions.length - idx}} [${{(v.commit || "head").slice(0, 8)}}] ${{escapeHtml(v.status || "present")}} - ${{escapeHtml(v.date ? v.date.slice(0, 10) : "")}}
            </option>
          `).join("");

          return `
            <div class="diff-panel">
              <div class="diff-panel-header">
                <span class="diff-panel-title">${{label}}</span>
                <select id="${{selectId}}" class="select-filter">
                  ${{options}}
                </select>
              </div>
              <div class="diff-img-container">
                ${{preview}}
              </div>
              <table class="diff-table">
                <tr><td>Commit:</td><td><code>${{escapeHtml(ver.commit || "none")}}</code></td></tr>
                <tr><td>Date:</td><td>${{escapeHtml(ver.date || "N/A")}}</td></tr>
                <tr><td>Message:</td><td>${{escapeHtml(ver.message || "N/A")}}</td></tr>
                <tr><td>Resolution:</td><td>${{ver.width != null && ver.height != null ? ver.width + "x" + ver.height + " px" : "N/A"}}</td></tr>
                <tr><td>File Size:</td><td>${{formatBytes(ver.bytes)}}</td></tr>
                <tr><td>SHA-256:</td><td><code>${{escapeHtml(ver.sha256 || "N/A")}}</code></td></tr>
                <tr><td>Status:</td><td><strong>${{escapeHtml(ver.status || "present")}}</strong></td></tr>
                <tr><td>Tags:</td><td>${{escapeHtml((ver.tags || []).join(", ") || "(none)")}}</td></tr>
              </table>
            </div>
          `;
        }}

        return `
          <div class="diff-summary-bar">
            <span class="diff-summary-title">Diff Comparison:</span>
            ${{contentTag}}
            ${{deltaDimsTag}}
            ${{deltaBytesTag}}
          </div>
          <div class="diff-side-by-side">
            ${{renderPanel(vA, "Version A (Reference / Older)", "sel-ver-a", verAIdx)}}
            ${{renderPanel(vB, "Version B (Target / Newer)", "sel-ver-b", verBIdx)}}
          </div>
        `;
      }}

      function updateDiffView() {{
        const multiVerItems = allItems.filter(i => (i.versions || []).length > 1);
        if (multiVerItems.length === 0) {{
          diffFileSelect.innerHTML = '<option value="">No multi-version images found</option>';
          diffContentArea.innerHTML = '<div class="empty-state">No images with multiple versions were found in the catalog.</div>';
          return;
        }}
        if (!state.diffSelectedPath || !multiVerItems.some(i => i.path === state.diffSelectedPath)) {{
          state.diffSelectedPath = multiVerItems[0].path;
          state.diffVerAIdx = (multiVerItems[0].versions.length > 1) ? multiVerItems[0].versions.length - 1 : 0;
          state.diffVerBIdx = 0;
        }}
        diffFileSelect.innerHTML = multiVerItems.map(item => `
          <option value="${{escapeHtml(item.path)}}" ${{item.path === state.diffSelectedPath ? "selected" : ""}}>
            ${{escapeHtml(item.path)}} (${{(item.versions || []).length}} versions)
          </option>
        `).join("");

        const item = multiVerItems.find(i => i.path === state.diffSelectedPath);
        if (item) {{
          diffContentArea.innerHTML = renderDiffSideBySide(item, state.diffVerAIdx, state.diffVerBIdx);
          attachDiffSelectEvents(item);
        }}
      }}

      function attachDiffSelectEvents(item) {{
        const sA = document.getElementById("sel-ver-a");
        const sB = document.getElementById("sel-ver-b");
        if (sA) sA.addEventListener("change", e => {{
          state.diffVerAIdx = parseInt(e.target.value, 10);
          diffContentArea.innerHTML = renderDiffSideBySide(item, state.diffVerAIdx, state.diffVerBIdx);
          attachDiffSelectEvents(item);
        }});
        if (sB) sB.addEventListener("change", e => {{
          state.diffVerBIdx = parseInt(e.target.value, 10);
          diffContentArea.innerHTML = renderDiffSideBySide(item, state.diffVerAIdx, state.diffVerBIdx);
          attachDiffSelectEvents(item);
        }});
      }}

      function openDiffModal(path) {{
        const item = allItems.find(i => i.path === path);
        if (!item || !item.versions || item.versions.length < 2) return;
        modalFileTitle.textContent = "Version Comparison: " + item.path;
        let vAIdx = item.versions.length - 1;
        let vBIdx = 0;

        function refreshModal() {{
          modalDiffContent.innerHTML = renderDiffSideBySide(item, vAIdx, vBIdx);
          const sA = modalDiffContent.querySelector("#sel-ver-a");
          const sB = modalDiffContent.querySelector("#sel-ver-b");
          if (sA) sA.addEventListener("change", e => {{
            vAIdx = parseInt(e.target.value, 10);
            refreshModal();
          }});
          if (sB) sB.addEventListener("change", e => {{
            vBIdx = parseInt(e.target.value, 10);
            refreshModal();
          }});
        }}

        refreshModal();
        diffModal.classList.add("open");
      }}

      function closeDiffModal() {{
        diffModal.classList.remove("open");
      }}

      searchInput.addEventListener("input", e => {{
        state.search = e.target.value;
        renderGallery();
      }});
      filterRepo.addEventListener("change", e => {{
        state.repo = e.target.value;
        renderGallery();
      }});
      filterScreen.addEventListener("change", e => {{
        state.screen = e.target.value;
        renderGallery();
      }});
      filterTag.addEventListener("change", e => {{
        state.tag = e.target.value;
        renderGallery();
      }});

      filterExtGroup.querySelectorAll(".btn").forEach(btn => {{
        btn.addEventListener("click", () => {{
          filterExtGroup.querySelectorAll(".btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          state.ext = btn.getAttribute("data-ext");
          renderGallery();
        }});
      }});

      filterStatusGroup.querySelectorAll(".btn").forEach(btn => {{
        btn.addEventListener("click", () => {{
          filterStatusGroup.querySelectorAll(".btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          state.status = btn.getAttribute("data-status");
          renderGallery();
        }});
      }});

      btnViewGallery.addEventListener("click", () => {{
        btnViewGallery.classList.add("active");
        btnViewDiff.classList.remove("active");
        galleryView.style.display = "grid";
        diffView.style.display = "none";
        state.viewMode = "gallery";
      }});

      btnViewDiff.addEventListener("click", () => {{
        btnViewDiff.classList.add("active");
        btnViewGallery.classList.remove("active");
        galleryView.style.display = "none";
        diffView.style.display = "flex";
        state.viewMode = "diff";
        updateDiffView();
      }});

      diffFileSelect.addEventListener("change", e => {{
        state.diffSelectedPath = e.target.value;
        const item = allItems.find(i => i.path === state.diffSelectedPath);
        if (item && item.versions) {{
          state.diffVerAIdx = item.versions.length > 1 ? item.versions.length - 1 : 0;
          state.diffVerBIdx = 0;
        }}
        updateDiffView();
      }});

      btnModalClose.addEventListener("click", closeDiffModal);
      diffModal.addEventListener("click", e => {{
        if (e.target === diffModal) closeDiffModal();
      }});

      renderGallery();
    }})();
  </script>
</body>
</html>
"""
    if output_path is not None:
        validate_private_output_path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = output_path.with_suffix(output_path.suffix + ".tmp")
        try:
            tmp.write_text(html_content, encoding="utf-8")
            tmp.replace(output_path)
        finally:
            tmp.unlink(missing_ok=True)
    return html_content


def write_private_catalog(catalog: dict, output: Path) -> Path:
    validate_private_output_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    try:
        tmp.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp.replace(output)
    finally:
        tmp.unlink(missing_ok=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to a local bare Git repository or Git bundle file",
    )
    parser.add_argument("--origin", help="Origin repository label")
    parser.add_argument("--output", type=Path, help="Private JSON output file (never inside site/)")
    parser.add_argument(
        "--gallery-output",
        "--html",
        dest="gallery_output",
        type=Path,
        help="Private self-contained HTML visual gallery report (never inside site/)",
    )
    parser.add_argument("--thumb-dir", type=Path, help="Private directory for deterministic PNG thumbnails")
    parser.add_argument("--thumb-size", type=int, default=160)
    parser.add_argument("--query", help="Filter images by path, ref, commit, or origin tokens")
    parser.add_argument("--deleted-only", action="store_true")
    parser.add_argument("--check-path", action="append", dest="check_paths", default=[])
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=50)
    parser.add_argument("--offset", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--no-pillow", action="store_true", help="Force stdlib-only mode (skip thumbnails)")
    parser.add_argument("--repo", help="Filter images by origin/repository")
    parser.add_argument("--screen", help="Filter images by screen name")
    parser.add_argument("--commit", help="Filter images by commit SHA")
    parser.add_argument("--tag", help="Filter images by git tag")
    parser.add_argument("--ext", help="Filter images by extension (e.g. svg, png, jpg, gif)")
    parser.add_argument("--diff", help="Path of an image to compare versions across commits")
    parser.add_argument("--no-embed-thumbnails", action="store_true", help="Reference thumbnails instead of base64 embedding")
    args = parser.parse_args()

    catalog = catalog_git_source(
        source=args.source,
        origin=args.origin,
        thumb_dir=args.thumb_dir,
        thumb_size=args.thumb_size,
        query=args.query,
        deleted_only=args.deleted_only,
        check_paths=args.check_paths or None,
        page=args.page,
        page_size=args.page_size,
        offset=args.offset,
        limit=args.limit,
        force_no_pillow=args.no_pillow,
        repo=args.repo,
        screen=args.screen,
        commit=args.commit,
        tag=args.tag,
        extension=args.ext,
        gallery_output=args.gallery_output,
        embed_thumbnails=not args.no_embed_thumbnails,
    )
    if args.diff:
        diff_result = compare_versions(catalog, args.diff)
        print(json.dumps(diff_result, ensure_ascii=False, indent=2))
        return

    if args.output is not None:
        write_private_catalog(catalog, args.output)
    print(json.dumps(catalog, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
