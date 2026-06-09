from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

URL = (
    "https://raw.githubusercontent.com/google/material-design-icons/refs/heads/master/"
    "variablefont/MaterialSymbolsOutlined%5BFILL%2CGRAD%2Copsz%2Cwght%5D.codepoints"
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_TARGET = (
    ROOT
    / "src"
    / "material_symbol_semantic_index"
    / "data"
    / "material_symbols_outlined.codepoints"
)
VISIBLE_TARGET = ROOT / "data" / "material_symbols_outlined.codepoints"


def main() -> int:
    with urlopen(URL, timeout=30) as response:
        content = response.read().decode("utf-8")
    lines = [line for line in content.splitlines() if line.strip()]
    if len(lines) < 3000:
        raise RuntimeError(f"Unexpectedly small Material Symbols file: {len(lines)} lines")
    PACKAGE_TARGET.write_text(content, encoding="utf-8")
    VISIBLE_TARGET.write_text(content, encoding="utf-8")
    print(f"Wrote {len(lines)} Material Symbols to {PACKAGE_TARGET}")
    print(f"Mirrored snapshot to {VISIBLE_TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
