from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any


DEFAULT_VISUAL_METADATA_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "icon_visual_metadata.jsonl"
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "so",
    "the",
    "to",
    "with",
}

ALIASES = {
    "ai": ("agent", "automation", "machine reasoning", "artificial intelligence"),
    "automate": ("automation", "workflow", "process", "agent"),
    "catalog": ("inventory", "repository", "collection", "dictionary"),
    "context": ("knowledge", "reference", "meaning", "metadata"),
    "data": ("dataset", "database", "catalog", "records"),
    "glossary": ("vocabulary", "definition", "business term", "knowledge"),
    "govern": ("governance", "policy", "rule", "control"),
    "governance": ("policy", "rule", "control", "stewardship"),
    "governed": ("governance", "govern", "policy", "trusted"),
    "insight": ("analysis", "discover", "measure", "learn"),
    "insights": ("insight", "analysis", "discover", "measure", "learn"),
    "issues": ("issue", "risk", "quality", "problem"),
    "lineage": ("relationship", "dependency", "flow", "link"),
    "policy": ("rule", "constraint", "compliance", "governance"),
    "product": ("asset", "object", "catalog", "data product"),
    "products": ("product", "asset", "object", "catalog"),
    "quality": ("valid", "validated", "score", "check"),
    "reuse": ("share", "repurpose", "copy", "reference"),
    "security": ("privacy", "protection", "shield", "access"),
    "team": ("people", "group", "organization", "actor"),
    "teams": ("team", "people", "group", "organization"),
    "trust": ("trusted", "verified", "approved", "quality"),
    "trusted": ("trust", "validated", "verified", "approved"),
    "truth": ("source", "reference", "trusted", "validated"),
    "workflow": ("process", "automation", "orchestration", "sequence"),
    "workflows": ("workflow", "process", "automation", "orchestration"),
}


@dataclass(frozen=True)
class VisualIconRecord:
    unique_name: str
    name: str
    source_path: str
    style: str
    source_collection: str
    category: str
    duplicate_of: str | None
    name_quality: str
    curation_status: str
    search_terms: tuple[str, ...]
    semantic_domains: tuple[str, ...]
    semiotic_roles: tuple[str, ...]
    best_for: tuple[str, ...]
    avoid_for: tuple[str, ...]
    connotations: tuple[str, ...]
    denotation: tuple[str, ...]
    possible_misreadings: tuple[str, ...]
    visual_elements: tuple[str, ...]
    visual_weight: str

    @property
    def document_text(self) -> str:
        parts = [
            self.unique_name,
            self.name,
            self.style,
            self.source_collection,
            self.category,
            self.name_quality,
            self.curation_status,
            " ".join(self.search_terms),
            " ".join(self.semantic_domains),
            " ".join(self.semiotic_roles),
            " ".join(self.best_for),
            " ".join(self.connotations),
            " ".join(self.denotation),
            " ".join(self.visual_elements),
            self.visual_weight,
        ]
        return " ".join(part for part in parts if part)


@dataclass(frozen=True)
class VisualSelectionItem:
    text: str
    label: str | None = None
    context: str = ""
    avoid: tuple[str, ...] = ()
    required_style: str | None = None

    @property
    def query_text(self) -> str:
        label = self.label or ""
        if re.fullmatch(r"item_[0-9]+", label):
            label = ""
        return " ".join(part for part in (label, self.text, self.context) if part)


@dataclass(frozen=True)
class VisualIconCandidate:
    icon: VisualIconRecord
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class VisualIconChoice:
    item: VisualSelectionItem
    icon: VisualIconRecord
    score: float
    rationale: str
    alternatives: tuple[VisualIconCandidate, ...]


@dataclass(frozen=True)
class VisualIconSelection:
    choices: tuple[VisualIconChoice, ...]
    warnings: tuple[str, ...]
    metadata_path: str
    metadata_sha256: str
    repo_commit: str | None
    prefer_style: str
    allow_material_fallback: bool


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if token not in STOPWORDS]


def expanded_query_terms(text: str) -> tuple[str, ...]:
    terms = tokenize(text)
    expanded: list[str] = []
    for term in terms:
        expanded.append(term)
        expanded.extend(tokenize(" ".join(ALIASES.get(term, ()))))
    return tuple(dict.fromkeys(expanded))


def as_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value if item is not None)
    if isinstance(value, str) and value:
        return (value,)
    return ()


def load_visual_metadata(path: str | Path | None = None) -> list[VisualIconRecord]:
    metadata_path = Path(path) if path else DEFAULT_VISUAL_METADATA_PATH
    records: list[VisualIconRecord] = []
    with metadata_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            metrics = raw.get("pixel_metrics") or {}
            records.append(
                VisualIconRecord(
                    unique_name=str(raw.get("unique_name") or raw.get("name")),
                    name=str(raw.get("name") or raw.get("unique_name")),
                    source_path=str(raw.get("source_path") or ""),
                    style=str(raw.get("style") or ""),
                    source_collection=str(raw.get("source_collection") or ""),
                    category=str(raw.get("category") or ""),
                    duplicate_of=raw.get("duplicate_of"),
                    name_quality=str(raw.get("name_quality") or ""),
                    curation_status=str(raw.get("curation_status") or ""),
                    search_terms=as_tuple(raw.get("search_terms")),
                    semantic_domains=as_tuple(raw.get("semantic_domains")),
                    semiotic_roles=as_tuple(raw.get("semiotic_roles")),
                    best_for=as_tuple(raw.get("best_for")),
                    avoid_for=as_tuple(raw.get("avoid_for")),
                    connotations=as_tuple(raw.get("connotations")),
                    denotation=as_tuple(raw.get("denotation")),
                    possible_misreadings=as_tuple(raw.get("possible_misreadings")),
                    visual_elements=as_tuple(raw.get("visual_elements")),
                    visual_weight=str(metrics.get("visual_weight") or ""),
                )
            )
    return records


class VisualMetadataSearchIndex:
    def __init__(self, icons: list[VisualIconRecord]):
        self.icons = icons
        self.documents = [Counter(tokenize(icon.document_text)) for icon in icons]
        self.doc_freq: Counter[str] = Counter()
        for document in self.documents:
            self.doc_freq.update(document.keys())
        self.avg_len = sum(sum(document.values()) for document in self.documents) / max(
            1, len(self.documents)
        )

    def search(
        self,
        item: VisualSelectionItem,
        *,
        limit: int = 24,
        prefer_style: str = "datagalaxy",
        allow_material_fallback: bool = False,
    ) -> list[VisualIconCandidate]:
        terms = expanded_query_terms(item.query_text)
        candidates: list[VisualIconCandidate] = []
        for icon, document in zip(self.icons, self.documents, strict=True):
            if not allow_material_fallback and icon.style != prefer_style:
                continue
            candidate = self.score_icon(icon, document, terms, item, prefer_style)
            if candidate.score > 0:
                candidates.append(candidate)
        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates[:limit]

    def score_icon(
        self,
        icon: VisualIconRecord,
        document: Counter[str],
        terms: tuple[str, ...],
        item: VisualSelectionItem,
        prefer_style: str,
    ) -> VisualIconCandidate:
        term_set = set(terms)
        score = bm25(document, terms, self.doc_freq, len(self.icons), self.avg_len)
        reasons: list[str] = []

        icon_terms = set(tokenize(" ".join(icon.search_terms)))
        icon_domains = set(tokenize(" ".join(icon.semantic_domains)))
        icon_roles = set(tokenize(" ".join(icon.semiotic_roles)))
        icon_best = set(tokenize(" ".join(icon.best_for + icon.connotations)))
        icon_name_terms = set(tokenize(icon.name.replace("_", " ")))

        literal = term_set & icon_name_terms
        term_hits = term_set & icon_terms
        domain_hits = term_set & icon_domains
        role_hits = term_set & icon_roles
        best_hits = term_set & icon_best

        if literal:
            score += 5.0 * len(literal)
            reasons.append("literal name: " + ", ".join(sorted(literal)[:4]))
        if term_hits:
            score += 2.8 * len(term_hits)
            reasons.append("search terms: " + ", ".join(sorted(term_hits)[:4]))
        if domain_hits:
            score += 2.2 * len(domain_hits)
            reasons.append("domain fit: " + ", ".join(sorted(domain_hits)[:4]))
        if role_hits:
            score += 2.8 * len(role_hits)
            reasons.append("role fit: " + ", ".join(sorted(role_hits)[:4]))
        if best_hits:
            score += 1.2 * len(best_hits)

        for phrase in icon.search_terms + icon.best_for + icon.connotations:
            normalized = phrase.lower()
            if len(normalized) > 4 and normalized in item.query_text.lower():
                score += 2.5
                reasons.append(f"phrase: {phrase}")
                break

        if icon.style == prefer_style:
            score += 5.0
            reasons.append(f"preferred style: {prefer_style}")
        elif icon.style == "datagalaxy":
            score += 3.5
        elif item.required_style and icon.style != item.required_style:
            score -= 8.0

        avoid_text = " ".join(item.avoid).lower()
        icon_avoid_text = " ".join(icon.avoid_for + icon.possible_misreadings).lower()
        if avoid_text:
            avoid_terms = set(tokenize(avoid_text))
            if avoid_terms & (icon_terms | icon_domains | icon_roles | icon_best):
                score -= 8.0
                reasons.append("user avoid overlap")
        if icon_avoid_text:
            avoid_overlap = term_set & set(tokenize(icon_avoid_text))
            if avoid_overlap:
                score -= 2.5 * len(avoid_overlap)
                reasons.append("metadata avoid overlap: " + ", ".join(sorted(avoid_overlap)[:3]))

        if icon.duplicate_of:
            score -= 7.0
        if icon.name_quality.startswith("weak"):
            score -= 2.0
        if icon.curation_status == "needs_human_review":
            score -= 1.5
        if icon.visual_weight == "heavy":
            score += 0.4

        if not reasons:
            reasons.append("semantic proximity")
        return VisualIconCandidate(
            icon=icon,
            score=round(score, 4),
            reasons=tuple(dict.fromkeys(reasons)),
        )


def bm25(
    document: Counter[str],
    terms: tuple[str, ...],
    doc_freq: Counter[str],
    doc_count: int,
    avg_doc_len: float,
) -> float:
    score = 0.0
    k1 = 1.45
    b = 0.72
    doc_len = sum(document.values())
    for term in terms:
        freq = document.get(term, 0)
        if not freq:
            continue
        df = doc_freq.get(term, 0)
        idf = math.log(1 + (doc_count - df + 0.5) / (df + 0.5))
        denom = freq + k1 * (1 - b + b * doc_len / max(1, avg_doc_len))
        score += idf * (freq * (k1 + 1) / denom)
    return score


def normalize_visual_items(
    items: list[VisualSelectionItem] | list[str] | list[dict[str, Any]],
) -> list[VisualSelectionItem]:
    normalized: list[VisualSelectionItem] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, VisualSelectionItem):
            normalized.append(item)
        elif isinstance(item, str):
            normalized.append(VisualSelectionItem(text=item, label=f"item_{index}"))
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            avoid_raw = item.get("avoid") or []
            if isinstance(avoid_raw, str):
                avoid = (avoid_raw,)
            elif isinstance(avoid_raw, list):
                avoid = tuple(str(value) for value in avoid_raw)
            else:
                avoid = ()
            normalized.append(
                VisualSelectionItem(
                    text=item["text"],
                    label=str(item.get("label") or f"item_{index}"),
                    context=str(item.get("context") or ""),
                    avoid=avoid,
                    required_style=item.get("required_style"),
                )
            )
        else:
            raise ValueError("items must be strings, VisualSelectionItems, or {label,text} objects")
    return normalized


def choose_coherent_visual_set(
    candidate_lists: list[list[VisualIconCandidate]],
) -> list[VisualIconCandidate]:
    selected: list[VisualIconCandidate] = []
    used_names: set[str] = set()
    used_categories: Counter[str] = Counter()

    for candidates in candidate_lists:
        best: VisualIconCandidate | None = None
        best_score = -10**9
        for candidate in candidates[:24]:
            adjusted = candidate.score
            if candidate.icon.unique_name in used_names:
                adjusted -= 100.0
            if candidate.icon.category and used_categories[candidate.icon.category] >= 2:
                adjusted -= 1.3
            if selected and candidate.icon.style != selected[-1].icon.style:
                adjusted -= 0.25
            if adjusted > best_score:
                best = candidate
                best_score = adjusted
        if best is None:
            raise ValueError("no candidate available for one item")
        selected.append(best)
        used_names.add(best.icon.unique_name)
        used_categories[best.icon.category] += 1
    return selected


def select_visual_icons(
    items: list[VisualSelectionItem] | list[str] | list[dict[str, Any]],
    *,
    metadata_path: str | Path | None = None,
    prefer_style: str = "datagalaxy",
    allow_material_fallback: bool = False,
    per_item_candidates: int = 36,
    alternatives: int = 4,
    repo_root: str | Path | None = None,
) -> VisualIconSelection:
    normalized_items = normalize_visual_items(items)
    metadata = Path(metadata_path) if metadata_path else DEFAULT_VISUAL_METADATA_PATH
    icons = load_visual_metadata(metadata)
    index = VisualMetadataSearchIndex(icons)
    candidate_lists = [
        index.search(
            item,
            limit=per_item_candidates,
            prefer_style=prefer_style,
            allow_material_fallback=allow_material_fallback,
        )
        for item in normalized_items
    ]
    selected = choose_coherent_visual_set(candidate_lists)

    choices: list[VisualIconChoice] = []
    warnings: list[str] = []
    for item, choice, candidates in zip(normalized_items, selected, candidate_lists, strict=True):
        if choice.icon.style != prefer_style:
            warnings.append(f"{item.label or item.text}: selected {choice.icon.style}, not {prefer_style}")
        choices.append(
            VisualIconChoice(
                item=item,
                icon=choice.icon,
                score=choice.score,
                rationale="; ".join(choice.reasons[:4]),
                alternatives=tuple(
                    candidate
                    for candidate in candidates
                    if candidate.icon.unique_name != choice.icon.unique_name
                )[:alternatives],
            )
        )

    return VisualIconSelection(
        choices=tuple(choices),
        warnings=tuple(warnings),
        metadata_path=str(metadata),
        metadata_sha256=sha256_file(metadata),
        repo_commit=git_commit(Path(repo_root) if repo_root else metadata.parents[1]),
        prefer_style=prefer_style,
        allow_material_fallback=allow_material_fallback,
    )


def icon_to_json(icon: VisualIconRecord, repo_root: str | Path | None = None) -> dict[str, Any]:
    asset_path = icon.source_path
    if repo_root and asset_path:
        asset_path = str((Path(repo_root) / asset_path).resolve())
    return {
        "icon_id": icon.unique_name,
        "name": icon.name,
        "style": icon.style,
        "source_collection": icon.source_collection,
        "asset_ref": asset_path,
        "source_path": icon.source_path,
        "semantic_domains": list(icon.semantic_domains),
        "semiotic_roles": list(icon.semiotic_roles),
        "visual_weight": icon.visual_weight,
    }


def selection_to_json(
    selection: VisualIconSelection,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "visual-icon-selection-v1",
        "metadata_path": selection.metadata_path,
        "metadata_sha256": selection.metadata_sha256,
        "repo_commit": selection.repo_commit,
        "prefer_style": selection.prefer_style,
        "allow_material_fallback": selection.allow_material_fallback,
        "choices": [
            {
                "label": choice.item.label,
                "text": choice.item.text,
                "icon": icon_to_json(choice.icon, repo_root),
                "score": choice.score,
                "rationale": choice.rationale,
                "alternatives": [
                    {
                        **icon_to_json(candidate.icon, repo_root),
                        "score": candidate.score,
                        "reasons": list(candidate.reasons),
                    }
                    for candidate in choice.alternatives
                ],
            }
            for choice in selection.choices
        ],
        "warnings": list(selection.warnings),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(repo_root: Path | None) -> str | None:
    if not repo_root or not (repo_root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()
