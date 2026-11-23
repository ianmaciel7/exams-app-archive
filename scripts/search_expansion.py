#!/usr/bin/env python3
"""Versioned bilingual (PT <-> EN) domain synonym and query expansion module.

Pure Python standard library only. Provides deterministic query normalization,
tokenization, and bidirectional Portuguese-English synonym expansion for the
Exams App historical archive search (commits, file paths, and image paths).
"""
from __future__ import annotations

import re
import unicodedata

DICTIONARY_VERSION = "1.0.0"

# Bidirectional synonym groups for the Exams / Notes / Graph / SRS domain.
# Multi-word phrases (e.g., "barra lateral") are normalized and matched alongside
# single tokens so queries like "barra lateral" expand to "sidebar" and vice versa.
SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    ("grafo", "graph"),
    ("barra lateral", "sidebar", "gaveta"),
    ("simulado", "exam", "exams", "mock"),
    ("prova", "exam", "exams", "test"),
    ("questao", "questoes", "question", "questions"),
    ("painel", "panel", "pane"),
    ("captura de tela", "captura", "capturas", "screenshot", "screenshots", "capture"),
    ("revisao", "review"),
    ("cartao", "cartoes", "flashcard", "flashcards", "card", "cards"),
    ("caderno", "notebook", "notebooks"),
    ("anotacao", "anotacoes", "note", "notes"),
    ("pesquisa", "busca", "search"),
    ("atalho", "atalhos", "shortcut", "shortcuts"),
    ("teclado", "keyboard"),
    ("tema", "theme"),
    ("escuro", "dark"),
    ("claro", "light"),
    ("lixeira", "trash"),
    ("marcador", "marcadores", "bookmark", "bookmarks"),
    ("grifo", "grifos", "highlight", "highlights"),
    ("colecao", "colecoes", "collection", "collections"),
    ("espaco", "espacos", "space", "spaces"),
    ("etiqueta", "etiquetas", "tag", "tags"),
    ("historico", "history"),
    ("imagem", "imagens", "image", "images"),
    ("arquivo", "arquivos", "file", "files"),
    ("repeticao espacada", "revisao espacada", "spaced repetition", "srs", "fsrs"),
    ("barra", "bar", "toolbar"),
    ("no", "nos", "node", "nodes"),
    ("aresta", "arestas", "edge", "edges"),
    ("filtro", "filtros", "filter", "filters"),
    ("exportacao", "exportar", "export"),
    ("importacao", "importar", "import"),
    ("autenticacao", "auth", "login"),
    ("usuario", "usuarios", "user", "users"),
    ("configuracao", "configuracoes", "settings", "config"),
    ("navegacao", "navigation"),
)

STOPWORDS = frozenset({"de", "do", "da", "dos", "das", "e", "em", "no", "na", "para", "com", "sem", "o", "a", "os", "as"})


def strip_accents(text: str) -> str:
    """Fold Unicode accents into ASCII base characters (e.g. 'questao' == 'questão')."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    """Lowercase, strip accents, and collapse whitespace."""
    return " ".join(strip_accents(text).lower().split())


def tokenize(text: str, *, max_tokens: int = 12) -> list[str]:
    """Extract alphanumeric word tokens in normalized form while preserving order."""
    norm = normalize_text(text)
    raw_tokens = re.findall(r"[a-z0-9_]+", norm)
    seen: set[str] = set()
    unique: list[str] = []
    for tok in raw_tokens:
        if tok and tok not in seen:
            seen.add(tok)
            unique.append(tok)
            if len(unique) >= max_tokens:
                break
    return unique


def _build_index() -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    token_map: dict[str, list[str]] = {}
    phrase_map: dict[str, list[str]] = {}
    for group in SYNONYM_GROUPS:
        normalized_terms = [normalize_text(term) for term in group if normalize_text(term)]
        for term in normalized_terms:
            peers = [p for p in normalized_terms if p != term]
            if not peers:
                continue
            if " " in term:
                bucket = phrase_map.setdefault(term, [])
            else:
                bucket = token_map.setdefault(term, [])
            for peer in peers:
                if peer not in bucket:
                    bucket.append(peer)
    return (
        {k: tuple(v) for k, v in token_map.items()},
        {k: tuple(v) for k, v in phrase_map.items()},
    )


TOKEN_SYNONYMS, PHRASE_SYNONYMS = _build_index()


def _clean_term(term: str) -> str:
    return re.sub(r'["*]+', "", term).strip()


def expand_query(
    query: str,
    *,
    max_tokens: int = 6,
    max_expansions_per_token: int = 4,
) -> dict:
    """Expand a user query with PT<->EN domain synonyms.

    Returns a dictionary with:
    - version: dictionary version string
    - original_query: input string
    - normalized_query: accent-folded lowercase query
    - tokens: normalized base tokens (bounded by max_tokens)
    - phrase_matches: matched multi-word phrases and their expansions
    - groups: list of synonym clusters, one per query concept
    - expanded_terms: flat deduplicated list of all terms
    - fts_matchers: ordered FTS5 MATCH expressions (strict AND/phrase first, OR fallback)
    """
    norm = normalize_text(query)
    if not norm:
        return {
            "version": DICTIONARY_VERSION,
            "original_query": query,
            "normalized_query": "",
            "tokens": [],
            "phrase_matches": {},
            "groups": [],
            "expanded_terms": [],
            "fts_matchers": [],
        }

    # Detect multi-word domain phrases first (longest first).
    phrase_matches: dict[str, list[str]] = {}
    consumed_spans: list[tuple[int, int]] = []
    padded = f" {norm} "
    for phrase in sorted(PHRASE_SYNONYMS.keys(), key=len, reverse=True):
        needle = f" {phrase} "
        idx = padded.find(needle)
        if idx != -1:
            span = (idx, idx + len(phrase))
            if not any(not (span[1] <= s[0] or span[0] >= s[1]) for s in consumed_spans):
                consumed_spans.append(span)
                phrase_matches[phrase] = list(PHRASE_SYNONYMS[phrase][:max_expansions_per_token])

    raw_tokens = tokenize(query, max_tokens=max_tokens)
    groups: list[list[str]] = []
    covered_phrase_tokens: set[str] = set()

    for phrase, peers in phrase_matches.items():
        cluster = [phrase]
        for peer in peers:
            if peer not in cluster:
                cluster.append(peer)
        groups.append(cluster)
        covered_phrase_tokens.update(phrase.split())

    # Include unaccented + original accent tokens when distinct so unicode61/raw matches work.
    raw_unicode_tokens = re.findall(r"\w+", query.lower(), flags=re.UNICODE)[:max_tokens]
    raw_by_norm: dict[str, list[str]] = {}
    for rt in raw_unicode_tokens:
        rt_norm = normalize_text(rt)
        if rt_norm:
            raw_by_norm.setdefault(rt_norm, [])
            if rt not in raw_by_norm[rt_norm]:
                raw_by_norm[rt_norm].append(rt)

    non_stop_tokens = [t for t in raw_tokens if t not in STOPWORDS]
    effective_tokens = non_stop_tokens if non_stop_tokens else raw_tokens

    for tok in effective_tokens:
        if tok in covered_phrase_tokens and len(phrase_matches) > 0:
            # Keep single-word synonyms of phrase constituents only if no phrase matched,
            # preventing "barra lateral" from diluting into generic "bar" / "side".
            continue
        cluster: list[str] = []
        for variant in raw_by_norm.get(tok, [tok]):
            if variant not in cluster:
                cluster.append(variant)
        if tok not in cluster:
            cluster.append(tok)
        for peer in TOKEN_SYNONYMS.get(tok, ()):
            if len(cluster) >= 1 + max_expansions_per_token + len(raw_by_norm.get(tok, [])):
                break
            if peer not in cluster:
                cluster.append(peer)
        groups.append(cluster)

    expanded_terms: list[str] = []
    for cluster in groups:
        for item in cluster:
            if item not in expanded_terms:
                expanded_terms.append(item)

    fts_matchers = build_fts_matchers(groups)
    return {
        "version": DICTIONARY_VERSION,
        "original_query": query,
        "normalized_query": norm,
        "tokens": raw_tokens,
        "phrase_matches": phrase_matches,
        "groups": groups,
        "expanded_terms": expanded_terms,
        "fts_matchers": fts_matchers,
    }


def _term_to_fts(term: str) -> str:
    cleaned = _clean_term(term)
    if not cleaned:
        return ""
    if " " in cleaned:
        return f'"{cleaned}"'
    return f'"{cleaned}"*'


def build_fts_matchers(groups: list[list[str]]) -> list[str]:
    """Build FTS5 MATCH expressions from concept synonym groups.

    1. Conjunctive (AND across concept groups, OR inside each synonym group)
    2. Disjunctive fallback (OR across all terms) when multiple concepts exist
    """
    if not groups:
        return []
    group_exprs: list[str] = []
    flat_exprs: list[str] = []
    seen_flat: set[str] = set()
    for cluster in groups:
        fts_terms = []
        for term in cluster:
            expr = _term_to_fts(term)
            if expr and expr not in fts_terms:
                fts_terms.append(expr)
            if expr and expr not in seen_flat:
                seen_flat.add(expr)
                flat_exprs.append(expr)
        if not fts_terms:
            continue
        if len(fts_terms) == 1:
            group_exprs.append(fts_terms[0])
        else:
            group_exprs.append("(" + " OR ".join(fts_terms) + ")")

    if not group_exprs:
        return []
    if len(group_exprs) == 1:
        return [group_exprs[0]]
    and_expr = " AND ".join(group_exprs)
    or_expr = " OR ".join(flat_exprs)
    return [and_expr, or_expr] if and_expr != or_expr else [and_expr]


def expanded_image_terms(query: str, *, max_terms: int = 10) -> list[str]:
    """Return flat normalized terms (single words and phrase tokens) for LIKE matching on image paths."""
    info = expand_query(query)
    out: list[str] = []
    for term in info["expanded_terms"]:
        cleaned = _clean_term(term).lower()
        if not cleaned:
            continue
        if " " in cleaned:
            # For image paths like 'sidebar_panel.png', also check compact/hyphenated forms.
            for variant in (cleaned.replace(" ", "-"), cleaned.replace(" ", "_")):
                if variant not in out:
                    out.append(variant)
        elif cleaned not in out:
            out.append(cleaned)
        if len(out) >= max_terms:
            break
    return out[:max_terms]


def dictionary_stats() -> dict:
    """Return deterministic metadata about the versioned PT<->EN synonym dictionary."""
    all_terms = {normalize_text(term) for group in SYNONYM_GROUPS for term in group if normalize_text(term)}
    return {
        "version": DICTIONARY_VERSION,
        "group_count": len(SYNONYM_GROUPS),
        "unique_terms": len(all_terms),
        "token_entries": len(TOKEN_SYNONYMS),
        "phrase_entries": len(PHRASE_SYNONYMS),
    }
