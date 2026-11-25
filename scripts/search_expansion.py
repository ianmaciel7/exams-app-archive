#!/usr/bin/env python3
"""Versioned bilingual (PT <-> EN) domain synonym and query expansion module.

Pure Python standard library only. Provides deterministic query normalization,
tokenization, and bidirectional Portuguese-English synonym expansion for the
Exams App historical archive search (commits, file paths, and image paths).
"""
from __future__ import annotations

from difflib import SequenceMatcher
import re
import unicodedata

DICTIONARY_VERSION = "2.0.0"

# Bidirectional synonym groups covering all 23 archive and product domains:
# produto, concursos, aprendizagem, avaliacao, ia-informacao, workspace, objetos,
# visualizacoes, design-system, interacao, motion, acessibilidade, responsividade,
# ai-native-ux, engenharia, arquitetura-tecnica, qualidade, historico, midia,
# referencias-externas, conhecimento-humano, operacoes, governanca.
SYNONYM_GROUPS: tuple[tuple[str, ...], ...] = (
    # Core existing groups (preserved for strict backward compatibility)
    ("grafo", "graph"),
    ("barra lateral", "sidebar", "gaveta"),
    ("simulado", "simulados", "exam", "exams", "mock", "mock exam"),
    ("prova", "provas", "exam", "exams", "test", "tests"),
    ("questao", "questoes", "question", "questions"),
    ("painel", "panel", "pane"),
    ("captura de tela", "captura", "capturas", "screenshot", "screenshots", "capture"),
    ("revisao", "revisoes", "review", "reviews"),
    ("cartao", "cartoes", "flashcard", "flashcards", "card", "cards"),
    ("caderno", "cadernos", "notebook", "notebooks"),
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
    # Produto & Requisitos
    ("produto", "product"),
    ("requisito", "requisitos", "requirement", "requirements", "prd"),
    ("escopo", "scope"),
    ("prioridade", "priority"),
    # Concursos & Avaliacao
    ("concurso", "concursos", "public exam", "public exams"),
    ("banca", "bancas", "exam board"),
    ("edital", "editais", "exam notice", "syllabus"),
    ("gabarito", "answer key", "correction key"),
    ("avaliacao", "assessment", "evaluation"),
    ("disciplina", "disciplinas", "subject", "subjects"),
    ("assunto", "assuntos", "topic", "topics"),
    ("desempenho", "performance", "score"),
    # Aprendizagem & SRS/FSRS
    ("aprendizagem", "learning", "study", "estudo"),
    ("retencao", "retention", "recall"),
    ("intervalo", "interval", "scheduler", "agendamento"),
    ("dificuldade", "difficulty"),
    ("estabilidade", "stability"),
    # IA e Arquitetura da Informacao / Objetos
    ("ontologia", "ontology"),
    ("taxonomia", "taxonomy"),
    ("entidade", "entidades", "entity", "entities"),
    ("objeto", "objetos", "object", "objects"),
    ("propriedade", "propriedades", "property", "properties"),
    ("relacao", "relacoes", "relationship", "relationships"),
    ("grafo de conhecimento", "knowledge graph"),
    # Workspace, Visualizacoes, Design System, Interacao, Motion
    ("area de trabalho", "workspace", "workspaces"),
    ("painel lateral", "side panel", "side peek"),
    ("aba", "abas", "tab", "tabs"),
    ("fixar", "pin", "pinned", "fixado", "fixados"),
    ("espiar", "peek", "hover peek"),
    ("recolher", "collapse", "collapsed"),
    ("arrastar", "drag", "reorder", "reordenar"),
    ("quadro branco", "whiteboard", "canvas"),
    ("diagrama", "diagram", "flowchart"),
    ("animacao", "animation", "motion", "transicao", "transition"),
    ("mola", "spring"),
    ("linguagem visual", "visual language", "design tokens", "tokens"),
    # Acessibilidade & Responsividade
    ("acessibilidade", "accessibility", "a11y", "wcag", "aria"),
    ("leitor de tela", "screen reader"),
    ("foco", "focus", "focus ring"),
    ("contraste", "contrast"),
    ("responsividade", "responsiveness", "responsive", "responsivo"),
    ("movel", "mobile", "celular"),
    ("gaveta inferior", "bottom sheet"),
    # AI-Native UX
    ("agente", "agentes", "agent", "agents"),
    ("artefato", "artefatos", "artifact", "artifacts"),
    ("fluxo continuo", "streaming", "shimmer"),
    ("aprovacao humana", "approval gate", "human in the loop"),
    ("explicabilidade", "explainability"),
    # Engenharia & Arquitetura Tecnica
    ("engenharia", "engineering", "software"),
    ("codigo", "code", "source"),
    ("refatoracao", "refactor", "refactoring"),
    ("arquitetura", "architecture"),
    ("decisao arquitetural", "architecture decision", "adr", "adrs"),
    ("componente", "componentes", "component", "components"),
    ("simbolo", "simbolos", "symbol", "symbols"),
    ("banco de dados", "database", "sqlite", "fts5"),
    # Qualidade & Testes
    ("qualidade", "quality", "qa"),
    ("teste", "testes", "test", "tests", "testing"),
    ("regressao", "regression"),
    ("cobertura", "coverage"),
    ("validacao", "validation", "verify", "verificacao"),
    # Historico, Midia & Referencias Externas
    ("repositorio", "repositorios", "repository", "repositories", "repo"),
    ("ramificacao", "branch", "branches"),
    ("confirmacao", "commit", "commits"),
    ("pacote", "bundle", "bundles"),
    ("proveniencia", "provenance"),
    ("video", "videos", "recording", "gravacao"),
    ("referencia", "referencias", "reference", "references", "benchmark"),
    # Conhecimento Humano, Operacoes & Governanca
    ("curadoria", "curation", "curated"),
    ("glossario", "glossary"),
    ("documentacao", "documentation", "docs"),
    ("operacoes", "operations", "ops"),
    ("copia de seguranca", "backup", "backups"),
    ("restauracao", "restore", "recover", "recuperacao"),
    ("lancamento", "release", "releases"),
    ("implantacao", "deploy", "deployment"),
    ("sincronizacao", "sync", "synchronization"),
    ("governanca", "governance"),
    ("seguranca", "security", "secrets"),
    ("privacidade", "privacy"),
    ("permissao", "permissoes", "permission", "permissions", "acl"),
    ("auditoria", "audit"),
    ("licenca", "license"),
)

STOPWORDS = frozenset({
    "de", "do", "da", "dos", "das", "e", "em", "no", "na", "para", "com", "sem",
    "o", "a", "os", "as", "um", "uma", "por", "the", "of", "and", "or", "in", "to", "for",
})

# Light PT/EN irregular/common inflection table before generic suffix stripping.
_IRREGULAR_LEMMAS: dict[str, str] = {
    "questoes": "questao",
    "anotacoes": "anotacao",
    "colecoes": "colecao",
    "configuracoes": "configuracao",
    "revisoes": "revisao",
    "relacoes": "relacao",
    "operacoes": "operacao",
    "permissoes": "permissao",
    "cartoes": "cartao",
    "imagens": "imagem",
    "espacos": "espaco",
    "fixados": "fixado",
    "repositories": "repository",
    "entities": "entity",
    "properties": "property",
    "branches": "branch",
}


def strip_accents(text: str) -> str:
    """Fold Unicode accents into ASCII base characters (e.g. 'questao' == 'questão')."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def split_identifier_cases(text: str) -> str:
    """Split camelCase, PascalCase, snake_case, kebab-case, and dot.case into space-separated words."""
    # Insert space between lower/digit and Upper (camelCase / PascalCase)
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(text))
    # Insert space between multi-letter acronym and TitleCase (e.g. HTMLParser -> HTML Parser, keep QConcursos intact)
    expanded = re.sub(r"([A-Z]{2,})([A-Z][a-z])", r"\1 \2", expanded)
    # Replace _, -, /, . separators with spaces
    expanded = re.sub(r"[_\-./]+", " ", expanded)
    return expanded


def normalize_text(text: str) -> str:
    """Lowercase, strip accents, split identifier cases, and collapse whitespace."""
    # Preserve simple word tokens while splitting camelCase/snake_case/kebab-case cleanly.
    # For standalone snake_case identifiers like "barra_lateral" or "pin_tab",
    # split_identifier_cases separates them into words so synonyms match.
    split = split_identifier_cases(text)
    return " ".join(strip_accents(split).lower().split())


def stem_simple(token: str) -> str:
    """Apply lightweight deterministic PT/EN singular/inflection normalization."""
    t = normalize_text(token).replace(" ", "")
    if not t:
        return ""
    if t in _IRREGULAR_LEMMAS:
        return _IRREGULAR_LEMMAS[t]
    if len(t) > 5 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 5 and t.endswith("ing"):
        return t[:-3]
    if len(t) > 4 and t.endswith("ed"):
        return t[:-2]
    if len(t) > 4 and t.endswith(("ches", "shes", "sses", "xes", "zes")):
        return t[:-2]
    if len(t) > 4 and t.endswith("oes"):
        return t[:-3] + "ao"
    if len(t) > 4 and t.endswith("es") and not t.endswith(("ses", "ies")):
        # Avoid stripping 'files' -> 'fil' by keeping 'e' when stem ends with single consonant after vowel
        if t.endswith(("tes", "des", "res", "nes", "les", "ges")):
            return t[:-1]
    if len(t) > 3 and t.endswith("s") and not t.endswith(("ss", "us", "is", "srs", "fsrs")):
        return t[:-1]
    return t


def tokenize(text: str, *, max_tokens: int = 12) -> list[str]:
    """Extract alphanumeric word tokens in normalized form while preserving order."""
    norm = normalize_text(text)
    raw_tokens = re.findall(r"[a-z0-9]+", norm)
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
        normalized_terms: list[str] = []
        for term in group:
            nt = normalize_text(term)
            if nt and nt not in normalized_terms:
                normalized_terms.append(nt)
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
_STEM_TO_TOKENS: dict[str, list[str]] = {}
for _tok in TOKEN_SYNONYMS:
    _st = stem_simple(_tok)
    if _st:
        _STEM_TO_TOKENS.setdefault(_st, []).append(_tok)


def _clean_term(term: str) -> str:
    return re.sub(r'["*]+', "", term).strip()


def lexical_fallback_candidates(
    term: str,
    vocabulary: list[str] | tuple[str, ...] | set[str] | None = None,
    *,
    min_confidence: float = 0.68,
    max_candidates: int = 5,
) -> list[dict[str, object]]:
    """Return ranked lexical fallback candidates with confidence in [0.0, 1.0]."""
    q = normalize_text(term)
    if not q:
        return []
    q_stem = stem_simple(q)
    vocab = sorted(set(vocabulary)) if vocabulary is not None else sorted(set(TOKEN_SYNONYMS) | set(PHRASE_SYNONYMS))
    scored: list[tuple[float, str, str]] = []
    for cand in vocab:
        c_norm = normalize_text(cand)
        if not c_norm:
            continue
        if c_norm == q:
            scored.append((1.0, cand, "exact"))
            continue
        c_stem = stem_simple(c_norm)
        if q_stem and c_stem == q_stem and " " not in c_norm and " " not in q:
            scored.append((0.92, cand, "inflection"))
            continue
        if len(q) >= 4 and (c_norm.startswith(q) or q.startswith(c_norm)):
            ratio = min(len(q), len(c_norm)) / max(len(q), len(c_norm))
            conf = round(0.75 + 0.15 * ratio, 4)
            if conf >= min_confidence:
                scored.append((conf, cand, "prefix"))
                continue
        sim = SequenceMatcher(None, q, c_norm).ratio()
        if sim >= min_confidence:
            scored.append((round(sim, 4), cand, "fuzzy"))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {"term": cand, "confidence": conf, "match_type": mtype}
        for conf, cand, mtype in scored[:max_candidates]
    ]


def expand_query(
    query: str,
    *,
    max_tokens: int = 6,
    max_expansions_per_token: int = 4,
    enable_lexical_fallback: bool = True,
) -> dict:
    """Expand a user query with PT<->EN domain synonyms, case splitting, and lexical fallback.

    Returns a dictionary with:
    - version: dictionary version string
    - original_query: input string
    - normalized_query: accent-folded lowercase query with identifier case splitting
    - tokens: normalized base tokens (bounded by max_tokens)
    - phrase_matches: matched multi-word phrases and their expansions
    - groups: list of synonym clusters, one per query concept
    - expanded_terms: flat deduplicated list of all terms
    - fts_matchers: ordered FTS5 MATCH expressions (strict AND/phrase first, OR fallback)
    - fallback_candidates: ranked lexical fallback matches when direct token lookup misses
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
            "fallback_candidates": [],
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
    raw_unicode_tokens = re.findall(r"\w+", split_identifier_cases(query).lower(), flags=re.UNICODE)[:max_tokens]
    raw_by_norm: dict[str, list[str]] = {}
    for rt in raw_unicode_tokens:
        rt_norm = normalize_text(rt)
        if rt_norm:
            raw_by_norm.setdefault(rt_norm, [])
            if rt not in raw_by_norm[rt_norm]:
                raw_by_norm[rt_norm].append(rt)

    non_stop_tokens = [t for t in raw_tokens if t not in STOPWORDS]
    effective_tokens = non_stop_tokens if non_stop_tokens else raw_tokens
    fallback_candidates: list[dict[str, object]] = []

    for tok in effective_tokens:
        if tok in covered_phrase_tokens and len(phrase_matches) > 0:
            continue
        cluster: list[str] = []
        for variant in raw_by_norm.get(tok, [tok]):
            if variant not in cluster:
                cluster.append(variant)
        if tok not in cluster:
            cluster.append(tok)

        peers = list(TOKEN_SYNONYMS.get(tok, ()))
        if not peers and enable_lexical_fallback:
            # Try inflection/stem match first
            st = stem_simple(tok)
            for stem_tok in _STEM_TO_TOKENS.get(st, []):
                if stem_tok not in cluster:
                    cluster.append(stem_tok)
                for p in TOKEN_SYNONYMS.get(stem_tok, ()):
                    if p not in peers:
                        peers.append(p)
                fallback_candidates.append({
                    "query_token": tok,
                    "term": stem_tok,
                    "confidence": 0.92,
                    "match_type": "inflection",
                })
            if not peers and len(tok) >= 5:
                fuzzy = lexical_fallback_candidates(tok, list(TOKEN_SYNONYMS.keys()), min_confidence=0.80, max_candidates=2)
                for cand in fuzzy:
                    cand_term = str(cand["term"])
                    if cand_term not in cluster:
                        cluster.append(cand_term)
                    for p in TOKEN_SYNONYMS.get(cand_term, ())[:2]:
                        if p not in peers:
                            peers.append(p)
                    fallback_candidates.append({"query_token": tok, **cand})

        for peer in peers:
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
        "fallback_candidates": fallback_candidates,
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
