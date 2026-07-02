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

For PNG-backed visual metadata, including DataGalaxy icons:

```bash
PYTHONPATH=src python -m material_symbol_semantic_index.cli visual-select \
  --items examples/slide-items.json \
  --allow-material-fallback \
  --json
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

For DataGalaxy/PNG visual metadata:

```python
from material_symbol_semantic_index import select_visual_icons

selection = select_visual_icons(
    [
        "Establish a single source of truth for governed data products.",
        "Automate workflows so teams can reuse trusted context.",
    ],
    allow_material_fallback=True,
)

for choice in selection.choices:
    print(choice.icon.unique_name, choice.icon.source_path)
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

Use `visual-select` when a downstream renderer needs an actual PNG asset path,
not only a Material Symbol codepoint. It scores the JSONL metadata locally,
prefers DataGalaxy-native icons by default, and can fall back to Material
Symbols when `--allow-material-fallback` is set.

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

## HTTP API

A minimal FastAPI service wraps `select_visual_icons` for one icon request at a
time.

Install API dependencies:

```bash
pip install -r requirements.txt
```

Run locally:

```bash
PYTHONPATH=src uvicorn material_symbol_semantic_index.api.main:app --host 0.0.0.0 --port 8000
```

### `POST /v1/icons/select`

Request body:

```json
{
  "text": "Establish a single source of truth for governed data products.",
  "tone": "confident",
  "context": "opening slide of a leadership deck",
  "prefer_style": "datagalaxy",
  "allow_material_fallback": true,
  "avoid": ["security"],
  "alternatives": 5
}
```

Only `text` is required (1-2000 characters). The response includes the
selected icon, its `asset_ref` path, `score`, `rationale`, `alternatives`,
`warnings`, `metadata_sha256`, and `service_version`. Invalid input (missing,
blank, or oversized `text`, wrong field types, or a request that leaves no
candidates) returns `400` with a `detail` explanation.

Example:

```bash
curl -s -X POST http://localhost:8000/v1/icons/select \
  -H "Content-Type: application/json" \
  -d '{"text": "Establish a single source of truth for governed data products."}'
```

### `POST /v1/icons/select-batch`

For selecting icons for several related items (e.g. every icon on one slide)
as a coherent set — reuses `select_visual_icons`' existing dedup/category
balancing across items, rather than each item picking independently and
risking duplicate icons.

```json
{
  "items": [
    {"label": "card1", "text": "Establish a single source of truth."},
    {"label": "card2", "text": "Automate workflows so teams can reuse trusted context."}
  ],
  "prefer_style": "datagalaxy",
  "alternatives": 5
}
```

Returns `{"choices": [...], "warnings": [...], "metadata_sha256": "...", "service_version": "..."}`,
one choice per input item in the same order, each shaped like the single-select
response (minus the top-level `metadata_sha256`/`service_version` duplication).

### `GET /assets/{path}`

Serves the icon PNGs referenced by `asset_ref`. Add `?color=` to get a
recolored variant instead of the template's default black — useful for
status-signaling icons (e.g. a risk icon tinted red). Accepts either a named
color (`black`, `white`, `red`, `orange`, `green`) or an arbitrary hex color
(`1E3A8A` or `#1E3A8A`) for anything outside that palette. Recoloring replaces
every non-transparent pixel's RGB with the target color while preserving the
original alpha, so it only makes sense for simple single-color line icons
(which is what this template's icon set is).

```bash
curl -s "http://localhost:8000/assets/raw/neo29/DataGalaxy%20Icons/dictionary/database.png?color=red" -o red-database.png
```

### `GET /health`

Returns `{"status": "ok", "service_version": "..."}` for uptime checks.

Interactive docs are available at `/docs` once the server is running.

### Deploying to Render

`render.yaml` defines a single web service that installs `requirements.txt`
and runs the same `uvicorn` command as above, bound to Render's `$PORT`, with
`/health` wired up as the health check path. Push this repo to a Git remote
Render can see, then create a Blueprint from `render.yaml` (or a Web Service
pointing at this repo) in the Render dashboard.
