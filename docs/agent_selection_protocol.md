# Agent Selection Protocol

This protocol gives an AI agent a disciplined way to choose Material Symbols for
short paragraphs, especially when several icons appear together on a slide.

## Tool Contract

The agent should call a local retriever first. For Material Symbols codepoints:

```bash
msi select --items slide-items.json --json
```

For visual metadata with PNG paths, including DataGalaxy icons:

```bash
msi visual-select --items slide-items.json --allow-material-fallback --json
```

The input JSON is an array of strings or objects:

```json
[
  {
    "label": "govern",
    "text": "Establish a single source of truth for governed data products."
  },
  {
    "label": "activate",
    "text": "Automate workflows so teams can reuse trusted context."
  }
]
```

The output contains a selected icon, alternatives, query analysis, rationale,
and neighbor relation for every item.

## Decision Loop

1. Parse the paragraph into intent, role, tone, and domain.
2. Retrieve candidates from the full Material Symbols codepoint list.
3. Rerank candidates by semantic fit, recognizability, connotation, and
   abstraction level.
4. Select the whole set with pairwise checks:
   - no accidental duplicate metaphor
   - no repeated icon root unless the slide intentionally shows a taxonomy
   - consistent abstraction level
   - neighboring icons should be related enough to feel like a system, but
     distinct enough to avoid semantic blur
5. Return the chosen icon plus rejected alternatives.

## DataGalaxy / PNG Selection

Use `visual-select` when the renderer needs a file-backed asset reference. It
reads `data/icon_visual_metadata.jsonl`, which includes both DataGalaxy icons
and Material Symbol PNGs.

Default behavior is strict brand mode: prefer DataGalaxy icons and do not use
Material Symbols. Add `--allow-material-fallback` when semantic precision is
more important than style purity.

The output includes:

- `icon_id`, such as `datagalaxy:glossary/reference-data`
- `asset_ref` / `source_path`
- semantic domains and roles
- score, rationale, alternatives, metadata hash, and repo commit

Do not paste the full visual metadata catalog into an LLM prompt. Run retrieval
locally, then pass only selected icons and a short alternatives list to the LLM
if high-stakes reranking is needed.

## Semiotic Rubric

- Denotation: what the glyph literally depicts.
- Connotation: what the glyph is likely to suggest at a glance.
- Role: actor, object, process, state, constraint, insight, result, or action.
- Neighbor relation: contrast, sequence, hierarchy, causality, or shared domain.
- Visual risk: tiny details, ambiguous metaphor, accidental warning, false
  completion, or culturally overloaded symbol.

## LLM Rerank

For higher-stakes slide work, use:

```bash
msi prompt --items slide-items.json
```

Feed that prompt to the language model after retrieval. The model must choose
only from the supplied candidates and must justify the set-level semiotics.
