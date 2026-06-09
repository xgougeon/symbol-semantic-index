from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .catalog import DEFAULT_CODEPOINTS_PATH, load_catalog
from .search import IconSearchIndex
from .selector import SelectionItem, select_icons


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="msi",
        description="Find meaningful Material Symbols for text, with set-aware semiotics.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search icons for one paragraph.")
    search_parser.add_argument("text")
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--catalog", default=str(DEFAULT_CODEPOINTS_PATH))
    search_parser.add_argument("--json", action="store_true")

    select_parser = subparsers.add_parser(
        "select", help="Choose a coherent icon set for one or more paragraphs."
    )
    select_parser.add_argument("texts", nargs="*")
    select_parser.add_argument("--items", help="JSON file with strings or {label,text} objects.")
    select_parser.add_argument("--catalog", default=str(DEFAULT_CODEPOINTS_PATH))
    select_parser.add_argument("--json", action="store_true")

    prompt_parser = subparsers.add_parser(
        "prompt", help="Emit an LLM rerank prompt for one or more paragraphs."
    )
    prompt_parser.add_argument("texts", nargs="*")
    prompt_parser.add_argument("--items", help="JSON file with strings or {label,text} objects.")
    prompt_parser.add_argument("--catalog", default=str(DEFAULT_CODEPOINTS_PATH))

    args = parser.parse_args(argv)
    if args.command == "search":
        return run_search(args)
    if args.command == "select":
        return run_select(args)
    if args.command == "prompt":
        return run_prompt(args)
    parser.error("Unknown command")
    return 2


def run_search(args: argparse.Namespace) -> int:
    icons = load_catalog(args.catalog)
    index = IconSearchIndex(icons)
    results = index.search(args.text, limit=args.limit)
    if args.json:
        print(json.dumps([search_result_to_json(result) for result in results], indent=2))
    else:
        for rank, result in enumerate(results, start=1):
            reasons = "; ".join(result.reasons)
            print(f"{rank:>2}. {result.icon.name}  score={result.score:.2f}  {reasons}")
    return 0


def run_select(args: argparse.Namespace) -> int:
    items = load_items(args.texts, args.items)
    selection = select_icons(items, catalog_path=args.catalog)
    if args.json:
        print(json.dumps(selection_to_json(selection), indent=2))
    else:
        print(selection.set_rationale)
        if selection.warnings:
            print("Warnings: " + "; ".join(selection.warnings))
        for choice in selection.choices:
            label = choice.item.label or "item"
            alternatives = ", ".join(alt.icon.name for alt in choice.alternatives)
            print(f"\n{label}: {choice.icon.name}  score={choice.score:.2f}")
            print(choice.rationale)
            print(choice.semiotic_relation)
            print(f"Alternatives: {alternatives}")
    return 0


def run_prompt(args: argparse.Namespace) -> int:
    items = load_items(args.texts, args.items)
    selection = select_icons(items, catalog_path=args.catalog, alternatives=8)
    print(build_llm_prompt(selection_to_json(selection)))
    return 0


def load_items(texts: list[str], items_path: str | None) -> list[SelectionItem]:
    if items_path:
        raw = json.loads(Path(items_path).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("--items must point to a JSON array")
        items: list[SelectionItem] = []
        for index, entry in enumerate(raw, start=1):
            if isinstance(entry, str):
                items.append(SelectionItem(text=entry, label=f"item_{index}"))
            elif isinstance(entry, dict) and isinstance(entry.get("text"), str):
                label = entry.get("label")
                items.append(
                    SelectionItem(
                        text=entry["text"],
                        label=label if isinstance(label, str) else f"item_{index}",
                    )
                )
            else:
                raise ValueError("Each --items entry must be a string or {label,text} object")
        return items
    if not texts:
        raise ValueError("Provide text arguments or --items")
    return [SelectionItem(text=text, label=f"item_{index}") for index, text in enumerate(texts, 1)]


def search_result_to_json(result: Any) -> dict[str, Any]:
    icon = result.icon
    return {
        "name": icon.name,
        "codepoint": icon.codepoint,
        "score": result.score,
        "reasons": list(result.reasons),
        "tokens": list(icon.tokens),
        "aliases": list(icon.aliases),
        "domains": list(icon.domains),
        "roles": list(icon.roles),
        "visual_family": icon.visual_family,
        "abstraction": icon.abstraction,
        "tone": list(icon.tone),
        "avoid_for": list(icon.avoid_for),
    }


def selection_to_json(selection: Any) -> dict[str, Any]:
    return {
        "set_rationale": selection.set_rationale,
        "warnings": list(selection.warnings),
        "choices": [
            {
                "label": choice.item.label,
                "text": choice.item.text,
                "icon": {
                    "name": choice.icon.name,
                    "codepoint": choice.icon.codepoint,
                    "domains": list(choice.icon.domains),
                    "roles": list(choice.icon.roles),
                    "visual_family": choice.icon.visual_family,
                    "abstraction": choice.icon.abstraction,
                },
                "score": choice.score,
                "rationale": choice.rationale,
                "semiotic_relation": choice.semiotic_relation,
                "analysis": {
                    "terms": list(choice.analysis.terms),
                    "domains": list(choice.analysis.domains),
                    "roles": list(choice.analysis.roles),
                    "preferred_abstraction": choice.analysis.preferred_abstraction,
                },
                "alternatives": [search_result_to_json(alt) for alt in choice.alternatives],
            }
            for choice in selection.choices
        ],
    }


def build_llm_prompt(payload: dict[str, Any]) -> str:
    return (
        "You are selecting Google Material Symbols for short text blocks.\n"
        "Choose icons as a coherent set, not independently. Evaluate denotation, "
        "connotation, abstraction level, visual family, and neighbor relations. "
        "Prefer precise but recognizable icons over generic metaphors.\n\n"
        "Use only icon names present in the candidates below. Return JSON with "
        "one chosen icon per item, rationale, rejected alternatives, and set-level "
        "semiotic notes.\n\n"
        + json.dumps(payload, indent=2)
    )


if __name__ == "__main__":
    raise SystemExit(main())

