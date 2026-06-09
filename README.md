# Material Symbol Semantic Index

This repository gives an AI agent a practical way to choose meaningful icons
for short text, including slide pages where several icons must work together as
a coherent semiotic set.

It does three things:

- loads the official Material Symbols codepoint list
- enriches sparse icon names with local semantic hints
- retrieves and selects icons with set-level neighbor checks
- builds a visual metadata catalog from local PNG icons

## Quick Start

From the repository root:

```bash
PYTHONPATH=src python -m material_symbol_semantic_index.cli search "reduce operational friction across teams"
```

```bash
PYTHONPATH=src python -m material_symbol_semantic_index.cli select \
  "Establish a single source of truth for governed data products." \
  "Automate workflows so teams can reuse trusted context." \
  "Surface insights before quality issues reach customers."
```

For an agent rerank prompt:

```bash
PYTHONPATH=src python -m material_symbol_semantic_index.cli prompt --items examples/slide-items.json
```

After installing the package, the same commands are available through `msi`:

```bash
msi select --items examples/slide-items.json
```

## Python Usage

```python
from material_symbol_semantic_index import select_icons

selection = select_icons([
    "Establish a single source of truth for governed data products.",
    "Automate workflows so teams can reuse trusted context.",
])

for choice in selection.choices:
    print(choice.icon.name, choice.rationale)
```

## Why This Shape

Material Symbols names are useful but thin. A careful agent needs a retrieval
layer that expands names into semantic domains, roles, tone, visual family, and
abstraction level. When multiple icons appear on one page, the selector chooses
the set together so the symbols read as neighbors rather than isolated guesses.

## Local PNG Visual Catalog

The local PNG pipeline reads the provided `Neo (29).zip` extraction under
`data/raw/neo29/` and includes two collections:

- `material-symbol`: 2,106 rounded Material Symbol PNGs
- `DataGalaxy Icons`: 333 DataGalaxy PNGs

Build the manifest:

```bash
python scripts/build_local_png_manifest.py
```

Generate the visual-semantic metadata:

```bash
python scripts/generate_icon_metadata.py
```

Generated files:

- `data/icon_png_manifest.json`
- `data/icon_png_manifest.jsonl`
- `data/icon_visual_metadata.json`
- `data/icon_visual_metadata.jsonl`

The metadata generator decodes the actual PNG pixels to compute bounding box,
ink coverage, symmetry, visual weight, orientation, and edge complexity. The
denotation/connotation fields are a first-pass semantic interpretation from
the visual metrics plus icon names and folder categories, marked with
`curation_status` for review.

## Data Source

The package includes a snapshot of the official Google Material Symbols
Outlined codepoint file. A visible mirror is kept at
`data/material_symbols_outlined.codepoints` for inspection.

<https://github.com/google/material-design-icons/tree/master/variablefont>

Google publishes Material Symbols under the Apache License 2.0.

Refresh the snapshot with:

```bash
python scripts/fetch_material_symbols.py
```

## Tests

```bash
PYTHONPATH=src python -m unittest discover -s tests
```
