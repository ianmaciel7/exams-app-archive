"""Label-blind natural-language ranking over approved public record fields."""
from collections import Counter
from functools import lru_cache
import math
import re
import search_expansion as sx

QUESTION_WORDS = sx.STOPWORDS | frozenset("""
how what which when where who why would should could can does did is are was were
it this that these those i my me you your use using instead than about between
qual quais como quando onde quem porque por que serve devo devemos posso pode
quer quero meu minha seus suas isto isso esta este esses essas fazer usar
""".split())

# Domain-independent lexical equivalences. Never read evaluation data.
EXTRA = (
    ("guardar", "salvar", "save", "saved", "store"),
    ("recuperar", "reabrir", "restore", "reopen", "retrieve"),
    ("criterio", "criterios", "criteria", "criterion"),
    ("transportar", "portabilidade", "portable", "portability", "interoperability", "interoperabilidade"),
    ("atividade", "activity", "activities"),
    ("evento", "event", "events", "eventos"),
    ("educacional", "educational", "education"),
    ("consulta", "query", "queries", "consultas"),
    ("dinamica", "dynamic", "dinamico"),
    ("agrupar", "group", "grouping", "agrupamento"),
    ("relacionado", "related", "relacionados"),
    ("hierarquia", "hierarchy"),
    ("tabela", "table", "tabular"),
    ("interromper", "interruption", "interrupt", "interrupted", "cancelamento"),
    ("fallback", "alternativa", "degradacao"),
    ("carga", "workload"),
    # Bilingual UI/learning vocabulary, not product- or query-ID rules.
    ("estado", "estados", "state", "states", "status"),
    ("progresso", "progress"),
    ("estudo", "estudos", "study", "studies", "aprendizagem", "learning"),
)

@lru_cache(maxsize=2048)
def tokens(value):
    # Retain compound identifiers as well as split camelCase words.
    raw = set(re.findall(r"[a-z0-9]+", sx.strip_accents(str(value)).lower()))
    raw.update(re.findall(r"[a-z0-9]+", sx.normalize_text(str(value))))
    return {sx.stem_simple(w) for w in raw if len(w) >= 2 and w not in QUESTION_WORDS}

@lru_cache(maxsize=128)
def query_groups(query):
    words = [w for w in re.findall(r"[a-z0-9]+", sx.normalize_text(query))
             if w not in QUESTION_WORDS and len(w) >= 2]
    groups = []
    for word in dict.fromkeys(words[:24]):
        primary = tokens(word)
        alternatives = set(primary)
        for group in (*sx.SYNONYM_GROUPS, *EXTRA):
            if any(primary == tokens(term) for term in group):
                # Multi-word alternatives are kept as phrase sets below,
                # not expanded as unrelated individual words.
                alternatives.update(t for term in group if len(tokens(term)) == 1 for t in tokens(term))
        groups.append((primary, alternatives))
    return groups

def fields(row):
    item = row.get("record", {})
    aliases = item.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    head = tokens(" ".join([str(row.get("title", "")), str(row.get("product") or ""),
                           " ".join(str(a) for a in aliases)]))
    body = tokens(" ".join(str(item.get(k, "")) for k in (
        "definition","purpose","behavior","anatomy","guardrail","description","summary",
        "notes","tests","keywords","title","name","product","classification",
        "principle","acceptance","acceptance_tests","limits","patterns","deliverable","include","avoid","exit","question")))
    return head, body | head

def ranked(query, records, *, product=None, limit=40):
    groups = query_groups(query)
    if not groups:
        return []
    corpus = [(row, *fields(row)) for row in records
              if not product or (row.get("product") or "").casefold() == product.casefold()]
    n = len(corpus)
    if not n:
        return []
    # A rare query concept carries more information than a broad match.
    weights = [math.log(1 + (n+.5)/(sum(bool(alt & body) for _,_,body in corpus)+.5))
               for _,alt in groups]
    total = sum(weights)
    out = []
    for row, head, body in corpus:
        matched = 0
        weighted = 0.0
        score = 0.0
        for (primary, alt), weight in zip(groups, weights):
            if not alt & body:
                continue
            matched += 1
            weighted += weight
            score += weight * (2.4 if primary & head else 1.8 if alt & head else 1.2 if primary & body else .8)
        # Require multiple distinct concepts for multi-concept questions.
        required = 1 if len(groups) == 1 else 2
        coverage = weighted / total
        if matched < required or (len(groups) >= 3 and coverage < .18):
            continue
        out.append((score * (.5 + coverage), row["id"], row))
    out.sort(key=lambda item: (-item[0], item[1]))
    return [(row, score) for score, _, row in out[:limit]]

def adequate_hit(query, hit):
    """Conservative check for non-catalog channels on public natural-language requests."""
    groups = query_groups(query)
    if len(groups) < 2:
        return True
    body = tokens(str(hit.get("title", ""))+" "+str(hit.get("snippet", "")))
    return sum(bool(alt & body) for _,alt in groups) >= 2


def grouped_bm25(query, documents, *, k1=1.5, b=.75):
    """Public reranking with the same bilingual concepts as candidate selection.

    Count one concept per query group, not every synonym as independent evidence.
    The caller supplies only searchable text, never file paths or evaluation labels.
    """
    groups = list(dict.fromkeys(frozenset(alternatives) for _, alternatives in query_groups(query) if alternatives))
    if not documents or not groups:
        return [0.0] * len(documents)
    counters = [Counter(sx.stem_simple(w) for w in re.findall(r"[a-z0-9]+", sx.normalize_text(doc))
                        if len(w) >= 2 and w not in QUESTION_WORDS) for doc in documents]
    lengths = [sum(c.values()) for c in counters]
    n = len(counters)
    avg = max(sum(lengths) / n, 1.0)
    frequencies = [[max((c.get(term, 0) for term in group), default=0)
                    for group in groups] for c in counters]
    dfs = [sum(row[i] > 0 for row in frequencies) for i in range(len(groups))]
    scores = []
    for length, row in zip(lengths, frequencies):
        length_norm = k1 * (1 - b + b * length / avg)
        total = sum(math.log(1 + (n - df + .5) / (df + .5)) *
                    (tf * (k1 + 1) / (tf + length_norm))
                    for tf, df in zip(row, dfs) if tf)
        scores.append(round(total, 6))
    return scores
