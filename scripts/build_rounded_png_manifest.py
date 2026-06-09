from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

OWNER = "google"
REPO = "material-design-icons"
BRANCH = "master"
API_ROOT = f"https://api.github.com/repos/{OWNER}/{REPO}/git/trees"
RAW_ROOT = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}"

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "github"
MANIFEST_PATH = ROOT / "data" / "rounded_png_manifest.json"
MANIFEST_JSONL_PATH = ROOT / "data" / "rounded_png_manifest.jsonl"

ANDROID_TREE_SHA = "caaed8df96e1c448ee6d38e51e6377ff893a7306"
ROUND_PNG_RE = re.compile(
    r"^materialiconsround/black/res/drawable-xhdpi/"
    r"round_(?P<name>.+)_black_24\.png$"
)


@dataclass(frozen=True)
class RoundedPngIcon:
    name: str
    category: str
    subcategory: str
    style: str
    source_family: str
    dp: int
    scale: int
    pixel_size: int
    color: str
    github_path: str
    raw_url: str
    github_blob_sha: str
    byte_size: int


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a manifest of rounded 24dp @2x PNG Material Icons."
    )
    parser.add_argument("--refresh", action="store_true", help="Refetch GitHub tree JSON.")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    android_tree = fetch_tree(ANDROID_TREE_SHA, RAW_DIR / "android-tree.json", args.refresh)
    categories = [
        entry for entry in android_tree["tree"] if entry["type"] == "tree"
    ]

    icons: list[RoundedPngIcon] = []
    for category_entry in categories:
        category = category_entry["path"]
        category_tree = fetch_tree(
            category_entry["sha"],
            RAW_DIR / f"android-{category}-direct.json",
            args.refresh,
        )
        for icon_entry in category_tree["tree"]:
            if icon_entry["type"] != "tree":
                continue
            subcategory = icon_entry["path"]
            icon_tree = fetch_tree(
                icon_entry["sha"],
                RAW_DIR / "icons" / category / f"{subcategory}.json",
                args.refresh,
                recursive=True,
            )
            icons.extend(find_rounded_pngs(category, subcategory, icon_tree))

    icons.sort(key=lambda icon: (icon.category, icon.name, icon.github_path))
    write_manifest(icons)
    print(f"Wrote {len(icons)} rounded PNG icons to {MANIFEST_PATH}")
    return 0


def fetch_tree(sha: str, cache_path: Path, refresh: bool, recursive: bool = False) -> dict:
    if cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{API_ROOT}/{sha}"
    if recursive:
        url += "?recursive=1"
    with urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("truncated"):
        raise RuntimeError(f"GitHub tree response was truncated: {url}")
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def find_rounded_pngs(category: str, subcategory: str, icon_tree: dict) -> list[RoundedPngIcon]:
    results: list[RoundedPngIcon] = []
    for entry in icon_tree["tree"]:
        if entry["type"] != "blob":
            continue
        match = ROUND_PNG_RE.match(entry["path"])
        if not match:
            continue
        name = match.group("name")
        github_path = f"android/{category}/{subcategory}/{entry['path']}"
        results.append(
            RoundedPngIcon(
                name=name,
                category=category,
                subcategory=subcategory,
                style="round",
                source_family="materialiconsround",
                dp=24,
                scale=2,
                pixel_size=48,
                color="black",
                github_path=github_path,
                raw_url=f"{RAW_ROOT}/{github_path}",
                github_blob_sha=entry["sha"],
                byte_size=entry.get("size", 0),
            )
        )
    return results


def write_manifest(icons: list[RoundedPngIcon]) -> None:
    payload = {
        "source": {
            "repository": f"{OWNER}/{REPO}",
            "branch": BRANCH,
            "image_filter": "android/<category>/<name>/materialiconsround/black/res/drawable-xhdpi/round_<name>_black_24.png",
            "dp": 24,
            "scale": 2,
            "pixel_size": 48,
        },
        "count": len(icons),
        "icons": [asdict(icon) for icon in icons],
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with MANIFEST_JSONL_PATH.open("w", encoding="utf-8") as output:
        for icon in icons:
            output.write(json.dumps(asdict(icon), sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())

