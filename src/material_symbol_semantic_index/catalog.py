from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .semantics import enrich_icon_name

DEFAULT_CODEPOINTS_PATH = (
    Path(__file__).resolve().parent / "data" / "material_symbols_outlined.codepoints"
)


@dataclass(frozen=True)
class IconRecord:
    """A Material Symbol plus inferred semantics used by the retriever."""

    name: str
    codepoint: str
    tokens: tuple[str, ...]
    aliases: tuple[str, ...]
    domains: tuple[str, ...]
    roles: tuple[str, ...]
    visual_family: str
    abstraction: str
    tone: tuple[str, ...]
    best_for: tuple[str, ...]
    avoid_for: tuple[str, ...]

    @property
    def search_text(self) -> str:
        parts: list[str] = [
            self.name.replace("_", " "),
            " ".join(self.tokens),
            " ".join(self.aliases),
            " ".join(self.domains),
            " ".join(self.roles),
            self.visual_family,
            self.abstraction,
            " ".join(self.tone),
            " ".join(self.best_for),
            " ".join(self.avoid_for),
        ]
        return " ".join(part for part in parts if part)


def parse_codepoints(lines: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        pieces = line.split()
        if len(pieces) != 2:
            raise ValueError(f"Invalid codepoint line: {raw_line!r}")
        name, codepoint = pieces
        pairs.append((name, codepoint))
    return pairs


def load_catalog(path: str | Path | None = None) -> list[IconRecord]:
    codepoints_path = Path(path) if path else DEFAULT_CODEPOINTS_PATH
    lines = codepoints_path.read_text(encoding="utf-8").splitlines()
    records: list[IconRecord] = []
    for name, codepoint in parse_codepoints(lines):
        semantics = enrich_icon_name(name)
        records.append(
            IconRecord(
                name=name,
                codepoint=codepoint,
                tokens=tuple(semantics.tokens),
                aliases=tuple(semantics.aliases),
                domains=tuple(semantics.domains),
                roles=tuple(semantics.roles),
                visual_family=semantics.visual_family,
                abstraction=semantics.abstraction,
                tone=tuple(semantics.tone),
                best_for=tuple(semantics.best_for),
                avoid_for=tuple(semantics.avoid_for),
            )
        )
    return records
