from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "raw" / "neo29"
DEFAULT_OUTPUT = ROOT / "data" / "icon_png_manifest.json"
DEFAULT_JSONL = ROOT / "data" / "icon_png_manifest.jsonl"


@dataclass(frozen=True)
class LocalPngIcon:
    name: str
    unique_name: str
    category: str | None
    subcategory: str | None
    source_collection: str
    style: str
    source_path: str
    width: int
    height: int
    byte_size: int
    sha256: str
    duplicate_of: str | None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a manifest from local PNG icons.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--jsonl", default=str(DEFAULT_JSONL))
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        raise FileNotFoundError(source)

    icons: list[LocalPngIcon] = []
    seen_hashes: dict[str, str] = {}
    for png_path in sorted(source.rglob("*.png")):
        collection = infer_collection(source, png_path)
        if collection not in {"material-symbol", "DataGalaxy Icons"}:
            continue
        name = png_path.stem
        unique_name = build_unique_name(source, png_path)
        data = png_path.read_bytes()
        width, height = read_png_size(data)
        digest = hashlib.sha256(data).hexdigest()
        duplicate_of = seen_hashes.get(digest)
        if duplicate_of is None:
            seen_hashes[digest] = unique_name
        icons.append(
            LocalPngIcon(
                name=name,
                unique_name=unique_name,
                category=infer_category(source, png_path),
                subcategory=infer_subcategory(source, png_path),
                source_collection=collection,
                style=infer_style(source, png_path),
                source_path=str(png_path.relative_to(ROOT)),
                width=width,
                height=height,
                byte_size=len(data),
                sha256=digest,
                duplicate_of=duplicate_of,
            )
        )

    payload = {
        "source": str(source),
        "count": len(icons),
        "unique_image_count": len({icon.sha256 for icon in icons}),
        "duplicate_image_count": sum(1 for icon in icons if icon.duplicate_of),
        "icons": [asdict(icon) for icon in icons],
    }
    output = Path(args.output)
    jsonl = Path(args.jsonl)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with jsonl.open("w", encoding="utf-8") as handle:
        for icon in icons:
            handle.write(json.dumps(asdict(icon), sort_keys=True) + "\n")
    print(
        f"Wrote {len(icons)} PNG records "
        f"({payload['unique_image_count']} unique images) to {output}"
    )
    return 0


def read_png_size(data: bytes) -> tuple[int, int]:
    png_signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(png_signature):
        raise ValueError("Not a PNG file")
    if data[12:16] != b"IHDR":
        raise ValueError("PNG missing IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def infer_collection(source_root: Path, png_path: Path) -> str:
    relative = png_path.relative_to(source_root)
    if len(relative.parts) > 1:
        return relative.parts[0]
    return source_root.name


def infer_category(source_root: Path, png_path: Path) -> str | None:
    relative = png_path.relative_to(source_root)
    collection = infer_collection(source_root, png_path)
    if collection == "material-symbol":
        return "material-symbol"
    if collection == "DataGalaxy Icons" and len(relative.parts) > 2:
        return relative.parts[1]
    return None


def infer_subcategory(source_root: Path, png_path: Path) -> str | None:
    relative = png_path.relative_to(source_root)
    collection = infer_collection(source_root, png_path)
    if collection == "DataGalaxy Icons" and len(relative.parts) > 3:
        return "/".join(relative.parts[2:-1])
    return None


def infer_style(source_root: Path, png_path: Path) -> str:
    collection = infer_collection(source_root, png_path)
    if collection == "material-symbol":
        return "material-symbol-rounded"
    if collection == "DataGalaxy Icons":
        return "datagalaxy"
    return "unknown"


def build_unique_name(source_root: Path, png_path: Path) -> str:
    relative = png_path.relative_to(source_root)
    collection = infer_collection(source_root, png_path)
    if collection == "material-symbol":
        return f"material-symbol:{png_path.stem}"
    if collection == "DataGalaxy Icons":
        parts = [part for part in relative.parts[1:-1] if part]
        prefix = "/".join(parts)
        return f"datagalaxy:{prefix}/{png_path.stem}" if prefix else f"datagalaxy:{png_path.stem}"
    return str(relative.with_suffix(""))


if __name__ == "__main__":
    raise SystemExit(main())
