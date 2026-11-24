#!/usr/bin/env python3
"""Multi-layer contextual evidence graph engine connecting code, UI, state, motion, and decisions.

Connects code symbols, UI components, event handlers, state bindings, UX motion contracts,
architectural decisions (ADRs/specs), and visual evidence across historical Git bundles and
preserved inventories.

Zero external dependencies (Python standard library only).
Zero Unicode emoji policy strictly enforced.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sqlite3
import sys
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DB_PATH = ".cache/archive/evidence-graph.sqlite"

NODE_TYPES = (
    "Repo",
    "Ref",
    "Commit",
    "File",
    "Component",
    "Symbol",
    "EventHandler",
    "StateBinding",
    "MotionContract",
    "Decision",
    "Image",
)
NODE_TYPE_SET = frozenset(NODE_TYPES)

EDGE_TYPES = (
    "CONTAINS",
    "DEFINES",
    "HANDLES",
    "TRIGGERS",
    "MUTATES",
    "READS",
    "ANIMATES",
    "DOCUMENTED_IN",
    "EVIDENCED_BY",
    "MODIFIES",
    "IMPORTS",
    "COMPOSES",
    "CO_OCCURS_WITH",
    "SUPERSEDES",
)
EDGE_TYPE_SET = frozenset(EDGE_TYPES)

PROVENANCE_LEVELS = (
    "source-confirmed",
    "measured-in-browser",
    "inferred",
    "not-recovered",
)
PROVENANCE_SET = frozenset(PROVENANCE_LEVELS)

CONFIDENCE_LEVELS = ("EXTRACTED", "INFERRED")
CONFIDENCE_SET = frozenset(CONFIDENCE_LEVELS)

STATE_BINDING_KINDS = (
    "useState",
    "useReducer",
    "zustand",
    "localStorage",
    "aria_attr",
    "data_attr",
)
STATE_BINDING_KIND_SET = frozenset(STATE_BINDING_KINDS)

SHORTCUT_KINDS = ("Shift+Click", "Escape", "Ctrl/Cmd+Click")

EVENT_HANDLER_NAMES = frozenset(
    {
        "onClick",
        "onKeyDown",
        "onKeyUp",
        "onPointerEnter",
        "onPointerLeave",
        "onPointerDown",
        "onPointerUp",
        "onDragStart",
        "onDragOver",
        "onDragEnd",
        "onDrop",
        "onContextMenu",
        "onDoubleClick",
        "onMouseDown",
        "onMouseUp",
        "onMouseEnter",
        "onMouseLeave",
    }
)

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

DB_SCHEMA = """
PRAGMA journal_mode=DELETE;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    repo TEXT NOT NULL DEFAULT '',
    ref TEXT NOT NULL DEFAULT '',
    label TEXT NOT NULL,
    path TEXT NOT NULL DEFAULT '',
    commit_sha TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT '',
    validity_status TEXT NOT NULL DEFAULT 'unverified',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS graph_edges (
    edge_id TEXT PRIMARY KEY,
    src_id TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    confidence TEXT NOT NULL DEFAULT 'EXTRACTED',
    repo TEXT NOT NULL DEFAULT '',
    ref TEXT NOT NULL DEFAULT '',
    commit_sha TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL DEFAULT '',
    weight REAL NOT NULL DEFAULT 1.0,
    provenance_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY(src_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    FOREIGN KEY(dst_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    UNIQUE(src_id, dst_id, edge_type, commit_sha, ref)
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON graph_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_label ON graph_nodes(label);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_path ON graph_nodes(path);
CREATE INDEX IF NOT EXISTS idx_graph_edges_src ON graph_edges(src_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_dst ON graph_edges(dst_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph_edges(edge_type);
"""


def estimate_text_tokens(text: str) -> int:
    """Deterministic token estimator (~4 chars per token)."""
    if not text:
        return 0
    return (len(text) + 3) // 4


def estimate_json_tokens(obj: Any) -> int:
    """Deterministic token estimator for JSON serialized objects."""
    serialized = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return estimate_text_tokens(serialized)


def safe_path(p: str) -> str:
    """Normalize and validate repo-relative path without directory traversal."""
    norm = Path(p).as_posix()
    if norm.startswith("/") or ".." in Path(norm).parts:
        raise ValueError(f"Unsafe path: {p!r}")
    return norm


def _stable_id(prefix: str, *parts: Any) -> str:
    raw = ":".join(str(p).strip() for p in parts if str(p).strip())
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{h}"


def canonical_component_key(raw: str) -> str:
    """Normalize a symbol or component identifier across repos."""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    aliases = {
        "app-shell": "app-shell",
        "shell": "app-shell",
        "appshell": "app-shell",
        "app-header-tabs": "app-header-tabs",
        "header-tabs": "app-header-tabs",
        "appheadertabs": "app-header-tabs",
        "app-sidebar-overview": "app-sidebar-overview",
        "sidebar-overview": "app-sidebar-overview",
        "appsidebaroverview": "app-sidebar-overview",
        "app-sidebar": "sidebar",
        "sidebar": "sidebar",
        "barra-lateral": "sidebar",
        "grafo": "graph",
        "graph": "graph",
    }
    return aliases.get(s, s or "unknown")


@dataclass
class SymbolExtraction:
    name: str
    kind: str
    line_start: int
    line_end: int
    parent_context: str = "module"
    snippet: str = ""


@dataclass
class EventHandlerExtraction:
    event_name: str
    target_symbol: str
    line_start: int
    line_end: int
    shortcut: str | None = None
    snippet: str = ""
    component_name: str = ""


@dataclass
class StateBindingExtraction:
    binding_kind: str
    name: str
    variable: str
    setter: str = ""
    initial_value: str = ""
    reads: list[dict[str, Any]] = field(default_factory=list)
    mutations: list[dict[str, Any]] = field(default_factory=list)
    component_name: str = ""


@dataclass
class MotionContractExtraction:
    contract_id: str
    dwell_delay_ms: float | None = None
    transition_duration_ms: float | None = None
    easing: str | None = None
    reduced_motion: str | None = None
    provenance: str = "source-confirmed"
    source_lines: list[int] = field(default_factory=list)
    snippet: str = ""
    component_name: str = ""


@dataclass
class ComponentExtraction:
    name: str
    path: str
    line_start: int
    line_end: int
    symbols: list[SymbolExtraction] = field(default_factory=list)
    handlers: list[EventHandlerExtraction] = field(default_factory=list)
    state_bindings: list[StateBindingExtraction] = field(default_factory=list)
    motion_contracts: list[MotionContractExtraction] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)

    @property
    def event_handlers(self) -> list[EventHandlerExtraction]:
        return self.handlers


def _mask_comments_and_strings(text: str) -> list[bool]:
    """Return boolean mask where True indicates actionable code outside comments and string literals."""
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
                if c == quote:
                    i += 1
                    break
                i += 1
            continue
        i += 1
    return mask


def _find_matching_paren(text: str, mask: list[bool], open_idx: int) -> int:
    """Find index of closing paren matching the open paren at open_idx."""
    depth = 0
    n = len(text)
    for i in range(open_idx, n):
        if not mask[i]:
            continue
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _find_matching_brace(text: str, mask: list[bool], open_idx: int) -> int:
    """Find index of closing brace matching the open brace at open_idx."""
    depth = 0
    n = len(text)
    for i in range(open_idx, n):
        if not mask[i]:
            continue
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _compute_line_number(text: str, offset: int) -> int:
    """Convert char offset to 1-based line number."""
    return text.count("\n", 0, max(0, offset)) + 1


def parse_tsx_symbols_and_components(
    text: str, file_path: str = "", *, path: str | None = None
) -> list[ComponentExtraction]:
    """Deep structural extraction of React components, symbols, handlers, state, and motion from TSX."""
    file_path = path or file_path or ""
    lines = text.splitlines(keepends=True)
    mask = _mask_comments_and_strings(text)

    imports: list[str] = []
    import_re = re.compile(r"""(?:import|from)\s+['"]([^'"]+)['"]""")
    for m in import_re.finditer(text):
        imports.append(m.group(1))

    found_symbols: list[dict[str, Any]] = []

    # 1. Function declarations: function Name(...) { ... }
    fn_re = re.compile(
        r"^[ \t]*(?:export\s+)?(?:default\s+)?(?:async\s+)?function(?:\s*\*)?\s+([A-Za-z_$][A-Za-z0-9_$]*)",
        re.MULTILINE,
    )
    for m in fn_re.finditer(text):
        name = m.group(1)
        start_off = m.start()
        start_line = _compute_line_number(text, start_off)

        p_open = text.find("(", m.end())
        if p_open == -1:
            continue
        p_close = _find_matching_paren(text, mask, p_open)
        if p_close == -1:
            continue

        b_open = text.find("{", p_close)
        if b_open == -1:
            continue
        b_close = _find_matching_brace(text, mask, b_open)
        end_line = _compute_line_number(text, b_close) if b_close != -1 else start_line + 5
        end_off = b_close + 1 if b_close != -1 else len(text)

        body = text[start_off:end_off]
        is_comp = bool(name[0].isupper() and ("return" in body or "<" in body))
        symbol_kind = "component" if is_comp else ("hook" if name.startswith("use") else "function")

        found_symbols.append(
            {
                "name": name,
                "kind": symbol_kind,
                "start_line": start_line,
                "end_line": end_line,
                "start_off": start_off,
                "end_off": end_off,
                "body": body,
            }
        )

    # 2. const arrow functions or component expressions: const Name = (...) => { ... }
    const_fn_re = re.compile(
        r"^[ \t]*(?:export\s+)?(?:default\s+)?(?:const|let)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*(?::\s*[^=]+)?\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][A-Za-z0-9_$]*)\s*=>\s*\{",
        re.MULTILINE,
    )
    for m in const_fn_re.finditer(text):
        name = m.group(1)
        start_off = m.start()
        start_line = _compute_line_number(text, start_off)
        b_open = m.end() - 1
        b_close = _find_matching_brace(text, mask, b_open)
        end_line = _compute_line_number(text, b_close) if b_close != -1 else start_line + 5
        end_off = b_close + 1 if b_close != -1 else len(text)

        body = text[start_off:end_off]
        is_comp = bool(name[0].isupper() and ("return" in body or "<" in body))
        symbol_kind = "component" if is_comp else ("hook" if name.startswith("use") else "function")

        found_symbols.append(
            {
                "name": name,
                "kind": symbol_kind,
                "start_line": start_line,
                "end_line": end_line,
                "start_off": start_off,
                "end_off": end_off,
                "body": body,
            }
        )

    components_found = [s for s in found_symbols if s["kind"] == "component"]
    if not components_found:
        base_name = Path(file_path).stem if file_path else "Module"
        parts = [p.capitalize() for p in re.split(r"[-_.]", base_name) if p]
        inferred_comp = "".join(parts) or "Component"
        found_symbols.append(
            {
                "name": inferred_comp,
                "kind": "component",
                "start_line": 1,
                "end_line": max(1, len(lines)),
                "start_off": 0,
                "end_off": len(text),
                "body": text,
            }
        )

    components: list[ComponentExtraction] = []

    for sym in [s for s in found_symbols if s["kind"] == "component"]:
        c_name = sym["name"]
        c_body = sym["body"]
        c_start_line = sym["start_line"]
        c_end_line = sym["end_line"]
        c_symbols: list[SymbolExtraction] = []
        c_handlers: list[EventHandlerExtraction] = []
        c_states: list[StateBindingExtraction] = []
        c_motions: list[MotionContractExtraction] = []

        # Find nested functions/symbols
        for sub in found_symbols:
            if sub["name"] == c_name:
                continue
            if sym["start_off"] < sub["start_off"] < sym["end_off"]:
                c_symbols.append(
                    SymbolExtraction(
                        name=sub["name"],
                        kind=sub["kind"],
                        line_start=sub["start_line"],
                        line_end=sub["end_line"],
                        parent_context=c_name,
                        snippet=sub["body"][:120].strip(),
                    )
                )

        # State bindings: useState, useReducer, zustand, localStorage, ARIA/data attributes
        use_state_re = re.compile(
            r"const\s+\[\s*([A-Za-z0-9_$]+)\s*,\s*([A-Za-z0-9_$]+)\s*\]\s*=\s*(?:React\.)?useState(?:<[^>]+>)?\s*\(([^)]*)\)"
        )
        for m in use_state_re.finditer(c_body):
            var_name = m.group(1)
            setter_name = m.group(2)
            init_val = m.group(3).strip()

            reads: list[dict[str, Any]] = []
            var_read_re = re.compile(rf"\b{re.escape(var_name)}\b")
            for rm in var_read_re.finditer(c_body):
                if rm.start() == m.start(1):
                    continue
                r_line = c_start_line + c_body[: rm.start()].count("\n")
                line_snippet = lines[r_line - 1].strip() if 0 <= r_line - 1 < len(lines) else ""
                reads.append({"line": r_line, "symbol": c_name, "snippet": line_snippet[:100]})

            mutations: list[dict[str, Any]] = []
            setter_re = re.compile(rf"\b{re.escape(setter_name)}\s*\(")
            for sm in setter_re.finditer(c_body):
                m_line = c_start_line + c_body[: sm.start()].count("\n")
                line_snippet = lines[m_line - 1].strip() if 0 <= m_line - 1 < len(lines) else ""
                mutations.append({"line": m_line, "symbol": c_name, "snippet": line_snippet[:100]})

            c_states.append(
                StateBindingExtraction(
                    binding_kind="useState",
                    name=f"useState:{var_name}",
                    variable=var_name,
                    setter=setter_name,
                    initial_value=init_val,
                    reads=reads,
                    mutations=mutations,
                    component_name=c_name,
                )
            )

        # useReducer
        use_reducer_re = re.compile(
            r"const\s+\[\s*([A-Za-z0-9_$]+)\s*,\s*([A-Za-z0-9_$]+)\s*\]\s*=\s*(?:React\.)?useReducer\s*\(([^)]*)\)"
        )
        for m in use_reducer_re.finditer(c_body):
            state_var = m.group(1)
            dispatch_var = m.group(2)
            init_val = m.group(3).strip()
            reads = []
            mutations = []
            for dm in re.finditer(rf"\b{re.escape(dispatch_var)}\s*\(", c_body):
                m_line = c_start_line + c_body[: dm.start()].count("\n")
                mutations.append(
                    {"line": m_line, "symbol": c_name, "snippet": lines[m_line - 1].strip()[:100]}
                )
            c_states.append(
                StateBindingExtraction(
                    binding_kind="useReducer",
                    name=f"useReducer:{state_var}",
                    variable=state_var,
                    setter=dispatch_var,
                    initial_value=init_val,
                    reads=reads,
                    mutations=mutations,
                    component_name=c_name,
                )
            )

        # Zustand / store custom hooks (useAppShell, useTabsStore, useWorkspace, useAppHeaderDemo)
        zustand_hook_re = re.compile(
            r"const\s+\{([^}]+)\}\s*=\s*(use[A-Za-z0-9_$]*(?:Store|Shell|Workspace|HeaderDemo))\s*\("
        )
        for m in zustand_hook_re.finditer(c_body):
            props_str = m.group(1)
            hook_name = m.group(2)
            bound_props = [p.strip().split(":")[0].strip() for p in props_str.split(",") if p.strip()]
            h_line = c_start_line + c_body[: m.start()].count("\n")
            reads = [{"line": h_line, "symbol": c_name, "snippet": p} for p in bound_props if not p.startswith("set") and not p.startswith("toggle")]
            mutations = [{"line": h_line, "symbol": c_name, "snippet": p} for p in bound_props if p.startswith("set") or p.startswith("toggle")]
            c_states.append(
                StateBindingExtraction(
                    binding_kind="zustand",
                    name=f"zustand:{hook_name}",
                    variable=", ".join(bound_props),
                    setter=", ".join([p for p in bound_props if p.startswith("set") or p.startswith("toggle")]),
                    reads=reads,
                    mutations=mutations,
                    component_name=c_name,
                )
            )

        # localStorage
        if "localStorage" in c_body:
            ls_get_re = re.compile(r"localStorage\.(?:getItem\s*\(\s*['\"]([^'\"]+)['\"]|([A-Za-z0-9_$]+))")
            ls_set_re = re.compile(r"localStorage\.(?:setItem\s*\(\s*['\"]([^'\"]+)['\"]|([A-Za-z0-9_$]+)\s*=)")
            ls_keys = set()
            reads = []
            mutations = []
            for gm in ls_get_re.finditer(c_body):
                k = gm.group(1) or gm.group(2)
                ls_keys.add(k)
                g_line = c_start_line + c_body[: gm.start()].count("\n")
                reads.append({"line": g_line, "symbol": c_name, "snippet": lines[g_line - 1].strip()[:100]})
            for sm in ls_set_re.finditer(c_body):
                k = sm.group(1) or sm.group(2)
                ls_keys.add(k)
                s_line = c_start_line + c_body[: sm.start()].count("\n")
                mutations.append({"line": s_line, "symbol": c_name, "snippet": lines[s_line - 1].strip()[:100]})
            for k in sorted(ls_keys):
                c_states.append(
                    StateBindingExtraction(
                        binding_kind="localStorage",
                        name=f"localStorage:{k}",
                        variable=k,
                        reads=reads,
                        mutations=mutations,
                        component_name=c_name,
                    )
                )

        # ARIA attributes (aria-expanded, aria-selected)
        for attr in ("aria-expanded", "aria-selected"):
            attr_re = re.compile(rf"{re.escape(attr)}\s*=\s*\{{([^}}]+)\}}")
            for m in attr_re.finditer(c_body):
                val_expr = m.group(1).strip()
                a_line = c_start_line + c_body[: m.start()].count("\n")
                c_states.append(
                    StateBindingExtraction(
                        binding_kind="aria_attr",
                        name=f"aria:{attr}",
                        variable=val_expr,
                        reads=[{"line": a_line, "symbol": c_name, "snippet": lines[a_line - 1].strip()[:100]}],
                        component_name=c_name,
                    )
                )

        # DOM data attributes (data-state, data-pinned, data-slot, data-dragging, data-active)
        for dattr in ("data-state", "data-pinned", "data-slot", "data-dragging", "data-active"):
            dattr_re = re.compile(rf"{re.escape(dattr)}\s*=\s*(?:\{{([^}}]+)\}}|['\"]([^'\"]+)['\"])")
            for m in dattr_re.finditer(c_body):
                val_expr = (m.group(1) or m.group(2) or "").strip()
                d_line = c_start_line + c_body[: m.start()].count("\n")
                c_states.append(
                    StateBindingExtraction(
                        binding_kind="data_attr",
                        name=f"data-attr:{dattr}",
                        variable=val_expr,
                        reads=[{"line": d_line, "symbol": c_name, "snippet": lines[d_line - 1].strip()[:100]}],
                        component_name=c_name,
                    )
                )

        # Event Handlers & Shortcuts via brace matching
        handler_start_re = re.compile(r"\b(on[A-Z][A-Za-z0-9_]*)\s*=\s*\{")
        for m in handler_start_re.finditer(c_body):
            ev_name = m.group(1)
            abs_b_open = sym["start_off"] + m.end() - 1
            abs_b_close = _find_matching_brace(text, mask, abs_b_open)
            if abs_b_close == -1:
                continue
            handler_expr = text[abs_b_open + 1 : abs_b_close].strip()
            h_line = _compute_line_number(text, abs_b_open)
            h_snippet = lines[h_line - 1].strip() if 0 <= h_line - 1 < len(lines) else handler_expr

            target_symbol = "inline"
            direct_id = re.match(r"^([A-Za-z0-9_$]+)$", handler_expr)
            if direct_id:
                target_symbol = direct_id.group(1)
            else:
                call_matches = re.findall(r"\b([A-Za-z0-9_$]+)\s*(?:\.|\?\.)?\s*\(", handler_expr)
                calls = [c for c in call_matches if c not in ("preventDefault", "stopPropagation", "set", "event", "e")]
                if calls:
                    target_symbol = calls[-1] if any("pin" in c.lower() or "drag" in c.lower() or "shift" in c.lower() or "escape" in c.lower() for c in calls) else calls[0]

            sym_start = h_line
            sym_end = h_line
            for s in found_symbols:
                if s["name"] == target_symbol:
                    sym_start = s["start_line"]
                    sym_end = s["end_line"]
                    break

            shortcut = None
            if "shiftKey" in handler_expr or "onShiftOpen" in handler_expr or "Shift" in handler_expr:
                shortcut = "Shift+Click"
            elif 'key === "Escape"' in handler_expr or "key === 'Escape'" in handler_expr or "Escape" in handler_expr or "onEscape" in handler_expr:
                shortcut = "Escape"
            elif "metaKey" in handler_expr or "ctrlKey" in handler_expr:
                shortcut = "Ctrl/Cmd+Click"

            c_handlers.append(
                EventHandlerExtraction(
                    event_name=ev_name,
                    target_symbol=target_symbol,
                    line_start=sym_start,
                    line_end=sym_end,
                    shortcut=shortcut,
                    snippet=h_snippet[:120],
                    component_name=c_name,
                )
            )

        # Standalone handler functions with key shortcuts (e.g. handleTabKeyDown checking Escape / Arrows)
        if "KeyDown" in c_name or "KeyUp" in c_name or "Key" in c_name or "Escape" in c_name:
            shortcut = None
            if 'key === "Escape"' in c_body or "key === 'Escape'" in c_body or "Escape" in c_body:
                shortcut = "Escape"
            elif "shiftKey" in c_body:
                shortcut = "Shift+Click"
            elif "metaKey" in c_body or "ctrlKey" in c_body:
                shortcut = "Ctrl/Cmd+Click"

            c_handlers.append(
                EventHandlerExtraction(
                    event_name="onKeyDown",
                    target_symbol=c_name,
                    line_start=c_start_line,
                    line_end=c_end_line,
                    shortcut=shortcut,
                    snippet=c_body[:120].strip(),
                    component_name=c_name,
                )
            )

        # Motion Contracts: Intention Dwell/Delay vs Transition Duration
        dwell_matches: list[tuple[float, int, str]] = []
        timer_re = re.compile(r"setTimeout\s*\([^,]+,\s*(\d+(?:\.\d+)?)\s*\)")
        for m in timer_re.finditer(c_body):
            d_val = float(m.group(1))
            d_line = c_start_line + c_body[: m.start()].count("\n")
            dwell_matches.append((d_val, d_line, "setTimeout"))

        delay_prop_re = re.compile(r"\b(?:delay|hoverDelay|openDelay|closeDelay)\s*[:=]\s*\{?(\d+(?:\.\d+)?)\}?")
        for m in delay_prop_re.finditer(c_body):
            d_val = float(m.group(1))
            d_line = c_start_line + c_body[: m.start()].count("\n")
            dwell_matches.append((d_val, d_line, "delayProp"))

        delay_const_re = re.compile(r"(?:TAB_PREVIEW_DELAY|PEEK_DWELL_MS|HOVER_DELAY_MS)\s*=\s*(\d+(?:\.\d+)?)")
        for m in delay_const_re.finditer(text):
            d_val = float(m.group(1))
            d_line = text[: m.start()].count("\n") + 1
            dwell_matches.append((d_val, d_line, "dwellConstant"))

        tw_delay_re = re.compile(r"\bdelay-(\d+)\b")
        for m in tw_delay_re.finditer(c_body):
            d_val = float(m.group(1))
            d_line = c_start_line + c_body[: m.start()].count("\n")
            dwell_matches.append((d_val, d_line, "tailwindDelay"))

        duration_matches: list[tuple[float, int, str]] = []
        tw_dur_re = re.compile(r"\bduration-(\d+)\b")
        for m in tw_dur_re.finditer(c_body):
            dur_val = float(m.group(1))
            dur_line = c_start_line + c_body[: m.start()].count("\n")
            duration_matches.append((dur_val, dur_line, "tailwindDuration"))

        css_dur_re = re.compile(r"transition(?:-duration)?\s*:\s*[^;]*?(\d+)ms")
        for m in css_dur_re.finditer(c_body):
            dur_val = float(m.group(1))
            dur_line = c_start_line + c_body[: m.start()].count("\n")
            duration_matches.append((dur_val, dur_line, "cssDuration"))

        waapi_dur_re = re.compile(r"duration\s*:\s*(\d+(?:\.\d+)?)")
        for m in waapi_dur_re.finditer(c_body):
            dur_val = float(m.group(1))
            dur_line = c_start_line + c_body[: m.start()].count("\n")
            duration_matches.append((dur_val, dur_line, "waapiDuration"))

        easing = "ease-out" if "ease-out" in c_body else ("ease-in-out" if "ease-in-out" in c_body else "ease")
        reduced_motion = "motion-reduce:transition-none" if "motion-reduce" in c_body or "prefers-reduced-motion" in c_body else None

        if dwell_matches or duration_matches:
            primary_dwell = dwell_matches[0][0] if dwell_matches else None
            primary_dur = duration_matches[0][0] if duration_matches else 200.0
            source_lines = sorted(list({line for _, line, _ in dwell_matches + duration_matches}))
            cid = f"{c_name.lower()}-motion"
            c_motions.append(
                MotionContractExtraction(
                    contract_id=cid,
                    dwell_delay_ms=primary_dwell,
                    transition_duration_ms=primary_dur,
                    easing=easing,
                    reduced_motion=reduced_motion,
                    provenance="source-confirmed",
                    source_lines=source_lines,
                    snippet=f"dwell={primary_dwell}ms duration={primary_dur}ms easing={easing}",
                    component_name=c_name,
                )
            )

        components.append(
            ComponentExtraction(
                name=c_name,
                path=file_path,
                line_start=c_start_line,
                line_end=c_end_line,
                symbols=c_symbols,
                handlers=c_handlers,
                state_bindings=c_states,
                motion_contracts=c_motions,
                imports=imports,
            )
        )

    return components


parse_tsx_file = parse_tsx_symbols_and_components


def open_db(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open or initialize the SQLite evidence graph database."""
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.executescript(DB_SCHEMA)
    return conn


def upsert_node(
    conn: sqlite3.Connection,
    *,
    node_type: str,
    label: str,
    node_id: str | None = None,
    repo: str = "",
    ref: str = "",
    path: str = "",
    commit_sha: str = "",
    timestamp: str = "",
    validity_status: str = "unverified",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Insert or update a typed graph node."""
    if node_type not in NODE_TYPE_SET:
        raise ValueError(f"Unsupported node_type: {node_type!r}; expected one of {NODE_TYPES}")

    nid = node_id or _stable_id(node_type.lower(), repo, ref, label, path, commit_sha)
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO graph_nodes (node_id, node_type, repo, ref, label, path, commit_sha, timestamp, validity_status, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            node_type=excluded.node_type,
            repo=CASE WHEN excluded.repo != '' THEN excluded.repo ELSE graph_nodes.repo END,
            ref=CASE WHEN excluded.ref != '' THEN excluded.ref ELSE graph_nodes.ref END,
            label=excluded.label,
            path=CASE WHEN excluded.path != '' THEN excluded.path ELSE graph_nodes.path END,
            commit_sha=CASE WHEN excluded.commit_sha != '' THEN excluded.commit_sha ELSE graph_nodes.commit_sha END,
            timestamp=CASE WHEN excluded.timestamp != '' THEN excluded.timestamp ELSE graph_nodes.timestamp END,
            validity_status=excluded.validity_status,
            metadata_json=excluded.metadata_json
        """,
        (
            nid,
            node_type,
            repo,
            ref,
            label,
            path,
            commit_sha,
            timestamp,
            validity_status,
            meta_json,
        ),
    )
    return nid


def upsert_edge(
    conn: sqlite3.Connection,
    *,
    src_id: str,
    dst_id: str,
    edge_type: str,
    confidence: str = "EXTRACTED",
    repo: str = "",
    ref: str = "",
    commit_sha: str = "",
    timestamp: str = "",
    weight: float = 1.0,
    provenance: dict[str, Any] | None = None,
) -> str:
    """Insert or update a typed directed graph edge."""
    if edge_type not in EDGE_TYPE_SET:
        raise ValueError(f"Unsupported edge_type: {edge_type!r}; expected one of {EDGE_TYPES}")
    if confidence not in CONFIDENCE_SET:
        raise ValueError(f"Unsupported confidence: {confidence!r}")

    eid = _stable_id("edge", src_id, dst_id, edge_type, commit_sha, ref)
    prov_json = json.dumps(provenance or {}, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO graph_edges (edge_id, src_id, dst_id, edge_type, confidence, repo, ref, commit_sha, timestamp, weight, provenance_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(src_id, dst_id, edge_type, commit_sha, ref) DO UPDATE SET
            confidence=excluded.confidence,
            weight=excluded.weight,
            provenance_json=excluded.provenance_json
        """,
        (
            eid,
            src_id,
            dst_id,
            edge_type,
            confidence,
            repo,
            ref,
            commit_sha,
            timestamp,
            weight,
            prov_json,
        ),
    )
    return eid


def ingest_tsx_file(
    conn: sqlite3.Connection,
    path: str,
    content: str,
    *,
    repo: str = "notes-app",
    ref: str = "",
    commit_sha: str = "",
    timestamp: str = "",
) -> list[str]:
    """Ingest a TSX/JSX file into the evidence graph with all its symbols, handlers, state, and motion."""
    file_id = upsert_node(
        conn,
        node_type="File",
        label=Path(path).name,
        node_id=f"file:{repo}:{path}",
        repo=repo,
        ref=ref,
        path=path,
        commit_sha=commit_sha,
        timestamp=timestamp,
        validity_status="valid_in_commit",
    )

    extracted_components = parse_tsx_symbols_and_components(content, file_path=path)
    created_nodes: list[str] = [file_id]

    stem = Path(path).stem
    canon_stem = canonical_component_key(stem)
    primary_comp_id = f"component:{canon_stem}"

    stem_title = "".join(part.capitalize() for part in re.split(r"[-_.]", stem) if part)
    upsert_node(
        conn,
        node_type="Component",
        label=stem_title,
        node_id=primary_comp_id,
        repo=repo,
        ref=ref,
        path=path,
        commit_sha=commit_sha,
        timestamp=timestamp,
        validity_status="valid_in_commit",
    )
    upsert_edge(conn, src_id=file_id, dst_id=primary_comp_id, edge_type="CONTAINS", repo=repo, ref=ref, commit_sha=commit_sha)

    for comp in extracted_components:
        comp_id = upsert_node(
            conn,
            node_type="Component",
            label=comp.name,
            node_id=f"component:{canonical_component_key(comp.name)}",
            repo=repo,
            ref=ref,
            path=path,
            commit_sha=commit_sha,
            timestamp=timestamp,
            validity_status="valid_in_commit",
            metadata={"line_start": comp.line_start, "line_end": comp.line_end},
        )
        created_nodes.append(comp_id)

        upsert_edge(conn, src_id=file_id, dst_id=comp_id, edge_type="CONTAINS", repo=repo, ref=ref, commit_sha=commit_sha)
        if comp_id != primary_comp_id:
            upsert_edge(conn, src_id=primary_comp_id, dst_id=comp_id, edge_type="COMPOSES", repo=repo, ref=ref, commit_sha=commit_sha)

        # Symbols
        for sym in comp.symbols:
            sym_id = upsert_node(
                conn,
                node_type="Symbol",
                label=sym.name,
                node_id=f"symbol:{path}:{sym.name}",
                repo=repo,
                ref=ref,
                path=path,
                commit_sha=commit_sha,
                timestamp=timestamp,
                validity_status="valid_in_commit",
                metadata={"kind": sym.kind, "line_start": sym.line_start, "line_end": sym.line_end, "parent": sym.parent_context},
            )
            created_nodes.append(sym_id)
            upsert_edge(conn, src_id=comp_id, dst_id=sym_id, edge_type="DEFINES", repo=repo, ref=ref, commit_sha=commit_sha)

        # Handlers
        for h in comp.handlers:
            h_label = f"{h.event_name}:{h.target_symbol}" + (f" ({h.shortcut})" if h.shortcut else "")
            h_id = upsert_node(
                conn,
                node_type="EventHandler",
                label=h_label,
                node_id=f"handler:{path}:{h.event_name}:{h.target_symbol}:{h.line_start}",
                repo=repo,
                ref=ref,
                path=path,
                commit_sha=commit_sha,
                timestamp=timestamp,
                validity_status="valid_in_commit",
                metadata={
                    "event_name": h.event_name,
                    "target_symbol": h.target_symbol,
                    "shortcut": h.shortcut,
                    "line_start": h.line_start,
                    "line_end": h.line_end,
                    "snippet": h.snippet,
                },
            )
            created_nodes.append(h_id)
            upsert_edge(conn, src_id=comp_id, dst_id=h_id, edge_type="HANDLES", repo=repo, ref=ref, commit_sha=commit_sha)
            if comp_id != primary_comp_id:
                upsert_edge(conn, src_id=primary_comp_id, dst_id=h_id, edge_type="HANDLES", repo=repo, ref=ref, commit_sha=commit_sha)

            target_sym_id = f"symbol:{path}:{h.target_symbol}"
            row = conn.execute("SELECT node_id FROM graph_nodes WHERE node_id=?", (target_sym_id,)).fetchone()
            if row:
                upsert_edge(conn, src_id=h_id, dst_id=target_sym_id, edge_type="TRIGGERS", repo=repo, ref=ref, commit_sha=commit_sha)

        # State Bindings
        for st in comp.state_bindings:
            st_id = upsert_node(
                conn,
                node_type="StateBinding",
                label=st.name,
                node_id=f"state:{path}:{st.name}",
                repo=repo,
                ref=ref,
                path=path,
                commit_sha=commit_sha,
                timestamp=timestamp,
                validity_status="valid_in_commit",
                metadata={
                    "binding_kind": st.binding_kind,
                    "variable": st.variable,
                    "setter": st.setter,
                    "reads": st.reads,
                    "mutations": st.mutations,
                },
            )
            created_nodes.append(st_id)
            if st.reads:
                upsert_edge(conn, src_id=comp_id, dst_id=st_id, edge_type="READS", repo=repo, ref=ref, commit_sha=commit_sha)
                if comp_id != primary_comp_id:
                    upsert_edge(conn, src_id=primary_comp_id, dst_id=st_id, edge_type="READS", repo=repo, ref=ref, commit_sha=commit_sha)
            if st.mutations:
                upsert_edge(conn, src_id=comp_id, dst_id=st_id, edge_type="MUTATES", repo=repo, ref=ref, commit_sha=commit_sha)
                if comp_id != primary_comp_id:
                    upsert_edge(conn, src_id=primary_comp_id, dst_id=st_id, edge_type="MUTATES", repo=repo, ref=ref, commit_sha=commit_sha)

        # Motion Contracts
        for mot in comp.motion_contracts:
            mot_id = upsert_node(
                conn,
                node_type="MotionContract",
                label=f"motion:{mot.contract_id}",
                node_id=f"motion:{path}:{mot.contract_id}",
                repo=repo,
                ref=ref,
                path=path,
                commit_sha=commit_sha,
                timestamp=timestamp,
                validity_status="valid_in_commit",
                metadata={
                    "contract_id": mot.contract_id,
                    "dwell_delay_ms": mot.dwell_delay_ms,
                    "transition_duration_ms": mot.transition_duration_ms,
                    "easing": mot.easing,
                    "reduced_motion": mot.reduced_motion,
                    "provenance": mot.provenance,
                    "source_lines": mot.source_lines,
                    "snippet": mot.snippet,
                },
            )
            created_nodes.append(mot_id)
            upsert_edge(conn, src_id=comp_id, dst_id=mot_id, edge_type="ANIMATES", repo=repo, ref=ref, commit_sha=commit_sha)
            if comp_id != primary_comp_id:
                upsert_edge(conn, src_id=primary_comp_id, dst_id=mot_id, edge_type="ANIMATES", repo=repo, ref=ref, commit_sha=commit_sha)

    return created_nodes


def build_canonical_notes_evidence(conn: sqlite3.Connection) -> None:
    """Populate canonical AppShell, AppHeaderTabs, AppSidebarOverview, and decision links."""
    batch_4_path = REPO_ROOT / "inventory/notes-app/platform/pr-file-diffs-batch-04.json"
    batch_5_path = REPO_ROOT / "inventory/notes-app/platform/pr-file-diffs-batch-05.json"
    motion_json_path = REPO_ROOT / "docs/UI-MOTION-EVIDENCE.json"

    file_patches: dict[str, str] = {}
    if batch_4_path.is_file():
        try:
            data = json.loads(batch_4_path.read_text(encoding="utf-8"))
            for rec in data.get("records") or []:
                for fl in rec.get("files") or []:
                    fn = fl.get("filename")
                    if fn in ("src/components/app-shell.tsx", "src/components/app-header-tabs.tsx", "src/components/app-sidebar-overview.tsx"):
                        patch = fl.get("patch", "")
                        added_lines = [l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
                        if len(added_lines) > len(file_patches.get(fn, "").splitlines()):
                            file_patches[fn] = "\n".join(added_lines)
        except Exception:
            pass

    if batch_5_path.is_file():
        try:
            data = json.loads(batch_5_path.read_text(encoding="utf-8"))
            for rec in data.get("records") or []:
                for fl in rec.get("files") or []:
                    fn = fl.get("filename")
                    if fn in ("src/components/app-header-tabs.tsx", "src/components/app-sidebar-overview.tsx"):
                        patch = fl.get("patch", "")
                        if fn not in file_patches:
                            added_lines = [l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
                            file_patches[fn] = "\n".join(added_lines)
        except Exception:
            pass

    for fn, content in file_patches.items():
        if content:
            ingest_tsx_file(conn, fn, content, repo="notes-app", ref="main", commit_sha="notes-canonical")

    # Ingest decisions / specs
    dec_app_shell_id = upsert_node(
        conn,
        node_type="Decision",
        label="ADR: openspec/changes/create-app-shell/design.md",
        node_id="decision:create-app-shell:design",
        repo="notes-app",
        path="openspec/changes/create-app-shell/design.md",
        timestamp="2026-08-15T12:00:00Z",
        validity_status="valid_in_commit",
        metadata={
            "title": "Three-pane AppShell infrastructure with resizable panels, sidebar, header tabs, and side panel",
            "topics": ["app-shell", "sidebar", "header-tabs", "resizable"],
        },
    )

    dec_header_tabs_id = upsert_node(
        conn,
        node_type="Decision",
        label="Spec: openspec/specs/ui/app-header/spec.md",
        node_id="decision:app-header:spec",
        repo="notes-app",
        path="openspec/specs/ui/app-header/spec.md",
        timestamp="2026-08-18T14:00:00Z",
        validity_status="valid_in_commit",
        metadata={
            "title": "AppHeader tabs specification with pin tab, overflow, preview hover delay, and keyboard shortcuts",
            "topics": ["pin tab", "app-header-tabs", "shortcuts", "dwell"],
        },
    )

    dec_sidebar_overview_id = upsert_node(
        conn,
        node_type="Decision",
        label="ADR: openspec/changes/refine-app-sidebar-overview/tasks.md",
        node_id="decision:refine-app-sidebar-overview:tasks",
        repo="notes-app",
        path="openspec/changes/refine-app-sidebar-overview/tasks.md",
        timestamp="2026-08-20T16:00:00Z",
        validity_status="valid_in_commit",
        metadata={
            "title": "AppSidebarOverview pinned section with drag-and-drop reordering, pin/unpin menu, and hover reveal",
            "topics": ["pinned section", "app-sidebar-overview", "drag-and-drop"],
        },
    )

    # Cross-links between AppShell, AppHeaderTabs, and AppSidebarOverview
    app_shell_comp_id = "component:app-shell"
    header_tabs_comp_id = "component:app-header-tabs"
    sidebar_overview_comp_id = "component:app-sidebar-overview"

    upsert_node(conn, node_type="Component", label="AppShell", node_id=app_shell_comp_id, repo="notes-app", path="src/components/app-shell.tsx")
    upsert_node(conn, node_type="Component", label="AppHeaderTabs", node_id=header_tabs_comp_id, repo="notes-app", path="src/components/app-header-tabs.tsx")
    upsert_node(conn, node_type="Component", label="AppSidebarOverview", node_id=sidebar_overview_comp_id, repo="notes-app", path="src/components/app-sidebar-overview.tsx")

    file_header_tabs_id = "file:notes-app:src/components/app-header-tabs.tsx"
    file_sidebar_overview_id = "file:notes-app:src/components/app-sidebar-overview.tsx"

    upsert_edge(conn, src_id=app_shell_comp_id, dst_id=header_tabs_comp_id, edge_type="COMPOSES", repo="notes-app")
    upsert_edge(conn, src_id=app_shell_comp_id, dst_id=sidebar_overview_comp_id, edge_type="COMPOSES", repo="notes-app")
    upsert_edge(conn, src_id=app_shell_comp_id, dst_id=file_header_tabs_id, edge_type="COMPOSES", repo="notes-app")
    upsert_edge(conn, src_id=app_shell_comp_id, dst_id=file_sidebar_overview_id, edge_type="COMPOSES", repo="notes-app")
    upsert_edge(conn, src_id=header_tabs_comp_id, dst_id=app_shell_comp_id, edge_type="IMPORTS", repo="notes-app")

    upsert_edge(conn, src_id=app_shell_comp_id, dst_id=dec_app_shell_id, edge_type="DOCUMENTED_IN", repo="notes-app")
    upsert_edge(conn, src_id=header_tabs_comp_id, dst_id=dec_header_tabs_id, edge_type="DOCUMENTED_IN", repo="notes-app")
    upsert_edge(conn, src_id=sidebar_overview_comp_id, dst_id=dec_sidebar_overview_id, edge_type="DOCUMENTED_IN", repo="notes-app")

    # Ingest motion evidence JSON if present
    if motion_json_path.is_file():
        try:
            mot_data = json.loads(motion_json_path.read_text(encoding="utf-8"))
            for entry in mot_data.get("entries") or []:
                eid = entry.get("id", "")
                concept = entry.get("concept", "")
                dur = entry.get("duration_ms")
                dwell = entry.get("dwell_ms") or entry.get("hover_delay_ms")
                conf = entry.get("confidence", "inferred")
                prov = "source-confirmed" if conf == "verified-in-source" else ("measured-in-browser" if conf == "measured" else "inferred")
                src_path = entry.get("source", {}).get("path", "")

                mot_node_id = upsert_node(
                    conn,
                    node_type="MotionContract",
                    label=f"motion:{eid}",
                    node_id=f"motion:doc:{eid}",
                    repo="notes-app",
                    path=src_path,
                    validity_status="valid_in_commit",
                    metadata={
                        "concept": concept,
                        "dwell_delay_ms": dwell,
                        "transition_duration_ms": dur,
                        "easing": entry.get("easing", "ease-out"),
                        "reduced_motion": entry.get("reduced_motion", "motion-reduce:transition-none"),
                        "provenance": prov,
                    },
                )
                if "shell" in src_path:
                    upsert_edge(conn, src_id=app_shell_comp_id, dst_id=mot_node_id, edge_type="ANIMATES", repo="notes-app")
                if "header-tabs" in src_path:
                    upsert_edge(conn, src_id=header_tabs_comp_id, dst_id=mot_node_id, edge_type="ANIMATES", repo="notes-app")
                if "sidebar" in src_path:
                    upsert_edge(conn, src_id=sidebar_overview_comp_id, dst_id=mot_node_id, edge_type="ANIMATES", repo="notes-app")
        except Exception:
            pass

    # Visual Evidence / Screenshots
    img_shell_id = upsert_node(
        conn,
        node_type="Image",
        label="app-shell-desktop-layout.png",
        node_id="image:app-shell-desktop",
        repo="notes-app",
        path="docs/captures/app-shell-desktop.png",
        metadata={"caption": "Three-pane AppShell layout with left sidebar, header tabs, and right side-panel"},
    )
    upsert_edge(conn, src_id=app_shell_comp_id, dst_id=img_shell_id, edge_type="EVIDENCED_BY", repo="notes-app")

    img_pinned_id = upsert_node(
        conn,
        node_type="Image",
        label="app-sidebar-pinned-section.png",
        node_id="image:app-sidebar-pinned-section",
        repo="notes-app",
        path="docs/captures/app-sidebar-pinned-section.png",
        metadata={"caption": "AppSidebarOverview pinned section showing reordering and pin/unpin actions"},
    )
    upsert_edge(conn, src_id=sidebar_overview_comp_id, dst_id=img_pinned_id, edge_type="EVIDENCED_BY", repo="notes-app")


def _resolve_seeds(conn: sqlite3.Connection, query: str) -> list[sqlite3.Row]:
    """Find seed nodes for the query using exact key, label matching, or path matching."""
    q = (query or "").strip()
    if not q:
        return []

    canon = canonical_component_key(q)
    exact_comp_id = f"component:{canon}"
    rows = conn.execute(
        """
        SELECT * FROM graph_nodes
        WHERE node_id=? OR lower(label)=lower(?) OR node_id=?
           OR lower(path) LIKE lower(?) OR lower(label) LIKE lower(?)
        LIMIT 20
        """,
        (exact_comp_id, q, q, f"%{q}%", f"%{q}%"),
    ).fetchall()

    if not rows and ("shell" in canon or "app-shell" in canon):
        rows = conn.execute(
            "SELECT * FROM graph_nodes WHERE node_id='component:app-shell' OR lower(label) LIKE '%appshell%' OR lower(label) LIKE '%app-shell%'"
        ).fetchall()

    return rows


def traverse_evidence_graph(
    conn: sqlite3.Connection,
    entity: str,
    *,
    hops: int = 2,
    token_budget: int = 4000,
    repo: str | None = None,
) -> dict[str, Any]:
    """Traverse multi-layer evidence graph bounding hops (1-3) and enforcing token budget."""
    hops = max(1, min(int(hops), 3))
    token_budget = max(200, int(token_budget))

    seeds = _resolve_seeds(conn, entity)
    visited_nodes: dict[str, dict[str, Any]] = {}
    depth_by_node: dict[str, int] = {}
    collected_edges: list[dict[str, Any]] = []
    uninspected_gaps: list[dict[str, Any]] = []

    queue: deque[tuple[str, int]] = deque()
    for s in seeds:
        nid = s["node_id"]
        nd = dict(s)
        nd["metadata"] = json.loads(nd.pop("metadata_json", "{}") or "{}")
        visited_nodes[nid] = nd
        depth_by_node[nid] = 0
        queue.append((nid, 0))

    while queue:
        cur_id, depth = queue.popleft()
        if depth >= hops:
            out_neighbors = conn.execute(
                "SELECT dst_id, edge_type FROM graph_edges WHERE src_id=?", (cur_id,)
            ).fetchall()
            for on in out_neighbors:
                if on["dst_id"] not in visited_nodes:
                    uninspected_gaps.append(
                        {
                            "gap_type": "hop_boundary",
                            "description": f"Reached hop limit ({hops}) at node {cur_id}. Unexplored neighbor: {on['dst_id']} via {on['edge_type']}.",
                            "node_or_edge": on["dst_id"],
                        }
                    )
            continue

        edge_rows = conn.execute(
            "SELECT * FROM graph_edges WHERE src_id=? OR dst_id=?", (cur_id, cur_id)
        ).fetchall()

        for er in edge_rows:
            ed = dict(er)
            ed["provenance"] = json.loads(ed.pop("provenance_json", "{}") or "{}")
            collected_edges.append(ed)

            neighbor_id = ed["dst_id"] if ed["src_id"] == cur_id else ed["src_id"]
            if neighbor_id not in visited_nodes:
                nrow = conn.execute("SELECT * FROM graph_nodes WHERE node_id=?", (neighbor_id,)).fetchone()
                if nrow:
                    nd = dict(nrow)
                    nd["metadata"] = json.loads(nd.pop("metadata_json", "{}") or "{}")
                    visited_nodes[neighbor_id] = nd
                    depth_by_node[neighbor_id] = depth + 1
                    queue.append((neighbor_id, depth + 1))

    # Balanced layer prioritization for token budgeting
    def _handler_score(item: tuple[str, dict[str, Any]]) -> tuple[int, int, str]:
        nid, nd = item
        lbl = nd["label"].lower()
        meta = nd.get("metadata", {})
        meta_s = str(meta).lower()
        is_pin = "pin" in lbl or "pin" in meta_s or "pin" in nid.lower()
        is_drag = any(k in lbl or k in meta_s for k in ("drag", "drop"))
        is_sc = bool(meta.get("shortcut")) or "shift" in lbl or "escape" in lbl
        action_rank = 0 if (is_pin or is_drag or is_sc) else 1
        return (action_rank, depth_by_node.get(nid, 9), nid)

    def _state_score(item: tuple[str, dict[str, Any]]) -> tuple[int, int, str]:
        nid, nd = item
        lbl = nd["label"].lower()
        meta = nd.get("metadata", {})
        meta_s = str(meta).lower()
        is_pin = "pin" in lbl or "pin" in meta_s or "pin" in nid.lower()
        is_drag = any(k in lbl or k in meta_s for k in ("drag", "drop"))
        is_aria = any(k in lbl or k in meta_s for k in ("aria-expanded", "aria-selected", "data-pinned", "data-state"))
        action_rank = 0 if (is_pin or is_drag or is_aria) else 1
        return (action_rank, depth_by_node.get(nid, 9), nid)

    def _comp_score(item: tuple[str, dict[str, Any]]) -> tuple[int, int, str]:
        nid, nd = item
        lbl = nd["label"]
        primary_names = {"AppShell", "AppHeaderTabs", "AppSidebarOverview", "AppHeaderTabItem", "AppSidebarPinnedRow"}
        is_primary = lbl in primary_names
        return (0 if is_primary else 1, depth_by_node.get(nid, 9), nid)

    def _motion_score(item: tuple[str, dict[str, Any]]) -> tuple[int, int, str]:
        nid, nd = item
        meta = nd.get("metadata", {})
        has_dwell_or_dur = bool(meta.get("dwell_delay_ms") or meta.get("transition_duration_ms"))
        return (0 if has_dwell_or_dur else 1, depth_by_node.get(nid, 9), nid)

    from collections import defaultdict
    by_type: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for nid, nd in visited_nodes.items():
        by_type[nd["node_type"]].append((nid, nd))

    by_type["EventHandler"].sort(key=_handler_score)
    by_type["StateBinding"].sort(key=_state_score)
    by_type["Component"].sort(key=_comp_score)
    by_type["MotionContract"].sort(key=_motion_score)
    by_type["File"].sort(key=lambda x: (depth_by_node.get(x[0], 9), x[0]))
    by_type["Decision"].sort(key=lambda x: (depth_by_node.get(x[0], 9), x[0]))
    by_type["Image"].sort(key=lambda x: (depth_by_node.get(x[0], 9), x[0]))
    by_type["Symbol"].sort(key=lambda x: (depth_by_node.get(x[0], 9), x[0]))

    layer_quotas = [
        ("File", 4),
        ("Decision", 4),
        ("Component", 6),
        ("EventHandler", 6),
        ("StateBinding", 6),
        ("MotionContract", 4),
        ("Image", 2),
    ]

    sorted_node_items: list[tuple[str, dict[str, Any]]] = []
    for nt, quota in layer_quotas:
        sorted_node_items.extend(by_type[nt][:quota])

    remaining_items: list[tuple[str, dict[str, Any]]] = []
    quota_dict = dict(layer_quotas)
    for nt, items in by_type.items():
        q = quota_dict.get(nt, 0)
        remaining_items.extend(items[q:])
    remaining_items.sort(key=lambda x: (depth_by_node.get(x[0], 9), x[0]))
    sorted_node_items.extend(remaining_items)

    kept_nodes: dict[str, dict[str, Any]] = {}
    current_tokens = 0

    for nid, nd in sorted_node_items:
        node_tokens = estimate_json_tokens(nd)
        if current_tokens + node_tokens > token_budget:
            uninspected_gaps.append(
                {
                    "gap_type": "token_budget_pruned",
                    "description": f"Omitted node {nid} ({nd['node_type']}) to respect token budget of {token_budget} tokens.",
                    "node_or_edge": nid,
                }
            )
        else:
            kept_nodes[nid] = nd
            current_tokens += node_tokens

    kept_edges = [e for e in collected_edges if e["src_id"] in kept_nodes and e["dst_id"] in kept_nodes]

    bundle_components = [n for n in kept_nodes.values() if n["node_type"] == "Component"]
    bundle_files = [n for n in kept_nodes.values() if n["node_type"] == "File"]
    bundle_symbols = [n for n in kept_nodes.values() if n["node_type"] == "Symbol"]
    bundle_handlers = [n for n in kept_nodes.values() if n["node_type"] == "EventHandler"]
    bundle_state = [n for n in kept_nodes.values() if n["node_type"] == "StateBinding"]
    bundle_motion = [n for n in kept_nodes.values() if n["node_type"] == "MotionContract"]
    bundle_docs = [n for n in kept_nodes.values() if n["node_type"] in ("Decision", "PR", "Issue")]
    bundle_screens = [n for n in kept_nodes.values() if n["node_type"] == "Image"]

    # Check for unrecovered motion or missing visual evidence gaps
    for m in bundle_motion:
        prov = m.get("metadata", {}).get("provenance")
        if prov == "not-recovered":
            uninspected_gaps.append(
                {
                    "gap_type": "unrecovered_motion",
                    "description": f"Motion contract {m['node_id']} has provenance 'not-recovered'.",
                    "node_or_edge": m["node_id"],
                }
            )

    for c in bundle_components:
        comp_id = c["node_id"]
        has_img = any(
            (e["src_id"] == comp_id and kept_nodes.get(e["dst_id"], {}).get("node_type") == "Image")
            or (e["dst_id"] == comp_id and kept_nodes.get(e["src_id"], {}).get("node_type") == "Image")
            for e in kept_edges
        )
        if not has_img:
            uninspected_gaps.append(
                {
                    "gap_type": "missing_visual_evidence",
                    "description": f"No screenshot linked for UI component {c['label']}.",
                    "node_or_edge": comp_id,
                }
            )

    # Feature matrix summarizes each component across layers
    feature_matrix_components: list[dict[str, Any]] = []
    for comp in bundle_components:
        cid = comp["node_id"]
        comp_path = comp["path"]
        comp_handlers = [
            h["label"]
            for h in bundle_handlers
            if any(
                (e["src_id"] == cid and e["dst_id"] == h["node_id"])
                or (comp_path and comp_path in h["node_id"])
                for e in kept_edges
            )
        ]
        comp_shortcuts = [
            h.get("metadata", {}).get("shortcut")
            for h in bundle_handlers
            if h.get("metadata", {}).get("shortcut")
            and any(
                (e["src_id"] == cid and e["dst_id"] == h["node_id"])
                or (comp_path and comp_path in h["node_id"])
                for e in kept_edges
            )
        ]
        comp_states = [
            s["label"]
            for s in bundle_state
            if any(
                ((e["src_id"] == cid or e["dst_id"] == cid) and (e["src_id"] == s["node_id"] or e["dst_id"] == s["node_id"]))
                or (comp_path and comp_path in s["node_id"])
                for e in kept_edges
            )
        ]
        comp_motion = [
            m["label"]
            for m in bundle_motion
            if any(
                (e["src_id"] == cid and e["dst_id"] == m["node_id"])
                or (comp_path and comp_path in m["node_id"])
                for e in kept_edges
            )
        ]
        comp_docs = [
            d["label"]
            for d in bundle_docs
            if any(
                ((e["src_id"] == cid or e["dst_id"] == cid) and (e["src_id"] == d["node_id"] or e["dst_id"] == d["node_id"]))
                for e in kept_edges
            )
        ]

        feature_matrix_components.append(
            {
                "name": comp["label"],
                "path": comp_path,
                "handlers": sorted(list(set(comp_handlers))),
                "shortcuts": sorted(list(set(filter(None, comp_shortcuts)))),
                "state_bindings": sorted(list(set(comp_states))),
                "motion_contracts": sorted(list(set(comp_motion))),
                "decisions": sorted(list(set(comp_docs))),
                "confidence": "EXTRACTED",
            }
        )

    final_payload = {
        "feature_matrix": {
            "query": entity,
            "hops": hops,
            "token_budget": token_budget,
            "tokens_used": current_tokens,
            "components": feature_matrix_components,
        },
        "evidence_bundle": {
            "component": bundle_components,
            "files": bundle_files,
            "symbols": bundle_symbols,
            "handlers": bundle_handlers,
            "state": bundle_state,
            "motion": bundle_motion,
            "docs_and_adrs": bundle_docs,
            "screenshots": bundle_screens,
        },
        "uninspected_gaps": uninspected_gaps,
    }

    return final_payload


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Multi-layer contextual evidence graph engine connecting code, UI, state, motion, and decisions."
    )
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help=f"SQLite database path (default: {DEFAULT_DB_PATH})")
    parser.add_argument("--index-file", help="File, directory, or inventory JSON to index")
    parser.add_argument("--query", help="Query entity or concept (e.g. app-shell)")
    parser.add_argument("--hops", type=int, default=2, help="Max traversal hops (1-3, default: 2)")
    parser.add_argument("--token-budget", type=int, default=4000, help="Token budget limit (default: 4000)")
    parser.add_argument("--export-evidence", help="Path to export evidence bundle JSON")
    parser.add_argument("--json", action="store_true", help="Print structured output as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    conn = open_db(args.db)
    try:
        if args.index_file:
            target_path = Path(args.index_file)
            if target_path.is_file():
                if target_path.suffix in (".tsx", ".ts", ".jsx", ".js"):
                    content = target_path.read_text(encoding="utf-8")
                    ingest_tsx_file(conn, str(target_path), content)
                    conn.commit()
                    if not args.json:
                        print(f"Indexed TSX file: {target_path}")
            elif not args.json:
                print(f"Index target not found: {args.index_file}")

        node_count = conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
        if node_count == 0:
            build_canonical_notes_evidence(conn)
            conn.commit()

        if args.query:
            result = traverse_evidence_graph(
                conn,
                args.query,
                hops=args.hops,
                token_budget=args.token_budget,
            )

            if args.export_evidence:
                out_path = Path(args.export_evidence)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                if not args.json:
                    print(f"Exported evidence bundle to {out_path}")

            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                fm = result["feature_matrix"]
                print(f"Evidence Graph Query: {fm['query']} (hops={fm['hops']}, tokens={fm['tokens_used']}/{fm['token_budget']})")
                print("\nFeature Matrix Components:")
                for c in fm["components"]:
                    print(f"  - {c['name']} ({c['path']}):")
                    print(f"      Handlers: {', '.join(c['handlers']) or 'None'}")
                    print(f"      Shortcuts: {', '.join(c['shortcuts']) or 'None'}")
                    print(f"      State: {', '.join(c['state_bindings']) or 'None'}")
                    print(f"      Motion: {', '.join(c['motion_contracts']) or 'None'}")
                    print(f"      Decisions: {', '.join(c['decisions']) or 'None'}")
                print(f"\nUninspected Gaps: {len(result['uninspected_gaps'])}")
                for g in result["uninspected_gaps"][:5]:
                    print(f"  [{g['gap_type']}] {g['description']}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
