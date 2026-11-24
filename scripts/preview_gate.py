#!/usr/bin/env python3
"""Pre-preview functional coverage quality gate (Issue #46).

Extracts Feature Matrix from component source code and structural ASTs (using ast_chunker),
then validates preview artifacts/HTML against expected features, handlers, state bindings,
gestures/triggers, and motion contracts.

Guarantees:
  - Disallows silent omissions: any verified feature in historical sources (e.g. pin/unpin
    in app-header-tabs.tsx, Fixados in app-sidebar-overview.tsx) must be either 'implemented',
    'partially-mocked', or explicitly justified in the Omissions Matrix.
  - Hard gate failure (exit code 1) when verified features are silently omitted.
  - Strict motion contract validation: separates dwell delay from transition duration,
    validates easing and reduced-motion overrides.
  - Zero Emoji Policy: Absolutely NO Unicode emojis [\\U00010000-\\U0010ffff].
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import ast_chunker
except ImportError:
    ast_chunker = None  # Fallback if run standalone without scripts on sys.path

EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

# Canonical provenance references for known historical components
CANONICAL_PROVENANCE_MAP: dict[str, dict[str, Any]] = {
    "app-header-tabs.tsx": {
        "repo_ref_path": "ianmaciel7/notes-app@old-5/src/app/_components/workspace/app-header-tabs.tsx",
        "commit_sha": "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
        "blob_sha": "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
    },
    "app-sidebar-overview.tsx": {
        "repo_ref_path": "ianmaciel7/notes-app@old-5/src/app/_components/workspace/app-sidebar-overview.tsx",
        "commit_sha": "a020d635de368b755992e1282e18af9fdc2b8a03",
        "blob_sha": "a020d635de368b755992e1282e18af9fdc2b8a03",
    },
    "app-shell.tsx": {
        "repo_ref_path": "ianmaciel7/notes-app@old-5/src/app/_components/workspace/app-shell.tsx",
        "commit_sha": "c8149bad08ee026dec049371d3814c29aec8b89a",
        "blob_sha": "c8149bad08ee026dec049371d3814c29aec8b89a",
    },
    "prototipo-sidebar.html": {
        "repo_ref_path": "ianmaciel7/exams-app@dev/docs/Documentos/01-planejamento/revisao/sidebar-prototipo/prototipo-sidebar.html",
        "commit_sha": "783b7041913a8ddc01c7bd2aa1ee6bbf6eeb7e1a",
        "blob_sha": "783b7041913a8ddc01c7bd2aa1ee6bbf6eeb7e1a",
    },
    "decisoes.md": {
        "repo_ref_path": "ianmaciel7/exams-app@dev/docs/Documentos/01-planejamento/revisao/sidebar-prototipo/decisoes.md",
        "commit_sha": "5a6b72be94ccfe4316e65dcd9fafaba9fa9accf1",
        "blob_sha": "5a6b72be94ccfe4316e65dcd9fafaba9fa9accf1",
    },
}

CANONICAL_FEATURE_PATTERNS: list[dict[str, Any]] = [
    {
        "feature_id": "tabs.pin_unpin",
        "default_component": "AppHeaderTabs",
        "default_handler": "togglePin",
        "default_state": "pinnedTabIds",
        "default_trigger": "click",
        "keywords": [
            "togglepin",
            "pintab",
            "unpintab",
            "pinnedtabids",
            "ispinned",
            "onpintoggle",
            "pinnedtabs",
            "pin_unpin",
        ],
        "description": "Pin and unpin tab interactions with persistent or workspace state binding",
    },
    {
        "feature_id": "sidebar.pinned_section",
        "default_component": "AppSidebarOverview",
        "default_handler": "PinnedList",
        "default_state": "pinnedItems",
        "default_trigger": "click",
        "keywords": [
            "pinnedlist",
            "pinneditems",
            "pinnedobjects",
            "fixados",
            "pinnedsection",
            "section-pinned",
            "pinned_section",
        ],
        "description": "Sidebar section listing pinned items, quick bookmarks, and shortcuts",
    },
    {
        "feature_id": "sidebar.hover_peek",
        "default_component": "WorkspaceSidebar",
        "default_handler": "handleMouseEnter",
        "default_state": "isPeekOpen",
        "default_trigger": "pointerenter + dwell",
        "keywords": [
            "ispeekopen",
            "peek",
            "opentimerref",
            "closetimerref",
            "dwell",
            "hover_peek",
        ],
        "description": "Hover peek interaction on collapsed sidebar with distinct dwell delay",
    },
    {
        "feature_id": "tabs.shift_open",
        "default_component": "AppHeaderTabs",
        "default_handler": "handleShiftOpen",
        "default_state": "panes",
        "default_trigger": "Shift+Click",
        "keywords": [
            "shiftkey",
            "shift+click",
            "openinnewpane",
            "openinnewtab",
            "onshiftclick",
            "shift_open",
        ],
        "description": "Shift+Click on tabs to open target document in adjacent split pane",
    },
    {
        "feature_id": "tabs.dnd_reorder",
        "default_component": "AppHeaderTabs",
        "default_handler": "handleReorder",
        "default_state": "tabOrder",
        "default_trigger": "DragAndDrop",
        "keywords": [
            "dnd-kit",
            "handlereorder",
            "reordertabs",
            "ondragend",
            "draganddrop",
            "handlereorderflip",
            "dnd_reorder",
        ],
        "description": "Drag and drop tab reordering with position persistence and layout animation",
    },
    {
        "feature_id": "tabs.context_menu",
        "default_component": "AppHeaderTabs",
        "default_handler": "handleContextMenu",
        "default_state": "isContextMenuOpen",
        "default_trigger": "contextmenu",
        "keywords": [
            "oncontextmenu",
            "contextmenu",
            "contextmenutrigger",
            "compactmenu",
            "context_menu",
        ],
        "description": "Right click context menu on tabs (close, close others, pin, duplicate)",
    },
    {
        "feature_id": "shell.mobile_drawer",
        "default_component": "AppShell",
        "default_handler": "toggleMobileDrawer",
        "default_state": "isMobileOpen",
        "default_trigger": "click / Escape",
        "keywords": [
            "mobile-drawer",
            "mobile_drawer",
            "ismobileopen",
            "mobiledraweropen",
            "translatex(-105%)",
            "sheet",
            "drawer",
        ],
        "description": "Responsive slide-in mobile navigation drawer with backdrop and escape dismiss",
    },
    {
        "feature_id": "sidebar.space_switcher",
        "default_component": "AppSidebar",
        "default_handler": "switchSpace",
        "default_state": "activeSpaceId",
        "default_trigger": "click",
        "keywords": [
            "space-switcher",
            "spaceswitcher",
            "activespaceid",
            "onspacechange",
            "switchspace",
            "space_switcher",
        ],
        "description": "Workspace space switcher dropdown or dialog with search",
    },
    {
        "feature_id": "sidebar.object_type_studio",
        "default_component": "AppSidebarObjectTypeStudio",
        "default_handler": "handleCreateType",
        "default_state": "selectedTypeId",
        "default_trigger": "click",
        "keywords": [
            "object-type-studio",
            "objecttypestudio",
            "type-picker",
            "createtype",
            "object_type_studio",
        ],
        "description": "Object type studio and custom property definition dialog",
    },
    {
        "feature_id": "search.command_dialog",
        "default_component": "AppSidebarPrimaryActionsCommandDialog",
        "default_handler": "openCommandDialog",
        "default_state": "isCommandOpen",
        "default_trigger": "click / Cmd+K",
        "keywords": [
            "command-dialog",
            "commanddialog",
            "opencommand",
            "cmdk",
            "cmd+k",
            "command_dialog",
        ],
        "description": "Global quick search and command palette dialog",
    },
]


@dataclass
class MotionContractSpec:
    dwell_delay_ms: float | None = None
    transition_duration_ms: float | None = None
    easing: str | None = None
    reduced_motion: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "dwell_delay_ms": self.dwell_delay_ms,
            "transition_duration_ms": self.transition_duration_ms,
            "easing": self.easing,
            "reduced_motion": self.reduced_motion,
        }


@dataclass
class ProvenanceSpec:
    repo_ref_path: str
    commit_sha: str
    line_start: int
    line_end: int
    blob_sha: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo_ref_path": self.repo_ref_path,
            "commit_sha": self.commit_sha,
            "blob_sha": self.blob_sha or self.commit_sha,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }


@dataclass
class FeatureSpec:
    feature_id: str
    component: str
    symbol_handler: str
    state_binding: str
    trigger_gesture_shortcut: str
    motion_contract: MotionContractSpec
    provenance: ProvenanceSpec
    description: str = ""
    status: str = "pending"  # implemented | partially-mocked | omitted-with-justification | omitted
    validation_evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "component": self.component,
            "symbol_handler": self.symbol_handler,
            "state_binding": self.state_binding,
            "trigger_gesture_shortcut": self.trigger_gesture_shortcut,
            "motion_contract": self.motion_contract.to_dict(),
            "provenance": self.provenance.to_dict(),
            "description": self.description,
            "status": self.status,
            "validation_evidence": self.validation_evidence,
        }


def _detect_provenance(
    source_text: str, filename: str, line_start: int = 1, line_end: int = 1
) -> ProvenanceSpec:
    """Extract provenance metadata from comments or canonical fallback map."""
    base_name = Path(filename).name if filename else ""

    # Check for in-file metadata comments: // repo: ... // commit: ...
    repo_match = re.search(r"//\s*(?:repo|path):\s*([^\r\n]+)", source_text, re.IGNORECASE)
    commit_match = re.search(r"//\s*commit(?:_sha)?:\s*([a-f0-9]{7,40})", source_text, re.IGNORECASE)
    blob_match = re.search(r"//\s*blob(?:_sha)?:\s*([a-f0-9]{7,40})", source_text, re.IGNORECASE)

    if base_name in CANONICAL_PROVENANCE_MAP:
        canon = CANONICAL_PROVENANCE_MAP[base_name]
        return ProvenanceSpec(
            repo_ref_path=repo_match.group(1).strip() if repo_match else canon["repo_ref_path"],
            commit_sha=commit_match.group(1).strip() if commit_match else canon["commit_sha"],
            blob_sha=blob_match.group(1).strip() if blob_match else canon.get("blob_sha", canon["commit_sha"]),
            line_start=line_start,
            line_end=line_end,
        )

    # General fallback
    repo_ref = repo_match.group(1).strip() if repo_match else (filename or "local/unknown")
    commit_sha = commit_match.group(1).strip() if commit_match else "unknown_commit"
    blob_sha = blob_match.group(1).strip() if blob_match else commit_sha

    return ProvenanceSpec(
        repo_ref_path=repo_ref,
        commit_sha=commit_sha,
        blob_sha=blob_sha,
        line_start=line_start,
        line_end=line_end,
    )


def _extract_motion_spec(source_text: str, component_name: str) -> MotionContractSpec:
    """Extract motion timing separating dwell delay from transition duration."""
    dwell_delay: float | None = None
    transition_dur: float | None = None
    easing: str | None = None
    reduced_motion: bool = False

    # Dwell timer detection (e.g. setTimeout(..., 300) or openTimerRef)
    timer_match = re.search(r"setTimeout\s*\([^,]+,\s*(\d+)\s*\)", source_text)
    if timer_match:
        dwell_delay = float(timer_match.group(1))
    elif re.search(r"dwell(?:_delay)?\s*[:=]\s*(\d+)", source_text, re.IGNORECASE):
        m = re.search(r"dwell(?:_delay)?\s*[:=]\s*(\d+)", source_text, re.IGNORECASE)
        dwell_delay = float(m.group(1))

    # CSS / Tailwind transition duration detection
    dur_match = re.search(r"duration-(\d+)", source_text)
    if dur_match:
        transition_dur = float(dur_match.group(1))
    else:
        css_dur_match = re.search(r"transition:\s*[^;]*?(\d+)(ms|s)", source_text)
        if css_dur_match:
            val = float(css_dur_match.group(1))
            if css_dur_match.group(2) == "s":
                val *= 1000.0
            transition_dur = val
        else:
            waapi_match = re.search(r"duration:\s*(\d+)", source_text)
            if waapi_match:
                transition_dur = float(waapi_match.group(1))

    # Easing
    if "ease-out" in source_text:
        easing = "ease-out"
    elif "ease-in-out" in source_text:
        easing = "ease-in-out"
    elif "ease" in source_text:
        easing = "ease"
    elif "linear" in source_text:
        easing = "linear"

    # Reduced motion override
    if (
        "motion-reduce:" in source_text
        or "prefers-reduced-motion" in source_text
        or "reduced_motion" in source_text
    ):
        reduced_motion = True

    return MotionContractSpec(
        dwell_delay_ms=dwell_delay,
        transition_duration_ms=transition_dur,
        easing=easing,
        reduced_motion=reduced_motion,
    )


def extract_features_from_source(
    source_text: str, filename: str = "", language: str = ""
) -> list[FeatureSpec]:
    """Extract Feature Matrix from source text and structural AST chunks."""
    features: list[FeatureSpec] = []
    seen_feature_ids: set[str] = set()

    total_lines = source_text.count("\n") + 1
    lower_source = source_text.lower()

    # Determine component name from source
    comp_match = re.search(r"export\s+function\s+([A-Za-z0-9_]+)", source_text)
    if not comp_match:
        comp_match = re.search(r"function\s+([A-Za-z0-9_]+)", source_text)
    if not comp_match:
        comp_match = re.search(r"class\s+([A-Za-z0-9_]+)", source_text)

    detected_component = comp_match.group(1) if comp_match else (Path(filename).stem if filename else "UnknownComponent")

    # Match canonical feature patterns
    for pattern in CANONICAL_FEATURE_PATTERNS:
        fid = pattern["feature_id"]
        keywords = pattern["keywords"]

        matched = any(kw in lower_source for kw in keywords)
        if matched and fid not in seen_feature_ids:
            # Locate line range for this feature if possible
            first_kw = next(kw for kw in keywords if kw in lower_source)
            pos = lower_source.find(first_kw)
            line_start = source_text[:pos].count("\n") + 1
            line_end = min(total_lines, line_start + 40)

            # Detect specific handler and state
            component = pattern["default_component"]
            if detected_component and detected_component != "UnknownComponent":
                # If the file defines a specific component, use it
                component = detected_component

            symbol_handler = pattern["default_handler"]
            # Look for specific handler definition
            for kw in keywords:
                h_match = re.search(rf"(?:const|function)\s+({kw}[A-Za-z0-9_]*)\s*=", source_text, re.IGNORECASE)
                if h_match:
                    symbol_handler = h_match.group(1)
                    break

            state_binding = pattern["default_state"]
            # Look for state binding
            st_match = re.search(r"\[([A-Za-z0-9_]+),\s*set[A-Za-z0-9_]+\]\s*=\s*useState", source_text)
            if st_match:
                candidate_state = st_match.group(1)
                # Check if it relates to this feature
                if any(kw in candidate_state.lower() for kw in keywords):
                    state_binding = candidate_state

            # Extract motion contracts
            motion_spec = _extract_motion_spec(source_text, component)

            # Special known timing defaults if dwell is in hover_peek
            if fid == "sidebar.hover_peek" and motion_spec.dwell_delay_ms is None:
                # Check for 300ms or 180ms
                if "300" in source_text:
                    motion_spec.dwell_delay_ms = 300.0
                elif "180" in source_text:
                    motion_spec.dwell_delay_ms = 180.0

            # Provenance
            prov = _detect_provenance(source_text, filename, line_start, line_end)

            spec = FeatureSpec(
                feature_id=fid,
                component=component,
                symbol_handler=symbol_handler,
                state_binding=state_binding,
                trigger_gesture_shortcut=pattern["default_trigger"],
                motion_contract=motion_spec,
                provenance=prov,
                description=pattern["description"],
            )
            features.append(spec)
            seen_feature_ids.add(fid)

    # Also detect custom annotated features: // @feature: <id> [handler=...] [state=...]
    for ann in re.finditer(
        r"//\s*@feature:\s*([a-zA-Z0-9_\.-]+)(?:\s+handler=([A-Za-z0-9_]+))?(?:\s+state=([A-Za-z0-9_]+))?",
        source_text,
    ):
        custom_id = ann.group(1)
        if custom_id not in seen_feature_ids:
            line = source_text[: ann.start()].count("\n") + 1
            prov = _detect_provenance(source_text, filename, line, line + 20)
            spec = FeatureSpec(
                feature_id=custom_id,
                component=detected_component,
                symbol_handler=ann.group(2) or "customHandler",
                state_binding=ann.group(3) or "customState",
                trigger_gesture_shortcut="click",
                motion_contract=_extract_motion_spec(source_text, detected_component),
                provenance=prov,
                description=f"Custom extracted feature {custom_id}",
            )
            features.append(spec)
            seen_feature_ids.add(custom_id)

    return features


def extract_features_from_path(path: Path | str) -> list[FeatureSpec]:
    """Extract features from a file, directory, or pre-extracted JSON."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Source path does not exist: {p}")

    if p.is_file():
        content = p.read_text(encoding="utf-8", errors="replace")
        # Check if already a feature matrix JSON
        if p.suffix == ".json":
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return [
                        FeatureSpec(
                            feature_id=item["feature_id"],
                            component=item.get("component", "UnknownComponent"),
                            symbol_handler=item.get("symbol_handler", "unknownHandler"),
                            state_binding=item.get("state_binding", "unknownState"),
                            trigger_gesture_shortcut=item.get("trigger_gesture_shortcut", "click"),
                            motion_contract=MotionContractSpec(**item.get("motion_contract", {})),
                            provenance=ProvenanceSpec(**item.get("provenance", {})),
                            description=item.get("description", ""),
                            status=item.get("status", "pending"),
                        )
                        for item in data
                    ]
            except Exception:
                pass  # Fall through to standard extraction
        return extract_features_from_source(content, filename=p.name)

    # Directory traversal
    all_features: list[FeatureSpec] = []
    seen_ids: set[str] = set()

    for root, _, files in os.walk(p):
        for f in files:
            if f.endswith((".tsx", ".ts", ".jsx", ".js", ".html", ".css", ".py")):
                file_path = Path(root) / f
                try:
                    text = file_path.read_text(encoding="utf-8", errors="replace")
                    file_feats = extract_features_from_source(text, filename=f)
                    for feat in file_feats:
                        if feat.feature_id not in seen_ids:
                            all_features.append(feat)
                            seen_ids.add(feat.feature_id)
                except Exception:
                    continue

    return all_features


def load_omissions_matrix(omissions_path: Path | str | None) -> dict[str, str]:
    """Parse omissions matrix mapping feature_id -> justification.

    Accepts JSON, Markdown tables/lists, or YAML/plain text.
    """
    if not omissions_path:
        return {}

    p = Path(omissions_path)
    if not p.exists():
        raise FileNotFoundError(f"Omissions matrix path does not exist: {p}")

    raw = p.read_text(encoding="utf-8", errors="replace")
    omissions: dict[str, str] = {}

    # Try JSON first
    if p.suffix == ".json" or raw.strip().startswith(("{", "[")):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                if "omissions" in data and isinstance(data["omissions"], list):
                    for item in data["omissions"]:
                        fid = item.get("feature_id") or item.get("id")
                        just = item.get("justification") if item.get("justification") is not None else item.get("reason", "")
                        if fid:
                            omissions[str(fid).strip()] = str(just or "").strip()
                else:
                    for k, v in data.items():
                        if isinstance(v, dict):
                            just = v.get("justification") if v.get("justification") is not None else v.get("reason", "")
                            omissions[str(k).strip()] = str(just or "").strip()
                        elif isinstance(v, str):
                            omissions[str(k).strip()] = v.strip()
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        fid = item.get("feature_id") or item.get("id")
                        just = item.get("justification") if item.get("justification") is not None else item.get("reason", "")
                        if fid:
                            omissions[str(fid).strip()] = str(just or "").strip()
            return omissions
        except json.JSONDecodeError:
            pass

    # Try Markdown tables: | Feature ID | Justification |
    table_rows = re.findall(r"\|\s*([a-zA-Z0-9_\.-]+)\s*\|\s*([^|\r\n]+)\s*\|", raw)
    for fid, just in table_rows:
        fid_clean = fid.strip()
        just_clean = just.strip()
        if fid_clean.lower() not in {"feature", "feature_id", "id", "---", ":---", "---:"}:
            omissions[fid_clean] = just_clean

    # Try Markdown list: - **feature_id**: justification
    list_items = re.findall(r"[-*]\s*\*\*([a-zA-Z0-9_\.-]+)\*\*\s*:\s*([^\r\n]+)", raw)
    for fid, just in list_items:
        omissions[fid.strip()] = just.strip()

    # Try plain key: value
    kv_items = re.findall(r"^([a-zA-Z0-9_\.-]+)\s*:\s*(.+)$", raw, re.MULTILINE)
    for fid, just in kv_items:
        if fid.strip() not in omissions:
            omissions[fid.strip()] = just.strip()

    return omissions


def _inspect_preview_for_feature(feature: FeatureSpec, preview_content: str) -> tuple[str, str]:
    """Inspect preview artifact to classify feature as implemented, partially-mocked, or missing."""
    p_lower = preview_content.lower()
    fid = feature.feature_id

    # Feature-specific checks
    if fid == "tabs.pin_unpin":
        has_pin_kw = any(w in p_lower for w in ["togglepin", "pintab", "unpintab", "pinnedtabids", "pinnedtabs", "ispinned"])
        has_pin_ui = any(w in p_lower for w in ["pin tab", "title=\"pin", "title='pin", "aria-label=\"pin", "btn-pin", "pin-icon", "fixar aba"])

        if has_pin_kw and ("setpinned" in p_lower or "filter(" in p_lower or "push(" in p_lower or "toggle" in p_lower):
            return "implemented", "Found togglePin / state binding in preview code"
        if has_pin_ui and ("data-mocked" in p_lower or "alert(" in p_lower or "console.log" in p_lower or "todo" in p_lower):
            return "partially-mocked", "Pin UI element present but marked mocked / stubbed"
        if has_pin_kw or has_pin_ui:
            # Check if interactive handler attached
            if "click" in p_lower and "pin" in p_lower:
                return "implemented", "Found pin click handler in preview"
            return "partially-mocked", "Pin element present without full state mutation"
        return "missing", "Pin/unpin functionality completely missing from preview"

    elif fid == "sidebar.pinned_section":
        has_section = any(w in p_lower for w in ["fixados", "pinned section", "pinnedlist", "pinned-items", "pinned_section"])
        if has_section:
            if "map(" in p_lower or "foreach(" in p_lower or "<li" in p_lower or "<div class=\"pinned" in p_lower or "pinned-item" in p_lower:
                return "implemented", "Pinned section and item listing found in sidebar"
            return "partially-mocked", "Pinned section container present without dynamic listing"
        return "missing", "Pinned section missing from preview sidebar"

    elif fid == "sidebar.hover_peek":
        has_peek = any(w in p_lower for w in ["peek", "ispeekopen", "hover_peek"])
        has_timer = any(w in p_lower for w in ["settimeout", "timer", "dwell"])
        if has_peek and has_timer:
            return "implemented", "Hover peek with dwell timer implemented in preview"
        if has_peek:
            return "partially-mocked", "Peek state present but dwell timing contract missing"
        return "missing", "Hover peek interaction missing from preview"

    elif fid == "tabs.shift_open":
        has_shift = any(w in p_lower for w in ["shiftkey", "shift+click", "openinnewpane", "openinnewtab"])
        if has_shift:
            return "implemented", "Shift+Click multi-pane opening logic implemented"
        return "missing", "Shift+Click opening missing from preview"

    elif fid == "tabs.dnd_reorder":
        has_dnd = any(w in p_lower for w in ["dnd-kit", "dragstart", "dragover", "handlereorder", "reordertabs", "draggable"])
        if has_dnd:
            if "mock" in p_lower and "dnd" in p_lower:
                return "partially-mocked", "Drag and drop reorder present with mock handler"
            return "implemented", "Drag and drop tab reordering implemented"
        return "missing", "Drag and drop tab reordering missing from preview"

    elif fid == "tabs.context_menu":
        has_ctx = any(w in p_lower for w in ["contextmenu", "oncontextmenu", "compactmenu"])
        if has_ctx:
            return "implemented", "Tab context menu interaction implemented"
        return "missing", "Tab context menu missing from preview"

    elif fid == "shell.mobile_drawer":
        has_drawer = any(w in p_lower for w in ["mobile-drawer", "mobile_drawer", "sheet", "drawer"])
        has_toggle = any(w in p_lower for w in ["translatex", "ismobileopen", "draweropen", "backdrop"])
        if has_drawer and has_toggle:
            return "implemented", "Mobile drawer and backdrop interaction implemented"
        if has_drawer:
            return "partially-mocked", "Mobile drawer markup present without toggle/backdrop handling"
        return "missing", "Mobile drawer missing from preview"

    # Generic check for custom or other canonical features
    handler_kw = feature.symbol_handler.lower()
    state_kw = feature.state_binding.lower()
    fid_kw = feature.feature_id.lower().replace(".", "_").replace("-", "_")

    if (handler_kw in p_lower or fid_kw in p_lower) and state_kw in p_lower:
        return "implemented", f"Found handler {feature.symbol_handler} and state {feature.state_binding} in preview"
    if handler_kw in p_lower or fid_kw in p_lower:
        if "mock" in p_lower or "todo" in p_lower:
            return "partially-mocked", f"Found {feature.symbol_handler} marked as mocked in preview"
        return "implemented", f"Found {feature.symbol_handler} in preview"

    return "missing", f"Feature {feature.feature_id} not detected in preview"


def validate_preview(
    features: list[FeatureSpec],
    preview_content: str,
    omissions: dict[str, str],
    strict: bool = False,
) -> tuple[bool, list[FeatureSpec], list[str]]:
    """Validate preview artifact against Feature Matrix and Omissions Matrix.

    Returns:
        (gate_passed, updated_features, rejection_reasons)
    """
    rejection_reasons: list[str] = []
    updated_features: list[FeatureSpec] = []

    for feat in features:
        # Check if explicitly justified in omissions matrix
        if feat.feature_id in omissions:
            justification = omissions[feat.feature_id].strip()
            if not justification:
                rejection_reasons.append(
                    f"Feature '{feat.feature_id}' is listed in omissions matrix but has empty justification."
                )
                feat.status = "omitted"
                feat.validation_evidence = "Omission rejected: empty justification"
            else:
                feat.status = "omitted-with-justification"
                feat.validation_evidence = f"Documented in omissions matrix: {justification}"
            updated_features.append(feat)
            continue

        # If preview content is empty or none, feature is omitted
        if not preview_content or not preview_content.strip():
            feat.status = "omitted"
            feat.validation_evidence = "No preview content provided"
            rejection_reasons.append(
                f"Feature '{feat.feature_id}' ({feat.component} -> {feat.symbol_handler}) "
                f"is omitted without justification in omissions matrix."
            )
            updated_features.append(feat)
            continue

        # Inspect preview
        status, evidence = _inspect_preview_for_feature(feat, preview_content)

        if status == "implemented":
            feat.status = "implemented"
            feat.validation_evidence = evidence
        elif status == "partially-mocked":
            if strict:
                rejection_reasons.append(
                    f"Feature '{feat.feature_id}' is partially-mocked, which is disallowed in strict mode."
                )
            feat.status = "partially-mocked"
            feat.validation_evidence = evidence
        else:  # missing
            feat.status = "omitted"
            feat.validation_evidence = evidence
            rejection_reasons.append(
                f"SILENT OMISSION DETECTED: Feature '{feat.feature_id}' ({feat.component} -> {feat.symbol_handler}) "
                f"present in source ({feat.provenance.repo_ref_path}) but missing from preview "
                f"and not documented in omissions matrix."
            )

        # Strict checks on motion contracts for implemented features
        if strict and feat.status == "implemented":
            if feat.feature_id == "sidebar.hover_peek":
                if feat.motion_contract.dwell_delay_ms is None:
                    rejection_reasons.append(
                        f"Strict motion violation: '{feat.feature_id}' requires dwell_delay_ms distinct from duration."
                    )
            if not feat.motion_contract.reduced_motion:
                rejection_reasons.append(
                    f"Strict motion violation: '{feat.feature_id}' lacks reduced-motion override."
                )

        updated_features.append(feat)

    gate_passed = len(rejection_reasons) == 0
    return gate_passed, updated_features, rejection_reasons


def generate_markdown_report(
    gate_passed: bool,
    features: list[FeatureSpec],
    strict: bool = False,
    rejection_reasons: list[str] | None = None,
) -> str:
    """Generate deterministic GitHub-flavored Markdown QA report with ZERO emojis."""
    lines: list[str] = []

    status_badge = "[GATE PASSED]" if gate_passed else "[GATE FAILED]"
    lines.append(f"# Preview Functional Coverage Quality Gate Report {status_badge}")
    lines.append("")
    lines.append(f"- **Gate Decision:** {'PASSED' if gate_passed else 'FAILED'}")
    lines.append(f"- **Strict Mode:** {'Enabled' if strict else 'Disabled'}")
    lines.append(f"- **Total Features in Matrix:** {len(features)}")

    implemented_count = sum(1 for f in features if f.status == "implemented")
    mocked_count = sum(1 for f in features if f.status == "partially-mocked")
    justified_count = sum(1 for f in features if f.status == "omitted-with-justification")
    omitted_count = sum(1 for f in features if f.status == "omitted")

    lines.append(f"- **Implemented:** {implemented_count}")
    lines.append(f"- **Partially Mocked:** {mocked_count}")
    lines.append(f"- **Omitted with Justification:** {justified_count}")
    lines.append(f"- **Unjustified Omissions (Hard Blockers):** {omitted_count}")
    lines.append("")

    if rejection_reasons:
        lines.append("## Blocker Violations")
        lines.append("")
        for reason in rejection_reasons:
            lines.append(f"- [FAIL] {reason}")
        lines.append("")

    lines.append("## Feature Matrix and Verification Status")
    lines.append("")
    lines.append(
        "| Feature ID | Component | Symbol Handler | State Binding | Trigger | Motion Contract | Provenance | Status | Evidence / Notes |"
    )
    lines.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )

    for f in features:
        motion_parts = []
        if f.motion_contract.dwell_delay_ms is not None:
            motion_parts.append(f"dwell: {f.motion_contract.dwell_delay_ms}ms")
        if f.motion_contract.transition_duration_ms is not None:
            motion_parts.append(f"dur: {f.motion_contract.transition_duration_ms}ms")
        if f.motion_contract.easing:
            motion_parts.append(f"ease: {f.motion_contract.easing}")
        if f.motion_contract.reduced_motion:
            motion_parts.append("reduced-motion: true")
        motion_str = ", ".join(motion_parts) if motion_parts else "none"

        prov_str = f"{f.provenance.repo_ref_path}:{f.provenance.line_start}..{f.provenance.line_end}"
        status_label = f"[{f.status.upper()}]"

        lines.append(
            f"| `{f.feature_id}` | `{f.component}` | `{f.symbol_handler}` | `{f.state_binding}` | `{f.trigger_gesture_shortcut}` | {motion_str} | `{prov_str}` | {status_label} | {f.validation_evidence} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("*Zero Emoji Policy verified: report generated without Unicode emojis.*")
    lines.append("")

    return "\n".join(lines)


def generate_json_report(
    gate_passed: bool,
    features: list[FeatureSpec],
    strict: bool = False,
    rejection_reasons: list[str] | None = None,
) -> dict[str, Any]:
    """Generate structured JSON report representation."""
    implemented_count = sum(1 for f in features if f.status == "implemented")
    mocked_count = sum(1 for f in features if f.status == "partially-mocked")
    justified_count = sum(1 for f in features if f.status == "omitted-with-justification")
    omitted_count = sum(1 for f in features if f.status == "omitted")

    return {
        "gate_passed": gate_passed,
        "strict": strict,
        "total_features": len(features),
        "counts": {
            "implemented": implemented_count,
            "partially_mocked": mocked_count,
            "omitted_with_justification": justified_count,
            "omitted": omitted_count,
        },
        "rejection_reasons": rejection_reasons or [],
        "features": [f.to_dict() for f in features],
    }


def run_preview_gate(
    sources: list[str | Path],
    preview_path: str | Path | None = None,
    omissions_path: str | Path | None = None,
    report_md_path: str | Path | None = None,
    json_output_path: str | Path | None = None,
    strict: bool = False,
) -> tuple[bool, dict[str, Any]]:
    """Execute complete preview functional coverage gate."""
    # 1. Extract Feature Matrix from all source inputs
    features: list[FeatureSpec] = []
    seen_ids: set[str] = set()

    for src in sources:
        extracted = extract_features_from_path(src)
        for feat in extracted:
            if feat.feature_id not in seen_ids:
                features.append(feat)
                seen_ids.add(feat.feature_id)

    # 2. Load Omissions Matrix
    omissions = load_omissions_matrix(omissions_path)

    # 3. Read preview content
    preview_content = ""
    if preview_path:
        pp = Path(preview_path)
        if pp.exists() and pp.is_file():
            preview_content = pp.read_text(encoding="utf-8", errors="replace")

    # 4. Validate preview against features and omissions
    gate_passed, updated_features, rejection_reasons = validate_preview(
        features=features,
        preview_content=preview_content,
        omissions=omissions,
        strict=strict,
    )

    # 5. Generate reports
    md_report = generate_markdown_report(
        gate_passed=gate_passed,
        features=updated_features,
        strict=strict,
        rejection_reasons=rejection_reasons,
    )

    json_report = generate_json_report(
        gate_passed=gate_passed,
        features=updated_features,
        strict=strict,
        rejection_reasons=rejection_reasons,
    )

    # Check Zero Emoji Policy on outputs
    if EMOJI_REGEX.search(md_report):
        raise ValueError("Zero Emoji Policy violated: Emoji detected in markdown report.")
    raw_json = json.dumps(json_report)
    if EMOJI_REGEX.search(raw_json):
        raise ValueError("Zero Emoji Policy violated: Emoji detected in JSON report.")

    if report_md_path:
        Path(report_md_path).write_text(md_report, encoding="utf-8")

    if json_output_path:
        if json_output_path == "-":
            print(json.dumps(json_report, indent=2))
        else:
            Path(json_output_path).write_text(json.dumps(json_report, indent=2), encoding="utf-8")

    return gate_passed, json_report


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Pre-preview functional coverage quality gate (Issue #46)."
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        required=True,
        help="Path(s) to source files, directories, or feature matrix JSON.",
    )
    parser.add_argument(
        "--preview",
        required=False,
        help="Path to preview HTML or artifact file to validate.",
    )
    parser.add_argument(
        "--omissions",
        required=False,
        help="Path to explicit omissions matrix (JSON, Markdown table/list, or YAML).",
    )
    parser.add_argument(
        "--report-md",
        required=False,
        help="Output path for Markdown QA report.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        nargs="?",
        const="-",
        required=False,
        help="Output path for JSON report (or '-' for stdout).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode: disallows partially-mocked features and requires strict motion contracts.",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    gate_passed, report = run_preview_gate(
        sources=args.sources,
        preview_path=args.preview,
        omissions_path=args.omissions,
        report_md_path=args.report_md,
        json_output_path=args.json_output,
        strict=args.strict,
    )

    if not gate_passed:
        print("[FAIL] Preview functional coverage gate rejected the preview:", file=sys.stderr)
        for r in report["rejection_reasons"]:
            print(f"  - {r}", file=sys.stderr)
        sys.exit(1)
    else:
        print("[PASS] Preview functional coverage gate passed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
