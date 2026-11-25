#!/usr/bin/env python3
"""Deterministic ADR, decision record, and disambiguated multilingual glossary indexer.

Extracts, indexes, and searches architecture decision records (ADRs), decision docs,
and PT/EN domain/UI glossaries in SQLite with temporal validity and semantic relationships.

Design guarantees:
  - Standard library only; zero network calls, zero external LLM/API dependencies.
  - Strict deduplication by blob SHA across multiple repositories and branches.
  - Zero Emoji Policy: Absolutely NO Unicode emojis [\\U00010000-\\U0010ffff] in code,
    comments, docstrings, or command-line output.
  - Explicit disambiguation of ambiguous UI and domain concepts:
      * ui.tabs.pin_tab (pin tab, fixar uma aba) -> app-header-tabs.tsx
      * ui.sidebar.pinned_entity (pinned sidebar entity, fixados sidebar) -> app-sidebar-overview.tsx
      * domain.object.pin_type (pin object type, fixar objeto)
      * ui.favorites (favorites, favoritos)
      * domain.space vs domain.workspace
      * domain.question vs domain.flashcard vs domain.simulado
      * ui.graph vs domain.grafo
      * ui.sidebar.peek vs ui.sidebar.collapse
  - Ambiguous queries return candidate groups partitioned by concept_id.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

INDEXER_VERSION = "1.0.0"
DEFAULT_DB_PATH = Path(".cache/archive/knowledge.sqlite")
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

VALID_STATUSES = frozenset({"proposed", "accepted", "superseded", "rejected", "not-recovered"})
VALID_RELATIONSHIPS = frozenset({"same-as", "alias", "related", "conflicts-with", "ambiguous-with"})
VALID_PROVENANCE_STATUSES = frozenset({"verified", "unverified", "not-recovered", "synthetic"})
ARTIFICIAL_SHA_PREFIXES = ("b000", "d000", "q000", "f000", "s000", "g000")
GIT_SHA1_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def resolve_with_ontology(query: str, domain: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Delegate multidomain resolution, ContextKey lookup, and rule retrieval to domain_ontology."""
    import domain_ontology
    return domain_ontology.resolve_query(query, domain=domain, **kwargs)


def sanitize_indexed_text(text: Any, *, max_length: int = 800) -> tuple[str, bool]:
    """Sanitize untrusted indexed text against prompt-injection directives via domain_ontology."""
    import domain_ontology
    return domain_ontology.sanitize_untrusted_text(text, max_length=max_length)

DEFAULT_INVESTIGATED_REFS = [
    "refs/heads/main",
    "refs/heads/dev",
    "refs/heads/backup/dev-before-adr2",
    "refs/heads/backup/dev-20261111-1903",
    "refs/heads/backup/old-1",
    "refs/heads/old-5",
    "refs/heads/chore/consolidate-legacy-sources-20261123",
]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS decision_records (
    decision_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('proposed', 'accepted', 'superseded', 'rejected', 'not-recovered')),
    motivation TEXT,
    alternatives_json TEXT,
    consequences TEXT,
    scope TEXT,
    valid_from_ref TEXT,
    valid_until_ref TEXT,
    supersedes_id TEXT,
    superseded_by_id TEXT,
    source_repo TEXT,
    source_ref TEXT,
    commit_sha TEXT,
    blob_sha TEXT,
    path TEXT,
    line_start INTEGER,
    line_end INTEGER,
    investigated_refs_json TEXT,
    provenance_status TEXT NOT NULL DEFAULT 'unverified' CHECK(provenance_status IN ('verified', 'unverified', 'not-recovered', 'synthetic')),
    is_synthetic BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS decision_occurrences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL,
    blob_sha TEXT,
    source_repo TEXT,
    source_ref TEXT,
    commit_sha TEXT,
    path TEXT,
    line_start INTEGER,
    line_end INTEGER,
    FOREIGN KEY (decision_id) REFERENCES decision_records(decision_id)
);

CREATE INDEX IF NOT EXISTS idx_decision_occ_blob ON decision_occurrences(blob_sha);
CREATE INDEX IF NOT EXISTS idx_decision_occ_dec ON decision_occurrences(decision_id);

CREATE TABLE IF NOT EXISTS glossary_concepts (
    concept_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    canonical_term_en TEXT NOT NULL,
    canonical_term_pt TEXT NOT NULL,
    description TEXT,
    implementation_file TEXT,
    implementation_sha TEXT,
    provenance_status TEXT NOT NULL DEFAULT 'unverified' CHECK(provenance_status IN ('verified', 'unverified', 'not-recovered', 'synthetic')),
    is_synthetic BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS glossary_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id TEXT NOT NULL,
    term TEXT NOT NULL,
    language TEXT NOT NULL CHECK(language IN ('pt', 'en', 'any')),
    relationship TEXT NOT NULL CHECK(relationship IN ('same-as', 'alias', 'related', 'conflicts-with', 'ambiguous-with')),
    related_concept_id TEXT,
    provenance TEXT,
    FOREIGN KEY (concept_id) REFERENCES glossary_concepts(concept_id)
);

CREATE INDEX IF NOT EXISTS idx_glossary_terms_term ON glossary_terms(term);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_concept ON glossary_terms(concept_id);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    entity_type,
    entity_id,
    title,
    content,
    tokenize = 'unicode61'
);
"""

# Canonical glossary concepts specification
CANONICAL_CONCEPTS: list[dict[str, Any]] = [
    {
        "concept_id": "ui.tabs.pin_tab",
        "category": "ui",
        "canonical_term_en": "Pin Tab",
        "canonical_term_pt": "Fixar Aba",
        "description": "Fixar uma aba aberta no cabecalho do workspace para manter acesso permanente sem fechar na navegacao.",
        "implementation_file": "notes-app@old-5/src/app/_components/workspace/app-header-tabs.tsx",
        "implementation_sha": "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
        "provenance_status": "verified",
        "is_synthetic": False,
        "terms": [
            ("pin tab", "en", "same-as", None, "app-header-tabs.tsx"),
            ("fixar uma aba", "pt", "same-as", None, "app-header-tabs.tsx"),
            ("fixar aba", "pt", "alias", None, "app-header-tabs.tsx"),
            ("unpin tab", "en", "related", None, "app-header-tabs.tsx"),
            ("desafixar aba", "pt", "related", None, "app-header-tabs.tsx"),
            ("pin", "en", "ambiguous-with", "ui.sidebar.pinned_entity", "app-header-tabs.tsx"),
            ("fixar", "pt", "ambiguous-with", "ui.sidebar.pinned_entity", "app-header-tabs.tsx"),
        ],
    },
    {
        "concept_id": "ui.sidebar.pinned_entity",
        "category": "ui",
        "canonical_term_en": "Pinned Sidebar Entity",
        "canonical_term_pt": "Fixados Sidebar",
        "description": "Entidade fixada na barra lateral (sidebar overview) para atalho rapido e persistente.",
        "implementation_file": "notes-app@old-5/src/app/_components/workspace/app-sidebar-overview.tsx",
        "implementation_sha": "a020d635de368b755992e1282e18af9fdc2b8a03",
        "provenance_status": "verified",
        "is_synthetic": False,
        "terms": [
            ("pinned sidebar entity", "en", "same-as", None, "app-sidebar-overview.tsx"),
            ("fixados sidebar", "pt", "same-as", None, "app-sidebar-overview.tsx"),
            ("fixar na barra lateral", "pt", "alias", None, "app-sidebar-overview.tsx"),
            ("pinned entity", "en", "alias", None, "app-sidebar-overview.tsx"),
            ("sidebar pin", "en", "alias", None, "app-sidebar-overview.tsx"),
            ("pin", "en", "ambiguous-with", "ui.tabs.pin_tab", "app-sidebar-overview.tsx"),
            ("fixar", "pt", "ambiguous-with", "ui.tabs.pin_tab", "app-sidebar-overview.tsx"),
        ],
    },
    {
        "concept_id": "domain.object.pin_type",
        "category": "domain",
        "canonical_term_en": "Pin Object Type",
        "canonical_term_pt": "Fixar Objeto",
        "description": "Vinculo ou fixacao de um tipo de objeto (anotacao, questao, etc.) a visoes e layouts do workspace.",
        "implementation_file": "notes-app@old-5/src/app/_components/workspace/app-sidebar-overview.tsx",
        "implementation_sha": "a020d635de368b755992e1282e18af9fdc2b8a03",
        "provenance_status": "verified",
        "is_synthetic": False,
        "terms": [
            ("pin object type", "en", "same-as", None, "object-type-contract"),
            ("fixar objeto", "pt", "same-as", None, "object-type-contract"),
            ("fixar tipo de objeto", "pt", "alias", None, "object-type-contract"),
            ("pin object", "en", "alias", None, "object-type-contract"),
            ("pin", "en", "ambiguous-with", "ui.tabs.pin_tab", "object-type-contract"),
            ("fixar", "pt", "ambiguous-with", "ui.tabs.pin_tab", "object-type-contract"),
        ],
    },
    {
        "concept_id": "ui.favorites",
        "category": "ui",
        "canonical_term_en": "Favorites",
        "canonical_term_pt": "Favoritos",
        "description": "Colecao de entidades marcadas como favoritas pelo usuario.",
        "implementation_file": "notes-app@old-5/src/app/_components/workspace/app-sidebar-overview.tsx",
        "implementation_sha": "a020d635de368b755992e1282e18af9fdc2b8a03",
        "provenance_status": "verified",
        "is_synthetic": False,
        "terms": [
            ("favorites", "en", "same-as", None, "ui-favorites"),
            ("favoritos", "pt", "same-as", None, "ui-favorites"),
            ("favorite", "en", "alias", None, "ui-favorites"),
            ("favorito", "pt", "alias", None, "ui-favorites"),
            ("marcador", "pt", "related", None, "ui-favorites"),
            ("bookmark", "en", "related", None, "ui-favorites"),
            ("fixados", "pt", "conflicts-with", "ui.sidebar.pinned_entity", "ui-favorites"),
        ],
    },
    {
        "concept_id": "domain.space",
        "category": "domain",
        "canonical_term_en": "Space",
        "canonical_term_pt": "Espaco",
        "description": "Container de nivel superior para organizacao e agrupamento de cadernos e conteudos de estudo.",
        "implementation_file": "docs/Documentos/01-planejamento/revisao/app-shell/decisoes.md",
        "implementation_sha": "d811241f0a0f694694d35e4636ed46d2e38478c9",
        "provenance_status": "verified",
        "is_synthetic": False,
        "terms": [
            ("space", "en", "same-as", None, "domain-space"),
            ("espaco", "pt", "same-as", None, "domain-space"),
            ("spaces", "en", "alias", None, "domain-space"),
            ("espacos", "pt", "alias", None, "domain-space"),
            ("workspace", "en", "conflicts-with", "domain.workspace", "domain-space"),
            ("area de trabalho", "pt", "conflicts-with", "domain.workspace", "domain-space"),
        ],
    },
    {
        "concept_id": "domain.workspace",
        "category": "domain",
        "canonical_term_en": "Workspace",
        "canonical_term_pt": "Area de Trabalho",
        "description": "Area de trabalho e visualizacao ativa do usuario onde paineis, abas e editores residem.",
        "implementation_file": "notes-app@old-5/src/app/_components/workspace/app-header-tabs.tsx",
        "implementation_sha": "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
        "provenance_status": "verified",
        "is_synthetic": False,
        "terms": [
            ("workspace", "en", "same-as", None, "domain-workspace"),
            ("area de trabalho", "pt", "same-as", None, "domain-workspace"),
            ("workspaces", "en", "alias", None, "domain-workspace"),
            ("areas de trabalho", "pt", "alias", None, "domain-workspace"),
            ("space", "en", "conflicts-with", "domain.space", "domain-workspace"),
            ("espaco", "pt", "conflicts-with", "domain.space", "domain-workspace"),
        ],
    },
    {
        "concept_id": "domain.question",
        "category": "domain",
        "canonical_term_en": "Question",
        "canonical_term_pt": "Questao",
        "description": (
            "Item avaliativo formal contendo enunciado, opcoes de resposta e justificativa/resolucao. "
            "[Proveniencia nao verificada: blob SHA de implementacao nao recuperado nas fontes auditadas.]"
        ),
        "implementation_file": "src/domain/question.ts",
        "implementation_sha": None,
        "provenance_status": "unverified",
        "is_synthetic": False,
        "terms": [
            ("question", "en", "same-as", None, "domain-question (provenance: unverified)"),
            ("questao", "pt", "same-as", None, "domain-question (provenance: unverified)"),
            ("questions", "en", "alias", None, "domain-question (provenance: unverified)"),
            ("questoes", "pt", "alias", None, "domain-question (provenance: unverified)"),
            ("item", "any", "related", None, "domain-question (provenance: unverified)"),
            ("flashcard", "en", "conflicts-with", "domain.flashcard", "domain-question (provenance: unverified)"),
            ("simulado", "pt", "conflicts-with", "domain.simulado", "domain-question (provenance: unverified)"),
        ],
    },
    {
        "concept_id": "domain.flashcard",
        "category": "domain",
        "canonical_term_en": "Flashcard",
        "canonical_term_pt": "Cartao de Memorizacao",
        "description": (
            "Cartao de estudo frente e verso agendado por algoritmo de repeticao espacada (SRS/FSRS). "
            "[Proveniencia nao verificada: blob SHA de implementacao nao recuperado nas fontes auditadas.]"
        ),
        "implementation_file": "src/domain/flashcard.ts",
        "implementation_sha": None,
        "provenance_status": "unverified",
        "is_synthetic": False,
        "terms": [
            ("flashcard", "en", "same-as", None, "domain-flashcard (provenance: unverified)"),
            ("cartao", "pt", "same-as", None, "domain-flashcard (provenance: unverified)"),
            ("flashcards", "en", "alias", None, "domain-flashcard (provenance: unverified)"),
            ("cartoes", "pt", "alias", None, "domain-flashcard (provenance: unverified)"),
            ("card", "en", "alias", None, "domain-flashcard (provenance: unverified)"),
            ("srs", "en", "related", None, "domain-flashcard (provenance: unverified)"),
            ("repeticao espacada", "pt", "related", None, "domain-flashcard (provenance: unverified)"),
            ("question", "en", "conflicts-with", "domain.question", "domain-flashcard (provenance: unverified)"),
        ],
    },
    {
        "concept_id": "domain.simulado",
        "category": "domain",
        "canonical_term_en": "Mock Exam",
        "canonical_term_pt": "Simulado",
        "description": (
            "Sessao cronometrada com conjunto estruturado de questoes reproduzindo condicoes reais de prova. "
            "[Proveniencia nao verificada: blob SHA de implementacao nao recuperado nas fontes auditadas.]"
        ),
        "implementation_file": "src/domain/exam.ts",
        "implementation_sha": None,
        "provenance_status": "unverified",
        "is_synthetic": False,
        "terms": [
            ("simulado", "pt", "same-as", None, "domain-simulado (provenance: unverified)"),
            ("mock exam", "en", "same-as", None, "domain-simulado (provenance: unverified)"),
            ("simulados", "pt", "alias", None, "domain-simulado (provenance: unverified)"),
            ("practice test", "en", "alias", None, "domain-simulado (provenance: unverified)"),
            ("prova", "pt", "related", None, "domain-simulado (provenance: unverified)"),
            ("exam", "en", "related", None, "domain-simulado (provenance: unverified)"),
            ("question", "en", "conflicts-with", "domain.question", "domain-simulado (provenance: unverified)"),
        ],
    },
    {
        "concept_id": "ui.graph",
        "category": "ui",
        "canonical_term_en": "UI Graph View",
        "canonical_term_pt": "Visualizacao em Grafo",
        "description": (
            "Componente interativo e responsivo de exibicao visual de nos e arestas no canvas. "
            "[Proveniencia nao verificada: blob SHA de implementacao nao recuperado nas fontes auditadas.]"
        ),
        "implementation_file": "src/components/graph-view.tsx",
        "implementation_sha": None,
        "provenance_status": "unverified",
        "is_synthetic": False,
        "terms": [
            ("graph view", "en", "same-as", None, "ui-graph (provenance: unverified)"),
            ("visualizacao em grafo", "pt", "same-as", None, "ui-graph (provenance: unverified)"),
            ("ui graph", "en", "alias", None, "ui-graph (provenance: unverified)"),
            ("grafo interativo", "pt", "alias", None, "ui-graph (provenance: unverified)"),
            ("graph", "en", "ambiguous-with", "domain.grafo", "ui-graph (provenance: unverified)"),
            ("grafo", "pt", "ambiguous-with", "domain.grafo", "ui-graph (provenance: unverified)"),
            ("domain grafo", "en", "conflicts-with", "domain.grafo", "ui-graph (provenance: unverified)"),
        ],
    },
    {
        "concept_id": "domain.grafo",
        "category": "domain",
        "canonical_term_en": "Domain Knowledge Graph",
        "canonical_term_pt": "Grafo de Dominio",
        "description": (
            "Estrutura de dados relacional e ontologica de nos, tags, arestas e pesos do conhecimento. "
            "[Proveniencia nao verificada: blob SHA canonico nao atribuido a implementacao historica no inventario.]"
        ),
        "implementation_file": "scripts/graph_linker.py",
        "implementation_sha": None,
        "provenance_status": "unverified",
        "is_synthetic": False,
        "terms": [
            ("knowledge graph", "en", "same-as", None, "domain-grafo (provenance: unverified)"),
            ("grafo de conhecimento", "pt", "same-as", None, "domain-grafo (provenance: unverified)"),
            ("graph data structure", "en", "alias", None, "domain-grafo (provenance: unverified)"),
            ("modelo de grafo", "pt", "alias", None, "domain-grafo (provenance: unverified)"),
            ("graph", "en", "ambiguous-with", "ui.graph", "domain-grafo (provenance: unverified)"),
            ("grafo", "pt", "ambiguous-with", "ui.graph", "domain-grafo (provenance: unverified)"),
            ("ui graph", "en", "conflicts-with", "ui.graph", "domain-grafo (provenance: unverified)"),
        ],
    },
    {
        "concept_id": "ui.sidebar.peek",
        "category": "ui",
        "canonical_term_en": "Sidebar Peek",
        "canonical_term_pt": "Espiar Barra Lateral",
        "description": "Abertura temporaria por sobreposicao da barra lateral sem alterar o estado colapsado persistido.",
        "implementation_file": "notes-app@old-5/src/app/_components/workspace/app-sidebar-overview.tsx",
        "implementation_sha": "a020d635de368b755992e1282e18af9fdc2b8a03",
        "provenance_status": "verified",
        "is_synthetic": False,
        "terms": [
            ("peek", "en", "same-as", None, "ui-sidebar-peek"),
            ("espiar", "pt", "same-as", None, "ui-sidebar-peek"),
            ("sidebar peek", "en", "alias", None, "ui-sidebar-peek"),
            ("preview lateral", "pt", "alias", None, "ui-sidebar-peek"),
            ("collapse", "en", "conflicts-with", "ui.sidebar.collapse", "ui-sidebar-peek"),
            ("recolher", "pt", "conflicts-with", "ui.sidebar.collapse", "ui-sidebar-peek"),
        ],
    },
    {
        "concept_id": "ui.sidebar.collapse",
        "category": "ui",
        "canonical_term_en": "Sidebar Collapse",
        "canonical_term_pt": "Recolher Barra Lateral",
        "description": "Recolhimento persistente da barra lateral para maximizar a visao do espaco de trabalho.",
        "implementation_file": "notes-app@old-5/src/app/_components/workspace/app-sidebar-overview.tsx",
        "implementation_sha": "a020d635de368b755992e1282e18af9fdc2b8a03",
        "provenance_status": "verified",
        "is_synthetic": False,
        "terms": [
            ("collapse", "en", "same-as", None, "ui-sidebar-collapse"),
            ("recolher", "pt", "same-as", None, "ui-sidebar-collapse"),
            ("sidebar collapse", "en", "alias", None, "ui-sidebar-collapse"),
            ("fechar barra lateral", "pt", "alias", None, "ui-sidebar-collapse"),
            ("minimizar barra", "pt", "alias", None, "ui-sidebar-collapse"),
            ("peek", "en", "conflicts-with", "ui.sidebar.peek", "ui-sidebar-collapse"),
            ("espiar", "pt", "conflicts-with", "ui.sidebar.peek", "ui-sidebar-collapse"),
        ],
    },
]

# Seed architecture decision records
SEED_DECISIONS: list[dict[str, Any]] = [
    {
        "decision_id": "ADR-0005",
        "title": "Production Baseline and Automated Testing",
        "status": "accepted",
        "motivation": "Establish reliable production test suite and CI validation baseline for release readiness.",
        "alternatives_json": json.dumps(["manual regression testing", "untested branch merges"]),
        "consequences": "Every change must pass automated suite before merge; reproducible CI across repositories.",
        "scope": "testing/ci",
        "valid_from_ref": "refs/heads/main",
        "valid_until_ref": None,
        "supersedes_id": "ADR-0001",
        "superseded_by_id": None,
        "source_repo": "exams-app-old",
        "source_ref": "refs/heads/backup/old-1",
        "commit_sha": "c2fca6232c45ce4d64d0088036e1ddd0742944d4",
        "blob_sha": "5f2eadd87895150960d5b0086f3772bfc70299f3",
        "path": "docs/adr/0005-configure-testing.md",
        "line_start": 1,
        "line_end": 50,
        "investigated_refs_json": None,
        "provenance_status": "verified",
        "is_synthetic": False,
    },
    {
        "decision_id": "ADR-0002",
        "title": "Add Basic Skills Framework",
        "status": "superseded",
        "motivation": "Provide foundational agent skills and automated orchestration tooling.",
        "alternatives_json": json.dumps(["monolithic bash scripts", "third-party proprietary agent SaaS"]),
        "consequences": "Standardized skill manifest format; superseded when consolidated into testing and tool matrix.",
        "scope": "tooling/agents",
        "valid_from_ref": "refs/heads/backup/dev-before-adr2",
        "valid_until_ref": "refs/heads/main",
        "supersedes_id": None,
        "superseded_by_id": "ADR-0005",
        "source_repo": "exams-app-old",
        "source_ref": "refs/heads/backup/dev-before-adr2",
        "commit_sha": "1db80ad136bbab8720637fbd33315d08bf6a5def",
        "blob_sha": "b1b64da0374bb002f797793d0953a7bcf54ae22d",
        "path": "docs/adr/0002-add-basic-skills.md",
        "line_start": 1,
        "line_end": 45,
        "investigated_refs_json": None,
        "provenance_status": "verified",
        "is_synthetic": False,
    },
    {
        "decision_id": "ADR-0008",
        "title": "Install Firebase UI Registry and Authentication",
        "status": "accepted",
        "motivation": "Integrate Firebase auth components with shadcn/ui registry to maintain consistent visual design.",
        "alternatives_json": json.dumps(["custom form authentication", "standalone auth modal without shadcn styling"]),
        "consequences": "Unified look and feel for authentication workflows with reactive auth state in header.",
        "scope": "auth/ui",
        "valid_from_ref": "refs/heads/backup/old-1",
        "valid_until_ref": None,
        "supersedes_id": None,
        "superseded_by_id": None,
        "source_repo": "exams-app-old",
        "source_ref": "refs/heads/backup/old-1",
        "commit_sha": "c2fca6232c45ce4d64d0088036e1ddd0742944d4",
        "blob_sha": "eb3e0712276da0b61ea0058369aca95b5160d59b",
        "path": "docs/adr/0008-install-firebase-ui-registry.md",
        "line_start": 1,
        "line_end": 52,
        "investigated_refs_json": None,
        "provenance_status": "verified",
        "is_synthetic": False,
    },
    {
        "decision_id": "DEC-APP-SHELL-01",
        "title": "Desacoplamento de Abas do App Shell e Fixacao de Abas",
        "status": "accepted",
        "motivation": "Permitir fixar e alternar abas abertas no cabecalho independentemente da visibilidade da barra lateral.",
        "alternatives_json": json.dumps(["abas renderizadas na propria sidebar", "aba unica sem suporte a multi-documento"]),
        "consequences": "Aba fixada permanece no topo do workspace (app-header-tabs.tsx) sem poluir a arvore da sidebar.",
        "scope": "ui.tabs",
        "valid_from_ref": "refs/heads/main",
        "valid_until_ref": None,
        "supersedes_id": None,
        "superseded_by_id": None,
        "source_repo": "notes-app",
        "source_ref": "refs/heads/old-5",
        "commit_sha": "4eb93c5013c27ba6724b4f116cc9fe5846398eb8",
        "blob_sha": "d811241f0a0f694694d35e4636ed46d2e38478c9",
        "path": "docs/Documentos/01-planejamento/revisao/app-shell/decisoes.md",
        "line_start": 1,
        "line_end": 38,
        "investigated_refs_json": None,
        "provenance_status": "verified",
        "is_synthetic": False,
    },
    {
        "decision_id": "DEC-SIDEBAR-PROTOTIPO-01",
        "title": "Fixados e Atividades Recentes na Barra Lateral",
        "status": "accepted",
        "motivation": "Separar entidades fixadas na barra lateral de abas ativas do workspace para acesso permanente a itens favoritos.",
        "alternatives_json": json.dumps(["misturar fixados com abas abertas na barra lateral"]),
        "consequences": "Entidades fixadas residem na secao pinned da sidebar (app-sidebar-overview.tsx) com acoes de desafixar e abrir.",
        "scope": "ui.sidebar",
        "valid_from_ref": "refs/heads/main",
        "valid_until_ref": None,
        "supersedes_id": None,
        "superseded_by_id": None,
        "source_repo": "notes-app",
        "source_ref": "refs/heads/old-5",
        "commit_sha": "a020d635de368b755992e1282e18af9fdc2b8a03",
        "blob_sha": "5a6b72be94ccfe4316e65dcd9fafaba9fa9accf1",
        "path": "docs/Documentos/01-planejamento/revisao/sidebar-prototipo/decisoes.md",
        "line_start": 1,
        "line_end": 42,
        "investigated_refs_json": None,
        "provenance_status": "verified",
        "is_synthetic": False,
    },
]


def strip_accents(text: str) -> str:
    """Strip accents and diacritics for uniform term normalization."""
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def normalize_term(term: str) -> str:
    """Normalize term for comparison: lowercase, strip accents, collapse spaces."""
    cleaned = strip_accents(term.lower().strip())
    return re.sub(r"\s+", " ", cleaned)


def normalize_adr_id(text: str) -> str:
    """Normalize ADR identifier variations like 'ADR 0005', 'ADR2', 'adr-8' to 'ADR-0005'."""
    raw = text.strip()
    m = re.match(r"(?i)^adr[\s\-_]*(\d+)$", raw)
    if m:
        num = int(m.group(1))
        return f"ADR-{num:04d}"
    return raw.upper() if raw.upper().startswith("ADR-") else raw


def normalize_status(status_str: str) -> str:
    """Map multilingual status string to one of the 5 canonical statuses."""
    s = normalize_term(status_str)
    if any(tok in s for tok in ("not-recovered", "not recovered", "nao recuperado", "unrecovered", "missing")):
        return "not-recovered"
    if any(tok in s for tok in ("accepted", "aceito", "aceita", "aprovado", "aprovada")):
        return "accepted"
    if any(tok in s for tok in ("superseded", "substituido", "substituida", "deprecado", "obsoleto")):
        return "superseded"
    if any(tok in s for tok in ("rejected", "rejeitado", "rejeitada", "descartado")):
        return "rejected"
    if any(tok in s for tok in ("proposed", "proposto", "proposta", "draft", "analise")):
        return "proposed"
    return "proposed"


def is_artificial_sha(sha: str | None) -> bool:
    """Return True if sha matches known artificial/placeholder patterns."""
    if not sha or not isinstance(sha, str):
        return False
    lowered = sha.strip().lower()
    if not lowered:
        return False
    if any(lowered.startswith(prefix) for prefix in ARTIFICIAL_SHA_PREFIXES):
        return True
    if lowered == "0" * 40 or lowered.endswith("0" * 16):
        return True
    return False


def validate_git_sha(sha: str | None) -> bool:
    """Validate that a SHA string is a genuine 40-char hex Git SHA-1 and not artificial."""
    if not sha or not isinstance(sha, str):
        return False
    candidate = sha.strip()
    if not GIT_SHA1_RE.match(candidate):
        return False
    if is_artificial_sha(candidate):
        return False
    return True


def _resolve_provenance_fields(
    sha: str | None,
    requested_status: str | None = None,
    requested_synthetic: bool = False,
) -> tuple[str | None, str, int]:
    """Normalize (sha, provenance_status, is_synthetic) without allowing artificial SHAs as verified."""
    if requested_status in VALID_PROVENANCE_STATUSES:
        status = requested_status
    else:
        status = "unverified"

    if sha is not None and str(sha).strip() != "":
        sha_str = str(sha).strip()
        if not validate_git_sha(sha_str):
            if is_artificial_sha(sha_str):
                return None, "synthetic" if requested_synthetic else "unverified", 1 if requested_synthetic else 0
            return None, "unverified", 1 if requested_synthetic else 0
        return sha_str, status, 1 if (requested_synthetic or status == "synthetic") else 0

    if status == "verified":
        status = "unverified"
    return None, status, 1 if (requested_synthetic or status == "synthetic") else 0


def compute_git_blob_sha(content_bytes: bytes) -> str:
    """Compute standard Git blob SHA-1 hash."""
    header = f"blob {len(content_bytes)}\0".encode("utf-8")
    return hashlib.sha1(header + content_bytes).hexdigest()


def open_knowledge_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open or create the knowledge SQLite database, configuring tables and seeding data."""
    if db_path is None or str(db_path) == ":memory:":
        target = ":memory:"
    else:
        p = Path(db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        target = str(p)

    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if target != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")

    conn.executescript(SCHEMA_SQL)
    seed_canonical_knowledge(conn)
    return conn


def seed_canonical_knowledge(conn: sqlite3.Connection) -> None:
    """Seed the database with canonical multilingual concepts, terms, and known ADRs."""
    # Seed concepts and terms
    for concept in CANONICAL_CONCEPTS:
        impl_sha, prov_status, is_synth = _resolve_provenance_fields(
            concept.get("implementation_sha"),
            concept.get("provenance_status", "unverified"),
            bool(concept.get("is_synthetic", False)),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO glossary_concepts (
                concept_id, category, canonical_term_en, canonical_term_pt,
                description, implementation_file, implementation_sha,
                provenance_status, is_synthetic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                concept["concept_id"],
                concept["category"],
                concept["canonical_term_en"],
                concept["canonical_term_pt"],
                concept["description"],
                concept.get("implementation_file"),
                impl_sha,
                prov_status,
                is_synth,
            ),
        )

        for term, lang, rel, rel_concept, prov in concept["terms"]:
            conn.execute(
                """
                INSERT OR IGNORE INTO glossary_terms (
                    concept_id, term, language, relationship, related_concept_id, provenance
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (concept["concept_id"], term, lang, rel, rel_concept, prov),
            )

        # Update FTS index for concept
        conn.execute(
            """
            INSERT INTO knowledge_fts (entity_type, entity_id, title, content)
            VALUES (?, ?, ?, ?)
            """,
            (
                "concept",
                concept["concept_id"],
                f"{concept['canonical_term_en']} / {concept['canonical_term_pt']}",
                f"{concept['description']} {' '.join(t[0] for t in concept['terms'])}",
            ),
        )

    # Seed known architecture decisions
    for dec in SEED_DECISIONS:
        blob_sha, prov_status, is_synth = _resolve_provenance_fields(
            dec.get("blob_sha"),
            dec.get("provenance_status", "unverified"),
            bool(dec.get("is_synthetic", False)),
        )
        commit_sha = dec.get("commit_sha")
        if commit_sha and not validate_git_sha(commit_sha):
            commit_sha = None
        conn.execute(
            """
            INSERT OR REPLACE INTO decision_records (
                decision_id, title, status, motivation, alternatives_json,
                consequences, scope, valid_from_ref, valid_until_ref,
                supersedes_id, superseded_by_id, source_repo, source_ref,
                commit_sha, blob_sha, path, line_start, line_end,
                investigated_refs_json, provenance_status, is_synthetic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dec["decision_id"],
                dec["title"],
                dec["status"],
                dec.get("motivation"),
                dec.get("alternatives_json"),
                dec.get("consequences"),
                dec.get("scope"),
                dec.get("valid_from_ref"),
                dec.get("valid_until_ref"),
                dec.get("supersedes_id"),
                dec.get("superseded_by_id"),
                dec.get("source_repo"),
                dec.get("source_ref"),
                commit_sha,
                blob_sha,
                dec.get("path"),
                dec.get("line_start", 1),
                dec.get("line_end", 1),
                dec.get("investigated_refs_json"),
                prov_status,
                is_synth,
            ),
        )

        conn.execute(
            """
            INSERT INTO decision_occurrences (
                decision_id, blob_sha, source_repo, source_ref, commit_sha, path, line_start, line_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dec["decision_id"],
                blob_sha,
                dec.get("source_repo"),
                dec.get("source_ref"),
                commit_sha,
                dec.get("path"),
                dec.get("line_start", 1),
                dec.get("line_end", 1),
            ),
        )

        # FTS index for decision
        conn.execute(
            """
            INSERT INTO knowledge_fts (entity_type, entity_id, title, content)
            VALUES (?, ?, ?, ?)
            """,
            (
                "decision",
                dec["decision_id"],
                dec["title"],
                f"{dec.get('motivation', '')} {dec.get('consequences', '')} {dec.get('scope', '')}",
            ),
        )

    conn.commit()


def record_not_recovered_adr(
    conn: sqlite3.Connection,
    adr_id: str,
    title: str = "",
    investigated_refs: list[str] | None = None,
    repo: str = "exams-app-archive",
    motivation: str = "Mentioned or cited but canonical document was not recovered in audited branches.",
) -> dict[str, Any]:
    """Record an unrecovered ADR with the explicit inventory of audited refs."""
    norm_id = normalize_adr_id(adr_id)
    refs = investigated_refs or DEFAULT_INVESTIGATED_REFS
    refs_json = json.dumps(refs)
    t = title or f"Unrecovered Decision {norm_id}"

    conn.execute(
        """
        INSERT OR REPLACE INTO decision_records (
            decision_id, title, status, motivation, alternatives_json,
            consequences, scope, valid_from_ref, valid_until_ref,
            supersedes_id, superseded_by_id, source_repo, source_ref,
            commit_sha, blob_sha, path, line_start, line_end,
            investigated_refs_json, provenance_status, is_synthetic
        ) VALUES (?, ?, 'not-recovered', ?, NULL, NULL, 'unrecovered', NULL, NULL, NULL, NULL, ?, NULL, NULL, NULL, NULL, NULL, NULL, ?, 'not-recovered', 0)
        """,
        (norm_id, t, motivation, repo, refs_json),
    )
    conn.commit()

    return {
        "decision_id": norm_id,
        "title": t,
        "status": "not-recovered",
        "motivation": motivation,
        "investigated_refs": refs,
        "source_repo": repo,
        "provenance_status": "not-recovered",
        "is_synthetic": False,
        "verified": False,
    }


def parse_markdown_adrs(
    content: str,
    path: str = "",
    repo: str = "exams-app-archive",
    ref: str = "refs/heads/main",
    commit_sha: str | None = None,
    blob_sha: str | None = None,
) -> list[dict[str, Any]]:
    """Parse Markdown content for ADRs, headings, metadata, sections, and tables."""
    results: list[dict[str, Any]] = []
    lines = content.splitlines()

    # Case 1: Check if this file itself is an ADR document (e.g. 0005-configure-testing.md or ADR-0001.md)
    path_norm = path.replace("\\", "/")
    filename = Path(path_norm).name
    file_adr_match = re.match(r"(?i)^(?:adr[-_]?)?(\d{1,4})[-_](.+)\.md$", filename)

    if file_adr_match or "/adr/" in path_norm.lower() or path_norm.lower().endswith("decisoes.md"):
        doc_id = ""
        doc_title = ""
        if file_adr_match:
            num = int(file_adr_match.group(1))
            doc_id = f"ADR-{num:04d}"
            doc_title = file_adr_match.group(2).replace("-", " ").strip().title()

        # Parse sections and metadata
        status = "accepted"
        motivation_lines: list[str] = []
        alternatives: list[str] = []
        consequences_lines: list[str] = []
        scope = "general"
        supersedes_id = None
        superseded_by_id = None
        current_section = None

        for idx, line in enumerate(lines, start=1):
            sline = line.strip()

            # Heading 1 can provide title or ID
            if sline.startswith("# "):
                h_text = sline[2:].strip()
                h_match = re.match(r"(?i)^(?:ADR[\s\-_]*(\d+)[:\s\-–—]+)?(.+)$", h_text)
                if h_match:
                    if h_match.group(1):
                        doc_id = f"ADR-{int(h_match.group(1)):04d}"
                    if h_match.group(2) and not doc_title:
                        doc_title = h_match.group(2).strip()
                continue

            # Check status line
            status_match = re.match(r"(?i)^(?:status|estado)\s*[:=]\s*(.+)$", sline)
            if status_match:
                status_raw = status_match.group(1).strip()
                status = normalize_status(status_raw)
                sup_match = re.search(r"(?i)(?:by|por)\s+(adr[\s\-_]*\d+)", status_raw)
                if sup_match:
                    superseded_by_id = normalize_adr_id(sup_match.group(1))
                    status = "superseded"
                continue

            # Check scope line in header
            scope_match = re.match(r"(?i)^(?:scope|escopo)\s*[:=]\s*(.+)$", sline)
            if scope_match:
                scope = scope_match.group(1).strip()
                continue

            # Check supersedes / superseded by lines
            sup_by_match = re.match(r"(?i)^(?:superseded\s*by|substituido\s*por)\s*[:=]\s*(.+)$", sline)
            if sup_by_match:
                superseded_by_id = normalize_adr_id(sup_by_match.group(1).strip())
                status = "superseded"
                continue

            sup_match = re.match(r"(?i)^(?:supersedes|substitui)\s*[:=]\s*(.+)$", sline)
            if sup_match:
                supersedes_id = normalize_adr_id(sup_match.group(1).strip())
                continue

            # Check section headings
            if sline.startswith("## ") or sline.startswith("### "):
                sec_header = normalize_term(sline.lstrip("#").strip())
                if any(k in sec_header for k in ("context", "contexto", "motiva", "rationale")):
                    current_section = "motivation"
                elif any(k in sec_header for k in ("alternative", "alternativa", "consider")):
                    current_section = "alternatives"
                elif any(k in sec_header for k in ("consequence", "consequencia", "outcome", "impact")):
                    current_section = "consequences"
                elif any(k in sec_header for k in ("scope", "escopo")):
                    current_section = "scope"
                elif any(k in sec_header for k in ("decision", "decisao")):
                    current_section = "decision"
                else:
                    current_section = None
                continue

            # Collect section content
            if current_section == "motivation" and sline:
                motivation_lines.append(sline)
            elif current_section == "alternatives" and sline:
                cleaned_alt = sline.lstrip("*-123456789.) ").strip()
                if cleaned_alt:
                    alternatives.append(cleaned_alt)
            elif current_section == "consequences" and sline:
                consequences_lines.append(sline)
            elif current_section == "scope" and sline:
                scope = sline

        if doc_id:
            results.append({
                "decision_id": doc_id,
                "title": doc_title or f"Architecture Decision {doc_id}",
                "status": status,
                "motivation": "\n".join(motivation_lines).strip() or "Documented architecture decision.",
                "alternatives_json": json.dumps(alternatives) if alternatives else None,
                "consequences": "\n".join(consequences_lines).strip() or None,
                "scope": scope,
                "valid_from_ref": ref,
                "valid_until_ref": ref if status == "superseded" else None,
                "supersedes_id": supersedes_id,
                "superseded_by_id": superseded_by_id,
                "source_repo": repo,
                "source_ref": ref,
                "commit_sha": commit_sha,
                "blob_sha": blob_sha,
                "path": path,
                "line_start": 1,
                "line_end": len(lines),
                "investigated_refs_json": None,
            })

    # Case 2: Markdown tables containing ADRs or decisions
    # Table headers: | ID | Title / Titulo | Status | Motivation / Motivacao | ... |
    in_table = False
    table_headers: list[str] = []

    for idx, line in enumerate(lines, start=1):
        sline = line.strip()
        if sline.startswith("|") and sline.endswith("|"):
            parts = [p.strip() for p in sline.split("|")[1:-1]]
            if not in_table:
                # Potential header row
                norm_parts = [normalize_term(p) for p in parts]
                if any("id" in p for p in norm_parts) and any("status" in p or "titul" in p or "decis" in p for p in norm_parts):
                    in_table = True
                    table_headers = norm_parts
                    continue
            elif in_table:
                # Separator row |---|---|
                if all(re.match(r"^:?-+:?$", p) for p in parts):
                    continue
                # Data row
                row_dict = dict(zip(table_headers, parts))
                id_val = ""
                for k in table_headers:
                    if "id" in k:
                        id_val = row_dict.get(k, "")
                        break
                if id_val and ("adr" in id_val.lower() or "dec" in id_val.lower()):
                    norm_id = normalize_adr_id(id_val)
                    title_val = ""
                    status_val = "accepted"
                    mot_val = ""
                    for k, v in row_dict.items():
                        if "titul" in k or "title" in k or "decis" in k:
                            title_val = v
                        elif "status" in k:
                            status_val = normalize_status(v)
                        elif "motiv" in k or "context" in k:
                            mot_val = v

                    results.append({
                        "decision_id": norm_id,
                        "title": title_val or f"Decision {norm_id}",
                        "status": status_val,
                        "motivation": mot_val or "Extracted from decision table.",
                        "alternatives_json": None,
                        "consequences": None,
                        "scope": "table-documented",
                        "valid_from_ref": ref,
                        "valid_until_ref": ref if status_val == "superseded" else None,
                        "supersedes_id": None,
                        "superseded_by_id": None,
                        "source_repo": repo,
                        "source_ref": ref,
                        "commit_sha": commit_sha,
                        "blob_sha": blob_sha,
                        "path": path,
                        "line_start": idx,
                        "line_end": idx,
                        "investigated_refs_json": None,
                    })
        else:
            in_table = False

    # Case 3: Embedded DEC headings (e.g. ## DEC-SIDEBAR-PROTOTIPO-01: ...)
    for idx, line in enumerate(lines, start=1):
        sline = line.strip()
        dec_heading = re.match(r"(?im)^#{2,3}\s+(DEC[-_][A-Z0-9_\-]+)[:\s\-–—]+(.+)$", sline)
        if dec_heading:
            d_id = dec_heading.group(1).upper()
            d_title = dec_heading.group(2).strip()
            # Look ahead for status and motivation
            d_status = "accepted"
            d_mot: list[str] = []
            for next_line in lines[idx:idx + 20]:
                sn = next_line.strip()
                if sn.startswith("#"):
                    break
                sm = re.match(r"(?i)^(?:status|estado)\s*[:=]\s*(.+)$", sn)
                if sm:
                    d_status = normalize_status(sm.group(1))
                elif sn:
                    d_mot.append(sn)

            results.append({
                "decision_id": d_id,
                "title": d_title,
                "status": d_status,
                "motivation": " ".join(d_mot).strip() or "Embedded decision section.",
                "alternatives_json": None,
                "consequences": None,
                "scope": "embedded-section",
                "valid_from_ref": ref,
                "valid_until_ref": ref if d_status == "superseded" else None,
                "supersedes_id": None,
                "superseded_by_id": None,
                "source_repo": repo,
                "source_ref": ref,
                "commit_sha": commit_sha,
                "blob_sha": blob_sha,
                "path": path,
                "line_start": idx,
                "line_end": idx + len(d_mot) + 1,
                "investigated_refs_json": None,
            })

    return results


def parse_commit_body(
    commit_sha: str,
    message: str,
    repo: str = "exams-app-archive",
    ref: str = "refs/heads/main",
) -> list[dict[str, Any]]:
    """Parse commit message for decision records or reference tracking."""
    results: list[dict[str, Any]] = []
    lines = message.splitlines()

    # Look for explicit ADR header in commit body
    for idx, line in enumerate(lines, start=1):
        m = re.match(r"(?i)^\s*(ADR[\s\-_]*\d+)[:\s\-–—]+(.+)$", line.strip())
        if m:
            adr_id = normalize_adr_id(m.group(1))
            title = m.group(2).strip()
            status = "accepted"
            motivation_lines: list[str] = []

            for follow_line in lines[idx:]:
                fl = follow_line.strip()
                st_match = re.match(r"(?i)^(?:status|estado)\s*[:=]\s*(.+)$", fl)
                if st_match:
                    status = normalize_status(st_match.group(1))
                elif fl:
                    motivation_lines.append(fl)

            results.append({
                "decision_id": adr_id,
                "title": title,
                "status": status,
                "motivation": "\n".join(motivation_lines).strip() or "Extracted from commit body.",
                "alternatives_json": None,
                "consequences": None,
                "scope": "commit-documented",
                "valid_from_ref": ref,
                "valid_until_ref": ref if status == "superseded" else None,
                "supersedes_id": None,
                "superseded_by_id": None,
                "source_repo": repo,
                "source_ref": ref,
                "commit_sha": commit_sha,
                "blob_sha": None,
                "path": f"commit:{commit_sha[:8]}",
                "line_start": idx,
                "line_end": idx + len(motivation_lines),
                "investigated_refs_json": None,
            })

    return results


def index_document_file(
    conn: sqlite3.Connection,
    file_path: Path | str,
    repo: str = "exams-app-archive",
    ref: str = "refs/heads/main",
    commit_sha: str | None = None,
) -> list[str]:
    """Index a Markdown or text document into SQLite with blob deduplication."""
    path_obj = Path(file_path)
    if not path_obj.exists() or not path_obj.is_file():
        return []

    try:
        content_bytes = path_obj.read_bytes()
    except Exception:
        return []

    blob_sha = compute_git_blob_sha(content_bytes)

    # Check deduplication by blob_sha
    existing = conn.execute(
        "SELECT decision_id FROM decision_occurrences WHERE blob_sha = ?",
        (blob_sha,),
    ).fetchall()

    if existing:
        # Record occurrence for existing blob and return IDs
        indexed_ids: list[str] = []
        for row in existing:
            dec_id = row["decision_id"]
            conn.execute(
                """
                INSERT INTO decision_occurrences (
                    decision_id, blob_sha, source_repo, source_ref, commit_sha, path, line_start, line_end
                ) VALUES (?, ?, ?, ?, ?, ?, 1, 1)
                """,
                (dec_id, blob_sha, repo, ref, commit_sha, str(file_path)),
            )
            indexed_ids.append(dec_id)
        conn.commit()
        return indexed_ids

    # Parse document content
    content_str = content_bytes.decode("utf-8", errors="replace")
    parsed_adrs = parse_markdown_adrs(
        content_str,
        path=str(file_path),
        repo=repo,
        ref=ref,
        commit_sha=commit_sha,
        blob_sha=blob_sha,
    )

    indexed_ids = []
    for adr in parsed_adrs:
        adr_blob_sha, adr_prov_status, adr_is_synth = _resolve_provenance_fields(
            adr.get("blob_sha"),
            "verified" if adr.get("blob_sha") else "unverified",
            False,
        )
        adr_commit_sha = adr.get("commit_sha")
        if adr_commit_sha and not validate_git_sha(adr_commit_sha):
            adr_commit_sha = None
        conn.execute(
            """
            INSERT OR REPLACE INTO decision_records (
                decision_id, title, status, motivation, alternatives_json,
                consequences, scope, valid_from_ref, valid_until_ref,
                supersedes_id, superseded_by_id, source_repo, source_ref,
                commit_sha, blob_sha, path, line_start, line_end,
                investigated_refs_json, provenance_status, is_synthetic
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                adr["decision_id"],
                adr["title"],
                adr["status"],
                adr["motivation"],
                adr["alternatives_json"],
                adr["consequences"],
                adr["scope"],
                adr["valid_from_ref"],
                adr["valid_until_ref"],
                adr["supersedes_id"],
                adr["superseded_by_id"],
                adr["source_repo"],
                adr["source_ref"],
                adr_commit_sha,
                adr_blob_sha,
                adr["path"],
                adr["line_start"],
                adr["line_end"],
                adr["investigated_refs_json"],
                adr_prov_status,
                adr_is_synth,
            ),
        )

        conn.execute(
            """
            INSERT INTO decision_occurrences (
                decision_id, blob_sha, source_repo, source_ref, commit_sha, path, line_start, line_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                adr["decision_id"],
                adr_blob_sha,
                adr["source_repo"],
                adr["source_ref"],
                adr_commit_sha,
                adr["path"],
                adr["line_start"],
                adr["line_end"],
            ),
        )

        conn.execute(
            """
            INSERT INTO knowledge_fts (entity_type, entity_id, title, content)
            VALUES (?, ?, ?, ?)
            """,
            (
                "decision",
                adr["decision_id"],
                adr["title"],
                f"{adr.get('motivation', '')} {adr.get('consequences', '')}",
            ),
        )

        indexed_ids.append(adr["decision_id"])

    conn.commit()
    return indexed_ids


def index_directory(
    conn: sqlite3.Connection,
    dir_path: Path | str,
    repo: str = "exams-app-archive",
    ref: str = "refs/heads/main",
) -> int:
    """Recursively index all markdown and decision documents within a directory."""
    root = Path(dir_path)
    if not root.exists():
        return 0

    count = 0
    for p in root.rglob("*.md"):
        if p.is_file():
            ids = index_document_file(conn, p, repo=repo, ref=ref)
            count += len(ids)

    return count


def _decision_summary_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Build decision summary dictionary including explicit provenance verification flags."""
    prov_status = row["provenance_status"] if "provenance_status" in row.keys() else "unverified"
    is_synth = bool(row["is_synthetic"]) if "is_synthetic" in row.keys() else False
    blob_sha = row["blob_sha"] if "blob_sha" in row.keys() else None
    is_verified = (prov_status == "verified") and not is_synth and validate_git_sha(blob_sha)
    return {
        "decision_id": row["decision_id"],
        "title": row["title"],
        "status": row["status"],
        "motivation": row["motivation"],
        "consequences": row["consequences"],
        "valid_from_ref": row["valid_from_ref"],
        "valid_until_ref": row["valid_until_ref"],
        "path": row["path"],
        "blob_sha": blob_sha,
        "provenance_status": prov_status,
        "is_synthetic": is_synth,
        "verified": is_verified,
    }


def get_applicable_decisions_for_concept(
    conn: sqlite3.Connection,
    concept_id: str,
    verified_only: bool = False,
) -> list[dict[str, Any]]:
    """Retrieve decision records applicable to a specific concept."""
    decisions = []
    # Match by scope, concept_id prefix, or implementation file
    rows = conn.execute(
        """
        SELECT decision_id, title, status, motivation, consequences,
               valid_from_ref, valid_until_ref, source_repo, path,
               blob_sha, provenance_status, is_synthetic
        FROM decision_records
        WHERE scope = ?
           OR scope LIKE ?
           OR path LIKE ?
        ORDER BY decision_id
        """,
        (concept_id, f"{concept_id}%", f"%{concept_id.split('.')[-1]}%"),
    ).fetchall()

    for r in rows:
        item = _decision_summary_from_row(r)
        if verified_only and not item["verified"]:
            continue
        decisions.append(item)

    # Explicit known links
    if concept_id == "ui.tabs.pin_tab":
        app_shell_dec = conn.execute(
            "SELECT * FROM decision_records WHERE decision_id = 'DEC-APP-SHELL-01'"
        ).fetchone()
        if app_shell_dec and not any(d["decision_id"] == "DEC-APP-SHELL-01" for d in decisions):
            item = _decision_summary_from_row(app_shell_dec)
            if not verified_only or item["verified"]:
                decisions.append(item)
    elif concept_id == "ui.sidebar.pinned_entity":
        sidebar_dec = conn.execute(
            "SELECT * FROM decision_records WHERE decision_id = 'DEC-SIDEBAR-PROTOTIPO-01'"
        ).fetchone()
        if sidebar_dec and not any(d["decision_id"] == "DEC-SIDEBAR-PROTOTIPO-01" for d in decisions):
            item = _decision_summary_from_row(sidebar_dec)
            if not verified_only or item["verified"]:
                decisions.append(item)

    return decisions


def query_knowledge(
    conn: sqlite3.Connection,
    query_str: str,
    verified_only: bool = False,
) -> dict[str, Any]:
    """Query knowledge index with concept disambiguation and ADR retrieval.

    When an ambiguous query (e.g., 'fixar' or 'pin') matches multiple concepts
    flagged as ambiguous-with, returns candidate groups partitioned by concept_id.
    Provenance uncertainty is surfaced via `provenance_status`, `is_synthetic`, and `verified`.
    """
    raw_query = query_str.strip()
    norm_q = normalize_term(raw_query)

    # Check if query is an ADR or decision reference
    adr_norm = normalize_adr_id(raw_query)
    if adr_norm.startswith("ADR-") or adr_norm.startswith("DEC-"):
        row = conn.execute(
            """
            SELECT * FROM decision_records WHERE decision_id = ?
            """,
            (adr_norm,),
        ).fetchone()

        if row:
            investigated = json.loads(row["investigated_refs_json"]) if row["investigated_refs_json"] else None
            prov_status = row["provenance_status"] if "provenance_status" in row.keys() else "unverified"
            is_synth = bool(row["is_synthetic"]) if "is_synthetic" in row.keys() else False
            is_verified = (prov_status == "verified") and not is_synth and validate_git_sha(row["blob_sha"])
            if verified_only and not is_verified:
                return {
                    "query": raw_query,
                    "is_adr": True,
                    "is_ambiguous": False,
                    "verified_only": True,
                    "decision": None,
                }
            return {
                "query": raw_query,
                "is_adr": True,
                "is_ambiguous": False,
                "decision": {
                    "decision_id": row["decision_id"],
                    "title": row["title"],
                    "status": row["status"],
                    "motivation": row["motivation"],
                    "alternatives": json.loads(row["alternatives_json"]) if row["alternatives_json"] else [],
                    "consequences": row["consequences"],
                    "scope": row["scope"],
                    "valid_from_ref": row["valid_from_ref"],
                    "valid_until_ref": row["valid_until_ref"],
                    "supersedes_id": row["supersedes_id"],
                    "superseded_by_id": row["superseded_by_id"],
                    "source_repo": row["source_repo"],
                    "source_ref": row["source_ref"],
                    "commit_sha": row["commit_sha"],
                    "blob_sha": row["blob_sha"],
                    "path": row["path"],
                    "investigated_refs": investigated,
                    "provenance_status": prov_status,
                    "is_synthetic": is_synth,
                    "verified": is_verified,
                },
            }
        else:
            # Not found in indexed records: track as not-recovered
            unrec = record_not_recovered_adr(conn, adr_norm)
            if verified_only:
                return {
                    "query": raw_query,
                    "is_adr": True,
                    "is_ambiguous": False,
                    "verified_only": True,
                    "decision": None,
                }
            return {
                "query": raw_query,
                "is_adr": True,
                "is_ambiguous": False,
                "decision": {
                    "decision_id": unrec["decision_id"],
                    "title": unrec["title"],
                    "status": "not-recovered",
                    "motivation": unrec["motivation"],
                    "alternatives": [],
                    "consequences": None,
                    "scope": "unrecovered",
                    "valid_from_ref": None,
                    "valid_until_ref": None,
                    "supersedes_id": None,
                    "superseded_by_id": None,
                    "source_repo": unrec["source_repo"],
                    "source_ref": None,
                    "commit_sha": None,
                    "blob_sha": None,
                    "path": None,
                    "investigated_refs": unrec["investigated_refs"],
                    "provenance_status": "not-recovered",
                    "is_synthetic": False,
                    "verified": False,
                },
            }

    # Query glossary terms
    term_matches = conn.execute(
        """
        SELECT t.concept_id, t.term, t.language, t.relationship, t.related_concept_id,
               c.category, c.canonical_term_en, c.canonical_term_pt, c.description,
               c.implementation_file, c.implementation_sha,
               c.provenance_status, c.is_synthetic
        FROM glossary_terms t
        JOIN glossary_concepts c ON t.concept_id = c.concept_id
        ORDER BY t.concept_id, t.relationship
        """
    ).fetchall()

    # Find matching concepts with relationship scoring
    RELATIONSHIP_SCORES = {
        "same-as": 100,
        "alias": 80,
        "related": 50,
        "ambiguous-with": 40,
        "conflicts-with": 10,
    }

    matching_concepts: dict[str, dict[str, Any]] = {}

    for row in term_matches:
        prov_status = row["provenance_status"] if "provenance_status" in row.keys() else "unverified"
        is_synth = bool(row["is_synthetic"]) if "is_synthetic" in row.keys() else False
        is_verified = (prov_status == "verified") and not is_synth and validate_git_sha(row["implementation_sha"])
        if verified_only and not is_verified:
            continue

        t_norm = normalize_term(row["term"])
        cid = row["concept_id"]
        rel = row["relationship"]

        matched = False
        exact_term_match = False
        if t_norm == norm_q:
            matched = True
            exact_term_match = True
        elif norm_q in t_norm or t_norm in norm_q:
            # Check whole word containment
            q_words = set(norm_q.split())
            t_words = set(t_norm.split())
            if q_words == t_words or q_words.issubset(t_words):
                matched = True

        if matched:
            score = RELATIONSHIP_SCORES.get(rel, 20)
            if exact_term_match:
                score += 50

            if cid not in matching_concepts:
                matching_concepts[cid] = {
                    "concept_id": cid,
                    "category": row["category"],
                    "canonical_term_en": row["canonical_term_en"],
                    "canonical_term_pt": row["canonical_term_pt"],
                    "description": row["description"],
                    "implementation_file": row["implementation_file"],
                    "implementation_sha": row["implementation_sha"],
                    "provenance_status": prov_status,
                    "is_synthetic": is_synth,
                    "verified": is_verified,
                    "matched_terms": [],
                    "relationships": set(),
                    "conflicts_with_concepts": [],
                    "best_score": 0,
                    "has_ambiguous_rel": False,
                    "has_primary_match": False,
                }
            info = matching_concepts[cid]
            info["matched_terms"].append(row["term"])
            info["relationships"].add(rel)
            if score > info["best_score"]:
                info["best_score"] = score
            if rel in ("same-as", "alias"):
                info["has_primary_match"] = True
            if rel == "ambiguous-with":
                info["has_ambiguous_rel"] = True
            if rel == "conflicts-with" and row["related_concept_id"]:
                info["conflicts_with_concepts"].append(row["related_concept_id"])

    # If multiple concepts share the ambiguous-with relationship or multiple have primary matches
    ambiguous_concepts_count = sum(1 for info in matching_concepts.values() if info["has_ambiguous_rel"])
    primary_concepts_count = sum(1 for info in matching_concepts.values() if info["has_primary_match"])

    is_truly_ambiguous = (ambiguous_concepts_count >= 2) or (
        primary_concepts_count > 1 and len(norm_q.split()) == 1 and not any(
            info["canonical_term_en"].lower() == norm_q or info["canonical_term_pt"].lower() == norm_q
            for info in matching_concepts.values()
        )
    )

    if is_truly_ambiguous:
        # Ambiguous query: return candidate groups partitioned by concept_id
        candidate_groups = []
        for cid, info in sorted(matching_concepts.items(), key=lambda x: -x[1]["best_score"]):
            # Filter out pure conflicts-with matches from ambiguous candidate groups
            if not info["has_primary_match"] and not info["has_ambiguous_rel"]:
                continue
            decisions = get_applicable_decisions_for_concept(conn, cid, verified_only=verified_only)
            candidate_groups.append({
                "concept_id": cid,
                "category": info["category"],
                "canonical_term_en": info["canonical_term_en"],
                "canonical_term_pt": info["canonical_term_pt"],
                "description": info["description"],
                "implementation_file": info["implementation_file"],
                "implementation_sha": info["implementation_sha"],
                "provenance_status": info["provenance_status"],
                "is_synthetic": info["is_synthetic"],
                "verified": info["verified"],
                "matched_terms": sorted(set(info["matched_terms"])),
                "applicable_decisions": decisions,
            })

        return {
            "query": raw_query,
            "is_adr": False,
            "is_ambiguous": True,
            "disambiguation_guidance": (
                f"Query '{raw_query}' is ambiguous across {len(candidate_groups)} distinct concepts. "
                "Candidate groups are partitioned by concept_id to prevent blending UI and domain behaviors."
            ),
            "candidate_groups": candidate_groups,
        }

    elif matching_concepts:
        # Rank by best score
        sorted_concepts = sorted(matching_concepts.items(), key=lambda x: -x[1]["best_score"])
        cid, info = sorted_concepts[0]
        decisions = get_applicable_decisions_for_concept(conn, cid, verified_only=verified_only)
        primary_concept = {
            "concept_id": cid,
            "category": info["category"],
            "canonical_term_en": info["canonical_term_en"],
            "canonical_term_pt": info["canonical_term_pt"],
            "description": info["description"],
            "implementation_file": info["implementation_file"],
            "implementation_sha": info["implementation_sha"],
            "provenance_status": info["provenance_status"],
            "is_synthetic": info["is_synthetic"],
            "verified": info["verified"],
            "matched_terms": sorted(set(info["matched_terms"])),
            "conflicts_with": sorted(set(info["conflicts_with_concepts"])),
            "applicable_decisions": decisions,
        }
        return {
            "query": raw_query,
            "is_adr": False,
            "is_ambiguous": False,
            "concept": primary_concept,
            "candidate_groups": [primary_concept],
        }

    # If no exact glossary term matched, check FTS5 for decisions and concepts
    fts_rows = conn.execute(
        """
        SELECT entity_type, entity_id, title, content
        FROM knowledge_fts
        WHERE knowledge_fts MATCH ?
        LIMIT 10
        """,
        (raw_query.replace("-", " "),),
    ).fetchall()

    fts_results = []
    for r in fts_rows:
        prov_status = "unverified"
        is_synth = False
        is_verified = False
        if r["entity_type"] == "concept":
            c_row = conn.execute(
                "SELECT implementation_sha, provenance_status, is_synthetic FROM glossary_concepts WHERE concept_id = ?",
                (r["entity_id"],),
            ).fetchone()
            if c_row:
                prov_status = c_row["provenance_status"]
                is_synth = bool(c_row["is_synthetic"])
                is_verified = (prov_status == "verified") and not is_synth and validate_git_sha(c_row["implementation_sha"])
        elif r["entity_type"] == "decision":
            d_row = conn.execute(
                "SELECT blob_sha, provenance_status, is_synthetic FROM decision_records WHERE decision_id = ?",
                (r["entity_id"],),
            ).fetchone()
            if d_row:
                prov_status = d_row["provenance_status"]
                is_synth = bool(d_row["is_synthetic"])
                is_verified = (prov_status == "verified") and not is_synth and validate_git_sha(d_row["blob_sha"])

        if verified_only and not is_verified:
            continue

        fts_results.append({
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "title": r["title"],
            "snippet": r["content"][:200],
            "provenance_status": prov_status,
            "is_synthetic": is_synth,
            "verified": is_verified,
        })

    return {
        "query": raw_query,
        "is_adr": False,
        "is_ambiguous": False,
        "matches": fts_results,
    }


def get_adr(conn: sqlite3.Connection, adr_id: str, verified_only: bool = False) -> dict[str, Any]:
    """Retrieve an ADR by ID or return its not-recovered status."""
    res = query_knowledge(conn, adr_id, verified_only=verified_only)
    if res.get("is_adr") and res.get("decision") is not None:
        return res["decision"]
    return {}


def list_glossary(
    conn: sqlite3.Connection,
    filter_str: str | None = None,
    verified_only: bool = False,
) -> list[dict[str, Any]]:
    """List all canonical glossary concepts with terms and relationships."""
    concepts_out = []
    c_rows = conn.execute(
        "SELECT * FROM glossary_concepts ORDER BY category, concept_id"
    ).fetchall()

    for c in c_rows:
        cid = c["concept_id"]
        if filter_str and normalize_term(filter_str) not in normalize_term(cid + c["canonical_term_en"] + c["canonical_term_pt"]):
            continue

        prov_status = c["provenance_status"] if "provenance_status" in c.keys() else "unverified"
        is_synth = bool(c["is_synthetic"]) if "is_synthetic" in c.keys() else False
        is_verified = (prov_status == "verified") and not is_synth and validate_git_sha(c["implementation_sha"])
        if verified_only and not is_verified:
            continue

        terms_rows = conn.execute(
            """
            SELECT term, language, relationship, related_concept_id, provenance
            FROM glossary_terms
            WHERE concept_id = ?
            ORDER BY relationship, term
            """,
            (cid,),
        ).fetchall()

        terms_list = []
        for tr in terms_rows:
            terms_list.append({
                "term": tr["term"],
                "language": tr["language"],
                "relationship": tr["relationship"],
                "related_concept_id": tr["related_concept_id"],
                "provenance": tr["provenance"],
            })

        concepts_out.append({
            "concept_id": cid,
            "category": c["category"],
            "canonical_term_en": c["canonical_term_en"],
            "canonical_term_pt": c["canonical_term_pt"],
            "description": c["description"],
            "implementation_file": c["implementation_file"],
            "implementation_sha": c["implementation_sha"],
            "provenance_status": prov_status,
            "is_synthetic": is_synth,
            "verified": is_verified,
            "terms": terms_list,
        })

    return concepts_out


def get_knowledge_coverage(conn: sqlite3.Connection) -> dict[str, Any]:
    """Calculate knowledge coverage metrics, temporal validity ranges, and benchmark."""
    # Count decisions by status
    status_counts: dict[str, int] = {}
    for st in VALID_STATUSES:
        status_counts[st] = 0

    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM decision_records GROUP BY status"
    ).fetchall()
    for r in rows:
        status_counts[r["status"]] = r["cnt"]

    # Count provenance status across decisions and concepts
    dec_prov_counts: dict[str, int] = {st: 0 for st in VALID_PROVENANCE_STATUSES}
    for r in conn.execute("SELECT provenance_status, COUNT(*) as cnt FROM decision_records GROUP BY provenance_status").fetchall():
        dec_prov_counts[r["provenance_status"]] = r["cnt"]

    concept_prov_counts: dict[str, int] = {st: 0 for st in VALID_PROVENANCE_STATUSES}
    for r in conn.execute("SELECT provenance_status, COUNT(*) as cnt FROM glossary_concepts GROUP BY provenance_status").fetchall():
        concept_prov_counts[r["provenance_status"]] = r["cnt"]

    # Count total occurrences
    total_occurrences = conn.execute(
        "SELECT COUNT(*) FROM decision_occurrences"
    ).fetchone()[0]

    # Count concepts and terms
    concept_count = conn.execute(
        "SELECT COUNT(*) FROM glossary_concepts"
    ).fetchone()[0]

    term_count = conn.execute(
        "SELECT COUNT(*) FROM glossary_terms"
    ).fetchone()[0]

    # Count relationships
    rel_counts: dict[str, int] = {}
    rel_rows = conn.execute(
        "SELECT relationship, COUNT(*) as cnt FROM glossary_terms GROUP BY relationship"
    ).fetchall()
    for rr in rel_rows:
        rel_counts[rr["relationship"]] = rr["cnt"]

    # Benchmark disambiguation queries recall@1
    test_queries = [
        ("fixar uma aba", "ui.tabs.pin_tab"),
        ("pin tab", "ui.tabs.pin_tab"),
        ("fixados sidebar", "ui.sidebar.pinned_entity"),
        ("pinned sidebar entity", "ui.sidebar.pinned_entity"),
        ("fixar objeto", "domain.object.pin_type"),
        ("pin object type", "domain.object.pin_type"),
        ("favorites", "ui.favorites"),
        ("espaco", "domain.space"),
        ("workspace", "domain.workspace"),
        ("questao", "domain.question"),
        ("flashcard", "domain.flashcard"),
        ("simulado", "domain.simulado"),
        ("visualizacao em grafo", "ui.graph"),
        ("grafo de conhecimento", "domain.grafo"),
        ("espiar", "ui.sidebar.peek"),
        ("recolher", "ui.sidebar.collapse"),
    ]

    recall_hits = 0
    for query_text, expected_concept_id in test_queries:
        res = query_knowledge(conn, query_text)
        if res.get("concept") and res["concept"]["concept_id"] == expected_concept_id:
            recall_hits += 1
        elif res.get("candidate_groups"):
            top = res["candidate_groups"][0]["concept_id"]
            if top == expected_concept_id:
                recall_hits += 1

    recall_at_1 = recall_hits / len(test_queries) if test_queries else 1.0

    return {
        "decisions": {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
            "by_provenance_status": dec_prov_counts,
            "total_occurrences": total_occurrences,
        },
        "glossary": {
            "concepts_count": concept_count,
            "terms_count": term_count,
            "by_relationship": rel_counts,
            "by_provenance_status": concept_prov_counts,
        },
        "benchmark": {
            "queries_evaluated": len(test_queries),
            "recall_at_1": recall_at_1,
            "disambiguation_evaluated": True,
        },
    }


def build_cli() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Index and query architecture decision records (ADRs) and domain/UI glossaries."
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(DEFAULT_DB_PATH),
        help="Path to SQLite knowledge database (default: .cache/archive/knowledge.sqlite)",
    )
    parser.add_argument(
        "--extract-dir",
        type=str,
        help="Recursively extract and index ADRs and decision files from directory.",
    )
    parser.add_argument(
        "--index-file",
        type=str,
        help="Extract and index a single Markdown or decision document.",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Search ADRs or glossary concepts; returns candidate groups for ambiguous queries.",
    )
    parser.add_argument(
        "--glossary",
        nargs="?",
        const="",
        default=None,
        help="List glossary concepts and semantic relationships, optionally filtered by term.",
    )
    parser.add_argument(
        "--adr",
        nargs="?",
        const="",
        default=None,
        help="Retrieve a specific ADR by ID (e.g., ADR-0005, ADR2) or list all decisions.",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Show knowledge coverage, status distribution, and recall@1 benchmark metrics.",
    )
    parser.add_argument(
        "--verified-only",
        action="store_true",
        help="Return only records with verified git SHA provenance.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Format command output as JSON.",
    )
    return parser


def main() -> int:
    """CLI entry point for knowledge_indexer."""
    parser = build_cli()
    args = parser.parse_args()

    conn = open_knowledge_db(args.db)

    try:
        # Index file if requested
        if args.index_file:
            ids = index_document_file(conn, args.index_file)
            if args.json:
                print(json.dumps({"indexed_decisions": ids, "file": args.index_file}, indent=2))
            else:
                print(f"Indexed {len(ids)} decision(s) from {args.index_file}: {', '.join(ids) if ids else 'None'}")

        # Index directory if requested
        if args.extract_dir:
            cnt = index_directory(conn, args.extract_dir)
            if args.json:
                print(json.dumps({"indexed_count": cnt, "directory": args.extract_dir}, indent=2))
            else:
                print(f"Indexed {cnt} decision(s) from directory {args.extract_dir}")

        # Coverage report
        if args.coverage:
            cov = get_knowledge_coverage(conn)
            if args.json:
                print(json.dumps(cov, indent=2))
            else:
                print("Knowledge Coverage & Disambiguation Metrics:")
                print(f"  Total Decisions: {cov['decisions']['total']}")
                print(f"  Decisions By Status: {cov['decisions']['by_status']}")
                print(f"  Glossary Concepts: {cov['glossary']['concepts_count']}")
                print(f"  Glossary Terms: {cov['glossary']['terms_count']}")
                print(f"  Terms By Relationship: {cov['glossary']['by_relationship']}")
                print(f"  Benchmark Recall@1: {cov['benchmark']['recall_at_1']:.2%}")

        # Retrieve specific ADR or list decisions
        if args.adr is not None:
            if args.adr.strip():
                adr_record = get_adr(conn, args.adr.strip(), verified_only=args.verified_only)
                if args.json:
                    print(json.dumps(adr_record, indent=2))
                else:
                    if adr_record:
                        print(f"ADR: {adr_record['decision_id']} - {adr_record['title']}")
                        print(f"Status: {adr_record['status']} (provenance: {adr_record.get('provenance_status', 'unverified')})")
                        print(f"Motivation: {adr_record.get('motivation')}")
                        if adr_record.get("investigated_refs"):
                            print(f"Investigated Refs: {', '.join(adr_record['investigated_refs'])}")
                    else:
                        print(f"ADR {args.adr} not found.")
            else:
                if args.verified_only:
                    rows = conn.execute(
                        "SELECT decision_id, title, status, scope, valid_from_ref, provenance_status, is_synthetic FROM decision_records WHERE provenance_status = 'verified' AND is_synthetic = 0 ORDER BY decision_id"
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT decision_id, title, status, scope, valid_from_ref, provenance_status, is_synthetic FROM decision_records ORDER BY decision_id"
                    ).fetchall()
                adrs_list = [dict(r) for r in rows]
                if args.json:
                    print(json.dumps(adrs_list, indent=2))
                else:
                    print(f"Registered Decisions ({len(adrs_list)}):")
                    for a in adrs_list:
                        print(f"  [{a['status']} | {a['provenance_status']}] {a['decision_id']}: {a['title']}")

        # Retrieve glossary concepts
        if args.glossary is not None:
            gloss = list_glossary(
                conn,
                filter_str=args.glossary.strip() if args.glossary else None,
                verified_only=args.verified_only,
            )
            if args.json:
                print(json.dumps(gloss, indent=2))
            else:
                print(f"Glossary Concepts ({len(gloss)}):")
                for c in gloss:
                    print(
                        f"  * {c['concept_id']} ({c['category']}, provenance={c['provenance_status']}): "
                        f"{c['canonical_term_en']} / {c['canonical_term_pt']}"
                    )
                    for t in c["terms"]:
                        rel_info = f" -> {t['related_concept_id']}" if t['related_concept_id'] else ""
                        print(f"      - '{t['term']}' [{t['language']}, {t['relationship']}{rel_info}]")

        # Query knowledge
        if args.query:
            result = query_knowledge(conn, args.query.strip(), verified_only=args.verified_only)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if result.get("is_ambiguous"):
                    print(f"Ambiguous Query: '{args.query}'")
                    print(f"Guidance: {result.get('disambiguation_guidance')}")
                    print(f"Candidate Groups ({len(result.get('candidate_groups', []))}):")
                    for cg in result.get("candidate_groups", []):
                        print(f"  - {cg['concept_id']} ({cg['canonical_term_en']} / {cg['canonical_term_pt']}) [{cg.get('provenance_status')}]")
                        print(f"      Category: {cg['category']}")
                        print(f"      Implementation: {cg.get('implementation_file')}")
                        print(f"      Matched Terms: {', '.join(cg['matched_terms'])}")
                elif result.get("concept"):
                    c = result["concept"]
                    print(f"Concept: {c['concept_id']} ({c['canonical_term_en']} / {c['canonical_term_pt']}) [{c.get('provenance_status')}]")
                    print(f"Category: {c['category']}")
                    print(f"Implementation: {c.get('implementation_file')}")
                    print(f"Description: {c.get('description')}")
                    if c.get("applicable_decisions"):
                        print(f"Applicable Decisions ({len(c['applicable_decisions'])}):")
                        for d in c["applicable_decisions"]:
                            print(f"  - {d['decision_id']}: {d['title']} [{d['status']}]")
                elif result.get("is_adr"):
                    d = result["decision"]
                    if d:
                        print(f"ADR: {d['decision_id']} - {d['title']} [{d['status']} | {d.get('provenance_status')}]")
                        print(f"Motivation: {d.get('motivation')}")
                        if d.get("investigated_refs"):
                            print(f"Investigated Refs: {', '.join(d['investigated_refs'])}")
                    else:
                        print(f"ADR '{args.query}' has no verified record.")
                else:
                    print(f"Query: '{args.query}'")
                    matches = result.get("matches", [])
                    print(f"Matches found: {len(matches)}")
                    for m in matches:
                        print(f"  [{m['entity_type']}] {m['entity_id']}: {m['title']}")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
