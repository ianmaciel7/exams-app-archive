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
from datetime import datetime, timezone
import hashlib
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

        # Scan full commit history for deleted images (including historical commits).
        last_sha: str | None = None
        for line in _git_stream(
            git_dir,
            "log",
            "--all",
            "--root",
            "--no-renames",
            "--name-status",
            "--format=%x1e%H%x1f%aI%x1f%s",
        ):
            if line.startswith("\x1e"):
                last_sha = line[1:].split("\x1f", 2)[0]
                continue
            if not last_sha or "\t" not in line:
                continue
            parts = line.split("\t")
            status_code = parts[0][:1]
            if status_code != "D":
                continue
            path = parts[-1]
            ext = Path(path).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            deleted_paths.add(path)
            containing_refs = commit_ref_map.get(last_sha, [])
            primary_ref = containing_refs[0] if containing_refs else ""
            parent_sha: str | None = None
            blob_sha: str | None = None
            try:
                parent_sha = _git_run(git_dir, "rev-parse", f"{last_sha}^").decode("utf-8", "replace").strip()
                blob_sha = _git_run(git_dir, "rev-parse", f"{parent_sha}:{path}").decode("utf-8", "replace").strip()
            except RuntimeError:
                blob_sha = None

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
        blobs = _read_blobs_batch(git_dir, blob_shas)

        all_items: list[dict] = []
        for rec in records_map.values():
            blob_sha = rec["blob_sha"]
            raw_bytes = blobs.get(blob_sha) if blob_sha is not None else None
            if raw_bytes is None:
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
    if deleted_only:
        filtered = [item for item in filtered if item["deleted"]]
    if query:
        tokens = [t.lower() for t in query.split() if t.strip()]
        if tokens:
            filtered = [
                item
                for item in filtered
                if all(
                    tok in " ".join([
                        item["origin"],
                        item["ref"],
                        item["commit"] or "",
                        item["path"],
                        item["extension"],
                        item["status"],
                    ]).lower()
                    for tok in tokens
                )
            ]

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

    # Strip internal byte buffers from items outside the returned slice too.
    for item in filtered:
        item.pop("_raw_bytes", None)

    return {
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
            "thumbnails_generated": thumbs_generated,
            "thumbnails_skipped": thumbs_skipped,
            "by_extension": dict(sorted(by_ext.items())),
        },
        "items": page_items,
        "limitations": [
            "Private catalog output only; never publish to site/ or GitHub Pages.",
            "SVG files are parsed as inert metadata without script or XML entity execution.",
            "Visual gallery UI and side-by-side version comparison remain pending.",
        ],
    }


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
    )
    if args.output is not None:
        write_private_catalog(catalog, args.output)
    print(json.dumps(catalog, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
