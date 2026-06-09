from __future__ import annotations

from dataclasses import dataclass

from .catalog import IconRecord, load_catalog
from .search import IconSearchIndex, QueryAnalysis, SearchResult


@dataclass(frozen=True)
class SelectionItem:
    text: str
    label: str | None = None


@dataclass(frozen=True)
class IconChoice:
    item: SelectionItem
    icon: IconRecord
    score: float
    rationale: str
    alternatives: tuple[SearchResult, ...]
    analysis: QueryAnalysis
    semiotic_relation: str


@dataclass(frozen=True)
class IconSetSelection:
    choices: tuple[IconChoice, ...]
    set_rationale: str
    warnings: tuple[str, ...]


def select_icons(
    items: list[SelectionItem] | list[str],
    *,
    catalog_path: str | None = None,
    per_item_candidates: int = 36,
    alternatives: int = 4,
) -> IconSetSelection:
    normalized_items = normalize_items(items)
    icons = load_catalog(catalog_path)
    index = IconSearchIndex(icons)
    candidate_lists = [
        index.search(item.text, limit=per_item_candidates) for item in normalized_items
    ]
    analyses = [index.analyze(item.text) for item in normalized_items]
    selected_results = choose_coherent_set(candidate_lists, analyses)
    warnings = tuple(build_warnings(selected_results, candidate_lists))

    choices: list[IconChoice] = []
    for position, (item, result, candidates, analysis) in enumerate(
        zip(normalized_items, selected_results, candidate_lists, analyses, strict=True)
    ):
        choices.append(
            IconChoice(
                item=item,
                icon=result.icon,
                score=result.score,
                rationale=explain_choice(result, analysis),
                alternatives=tuple(
                    candidate
                    for candidate in candidates
                    if candidate.icon.name != result.icon.name
                )[:alternatives],
                analysis=analysis,
                semiotic_relation=explain_neighbor_relation(
                    position, selected_results, analyses
                ),
            )
        )

    return IconSetSelection(
        choices=tuple(choices),
        set_rationale=explain_set(selected_results, analyses),
        warnings=warnings,
    )


def normalize_items(items: list[SelectionItem] | list[str]) -> list[SelectionItem]:
    normalized: list[SelectionItem] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, SelectionItem):
            normalized.append(item)
        else:
            normalized.append(SelectionItem(text=item, label=f"item_{index}"))
    return normalized


def choose_coherent_set(
    candidate_lists: list[list[SearchResult]], analyses: list[QueryAnalysis]
) -> list[SearchResult]:
    if not candidate_lists:
        return []
    beam: list[tuple[float, list[SearchResult]]] = [(0.0, [])]
    beam_width = 72
    for position, candidates in enumerate(candidate_lists):
        if not candidates:
            raise ValueError(f"No icon candidates for item {position + 1}")
        next_beam: list[tuple[float, list[SearchResult]]] = []
        for beam_score, previous in beam:
            for candidate in candidates[:24]:
                coherence = set_coherence_delta(candidate, previous, position, analyses)
                next_beam.append((beam_score + candidate.score + coherence, previous + [candidate]))
        next_beam.sort(key=lambda entry: entry[0], reverse=True)
        beam = next_beam[:beam_width]
    return beam[0][1]


def set_coherence_delta(
    candidate: SearchResult,
    previous: list[SearchResult],
    position: int,
    analyses: list[QueryAnalysis],
) -> float:
    if not previous:
        return 0.0
    score = 0.0
    selected_names = {result.icon.name for result in previous}
    if candidate.icon.name in selected_names:
        score -= 100.0

    previous_icon = previous[-1].icon
    previous_analysis = analyses[position - 1]
    current_analysis = analyses[position]
    score += pairwise_coherence(candidate.icon, previous_icon, current_analysis, previous_analysis)

    target_abstraction = dominant_abstraction([result.icon for result in previous])
    if candidate.icon.abstraction == target_abstraction:
        score += 1.2
    elif candidate.icon.abstraction == "generic":
        score -= 1.4

    repeated_families = sum(
        1 for result in previous if result.icon.visual_family == candidate.icon.visual_family
    )
    if repeated_families >= 2 and candidate.icon.visual_family in {"symbol", "state"}:
        score -= 1.8
    return score


def pairwise_coherence(
    current: IconRecord,
    previous: IconRecord,
    current_analysis: QueryAnalysis,
    previous_analysis: QueryAnalysis,
) -> float:
    score = 0.0
    shared_domains = set(current.domains) & set(previous.domains)
    shared_roles = set(current.roles) & set(previous.roles)
    query_domain_overlap = set(current_analysis.domains) & set(previous_analysis.domains)

    if current.name == previous.name:
        return -100.0
    if current.tokens and previous.tokens and current.tokens[0] == previous.tokens[0]:
        score -= 4.2
    if shared_domains and query_domain_overlap:
        score += 1.2
    elif shared_domains and not query_domain_overlap:
        score -= 1.1
    if shared_roles and not set(current_analysis.roles) & set(previous_analysis.roles):
        score -= 1.0
    if current.abstraction == previous.abstraction:
        score += 0.9
    if current.visual_family == previous.visual_family and current.visual_family in {
        "concept",
        "process",
    }:
        score += 0.45
    return score


def dominant_abstraction(icons: list[IconRecord]) -> str:
    counts: dict[str, int] = {}
    for icon in icons:
        counts[icon.abstraction] = counts.get(icon.abstraction, 0) + 1
    return max(counts, key=counts.get)


def explain_choice(result: SearchResult, analysis: QueryAnalysis) -> str:
    icon = result.icon
    reason = "; ".join(result.reasons[:3])
    domains = ", ".join(icon.domains[:3]) or "general"
    roles = ", ".join(icon.roles[:3]) or icon.visual_family
    return (
        f"`{icon.name}` is a {icon.abstraction} {icon.visual_family} symbol. "
        f"It fits {domains} and reads as {roles}. Evidence: {reason}."
    )


def explain_neighbor_relation(
    position: int, selected: list[SearchResult], analyses: list[QueryAnalysis]
) -> str:
    current = selected[position].icon
    pieces: list[str] = []
    if position > 0:
        previous = selected[position - 1].icon
        pieces.append(relation_sentence("previous", current, previous))
    if position + 1 < len(selected):
        following = selected[position + 1].icon
        pieces.append(relation_sentence("next", current, following))
    if not pieces:
        return "Standalone choice; no neighbor constraints were needed."
    return " ".join(pieces)


def relation_sentence(direction: str, current: IconRecord, other: IconRecord) -> str:
    shared_domains = sorted(set(current.domains) & set(other.domains))
    if shared_domains:
        return (
            f"Relative to the {direction} icon `{other.name}`, it keeps continuity "
            f"through {', '.join(shared_domains[:2])} while using a distinct "
            f"{current.visual_family} form."
        )
    return (
        f"Relative to the {direction} icon `{other.name}`, it separates the concept "
        f"visually by switching to a {current.visual_family} form."
    )


def explain_set(selected: list[SearchResult], analyses: list[QueryAnalysis]) -> str:
    if not selected:
        return "No icons selected."
    abstractions = {result.icon.abstraction for result in selected}
    families = [result.icon.visual_family for result in selected]
    domains = sorted({domain for result in selected for domain in result.icon.domains})
    family_summary = ", ".join(dict.fromkeys(families))
    if len(abstractions) == 1:
        abstraction_summary = f"a consistent {next(iter(abstractions))} abstraction level"
    else:
        abstraction_summary = "a controlled mix of abstraction levels"
    return (
        f"The set uses {abstraction_summary}, with visual roles spanning "
        f"{family_summary}. Shared semantic ground: {', '.join(domains[:6]) or 'general concepts'}."
    )


def build_warnings(
    selected: list[SearchResult], candidate_lists: list[list[SearchResult]]
) -> list[str]:
    warnings: list[str] = []
    names = [result.icon.name for result in selected]
    if len(names) != len(set(names)):
        warnings.append("Duplicate icon names remain in the set.")
    if any(not candidates for candidates in candidate_lists):
        warnings.append("At least one item had no candidates.")
    generic_count = sum(1 for result in selected if result.icon.abstraction == "generic")
    if generic_count > max(1, len(selected) // 2):
        warnings.append("The set leans generic; consider an LLM rerank with stronger context.")
    return warnings

