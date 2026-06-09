from __future__ import annotations

import argparse
import json
import re
import struct
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "icon_png_manifest.json"
DEFAULT_OUTPUT = ROOT / "data" / "icon_visual_metadata.json"
DEFAULT_JSONL = ROOT / "data" / "icon_visual_metadata.jsonl"

TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


@dataclass(frozen=True)
class PixelMetrics:
    canvas_width: int
    canvas_height: int
    bbox: dict[str, int] | None
    ink_coverage: float
    bbox_coverage: float
    bbox_aspect_ratio: float | None
    center_of_mass: dict[str, float] | None
    horizontal_symmetry: float
    vertical_symmetry: float
    edge_complexity: float
    visual_weight: str
    dominant_orientation: str


TOKEN_METADATA: dict[str, dict[str, list[str]]] = {
    "access": {"domains": ["accessibility", "permission"], "connotations": ["entry", "permission", "availability"], "roles": ["access"]},
    "accessibility": {"domains": ["accessibility", "inclusion"], "connotations": ["universal access", "human-centered design", "assistive support"], "roles": ["actor"]},
    "accessible": {"domains": ["accessibility", "mobility"], "connotations": ["inclusive access", "assistive mobility", "barrier-free movement"], "roles": ["actor"]},
    "account": {"domains": ["identity", "people"], "connotations": ["user identity", "profile", "ownership"], "roles": ["actor"]},
    "ai": {"domains": ["artificial intelligence"], "connotations": ["automation", "assistance", "machine reasoning"], "roles": ["agent"]},
    "alert": {"domains": ["status", "risk"], "connotations": ["attention", "warning", "urgency"], "roles": ["signal"]},
    "analytics": {"domains": ["data", "insight"], "connotations": ["measurement", "analysis", "performance"], "roles": ["insight"]},
    "api": {"domains": ["technology", "integration"], "connotations": ["connection", "interface", "system integration"], "roles": ["interface"]},
    "arrow": {"domains": ["navigation", "direction"], "connotations": ["movement", "transition", "flow"], "roles": ["direction"]},
    "asset": {"domains": ["data", "inventory"], "connotations": ["resource", "managed object", "catalog item"], "roles": ["object"]},
    "automation": {"domains": ["process", "technology"], "connotations": ["orchestration", "repeatability", "efficiency"], "roles": ["process"]},
    "calendar": {"domains": ["time", "planning"], "connotations": ["schedule", "date", "event"], "roles": ["time"]},
    "catalog": {"domains": ["data catalog", "inventory"], "connotations": ["organized collection", "reference system"], "roles": ["collection"]},
    "check": {"domains": ["status", "quality"], "connotations": ["completion", "validation", "success"], "roles": ["validation"]},
    "circle": {"domains": ["status", "shape"], "connotations": ["state", "focus", "selection"], "roles": ["state"]},
    "cloud": {"domains": ["technology", "platform"], "connotations": ["remote service", "online storage", "SaaS"], "roles": ["place"]},
    "code": {"domains": ["development", "technology"], "connotations": ["software", "implementation", "technical work"], "roles": ["object"]},
    "column": {"domains": ["data", "structure"], "connotations": ["field", "attribute", "tabular structure"], "roles": ["structure"]},
    "comment": {"domains": ["communication"], "connotations": ["feedback", "discussion", "annotation"], "roles": ["interaction"]},
    "concept": {"domains": ["knowledge", "glossary"], "connotations": ["idea", "meaning", "business term"], "roles": ["concept"]},
    "data": {"domains": ["data"], "connotations": ["information", "dataset", "records"], "roles": ["object"]},
    "database": {"domains": ["data", "storage"], "connotations": ["repository", "structured storage", "source system"], "roles": ["object"]},
    "delete": {"domains": ["action"], "connotations": ["remove", "discard", "destructive action"], "roles": ["action"]},
    "diagram": {"domains": ["modeling", "relationships"], "connotations": ["structure", "graph", "lineage"], "roles": ["structure"]},
    "dictionary": {"domains": ["knowledge", "data catalog"], "connotations": ["definition", "business vocabulary", "reference"], "roles": ["knowledge"]},
    "download": {"domains": ["action", "transfer"], "connotations": ["import", "receive", "save"], "roles": ["action"]},
    "edit": {"domains": ["action", "content"], "connotations": ["modify", "author", "change"], "roles": ["action"]},
    "error": {"domains": ["risk", "status"], "connotations": ["failure", "problem", "exception"], "roles": ["problem"]},
    "field": {"domains": ["data", "structure"], "connotations": ["attribute", "column", "data element"], "roles": ["structure"]},
    "file": {"domains": ["content", "storage"], "connotations": ["document", "artifact", "record"], "roles": ["object"]},
    "filter": {"domains": ["search", "control"], "connotations": ["refinement", "selection", "narrowing"], "roles": ["control"]},
    "flow": {"domains": ["process", "lineage"], "connotations": ["movement", "pipeline", "sequence"], "roles": ["process"]},
    "glossary": {"domains": ["knowledge", "vocabulary"], "connotations": ["definitions", "business terms", "shared language"], "roles": ["knowledge"]},
    "governance": {"domains": ["governance", "compliance"], "connotations": ["control", "stewardship", "accountability"], "roles": ["constraint"]},
    "group": {"domains": ["people", "organization"], "connotations": ["team", "collection", "membership"], "roles": ["actor"]},
    "help": {"domains": ["support"], "connotations": ["assistance", "question", "guidance"], "roles": ["support"]},
    "hierarchy": {"domains": ["structure"], "connotations": ["parent-child relation", "taxonomy", "levels"], "roles": ["structure"]},
    "home": {"domains": ["navigation", "place"], "connotations": ["start", "main area", "origin"], "roles": ["place"]},
    "info": {"domains": ["knowledge", "status"], "connotations": ["context", "detail", "explanation"], "roles": ["knowledge"]},
    "key": {"domains": ["security", "access"], "connotations": ["credential", "unlocking", "permission"], "roles": ["access"]},
    "label": {"domains": ["metadata", "classification"], "connotations": ["tag", "category", "mark"], "roles": ["classification"]},
    "language": {"domains": ["language", "ai"], "connotations": ["translation", "text understanding", "localization"], "roles": ["knowledge"]},
    "lineage": {"domains": ["data lineage", "relationships"], "connotations": ["traceability", "dependency", "data journey"], "roles": ["relationship"]},
    "link": {"domains": ["relationships", "integration"], "connotations": ["connection", "association", "dependency"], "roles": ["relationship"]},
    "lock": {"domains": ["security"], "connotations": ["restriction", "privacy", "protection"], "roles": ["constraint"]},
    "mapping": {"domains": ["data", "integration"], "connotations": ["correspondence", "transformation", "alignment"], "roles": ["relationship"]},
    "marketplace": {"domains": ["product", "exchange"], "connotations": ["discovery", "sharing", "reuse"], "roles": ["place"]},
    "notification": {"domains": ["communication", "status"], "connotations": ["alert", "update", "message"], "roles": ["signal"]},
    "object": {"domains": ["modeling", "data catalog"], "connotations": ["entity", "managed item", "business object"], "roles": ["object"]},
    "person": {"domains": ["people", "identity"], "connotations": ["user", "owner", "individual"], "roles": ["actor"]},
    "policy": {"domains": ["governance", "compliance"], "connotations": ["rule", "standard", "constraint"], "roles": ["constraint"]},
    "process": {"domains": ["process", "operations"], "connotations": ["workflow", "sequence", "activity"], "roles": ["process"]},
    "product": {"domains": ["product", "data product"], "connotations": ["packaged value", "offering", "deliverable"], "roles": ["object"]},
    "quality": {"domains": ["quality", "trust"], "connotations": ["fitness", "reliability", "validation"], "roles": ["validation"]},
    "rule": {"domains": ["governance", "logic"], "connotations": ["condition", "policy", "control"], "roles": ["constraint"]},
    "save": {"domains": ["action", "storage"], "connotations": ["preserve", "store", "commit"], "roles": ["action"]},
    "schema": {"domains": ["data", "structure"], "connotations": ["data model", "relationships", "architecture"], "roles": ["structure"]},
    "search": {"domains": ["discovery"], "connotations": ["find", "explore", "lookup"], "roles": ["discovery"]},
    "security": {"domains": ["security", "risk"], "connotations": ["protection", "confidentiality", "trust"], "roles": ["constraint"]},
    "sensor": {"domains": ["monitoring", "data collection"], "connotations": ["measurement", "signal", "source"], "roles": ["source"]},
    "settings": {"domains": ["configuration", "control"], "connotations": ["preferences", "tuning", "administration"], "roles": ["control"]},
    "share": {"domains": ["communication", "collaboration"], "connotations": ["distribution", "publishing", "reuse"], "roles": ["action"]},
    "source": {"domains": ["data", "origin"], "connotations": ["origin", "reference", "system of record"], "roles": ["origin"]},
    "star": {"domains": ["status", "preference"], "connotations": ["favorite", "importance", "quality"], "roles": ["state"]},
    "sync": {"domains": ["integration", "coordination"], "connotations": ["alignment", "refresh", "two-way update"], "roles": ["process"]},
    "table": {"domains": ["data", "structure"], "connotations": ["rows and columns", "dataset", "structured records"], "roles": ["structure"]},
    "tag": {"domains": ["metadata", "classification"], "connotations": ["label", "keyword", "taxonomy"], "roles": ["classification"]},
    "team": {"domains": ["people", "collaboration"], "connotations": ["ownership", "group work", "responsibility"], "roles": ["actor"]},
    "term": {"domains": ["glossary", "knowledge"], "connotations": ["definition", "business meaning", "vocabulary"], "roles": ["knowledge"]},
    "upload": {"domains": ["action", "transfer"], "connotations": ["publish", "send", "import"], "roles": ["action"]},
    "user": {"domains": ["people", "identity"], "connotations": ["person", "account", "actor"], "roles": ["actor"]},
    "validation": {"domains": ["quality", "governance"], "connotations": ["approval", "control", "readiness"], "roles": ["validation"]},
    "view": {"domains": ["visualization", "navigation"], "connotations": ["display", "perspective", "inspection"], "roles": ["view"]},
    "warning": {"domains": ["risk", "status"], "connotations": ["caution", "attention", "problem"], "roles": ["signal"]},
    "wheelchair": {"domains": ["accessibility", "mobility"], "connotations": ["assistive mobility", "access needs", "inclusive facilities"], "roles": ["actor"]},
    "workflow": {"domains": ["process", "operations"], "connotations": ["sequence", "orchestration", "activity chain"], "roles": ["process"]},
}

COLLECTION_METADATA = {
    "material-symbol": {
        "connotations": ["generic UI metaphor", "Material Design visual language"],
        "domains": ["general interface"],
    },
    "DataGalaxy Icons": {
        "connotations": ["data governance product language", "enterprise data catalog"],
        "domains": ["data governance", "data catalog"],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate visual-semantic metadata for icon PNGs.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL))
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for icon in manifest["icons"]:
        image_path = ROOT / icon["source_path"]
        pixels = decode_png_rgba(image_path.read_bytes())
        metrics = compute_pixel_metrics(pixels)
        records.append(build_record(icon, metrics))

    output_payload = {
        "analysis_method": (
            "Programmatic first-pass metadata from local PNG pixels plus icon names and "
            "folder categories. Pixel-derived fields come from the actual image. "
            "Denotation and connotation fields are draft semantic interpretations and "
            "should be reviewed or upgraded with a vision-language model for final curation."
        ),
        "count": len(records),
        "records": records,
    }

    Path(args.output).write_text(json.dumps(output_payload, indent=2), encoding="utf-8")
    with Path(args.jsonl).open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(f"Wrote {len(records)} visual metadata records to {args.output}")
    return 0


def build_record(icon: dict[str, Any], metrics: PixelMetrics) -> dict[str, Any]:
    tokens = tokenize(icon["name"])
    semantic = collect_semantics(tokens, icon["source_collection"], icon.get("category"))
    phrase = humanize_name(icon["name"])
    visual_description = describe_visual(icon, metrics, phrase)
    denotation = build_denotation(tokens, phrase, metrics)
    possible_misreadings = build_possible_misreadings(tokens, metrics)
    return {
        "unique_name": icon["unique_name"],
        "name": icon["name"],
        "source_collection": icon["source_collection"],
        "category": icon.get("category"),
        "subcategory": icon.get("subcategory"),
        "style": icon["style"],
        "source_path": icon["source_path"],
        "duplicate_of": icon.get("duplicate_of"),
        "visual_description": visual_description,
        "denotation": denotation,
        "connotations": semantic["connotations"],
        "semantic_domains": semantic["domains"],
        "semiotic_roles": semantic["roles"],
        "visual_elements": build_visual_elements(metrics),
        "pixel_metrics": asdict(metrics),
        "abstraction_level": infer_abstraction(tokens, semantic["roles"]),
        "best_for": build_best_for(semantic, phrase),
        "avoid_for": build_avoid_for(tokens, metrics),
        "possible_misreadings": possible_misreadings,
        "name_quality": infer_name_quality(icon["name"], tokens),
        "curation_status": infer_curation_status(icon["name"], tokens),
        "search_terms": sorted(set(tokens + semantic["domains"] + semantic["connotations"] + semantic["roles"])),
    }


def decode_png_rgba(data: bytes) -> list[list[tuple[int, int, int, int]]]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Not a PNG")
    offset = 8
    width = height = bit_depth = color_type = None
    idat = bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break
    if width is None or height is None or bit_depth != 8 or color_type not in {2, 4, 6}:
        raise ValueError("Unsupported PNG format; expected 8-bit RGB/RGBA/gray+alpha")

    channels = {2: 3, 4: 2, 6: 4}[color_type]
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    rows: list[bytes] = []
    previous = bytes(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        scanline = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        recon = unfilter(scanline, previous, filter_type, channels)
        rows.append(bytes(recon))
        previous = bytes(recon)

    rgba_rows: list[list[tuple[int, int, int, int]]] = []
    for row in rows:
        rgba_row: list[tuple[int, int, int, int]] = []
        for x in range(width):
            index = x * channels
            if color_type == 6:
                rgba_row.append((row[index], row[index + 1], row[index + 2], row[index + 3]))
            elif color_type == 2:
                rgba_row.append((row[index], row[index + 1], row[index + 2], 255))
            else:
                gray, alpha = row[index], row[index + 1]
                rgba_row.append((gray, gray, gray, alpha))
        rgba_rows.append(rgba_row)
    return rgba_rows


def unfilter(scanline: bytearray, previous: bytes, filter_type: int, bpp: int) -> bytearray:
    result = bytearray(scanline)
    for i, value in enumerate(scanline):
        left = result[i - bpp] if i >= bpp else 0
        up = previous[i]
        up_left = previous[i - bpp] if i >= bpp else 0
        if filter_type == 0:
            result[i] = value
        elif filter_type == 1:
            result[i] = (value + left) & 0xFF
        elif filter_type == 2:
            result[i] = (value + up) & 0xFF
        elif filter_type == 3:
            result[i] = (value + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            result[i] = (value + paeth(left, up, up_left)) & 0xFF
        else:
            raise ValueError(f"Unsupported PNG filter type: {filter_type}")
    return result


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def compute_pixel_metrics(pixels: list[list[tuple[int, int, int, int]]]) -> PixelMetrics:
    height = len(pixels)
    width = len(pixels[0])
    alpha_points: list[tuple[int, int, int]] = []
    for y, row in enumerate(pixels):
        for x, (_, _, _, alpha) in enumerate(row):
            if alpha > 16:
                alpha_points.append((x, y, alpha))
    if not alpha_points:
        return PixelMetrics(width, height, None, 0, 0, None, None, 1, 1, 0, "empty", "none")

    xs = [point[0] for point in alpha_points]
    ys = [point[1] for point in alpha_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    bbox_width = max_x - min_x + 1
    bbox_height = max_y - min_y + 1
    alpha_sum = sum(point[2] for point in alpha_points)
    cx = sum(x * alpha for x, _, alpha in alpha_points) / alpha_sum
    cy = sum(y * alpha for _, y, alpha in alpha_points) / alpha_sum
    ink_coverage = len(alpha_points) / (width * height)
    bbox_coverage = len(alpha_points) / (bbox_width * bbox_height)
    aspect = bbox_width / bbox_height
    horizontal = symmetry_score(pixels, axis="horizontal")
    vertical = symmetry_score(pixels, axis="vertical")
    edge_complexity = compute_edge_complexity(pixels)
    return PixelMetrics(
        canvas_width=width,
        canvas_height=height,
        bbox={"x": min_x, "y": min_y, "width": bbox_width, "height": bbox_height},
        ink_coverage=round(ink_coverage, 4),
        bbox_coverage=round(bbox_coverage, 4),
        bbox_aspect_ratio=round(aspect, 3),
        center_of_mass={"x": round(cx / width, 3), "y": round(cy / height, 3)},
        horizontal_symmetry=horizontal,
        vertical_symmetry=vertical,
        edge_complexity=edge_complexity,
        visual_weight=visual_weight(ink_coverage),
        dominant_orientation=orientation(aspect),
    )


def alpha_at(pixels: list[list[tuple[int, int, int, int]]], x: int, y: int) -> int:
    return pixels[y][x][3]


def symmetry_score(pixels: list[list[tuple[int, int, int, int]]], axis: str) -> float:
    height = len(pixels)
    width = len(pixels[0])
    diffs = total = 0
    if axis == "horizontal":
        for y in range(height):
            mirror_y = height - 1 - y
            for x in range(width):
                diffs += abs(alpha_at(pixels, x, y) - alpha_at(pixels, x, mirror_y))
                total += 255
    else:
        for y in range(height):
            for x in range(width):
                mirror_x = width - 1 - x
                diffs += abs(alpha_at(pixels, x, y) - alpha_at(pixels, mirror_x, y))
                total += 255
    return round(1 - diffs / max(1, total), 4)


def compute_edge_complexity(pixels: list[list[tuple[int, int, int, int]]]) -> float:
    height = len(pixels)
    width = len(pixels[0])
    transitions = 0
    for y in range(height):
        for x in range(width):
            here = alpha_at(pixels, x, y) > 16
            if x + 1 < width and here != (alpha_at(pixels, x + 1, y) > 16):
                transitions += 1
            if y + 1 < height and here != (alpha_at(pixels, x, y + 1) > 16):
                transitions += 1
    return round(transitions / (width * height), 4)


def tokenize(name: str) -> list[str]:
    tokens: list[str] = []
    for token in TOKEN_RE.findall(name.lower().replace("-", "_")):
        tokens.extend(part for part in token.split("_") if part)
    return [token for token in tokens if token not in {"black", "round", "filled"}]


def collect_semantics(tokens: list[str], collection: str, category: str | None) -> dict[str, list[str]]:
    domains: list[str] = []
    connotations: list[str] = []
    roles: list[str] = []
    collection_meta = COLLECTION_METADATA.get(collection, {})
    domains.extend(collection_meta.get("domains", []))
    connotations.extend(collection_meta.get("connotations", []))
    if category and category not in {"material-symbol"}:
        domains.append(category.replace("-", " "))
    for token in tokens:
        meta = TOKEN_METADATA.get(token)
        if not meta:
            continue
        domains.extend(meta["domains"])
        connotations.extend(meta["connotations"])
        roles.extend(meta["roles"])
    return {
        "domains": unique(domains or ["general interface"]),
        "connotations": unique(connotations or [humanize_name("_".join(tokens))]),
        "roles": unique(roles or ["symbol"]),
    }


def describe_visual(icon: dict[str, Any], metrics: PixelMetrics, phrase: str) -> str:
    if not metrics.bbox:
        return f"An empty or fully transparent PNG associated with {phrase}."
    symmetry = []
    if metrics.vertical_symmetry > 0.9:
        symmetry.append("vertically balanced")
    if metrics.horizontal_symmetry > 0.9:
        symmetry.append("horizontally balanced")
    symmetry_text = ", ".join(symmetry) if symmetry else "asymmetrical"
    return (
        f"A {metrics.visual_weight} rounded monochrome glyph on a transparent "
        f"{metrics.canvas_width}x{metrics.canvas_height} canvas. The silhouette is "
        f"{metrics.dominant_orientation}, {symmetry_text}, and visually associated "
        f"with {phrase}."
    )


def build_denotation(tokens: list[str], phrase: str, metrics: PixelMetrics) -> list[str]:
    denotation = [f"literal icon named {phrase}"]
    if tokens:
        denotation.append("visual symbol for " + " ".join(tokens[:4]))
    if metrics.dominant_orientation != "balanced":
        denotation.append(f"{metrics.dominant_orientation} silhouette")
    return unique(denotation)


def build_visual_elements(metrics: PixelMetrics) -> list[str]:
    elements = [metrics.visual_weight, metrics.dominant_orientation]
    if metrics.vertical_symmetry > 0.9:
        elements.append("vertical symmetry")
    if metrics.horizontal_symmetry > 0.9:
        elements.append("horizontal symmetry")
    if metrics.edge_complexity > 0.12:
        elements.append("detailed outline")
    elif metrics.edge_complexity < 0.045:
        elements.append("simple silhouette")
    return unique(elements)


def infer_abstraction(tokens: list[str], roles: list[str]) -> str:
    if any(role in roles for role in {"structure", "relationship", "constraint", "knowledge", "process"}):
        return "conceptual"
    if any(role in roles for role in {"actor", "object", "place"}):
        return "concrete"
    if len(tokens) >= 3:
        return "specific"
    return "generic"


def build_best_for(semantic: dict[str, list[str]], phrase: str) -> list[str]:
    best = [phrase]
    best.extend(semantic["domains"][:3])
    best.extend(semantic["roles"][:2])
    return unique(best)


def build_avoid_for(tokens: list[str], metrics: PixelMetrics) -> list[str]:
    avoid: list[str] = []
    if any(token in tokens for token in {"warning", "error", "dangerous", "alert"}):
        avoid.append("neutral success states where a warning connotation would mislead")
    if any(token in tokens for token in {"delete", "close", "remove", "cancel"}):
        avoid.append("constructive or additive concepts")
    if metrics.edge_complexity > 0.15:
        avoid.append("very small sizes where the glyph details may collapse")
    if metrics.visual_weight == "light":
        avoid.append("high-emphasis status markers that require strong visual weight")
    return unique(avoid)


def build_possible_misreadings(tokens: list[str], metrics: PixelMetrics) -> list[str]:
    misreadings: list[str] = []
    if any(token in tokens for token in {"cloud", "download", "upload", "sync"}):
        misreadings.append("may be read as generic cloud/file transfer rather than the specific concept")
    if any(token in tokens for token in {"person", "account", "user"}):
        misreadings.append("may imply an individual actor even when the concept is systemic")
    if any(token in tokens for token in {"star", "favorite", "grade"}):
        misreadings.append("may imply rating or preference")
    if metrics.dominant_orientation in {"wide", "tall"}:
        misreadings.append("may feel visually heavier in one direction next to balanced icons")
    return unique(misreadings)


def infer_name_quality(name: str, tokens: list[str]) -> str:
    normalized = name.lower().strip()
    if re.fullmatch(r"group[\s_-]*\d+", normalized):
        return "weak_export_name"
    if not tokens or all(token.isdigit() for token in tokens):
        return "weak_numeric_name"
    if len(tokens) == 1 and tokens[0] in {"h1", "h2", "h3"}:
        return "compact_typographic_name"
    return "descriptive"


def infer_curation_status(name: str, tokens: list[str]) -> str:
    quality = infer_name_quality(name, tokens)
    if quality.startswith("weak"):
        return "needs_human_review"
    return "draft_generated"


def visual_weight(coverage: float) -> str:
    if coverage < 0.12:
        return "light"
    if coverage < 0.22:
        return "medium"
    return "heavy"


def orientation(aspect: float) -> str:
    if aspect > 1.25:
        return "wide"
    if aspect < 0.8:
        return "tall"
    return "balanced"


def humanize_name(name: str) -> str:
    return " ".join(tokenize(name))


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        item = item.strip().lower()
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
