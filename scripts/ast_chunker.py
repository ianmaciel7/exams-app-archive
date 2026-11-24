#!/usr/bin/env python3
"""Structural AST chunker and deterministic UI/motion contract extractor.

Evolves line-based chunking (40-line fixed windows in scripts/content_index.py)
into deterministic structural AST chunks using only the Python standard library:
- Python: stdlib `ast` module for modules, classes, functions, async functions,
  methods, and timer/motion calls.
- TypeScript / TSX / JavaScript / JSX: deterministic lexer + brace-balanced
  structural parser identifying React/TSX components, hooks, functions, classes,
  event handlers (`onMouseEnter`, `onMouseLeave`, `onClick`, etc.), timers
  (`setTimeout`, `setInterval`, `requestAnimationFrame`), WAAPI `.animate(...)`
  calls, and Tailwind transition/duration/delay/ease tokens.
- CSS / SCSS / HTML `<style>`: deterministic rule and `@keyframes` parser
  extracting selectors, keyframe blocks, and motion contracts (properties,
  duration, delay, easing, reduced-motion media rules).

Every chunk carries deterministic byte/char offsets (`start_offset`, `end_offset`),
1-based lines (`start_line`, `end_line`), `node_type`, `name`, `parent_context`,
`language`, `blob_sha` (Git blob SHA-1 compatible when requested or SHA-256 fallback),
`chunk_sha`, `motion_contracts`, and optional `symbol_id` / `extractor_version`.

Also includes a reproducible benchmark comparing 40-line fixed chunking vs AST
structural chunking across sidebar, graph, and motion corpus fixtures.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import sqlite3
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

EXTRACTOR_VERSION = "1.0.0"

LANGUAGE_ALIASES: dict[str, str] = {
    "py": "python",
    "python": "python",
    ".py": "python",
    ".pyi": "python",
    "ts": "typescript",
    "typescript": "typescript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    "tsx": "tsx",
    ".tsx": "tsx",
    "js": "javascript",
    "javascript": "javascript",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    "jsx": "jsx",
    ".jsx": "jsx",
    "css": "css",
    ".css": "css",
    "scss": "css",
    ".scss": "css",
    "html": "html",
    ".html": "html",
    ".htm": "html",
}

HANDLER_PROP_RE = re.compile(
    r"\b(on(?:MouseEnter|MouseLeave|MouseMove|MouseDown|MouseUp|Click|DoubleClick|"
    r"PointerDown|PointerMove|PointerUp|PointerEnter|PointerLeave|DragStart|DragOver|"
    r"DragEnd|Drop|KeyDown|KeyUp|Focus|Blur|TransitionEnd|AnimationEnd))\b"
)
ADD_EVENT_RE = re.compile(
    r"\baddEventListener\s*\(\s*['\"](mouseenter|mouseleave|mousemove|mousedown|mouseup|"
    r"click|pointerdown|pointermove|pointerup|dragstart|dragover|dragend|drop|keydown|"
    r"focus|blur|transitionend|animationend)['\"]"
)
TIMER_CALL_RE = re.compile(
    r"\b(setTimeout|setInterval|clearTimeout|clearInterval|requestAnimationFrame)\s*\("
)
WAAPI_ANIMATE_RE = re.compile(r"\.animate\s*\(")

# Tailwind motion token patterns (e.g. duration-200, delay-150, ease-out, transition-opacity)
TW_DURATION_RE = re.compile(r"\bduration-(\d+|\[[^\]]+\])\b")
TW_DELAY_RE = re.compile(r"\bdelay-(\d+|\[[^\]]+\])\b")
TW_EASE_RE = re.compile(r"\bease-(linear|in-out|in|out|\[[^\]]+\])\b")
TW_TRANSITION_RE = re.compile(
    r"\b(transition(?:-(?:none|all|colors|opacity|shadow|transform))?|animate-[a-z0-9-]+|motion-reduce:[a-z0-9:-]+)\b"
)

# CSS transition / animation declaration patterns
CSS_TRANSITION_PROP_RE = re.compile(
    r"(?<![-\w])transition(?:-property|-duration|-timing-function|-delay)?\s*:\s*([^;}{]+)",
    re.IGNORECASE,
)
CSS_ANIMATION_PROP_RE = re.compile(
    r"(?<![-\w])animation(?:-name|-duration|-timing-function|-delay|-iteration-count)?\s*:\s*([^;}{]+)",
    re.IGNORECASE,
)
CSS_TIME_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(ms|s)\b", re.IGNORECASE)
CSS_EASING_RE = re.compile(
    r"\b(cubic-bezier\([^)]+\)|steps\([^)]+\)|ease-in-out|ease-out|ease-in|ease|linear)\b",
    re.IGNORECASE,
)
REDUCED_MOTION_RE = re.compile(r"prefers-reduced-motion|motion-reduce:", re.IGNORECASE)


@dataclass(frozen=True)
class MotionContract:
    """Deterministic motion/interaction timing contract extracted from code/styles."""

    kind: str  # "css-transition" | "css-animation" | "tailwind" | "waapi" | "timer" | "handler"
    properties: tuple[str, ...] = ()
    duration_ms: float | None = None
    delay_ms: float | None = None
    easing: str | None = None
    reduced_motion: bool = False
    trigger: str | None = None
    raw_snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "properties": list(self.properties),
            "duration_ms": self.duration_ms,
            "delay_ms": self.delay_ms,
            "easing": self.easing,
            "reduced_motion": self.reduced_motion,
            "trigger": self.trigger,
            "raw_snippet": self.raw_snippet,
        }


@dataclass(frozen=True)
class ASTChunk:
    """Structural code/style chunk with deterministic offsets, lineage, and blob hash."""

    chunk_index: int
    node_type: str
    name: str
    parent_context: str
    language: str
    start_line: int
    end_line: int
    start_offset: int
    end_offset: int
    blob_sha: str
    chunk_sha: str
    content: str
    symbol_id: str = ""
    extractor_version: str = EXTRACTOR_VERSION
    status: str = "parsed"
    motion_contracts: tuple[MotionContract, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_index": self.chunk_index,
            "node_type": self.node_type,
            "name": self.name,
            "parent_context": self.parent_context,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "blob_sha": self.blob_sha,
            "chunk_sha": self.chunk_sha,
            "symbol_id": self.symbol_id,
            "extractor_version": self.extractor_version,
            "status": self.status,
            "content": self.content,
            "motion_contracts": [m.to_dict() for m in self.motion_contracts],
        }


def normalize_language(language_or_ext: str) -> str:
    key = (language_or_ext or "").strip().lower()
    return LANGUAGE_ALIASES.get(key, key or "text")


def compute_git_blob_sha(text: str) -> str:
    """Compute exact Git blob SHA-1 hash for deterministic deduplication."""
    raw = text.encode("utf-8")
    header = f"blob {len(raw)}\x00".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _compute_chunk_sha(content: str, node_type: str, name: str, parent_context: str) -> str:
    payload = f"{EXTRACTOR_VERSION}|{node_type}|{name}|{parent_context}|{content}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _line_starts(text: str) -> list[int]:
    """Return 0-based character offset of each 1-based line start."""
    starts = [0]
    for idx, ch in enumerate(text):
        if ch == "\n":
            starts.append(idx + 1)
    return starts


def _offset_to_line(starts: list[int], offset: int) -> int:
    """Binary search 1-based line number for a 0-based character offset."""
    lo, hi = 0, len(starts) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if starts[mid] <= offset:
            lo = mid + 1
        else:
            hi = mid - 1
    return max(1, hi + 1)


def _line_col_to_offset(starts: list[int], line: int, col: int, text_len: int) -> int:
    idx = max(0, min(line - 1, len(starts) - 1))
    return max(0, min(starts[idx] + max(0, col), text_len))


def _parse_time_to_ms(value: str, unit: str) -> float:
    num = float(value)
    return num * 1000.0 if unit.lower() == "s" else num


def extract_motion_contracts(text: str, language: str) -> tuple[MotionContract, ...]:
    """Extract deterministic motion/timing contracts from code, Tailwind classes, WAAPI, or CSS."""
    contracts: list[MotionContract] = []
    seen: set[tuple[Any, ...]] = set()
    has_reduced_motion = bool(REDUCED_MOTION_RE.search(text))

    def add_contract(c: MotionContract) -> None:
        key = (
            c.kind,
            c.properties,
            c.duration_ms,
            c.delay_ms,
            c.easing,
            c.reduced_motion,
            c.trigger,
            c.raw_snippet,
        )
        if key not in seen:
            seen.add(key)
            contracts.append(c)

    # 1. CSS transitions & animations
    for m in CSS_TRANSITION_PROP_RE.finditer(text):
        val = " ".join(m.group(1).strip().split())
        times = [_parse_time_to_ms(t.group(1), t.group(2)) for t in CSS_TIME_RE.finditer(val)]
        dur = times[0] if len(times) >= 1 else None
        delay = times[1] if len(times) >= 2 else None
        ease_m = CSS_EASING_RE.search(val)
        easing = ease_m.group(1).lower() if ease_m else None
        prop_tokens = tuple(
            tok
            for tok in re.findall(r"[a-z-]+", val.lower())
            if tok not in {"ms", "s", "ease", "ease-in", "ease-out", "ease-in-out", "linear"}
            and not tok.isdigit()
        )
        add_contract(
            MotionContract(
                kind="css-transition",
                properties=prop_tokens[:6],
                duration_ms=dur,
                delay_ms=delay,
                easing=easing,
                reduced_motion=has_reduced_motion,
                trigger="css-transition",
                raw_snippet=m.group(0).strip()[:160],
            )
        )

    for m in CSS_ANIMATION_PROP_RE.finditer(text):
        val = " ".join(m.group(1).strip().split())
        times = [_parse_time_to_ms(t.group(1), t.group(2)) for t in CSS_TIME_RE.finditer(val)]
        dur = times[0] if len(times) >= 1 else None
        delay = times[1] if len(times) >= 2 else None
        ease_m = CSS_EASING_RE.search(val)
        easing = ease_m.group(1).lower() if ease_m else None
        add_contract(
            MotionContract(
                kind="css-animation",
                properties=("animation",),
                duration_ms=dur,
                delay_ms=delay,
                easing=easing,
                reduced_motion=has_reduced_motion,
                trigger="css-animation",
                raw_snippet=m.group(0).strip()[:160],
            )
        )

    # 2. Tailwind utility motion contracts (inspect line-by-line for cohesive classes)
    if language in {"tsx", "jsx", "typescript", "javascript", "html", "css"}:
        for line in text.splitlines():
            tw_trans = TW_TRANSITION_RE.findall(line)
            tw_dur = TW_DURATION_RE.findall(line)
            tw_delay = TW_DELAY_RE.findall(line)
            tw_ease = TW_EASE_RE.findall(line)
            if tw_trans or tw_dur or tw_delay:
                dur_ms: float | None = None
                if tw_dur:
                    raw_d = tw_dur[0].strip("[]")
                    if raw_d.endswith("ms"):
                        raw_d = raw_d[:-2]
                    elif raw_d.endswith("s"):
                        try:
                            dur_ms = float(raw_d[:-1]) * 1000.0
                            raw_d = ""
                        except ValueError:
                            raw_d = ""
                    if raw_d:
                        try:
                            dur_ms = float(raw_d)
                        except ValueError:
                            dur_ms = None
                delay_ms: float | None = None
                if tw_delay:
                    raw_dl = tw_delay[0].strip("[]")
                    if raw_dl.endswith("ms"):
                        raw_dl = raw_dl[:-2]
                    try:
                        delay_ms = float(raw_dl)
                    except ValueError:
                        delay_ms = None
                easing = tw_ease[0] if tw_ease else None
                props = tuple(dict.fromkeys(tw_trans))[:6]
                add_contract(
                    MotionContract(
                        kind="tailwind",
                        properties=props,
                        duration_ms=dur_ms,
                        delay_ms=delay_ms,
                        easing=easing,
                        reduced_motion=has_reduced_motion or ("motion-reduce:" in line),
                        trigger="tailwind-class",
                        raw_snippet=line.strip()[:160],
                    )
                )

    # 3. WAAPI .animate(keyframes, options)
    for m in WAAPI_ANIMATE_RE.finditer(text):
        window = text[m.start() : min(len(text), m.start() + 360)]
        dur_m = re.search(r"duration\s*:\s*(\d+(?:\.\d+)?)", window)
        delay_m = re.search(r"delay\s*:\s*(\d+(?:\.\d+)?)", window)
        ease_m = re.search(r"easing\s*:\s*['\"]([^'\"]+)['\"]", window)
        props = tuple(
            dict.fromkeys(re.findall(r"\b(transform|opacity|width|height|translateY|translateX)\b", window))
        )
        add_contract(
            MotionContract(
                kind="waapi",
                properties=props or ("transform",),
                duration_ms=float(dur_m.group(1)) if dur_m else None,
                delay_ms=float(delay_m.group(1)) if delay_m else None,
                easing=ease_m.group(1) if ease_m else None,
                reduced_motion=has_reduced_motion,
                trigger="element.animate",
                raw_snippet=" ".join(window.split())[:160],
            )
        )

    # 4. Timers (setTimeout(..., ms) / setInterval(..., ms))
    for m in TIMER_CALL_RE.finditer(text):
        fn_name = m.group(1)
        window = text[m.start() : min(len(text), m.start() + 260)]
        # Look for trailing numeric timeout argument like `, 300)` or `, HOVER_DELAY_MS)`
        ms_m = re.search(r",\s*(\d+(?:\.\d+)?)\s*\)", window)
        delay_val = float(ms_m.group(1)) if ms_m else None
        add_contract(
            MotionContract(
                kind="timer",
                properties=(fn_name,),
                duration_ms=None,
                delay_ms=delay_val,
                easing=None,
                reduced_motion=has_reduced_motion,
                trigger=fn_name,
                raw_snippet=" ".join(window.splitlines()[:3]).strip()[:160],
            )
        )

    # 5. Event handlers (onMouseEnter, onMouseLeave, onClick, pointer/drag handlers)
    for m in HANDLER_PROP_RE.finditer(text):
        handler = m.group(1)
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        if line_end == -1:
            line_end = len(text)
        add_contract(
            MotionContract(
                kind="handler",
                properties=(handler,),
                duration_ms=None,
                delay_ms=None,
                easing=None,
                reduced_motion=has_reduced_motion,
                trigger=handler,
                raw_snippet=text[line_start:line_end].strip()[:160],
            )
        )

    for m in ADD_EVENT_RE.finditer(text):
        ev = m.group(1)
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        if line_end == -1:
            line_end = len(text)
        add_contract(
            MotionContract(
                kind="handler",
                properties=(ev,),
                duration_ms=None,
                delay_ms=None,
                easing=None,
                reduced_motion=has_reduced_motion,
                trigger=f"addEventListener:{ev}",
                raw_snippet=text[line_start:line_end].strip()[:160],
            )
        )

    return tuple(contracts)


# ---------------------------------------------------------------------------
# Python AST extractor (stdlib ast)
# ---------------------------------------------------------------------------

def _python_chunk_spans(text: str, starts: list[int]) -> tuple[list[dict[str, Any]], str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [], "syntax_error_fallback"

    spans: list[dict[str, Any]] = []
    text_len = len(text)

    def span_from_node(node: ast.AST) -> tuple[int, int, int, int]:
        start_line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", start_line) or start_line
        # Include leading decorators if present
        deco_list = getattr(node, "decorator_list", [])
        if deco_list:
            start_line = min(start_line, min(getattr(d, "lineno", start_line) for d in deco_list))
        s_off = _line_col_to_offset(starts, start_line, 0, text_len)
        if end_line < len(starts):
            e_off = max(s_off, starts[end_line] - 1)
        else:
            e_off = text_len
        return start_line, end_line, s_off, e_off

    def visit_body(body: list[ast.stmt], parent_ctx: str) -> None:
        for stmt in body:
            if isinstance(stmt, ast.ClassDef):
                s_line, e_line, s_off, e_off = span_from_node(stmt)
                ctx = f"{parent_ctx}.{stmt.name}" if parent_ctx != "module" else stmt.name
                spans.append(
                    {
                        "node_type": "class",
                        "name": stmt.name,
                        "parent_context": parent_ctx,
                        "start_line": s_line,
                        "end_line": e_line,
                        "start_offset": s_off,
                        "end_offset": e_off,
                        "symbol_id": f"py:{ctx}",
                    }
                )
                visit_body(stmt.body, ctx)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                s_line, e_line, s_off, e_off = span_from_node(stmt)
                is_method = parent_ctx != "module"
                node_type = "method" if is_method else ("async_function" if isinstance(stmt, ast.AsyncFunctionDef) else "function")
                ctx = f"{parent_ctx}.{stmt.name}" if is_method else stmt.name
                spans.append(
                    {
                        "node_type": node_type,
                        "name": stmt.name,
                        "parent_context": parent_ctx,
                        "start_line": s_line,
                        "end_line": e_line,
                        "start_offset": s_off,
                        "end_offset": e_off,
                        "symbol_id": f"py:{ctx}",
                    }
                )

    visit_body(tree.body, "module")

    if not spans and text.strip():
        lines = text.splitlines()
        spans.append(
            {
                "node_type": "module",
                "name": "module",
                "parent_context": "root",
                "start_line": 1,
                "end_line": max(1, len(lines)),
                "start_offset": 0,
                "end_offset": text_len,
                "symbol_id": "py:module",
            }
        )

    return spans, "parsed"


# ---------------------------------------------------------------------------
# TypeScript / TSX / JS / JSX structural parser (deterministic lexer + braces)
# ---------------------------------------------------------------------------

def _scan_js_code_mask(text: str) -> list[bool]:
    """Return True for character positions that belong to active JS/TS syntax (not strings/comments)."""
    n = len(text)
    mask = [True] * n
    i = 0
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "/":
            while i < n and text[i] != "\n":
                mask[i] = False
                i += 1
            continue
        if ch == "/" and nxt == "*":
            mask[i] = False
            mask[i + 1] = False
            i += 2
            while i < n - 1 and not (text[i] == "*" and text[i + 1] == "/"):
                mask[i] = False
                i += 1
            if i < n:
                mask[i] = False
                if i + 1 < n:
                    mask[i + 1] = False
                i += 2
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            mask[i] = False
            i += 1
            while i < n:
                c = text[i]
                mask[i] = False
                if c == "\\":
                    i += 1
                    if i < n:
                        mask[i] = False
                        i += 1
                    continue
                if quote == "`" and c == "$" and i + 1 < n and text[i + 1] == "{":
                    # Keep template expression braces visible? Keeping inner expr masked avoids brace imbalance on strings.
                    i += 1
                    continue
                if c == quote:
                    i += 1
                    break
                i += 1
            continue
        i += 1
    return mask


def _find_matching_delimiter(text: str, mask: list[bool], open_idx: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    n = len(text)
    for i in range(open_idx, n):
        if not mask[i]:
            continue
        ch = text[i]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
    return -1


_TS_DECL_START_RE = re.compile(
    r"^[ \t]*(?:export\s+)?(?:default\s+)?(?:declare\s+)?(?:abstract\s+)?"
    r"(?:(async)\s+)?"
    r"(function\*?|class|interface|type|enum|const|let|var)\s+"
    r"([A-Za-z_$][A-Za-z0-9_$]*)",
    re.MULTILINE,
)

_TS_NESTED_HOOK_OR_HANDLER_RE = re.compile(
    r"^[ \t]*(?:const|let|function)\s+"
    r"([A-Za-z_$][A-Za-z0-9_$]*)\s*"
    r"(?:=\s*(?:async\s+)?(?:\([^)]*\)|[A-Za-z_$][A-Za-z0-9_$]*)\s*=>|"
    r"=\s*(?:useCallback|useMemo|useEffect|useLayoutEffect|useRef)\s*\(|"
    r"\([^)]*\)\s*(?::\s*[^=>{]+)?\{)",
    re.MULTILINE,
)

_USE_EFFECT_RE = re.compile(
    r"^[ \t]*(useEffect|useLayoutEffect)\s*\(",
    re.MULTILINE,
)


def _classify_ts_node(keyword: str, name: str, body_text: str) -> str:
    if keyword == "class":
        return "class"
    if keyword in {"interface", "type", "enum"}:
        return keyword
    if name.startswith("use") and len(name) > 3 and name[3].isupper():
        return "hook"
    if name[0].isupper() and ("<" in body_text or "React" in body_text or "return (" in body_text or "jsx" in body_text.lower()):
        return "component"
    if re.search(r"^(?:on|handle)[A-Z]", name):
        return "handler"
    if keyword in {"const", "let", "var"}:
        if "=>" in body_text[:200] or "function" in body_text[:200]:
            return "component" if name[0].isupper() and ("<" in body_text or "return" in body_text) else "function"
        return "declaration"
    return "function"


def _ts_chunk_spans(text: str, starts: list[int], language: str) -> tuple[list[dict[str, Any]], str]:
    mask = _scan_js_code_mask(text)
    n = len(text)
    spans: list[dict[str, Any]] = []
    top_blocks: list[tuple[int, int, str, str]] = []

    # Track brace depth at every index so we know top-level vs nested declarations
    depth_at = [0] * (n + 1)
    d = 0
    for i in range(n):
        depth_at[i] = d
        if mask[i]:
            if text[i] == "{":
                d += 1
            elif text[i] == "}":
                d = max(0, d - 1)
    depth_at[n] = d
    unbalanced = d != 0

    for m in _TS_DECL_START_RE.finditer(text):
        start_pos = m.start()
        if not mask[start_pos]:
            continue
        if depth_at[start_pos] > 0:
            continue
        keyword = m.group(2).rstrip("*")
        name = m.group(3)

        # Find end of declaration: locate opening '{' or ';' after signature
        pos = m.end()
        # Skip type annotations / parameter lists / generics until '{' or ';' at current level
        paren_depth = 0
        angle_depth = 0
        end_pos = -1
        brace_open = -1
        while pos < n:
            if not mask[pos]:
                pos += 1
                continue
            ch = text[pos]
            if ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth = max(0, paren_depth - 1)
            elif ch == "<" and keyword in {"function", "class", "interface", "type"}:
                angle_depth += 1
            elif ch == ">" and angle_depth > 0 and (pos == 0 or text[pos - 1] != "="):
                angle_depth -= 1
            elif ch == "{" and paren_depth == 0:
                brace_open = pos
                break
            elif ch == ";" and paren_depth == 0:
                end_pos = pos
                break
            pos += 1

        if brace_open != -1:
            brace_close = _find_matching_delimiter(text, mask, brace_open, "{", "}")
            if brace_close != -1:
                end_pos = brace_close
                # Check for trailing semicolon
                if end_pos + 1 < n and text[end_pos + 1] == ";":
                    end_pos += 1
            else:
                end_pos = n - 1
        elif end_pos == -1:
            # Fallback to end of line
            nl = text.find("\n", m.end())
            end_pos = (nl - 1) if nl != -1 else (n - 1)

        end_pos = max(start_pos, end_pos)
        body_text = text[start_pos : end_pos + 1]
        node_type = _classify_ts_node(keyword, name, body_text)
        s_line = _offset_to_line(starts, start_pos)
        e_line = _offset_to_line(starts, end_pos)
        top_blocks.append((start_pos, end_pos + 1, node_type, name))
        spans.append(
            {
                "node_type": node_type,
                "name": name,
                "parent_context": "module",
                "start_line": s_line,
                "end_line": e_line,
                "start_offset": start_pos,
                "end_offset": end_pos + 1,
                "symbol_id": f"{language}:{name}",
            }
        )

    # Extract nested hooks (useEffect) and nested handlers inside large component/class blocks
    for blk_start, blk_end, blk_type, blk_name in top_blocks:
        if blk_type not in {"component", "class", "hook", "function"}:
            continue
        sub_text = text[blk_start:blk_end]
        for hm in _TS_NESTED_HOOK_OR_HANDLER_RE.finditer(sub_text):
            rel_s = hm.start()
            abs_s = blk_start + rel_s
            if abs_s == blk_start or not mask[abs_s]:
                continue
            child_name = hm.group(1)
            # Only elevate meaningful hooks, handlers, or timers/effects
            if not (
                re.search(r"^(?:on|handle|use)[A-Z]", child_name)
                or "drag" in child_name.lower()
                or "hover" in child_name.lower()
                or "peek" in child_name.lower()
                or "timer" in child_name.lower()
            ):
                continue
            # Find matching block end
            p = abs_s
            inner_brace = -1
            inner_paren = -1
            while p < blk_end:
                if mask[p]:
                    if text[p] == "{":
                        inner_brace = p
                        break
                    if text[p] == "(" and "use" in child_name:
                        inner_paren = p
                        break
                p += 1
            abs_e = -1
            if inner_brace != -1:
                close_b = _find_matching_delimiter(text, mask, inner_brace, "{", "}")
                if close_b != -1 and close_b < blk_end:
                    abs_e = close_b + 1
            elif inner_paren != -1:
                close_p = _find_matching_delimiter(text, mask, inner_paren, "(", ")")
                if close_p != -1 and close_p < blk_end:
                    abs_e = close_p + 1
            if abs_e == -1:
                continue
            c_type = "hook" if child_name.startswith("use") else "handler"
            spans.append(
                {
                    "node_type": c_type,
                    "name": child_name,
                    "parent_context": blk_name,
                    "start_line": _offset_to_line(starts, abs_s),
                    "end_line": _offset_to_line(starts, abs_e - 1),
                    "start_offset": abs_s,
                    "end_offset": abs_e,
                    "symbol_id": f"{language}:{blk_name}.{child_name}",
                }
            )

        for em in _USE_EFFECT_RE.finditer(sub_text):
            abs_s = blk_start + em.start()
            if not mask[abs_s]:
                continue
            open_p = text.find("(", abs_s)
            if open_p == -1 or open_p >= blk_end:
                continue
            close_p = _find_matching_delimiter(text, mask, open_p, "(", ")")
            if close_p == -1 or close_p >= blk_end:
                continue
            abs_e = close_p + 1
            if abs_e < blk_end and text[abs_e] == ";":
                abs_e += 1
            hook_name = em.group(1)
            spans.append(
                {
                    "node_type": "hook",
                    "name": hook_name,
                    "parent_context": blk_name,
                    "start_line": _offset_to_line(starts, abs_s),
                    "end_line": _offset_to_line(starts, abs_e - 1),
                    "start_offset": abs_s,
                    "end_offset": abs_e,
                    "symbol_id": f"{language}:{blk_name}.{hook_name}@{_offset_to_line(starts, abs_s)}",
                }
            )

    if not spans and text.strip():
        lines = text.splitlines()
        spans.append(
            {
                "node_type": "module",
                "name": "module",
                "parent_context": "root",
                "start_line": 1,
                "end_line": max(1, len(lines)),
                "start_offset": 0,
                "end_offset": n,
                "symbol_id": f"{language}:module",
            }
        )

    spans.sort(key=lambda s: (s["start_offset"], -s["end_offset"]))
    status = "partial_unbalanced_braces" if unbalanced else "parsed"
    return spans, status


# ---------------------------------------------------------------------------
# CSS / HTML <style> / <script> parser
# ---------------------------------------------------------------------------

def _scan_css_mask(text: str) -> list[bool]:
    n = len(text)
    mask = [True] * n
    i = 0
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == "/" and nxt == "*":
            mask[i] = False
            mask[i + 1] = False
            i += 2
            while i < n - 1 and not (text[i] == "*" and text[i + 1] == "/"):
                mask[i] = False
                i += 1
            if i < n:
                mask[i] = False
                if i + 1 < n:
                    mask[i + 1] = False
                i += 2
            continue
        if ch in ("'", '"'):
            q = ch
            mask[i] = False
            i += 1
            while i < n:
                mask[i] = False
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == q:
                    i += 1
                    break
                i += 1
            continue
        i += 1
    return mask


def _css_chunk_spans(
    text: str,
    starts: list[int],
    *,
    base_offset: int = 0,
    parent_ctx: str = "stylesheet",
) -> tuple[list[dict[str, Any]], str]:
    mask = _scan_css_mask(text)
    n = len(text)
    spans: list[dict[str, Any]] = []
    i = 0
    rule_start = 0

    while i < n:
        if not mask[i]:
            i += 1
            continue
        ch = text[i]
        if ch == "{":
            header = " ".join(text[rule_start:i].strip().split())
            # Strip leading CSS comments from header
            header = re.sub(r"/\*.*?\*/", "", header, flags=re.DOTALL).strip()
            close_idx = _find_matching_delimiter(text, mask, i, "{", "}")
            if close_idx == -1:
                return spans, "syntax_error_fallback"
            # Determine actual start (first non-whitespace/non-comment token in rule_start..i)
            actual_start = rule_start
            while actual_start < i and (not mask[actual_start] or text[actual_start].isspace()):
                actual_start += 1
            abs_s = base_offset + actual_start
            abs_e = base_offset + close_idx + 1
            lower_hdr = header.lower()
            if lower_hdr.startswith("@keyframes"):
                kf_name = header.split(None, 1)[1] if " " in header else header
                spans.append(
                    {
                        "node_type": "keyframes",
                        "name": kf_name,
                        "parent_context": parent_ctx,
                        "start_line": _offset_to_line(starts, abs_s),
                        "end_line": _offset_to_line(starts, abs_e - 1),
                        "start_offset": abs_s,
                        "end_offset": abs_e,
                        "symbol_id": f"css:@keyframes:{kf_name}",
                    }
                )
            elif lower_hdr.startswith("@media"):
                media_name = header[:80]
                spans.append(
                    {
                        "node_type": "media_rule",
                        "name": media_name,
                        "parent_context": parent_ctx,
                        "start_line": _offset_to_line(starts, abs_s),
                        "end_line": _offset_to_line(starts, abs_e - 1),
                        "start_offset": abs_s,
                        "end_offset": abs_e,
                        "symbol_id": f"css:{media_name}",
                    }
                )
                inner_spans, _ = _css_chunk_spans(
                    text[i + 1 : close_idx],
                    starts,
                    base_offset=base_offset + i + 1,
                    parent_ctx=media_name,
                )
                spans.extend(inner_spans)
            else:
                sel_name = header[:120] or "rule"
                spans.append(
                    {
                        "node_type": "css_rule",
                        "name": sel_name,
                        "parent_context": parent_ctx,
                        "start_line": _offset_to_line(starts, abs_s),
                        "end_line": _offset_to_line(starts, abs_e - 1),
                        "start_offset": abs_s,
                        "end_offset": abs_e,
                        "symbol_id": f"css:{sel_name}",
                    }
                )
            i = close_idx + 1
            rule_start = i
            continue
        elif ch == ";":
            rule_start = i + 1
        i += 1

    return spans, "parsed"


_HTML_STYLE_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
_HTML_SCRIPT_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)


def _html_chunk_spans(text: str, starts: list[int]) -> tuple[list[dict[str, Any]], str]:
    spans: list[dict[str, Any]] = []
    status = "parsed"

    for idx, m in enumerate(_HTML_STYLE_RE.finditer(text)):
        inner = m.group(1)
        base = m.start(1)
        css_spans, css_status = _css_chunk_spans(inner, starts, base_offset=base, parent_ctx=f"style[{idx}]")
        if css_status != "parsed":
            status = css_status
        spans.extend(css_spans)

    for idx, m in enumerate(_HTML_SCRIPT_RE.finditer(text)):
        inner = m.group(1)
        base = m.start(1)
        sub_starts = _line_starts(inner)
        js_spans, js_status = _ts_chunk_spans(inner, sub_starts, "javascript")
        if js_status != "parsed":
            status = js_status
        for sp in js_spans:
            abs_s = base + sp["start_offset"]
            abs_e = base + sp["end_offset"]
            spans.append(
                {
                    "node_type": sp["node_type"],
                    "name": sp["name"],
                    "parent_context": f"script[{idx}].{sp['parent_context']}",
                    "start_line": _offset_to_line(starts, abs_s),
                    "end_line": _offset_to_line(starts, max(abs_s, abs_e - 1)),
                    "start_offset": abs_s,
                    "end_offset": abs_e,
                    "symbol_id": sp["symbol_id"],
                }
            )

    if not spans and text.strip():
        lines = text.splitlines()
        spans.append(
            {
                "node_type": "document",
                "name": "html",
                "parent_context": "root",
                "start_line": 1,
                "end_line": max(1, len(lines)),
                "start_offset": 0,
                "end_offset": len(text),
                "symbol_id": "html:document",
            }
        )
    return spans, status


def _line_fallback_spans(text: str, starts: list[int], language: str, chunk_lines: int = 40) -> list[dict[str, Any]]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return []
    spans: list[dict[str, Any]] = []
    n = len(lines)
    idx = 0
    text_len = len(text)
    while idx < n:
        end_idx = min(idx + chunk_lines, n)
        s_line = idx + 1
        e_line = end_idx
        s_off = _line_col_to_offset(starts, s_line, 0, text_len)
        e_off = max(s_off, starts[e_line] - 1) if e_line < len(starts) else text_len
        spans.append(
            {
                "node_type": "fallback_block",
                "name": f"lines_{s_line}_{e_line}",
                "parent_context": "fallback",
                "start_line": s_line,
                "end_line": e_line,
                "start_offset": s_off,
                "end_offset": e_off,
                "symbol_id": f"{language}:lines_{s_line}_{e_line}",
            }
        )
        idx = end_idx
    return spans


def chunk_code(
    text: str,
    *,
    language: str,
    blob_sha: str | None = None,
    max_chunk_chars: int = 12000,
) -> list[ASTChunk]:
    """Extract deterministic structural AST chunks from Python, TS/TSX/JS/JSX, CSS, or HTML."""
    normalized = _normalize_newlines(text)
    if not normalized.strip():
        return []

    lang = normalize_language(language)
    bsha = blob_sha or compute_git_blob_sha(normalized)
    starts = _line_starts(normalized)

    spans: list[dict[str, Any]]
    status = "parsed"

    if lang == "python":
        spans, status = _python_chunk_spans(normalized, starts)
        if status == "syntax_error_fallback" or not spans:
            spans = _line_fallback_spans(normalized, starts, lang)
    elif lang in {"typescript", "tsx", "javascript", "jsx"}:
        spans, status = _ts_chunk_spans(normalized, starts, lang)
        if not spans:
            spans = _line_fallback_spans(normalized, starts, lang)
            status = "syntax_error_fallback"
    elif lang == "css":
        spans, status = _css_chunk_spans(normalized, starts)
        if not spans:
            spans = _line_fallback_spans(normalized, starts, lang)
            if status == "parsed":
                status = "fallback"
    elif lang == "html":
        spans, status = _html_chunk_spans(normalized, starts)
    else:
        spans = _line_fallback_spans(normalized, starts, lang)
        status = "unsupported_language_fallback"

    chunks: list[ASTChunk] = []
    for idx, sp in enumerate(spans):
        s_off = sp["start_offset"]
        e_off = sp["end_offset"]
        body = normalized[s_off:e_off]
        if len(body) > max_chunk_chars:
            body = body[:max_chunk_chars]
            e_off = s_off + len(body)
        if not body.strip():
            continue
        contracts = extract_motion_contracts(body, lang)
        csha = _compute_chunk_sha(body, sp["node_type"], sp["name"], sp["parent_context"])
        chunks.append(
            ASTChunk(
                chunk_index=len(chunks),
                node_type=sp["node_type"],
                name=sp["name"],
                parent_context=sp["parent_context"],
                language=lang,
                start_line=sp["start_line"],
                end_line=sp["end_line"],
                start_offset=s_off,
                end_offset=e_off,
                blob_sha=bsha,
                chunk_sha=csha,
                content=body,
                symbol_id=sp.get("symbol_id", ""),
                extractor_version=EXTRACTOR_VERSION,
                status=status,
                motion_contracts=contracts,
            )
        )
    return chunks


def fixed_line_chunks(
    text: str,
    *,
    chunk_lines: int = 40,
    overlap_lines: int = 5,
) -> list[dict[str, Any]]:
    """Reproduce the baseline 40-line chunking strategy from content_index.py for comparison."""
    normalized = _normalize_newlines(text)
    lines = normalized.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or all(not l.strip() for l in lines):
        return []
    out: list[dict[str, Any]] = []
    n = len(lines)
    idx = 0
    while idx < n:
        end = min(idx + chunk_lines, n)
        body = "\n".join(lines[idx:end])
        out.append({"start_line": idx + 1, "end_line": end, "content": body})
        if end >= n:
            break
        idx += max(1, (end - idx) - overlap_lines)
    return out


def deduplicate_chunks_by_blob(
    occurrences: list[dict[str, str]],
) -> dict[str, Any]:
    """Deduplicate AST chunks across branches/commits by blob_sha while keeping full occurrence lineage."""
    blob_store: dict[str, dict[str, Any]] = {}
    lineage: list[dict[str, Any]] = []
    dedup_hits = 0

    for occ in occurrences:
        text = occ["content"]
        lang = occ["language"]
        bsha = occ.get("blob_sha") or compute_git_blob_sha(_normalize_newlines(text))
        if bsha not in blob_store:
            chunks = chunk_code(text, language=lang, blob_sha=bsha)
            blob_store[bsha] = {
                "blob_sha": bsha,
                "language": normalize_language(lang),
                "chunks": [c.to_dict() for c in chunks],
            }
        else:
            dedup_hits += 1

        lineage.append(
            {
                "repo": occ.get("repo", ""),
                "ref": occ.get("ref", ""),
                "commit_sha": occ.get("commit_sha", ""),
                "path": occ["path"],
                "blob_sha": bsha,
            }
        )

    return {
        "unique_blobs": len(blob_store),
        "total_occurrences": len(lineage),
        "dedup_hits": dedup_hits,
        "blobs": blob_store,
        "occurrences": lineage,
    }


# ---------------------------------------------------------------------------
# Reproducible Benchmark Corpus & Evaluator (Fixed 40-line vs AST Chunking)
# ---------------------------------------------------------------------------

def build_benchmark_corpus() -> list[dict[str, str]]:
    """Build realistic corpus covering 3+ sidebar implementations, graph physics, and 5+ motion contracts."""
    sidebar_v1_tsx = (
        "import React, { useState, useRef, useEffect } from 'react';\n"
        + "\n".join(f"// space-frame sidebar setup line {i}" for i in range(1, 14))
        + "\n"
        + """export interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function WorkspaceSidebar({ collapsed, onToggle }: SidebarProps) {
  const [peek, setPeek] = useState(false);
  const openTimerRef = useRef<number | null>(null);
  const closeTimerRef = useRef<number | null>(null);
"""
        + "\n".join(f"  const railMetric_{i} = {i} * 4;" for i in range(1, 20))
        + """
  const handleMouseEnter = () => {
    if (!collapsed) return;
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    openTimerRef.current = window.setTimeout(() => {
      setPeek(true);
    }, 300);
  };

  const handleMouseLeave = () => {
    if (openTimerRef.current) clearTimeout(openTimerRef.current);
    closeTimerRef.current = window.setTimeout(() => {
      setPeek(false);
    }, 150);
  };

  const handleReorderFlip = (el: HTMLElement, deltaY: number) => {
    el.animate(
      [{ transform: `translateY(${deltaY}px)` }, { transform: 'translateY(0)' }],
      { duration: 200, easing: 'ease-out', fill: 'both' }
    );
  };

  return (
    <aside
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="transition-all duration-200 ease-out motion-reduce:transition-none"
    >
      <button onClick={onToggle}>Toggle</button>
    </aside>
  );
}
"""
    )

    sidebar_v2_tsx = (
        "import React from 'react';\n"
        + "\n".join(f"// tailwind app-shell header comment {i}" for i in range(1, 18))
        + "\n"
        + """export function AppSidebarOverview({ activeId }: { activeId: string }) {
  const label = activeId.trim();
"""
        + "\n".join(f"  const slotPad_{i} = {i};" for i in range(1, 24))
        + """
  return (
    <div className="group flex items-center transition-colors duration-200 ease-out motion-reduce:transition-none">
      <span>{label}</span>
      <button
        aria-label="More actions"
        className="opacity-0 invisible pointer-events-none group-hover:opacity-100 group-hover:visible group-hover:pointer-events-auto transition-opacity duration-200 ease-out motion-reduce:transition-none"
      >
        ...
      </button>
    </div>
  );
}
"""
    )

    sidebar_proto_css = (
        "\n".join(f"/* layout token comment {i} */" for i in range(1, 15))
        + """
.shell {
  width: 240px;
  transition: margin-left 200ms ease, width 200ms ease;
}
.shell.collapsed {
  margin-left: -240px;
}
.section-chevron {
  transition: transform 150ms ease;
}
.mobile-drawer {
  transform: translateX(-105%);
  transition: transform 200ms ease;
}
.mobile-drawer.open {
  transform: translateX(0);
}
@keyframes skeletonPulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  """
        + "\n".join(f"  /* frame step {i} */" for i in range(1, 12))
        + """
  50% {
    opacity: 0.5;
    transform: scale(0.99);
  }
}
.skeleton-row {
  animation: skeletonPulse 1200ms ease-in-out infinite;
}
@media (prefers-reduced-motion: reduce) {
  .shell, .section-chevron, .mobile-drawer, .skeleton-row {
    transition: none;
    animation: none;
  }
}
"""
    )

    graph_canvas_tsx = (
        "import React, { useEffect, useRef } from 'react';\n"
        + "\n".join(f"// graph physics config line {i}" for i in range(1, 16))
        + "\n"
        + """export function GraphCanvas({ nodes }: { nodes: Array<{ id: string }> }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
"""
        + "\n".join(f"  const forceParam_{i} = {i} * 0.1;" for i in range(1, 22))
        + """
  useEffect(() => {
    const frameId = requestAnimationFrame(() => {
      if (canvasRef.current) {
        canvasRef.current.dataset.nodeCount = String(nodes.length);
      }
    });
    return () => cancelAnimationFrame(frameId);
  }, [nodes]);

  const handleNodeClick = (nodeId: string) => {
    return nodeId;
  };

  return <canvas ref={canvasRef} onClick={() => handleNodeClick('root')} />;
}
"""
    )

    graph_engine_py = (
        '"""Python graph layout and FSRS spacing state."""\n\n'
        "class GraphForceModel:\n"
        "    def __init__(self, damping: float = 0.85) -> None:\n"
        "        self.damping = damping\n"
        + "".join(f"        self.slot_{i} = {i}\n" for i in range(1, 35))
        + "\n"
        "    def step_layout(self, velocity: float) -> float:\n"
        "        return velocity * self.damping\n\n"
        "def compute_peek_dwell_contract(open_ms: int = 300, close_ms: int = 150) -> dict:\n"
        '    return {"open_delay_ms": open_ms, "close_delay_ms": close_ms}\n'
    )

    return [
        {
            "repo": "ianmaciel7/notes-app",
            "ref": "old-10",
            "path": "src/components/space-frame.tsx",
            "language": "tsx",
            "content": sidebar_v1_tsx,
        },
        {
            "repo": "ianmaciel7/notes-app",
            "ref": "old-5",
            "path": "src/app/_components/workspace/app-sidebar-overview.tsx",
            "language": "tsx",
            "content": sidebar_v2_tsx,
        },
        {
            "repo": "ianmaciel7/exams-app",
            "ref": "dev",
            "path": "docs/sidebar-prototipo/prototipo-sidebar.css",
            "language": "css",
            "content": sidebar_proto_css,
        },
        {
            "repo": "ianmaciel7/exams-app-antigo-2",
            "ref": "feat/67-unified-graph-20261115",
            "path": "src/components/graph/graph-canvas.tsx",
            "language": "tsx",
            "content": graph_canvas_tsx,
        },
        {
            "repo": "ianmaciel7/exams-app",
            "ref": "main",
            "path": "src/domain/graph_force.py",
            "language": "python",
            "content": graph_engine_py,
        },
    ]


def _score_fts_chunks(
    chunks: list[dict[str, Any]],
    query_terms: list[str],
) -> list[dict[str, Any]]:
    """Index chunks into an in-memory SQLite FTS5 table and execute BM25 search."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            "CREATE VIRTUAL TABLE bench_fts USING fts5("
            "content, doc_id UNINDEXED, node_type UNINDEXED, name UNINDEXED, "
            "start_line UNINDEXED, end_line UNINDEXED, tokenize='unicode61')"
        )
        for ch in chunks:
            conn.execute(
                "INSERT INTO bench_fts (content, doc_id, node_type, name, start_line, end_line) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    ch["content"],
                    ch["doc_id"],
                    ch.get("node_type", "line_window"),
                    ch.get("name", ""),
                    str(ch["start_line"]),
                    str(ch["end_line"]),
                ),
            )
        matcher = " AND ".join(f'"{t}"*' for t in query_terms)
        rows = conn.execute(
            "SELECT doc_id, node_type, name, CAST(start_line AS INTEGER), CAST(end_line AS INTEGER), content, bm25(bench_fts) AS s "
            "FROM bench_fts WHERE bench_fts MATCH ? ORDER BY s ASC LIMIT 10",
            (matcher,),
        ).fetchall()
        return [
            {
                "doc_id": r[0],
                "node_type": r[1],
                "name": r[2],
                "start_line": r[3],
                "end_line": r[4],
                "content": r[5],
            }
            for r in rows
        ]
    finally:
        conn.close()


def _is_structurally_complete(chunk_text: str, required_tokens: tuple[str, ...]) -> bool:
    """True only if a single retrieved chunk preserves all cohesive structural tokens."""
    return all(tok in chunk_text for tok in required_tokens)


def run_benchmark() -> dict[str, Any]:
    """Compare 40-line fixed chunking vs AST structural chunking on sidebar/graph/motion queries."""
    corpus = build_benchmark_corpus()

    tracemalloc.start()
    t0 = time.perf_counter()
    fixed_records: list[dict[str, Any]] = []
    for doc in corpus:
        for ch in fixed_line_chunks(doc["content"], chunk_lines=40, overlap_lines=5):
            fixed_records.append(
                {
                    "doc_id": doc["path"],
                    "node_type": "line_window",
                    "name": f"lines_{ch['start_line']}_{ch['end_line']}",
                    "start_line": ch["start_line"],
                    "end_line": ch["end_line"],
                    "content": ch["content"],
                }
            )
    fixed_ingest_ms = (time.perf_counter() - t0) * 1000.0
    _, fixed_peak_ram = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    t1 = time.perf_counter()
    ast_records: list[dict[str, Any]] = []
    ast_objs: list[ASTChunk] = []
    for doc in corpus:
        bsha = compute_git_blob_sha(doc["content"])
        for ch in chunk_code(doc["content"], language=doc["language"], blob_sha=bsha):
            ast_objs.append(ch)
            ast_records.append(
                {
                    "doc_id": doc["path"],
                    "node_type": ch.node_type,
                    "name": ch.name,
                    "start_line": ch.start_line,
                    "end_line": ch.end_line,
                    "content": ch.content,
                }
            )
    ast_ingest_ms = (time.perf_counter() - t1) * 1000.0
    _, ast_peak_ram = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Queries requiring cohesive structural context (where 40-line boundaries split a component or function)
    queries = [
        {
            "id": "q_peek_hover_contract",
            "terms": ["WorkspaceSidebar", "onMouseEnter", "setTimeout"],
            "expected_path": "src/components/space-frame.tsx",
            "cohesive_tokens": ("WorkspaceSidebar", "handleMouseEnter", "300", "onMouseEnter"),
        },
        {
            "id": "q_flip_waapi_sidebar",
            "terms": ["WorkspaceSidebar", "animate", "translateY"],
            "expected_path": "src/components/space-frame.tsx",
            "cohesive_tokens": ("WorkspaceSidebar", "handleReorderFlip", "duration: 200", "ease-out"),
        },
        {
            "id": "q_overflow_reveal",
            "terms": ["AppSidebarOverview", "opacity", "duration"],
            "expected_path": "src/app/_components/workspace/app-sidebar-overview.tsx",
            "cohesive_tokens": ("AppSidebarOverview", "opacity-0", "duration-200", "motion-reduce:transition-none"),
        },
        {
            "id": "q_skeleton_keyframes",
            "terms": ["skeletonPulse", "opacity"],
            "expected_path": "docs/sidebar-prototipo/prototipo-sidebar.css",
            "cohesive_tokens": ("@keyframes skeletonPulse", "0%, 100%", "opacity: 0.5"),
        },
        {
            "id": "q_graph_canvas_hook",
            "terms": ["GraphCanvas", "requestAnimationFrame", "onClick"],
            "expected_path": "src/components/graph/graph-canvas.tsx",
            "cohesive_tokens": ("GraphCanvas", "useEffect", "requestAnimationFrame", "onClick"),
        },
        {
            "id": "q_python_force_model",
            "terms": ["GraphForceModel", "step_layout", "damping"],
            "expected_path": "src/domain/graph_force.py",
            "cohesive_tokens": ("class GraphForceModel", "def step_layout", "self.damping"),
        },
    ]

    def eval_strategy(records: list[dict[str, Any]]) -> dict[str, Any]:
        complete_hits = 0
        recall_sum = 0.0
        total_tokens_top1 = 0
        per_query: list[dict[str, Any]] = []
        for q in queries:
            hits = _score_fts_chunks(records, q["terms"])
            matched_doc = any(h["doc_id"] == q["expected_path"] for h in hits[:3])
            cohesive_top3 = any(
                h["doc_id"] == q["expected_path"] and _is_structurally_complete(h["content"], q["cohesive_tokens"])
                for h in hits[:3]
            )
            recall_sum += 1.0 if matched_doc else 0.0
            if cohesive_top3:
                complete_hits += 1
            top_tokens = math.ceil(len(hits[0]["content"]) / 4) if hits else 0
            total_tokens_top1 += top_tokens
            per_query.append(
                {
                    "id": q["id"],
                    "matched_top3": matched_doc,
                    "cohesive_single_chunk_top3": cohesive_top3,
                    "top1_node_type": hits[0]["node_type"] if hits else None,
                    "top1_tokens": top_tokens,
                }
            )
        n_q = len(queries)
        return {
            "chunk_count": len(records),
            "recall_at_3": round(recall_sum / n_q, 4),
            "cohesive_structure_rate": round(complete_hits / n_q, 4),
            "mean_top1_tokens": round(total_tokens_top1 / n_q, 2),
            "per_query": per_query,
        }

    fixed_eval = eval_strategy(fixed_records)
    ast_eval = eval_strategy(ast_records)

    all_contracts = [c.to_dict() for ch in ast_objs for c in ch.motion_contracts]
    return {
        "extractor_version": EXTRACTOR_VERSION,
        "corpus_files": len(corpus),
        "fixed_40_lines": {
            **fixed_eval,
            "ingest_ms": round(fixed_ingest_ms, 3),
            "peak_ram_kib": round(fixed_peak_ram / 1024.0, 2),
        },
        "ast_structural": {
            **ast_eval,
            "ingest_ms": round(ast_ingest_ms, 3),
            "peak_ram_kib": round(ast_peak_ram / 1024.0, 2),
            "motion_contracts_extracted": len(all_contracts),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="Extract structural AST chunks from a file")
    p_extract.add_argument("path", help="Source file path")
    p_extract.add_argument("--lang", default=None, help="Override language (python, tsx, ts, js, css, html)")

    sub.add_parser("benchmark", help="Run reproducible fixed-40-line vs AST chunking benchmark")

    args = ap.parse_args()
    if args.command == "benchmark":
        out = run_benchmark()
    else:
        target = Path(args.path)
        text = target.read_text(encoding="utf-8")
        lang = args.lang or target.suffix.lower() or "text"
        chunks = chunk_code(text, language=lang)
        out = {
            "path": str(target),
            "language": normalize_language(lang),
            "blob_sha": compute_git_blob_sha(_normalize_newlines(text)),
            "chunk_count": len(chunks),
            "chunks": [c.to_dict() for c in chunks],
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
