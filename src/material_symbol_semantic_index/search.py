from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math

from .catalog import IconRecord
from .semantics import (
    DOMAIN_BY_TOKEN,
    ROLE_BY_TOKEN,
    TOKEN_ALIASES,
    expand_query_terms,
    infer_domains,
    infer_roles,
    tokenize_text,
)


@dataclass(frozen=True)
class QueryAnalysis:
    text: str
    terms: tuple[str, ...]
    domains: tuple[str, ...]
    roles: tuple[str, ...]
    preferred_abstraction: str


@dataclass(frozen=True)
class SearchResult:
    icon: IconRecord
    score: float
    reasons: tuple[str, ...]


class IconSearchIndex:
    """A deterministic semantic search index for sparse Material Symbol names."""

    def __init__(self, icons: list[IconRecord]):
        self.icons = icons
        self._documents: list[Counter[str]] = [
            Counter(tokenize_text(icon.search_text)) for icon in icons
        ]
        self._doc_freq: Counter[str] = Counter()
        for document in self._documents:
            self._doc_freq.update(document.keys())
        self._avg_doc_len = sum(sum(doc.values()) for doc in self._documents) / max(
            1, len(self._documents)
        )
        self._by_term: dict[str, list[int]] = defaultdict(list)
        for index, document in enumerate(self._documents):
            for term in document:
                self._by_term[term].append(index)

    def analyze(self, text: str) -> QueryAnalysis:
        terms = expand_query_terms(text)
        domains = infer_domains(terms)
        roles = infer_query_roles(text, terms)
        preferred_abstraction = infer_query_abstraction(roles, domains)
        return QueryAnalysis(
            text=text,
            terms=tuple(terms),
            domains=tuple(domains),
            roles=tuple(roles),
            preferred_abstraction=preferred_abstraction,
        )

    def search(self, text: str, limit: int = 24) -> list[SearchResult]:
        analysis = self.analyze(text)
        candidate_ids = self._candidate_ids(analysis.terms)
        scored = [self._score_icon(icon_id, analysis) for icon_id in candidate_ids]
        scored = [result for result in scored if result.score > 0]
        scored.sort(key=lambda result: result.score, reverse=True)
        return scored[:limit]

    def _candidate_ids(self, terms: tuple[str, ...]) -> set[int]:
        ids: set[int] = set()
        for term in terms:
            ids.update(self._by_term.get(term, ()))
        if not ids:
            return set(range(len(self.icons)))
        return ids

    def _score_icon(self, icon_id: int, analysis: QueryAnalysis) -> SearchResult:
        icon = self.icons[icon_id]
        document = self._documents[icon_id]
        bm25 = self._bm25(document, analysis.terms)
        reasons: list[str] = []

        exact_tokens = set(analysis.terms) & set(icon.tokens)
        alias_hits = set(analysis.terms) & set(icon.aliases)
        domain_hits = set(analysis.domains) & set(icon.domains)
        role_hits = set(analysis.roles) & set(icon.roles)

        score = bm25
        if exact_tokens:
            score += 3.2 * len(exact_tokens)
            reasons.append("literal tokens: " + ", ".join(sorted(exact_tokens)[:4]))
        if alias_hits:
            score += 1.4 * len(alias_hits)
            reasons.append("semantic aliases: " + ", ".join(sorted(alias_hits)[:4]))
        if domain_hits:
            score += 2.1 * len(domain_hits)
            reasons.append("domain fit: " + ", ".join(sorted(domain_hits)[:4]))
        if role_hits:
            score += 1.8 * len(role_hits)
            reasons.append("role fit: " + ", ".join(sorted(role_hits)[:4]))
        if icon.abstraction == analysis.preferred_abstraction:
            score += 1.1
            reasons.append(f"{icon.abstraction} abstraction")
        score += recognizability_bonus(icon)
        score -= generic_penalty(icon, analysis)
        score -= secondary_token_penalty(icon, analysis)

        if not reasons:
            reasons.append("lexical and semantic proximity")
        return SearchResult(icon=icon, score=round(score, 4), reasons=tuple(reasons))

    def _bm25(self, document: Counter[str], terms: tuple[str, ...]) -> float:
        k1 = 1.45
        b = 0.72
        doc_len = sum(document.values())
        score = 0.0
        for term in terms:
            freq = document.get(term, 0)
            if not freq:
                continue
            df = self._doc_freq.get(term, 0)
            idf = math.log(1 + (len(self.icons) - df + 0.5) / (df + 0.5))
            denom = freq + k1 * (1 - b + b * doc_len / self._avg_doc_len)
            score += idf * (freq * (k1 + 1) / denom)
        return score


def infer_query_roles(text: str, terms: list[str]) -> list[str]:
    normalized = " ".join(tokenize_text(text))
    roles: list[str] = []
    cue_groups: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("problem", ("risk", "issue", "friction", "bottleneck", "blocker", "error", "fail")),
        ("process", ("workflow", "process", "operate", "orchestrate", "automate", "integrate")),
        ("outcome", ("increase", "improve", "accelerate", "enable", "result", "value", "growth")),
        ("insight", ("insight", "understand", "analyze", "discover", "measure", "learn")),
        ("constraint", ("govern", "policy", "rule", "compliance", "privacy", "security")),
        ("actor", ("team", "user", "customer", "employee", "people", "stakeholder")),
        ("structure", ("model", "schema", "taxonomy", "layer", "hierarchy", "catalog")),
    )
    term_set = set(terms)
    for role, cues in cue_groups:
        if any(cue in normalized or cue in term_set for cue in cues):
            roles.append(role)
    if not roles:
        roles.append("concept")
    return roles


def infer_query_abstraction(roles: list[str], domains: list[str]) -> str:
    if any(role in roles for role in ("structure", "constraint", "insight")):
        return "conceptual"
    if any(role in roles for role in ("process", "outcome")):
        return "conceptual"
    if any(role in roles for role in ("actor",)):
        return "concrete"
    if any(domain in domains for domain in ("data", "ai", "governance", "trust")):
        return "conceptual"
    return "generic"


def recognizability_bonus(icon: IconRecord) -> float:
    token_count = len(icon.tokens)
    if token_count == 1:
        return 0.9
    if token_count == 2:
        return 0.65
    if token_count == 3:
        return 0.25
    return -0.15


def generic_penalty(icon: IconRecord, analysis: QueryAnalysis) -> float:
    generic_names = {"add", "check", "done", "star", "home", "info", "circle", "menu"}
    if icon.name in generic_names and icon.name not in analysis.terms:
        return 2.8
    if icon.name.endswith("_alt") and icon.name.removesuffix("_alt") not in analysis.terms:
        return 0.35
    return 0.0


def secondary_token_penalty(icon: IconRecord, analysis: QueryAnalysis) -> float:
    if len(icon.tokens) <= 1:
        return 0.0
    query_terms = set(analysis.terms)
    query_domains = set(analysis.domains)
    query_roles = set(analysis.roles)
    unmatched = 0
    for token in icon.tokens:
        if token in query_terms:
            continue
        aliases = set(TOKEN_ALIASES.get(token, ()))
        domains = set(DOMAIN_BY_TOKEN.get(token, ()))
        roles = set(ROLE_BY_TOKEN.get(token, ()))
        if aliases & query_terms or domains & query_domains or roles & query_roles:
            continue
        unmatched += 1
    return 3.25 * unmatched
