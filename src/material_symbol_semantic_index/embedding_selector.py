from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from tokenizers import Tokenizer
import onnxruntime as ort

from .visual_selector import (
    VisualIconCandidate,
    VisualIconChoice,
    VisualIconRecord,
    VisualIconSelection,
    VisualSelectionItem,
    choose_coherent_visual_set,
    git_commit,
    load_visual_metadata,
    normalize_visual_items,
    sha256_file,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VISUAL_METADATA_PATH = REPO_ROOT / "data" / "icon_visual_metadata_v2.jsonl"
DEFAULT_EMBEDDINGS_PATH = REPO_ROOT / "data" / "icon_embeddings.npy"
DEFAULT_EMBEDDINGS_INDEX_PATH = REPO_ROOT / "data" / "icon_embeddings_index.json"
DEFAULT_ONNX_MODEL_DIR = REPO_ROOT / "model" / "all-MiniLM-L6-v2-onnx"

STYLE_PREFERENCE_BONUS = 0.05
AVOID_PENALTY = 0.25


class EmbeddingModel:
    """Lazily-loaded singleton wrapping the ONNX model + tokenizer. No torch required."""

    _instance: "EmbeddingModel | None" = None

    def __init__(self, model_dir: Path):
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self.tokenizer.enable_truncation(max_length=256)
        self.session = ort.InferenceSession(
            str(model_dir / "model.onnx"), providers=["CPUExecutionProvider"]
        )
        self._input_names = {i.name for i in self.session.get_inputs()}

    @classmethod
    def get(cls, model_dir: Path | None = None) -> "EmbeddingModel":
        if cls._instance is None:
            cls._instance = cls(model_dir or DEFAULT_ONNX_MODEL_DIR)
        return cls._instance

    def embed(self, texts: list[str]) -> np.ndarray:
        encodings = self.tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        type_ids = np.array([e.type_ids for e in encodings], dtype=np.int64)
        feed = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": type_ids,
        }
        feed = {k: v for k, v in feed.items() if k in self._input_names}
        last_hidden = self.session.run(None, feed)[0]
        mask = attention_mask[..., None].astype(np.float32)
        pooled = (last_hidden * mask).sum(axis=1) / mask.sum(axis=1)
        return pooled / np.linalg.norm(pooled, axis=1, keepdims=True)


class EmbeddingSearchIndex:
    """Cosine-similarity search over a precomputed icon embedding corpus."""

    def __init__(
        self,
        icons: list[VisualIconRecord],
        *,
        embeddings_path: Path,
        embeddings_index_path: Path,
        model: EmbeddingModel,
    ):
        import json

        self.icons_by_name = {icon.unique_name: icon for icon in icons}
        self.vectors = np.load(embeddings_path)
        self.names: list[str] = json.load(embeddings_index_path.open())
        missing = [n for n in self.names if n not in self.icons_by_name]
        if missing:
            raise ValueError(
                f"{len(missing)} embedding-index entries have no matching metadata record, "
                f"e.g. {missing[:3]} — metadata and embeddings are out of sync"
            )
        self.model = model

    def search(
        self,
        item: VisualSelectionItem,
        *,
        limit: int = 24,
        prefer_style: str = "datagalaxy",
        allow_material_fallback: bool = True,
    ) -> list[VisualIconCandidate]:
        query_vec = self.model.embed([item.query_text])[0]
        sims = self.vectors @ query_vec

        rows = np.arange(len(self.names))
        if not allow_material_fallback:
            rows = np.array(
                [i for i in rows if self.icons_by_name[self.names[i]].style == prefer_style]
            )
            if len(rows) == 0:
                return []

        scores = sims[rows].astype(np.float64)
        avoid_terms = [a.lower() for a in item.avoid]

        candidates: list[VisualIconCandidate] = []
        for row, score in zip(rows, scores):
            icon = self.icons_by_name[self.names[row]]
            reasons = [f"cosine similarity {score:.3f} to query embedding"]
            if icon.style == prefer_style:
                score += STYLE_PREFERENCE_BONUS
                reasons.append(f"preferred style: {prefer_style}")
            if avoid_terms:
                avoid_text = " ".join(icon.avoid_for + icon.possible_misreadings + icon.connotations).lower()
                if any(term in avoid_text for term in avoid_terms):
                    score -= AVOID_PENALTY
                    reasons.append("user avoid overlap")
            candidates.append(VisualIconCandidate(icon=icon, score=round(float(score), 4), reasons=tuple(reasons)))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:limit]


def select_visual_icons_v2(
    items: list[VisualSelectionItem] | list[str] | list[dict[str, Any]],
    *,
    metadata_path: str | Path | None = None,
    embeddings_path: str | Path | None = None,
    embeddings_index_path: str | Path | None = None,
    onnx_model_dir: str | Path | None = None,
    prefer_style: str = "datagalaxy",
    allow_material_fallback: bool = True,
    per_item_candidates: int = 36,
    alternatives: int = 4,
    repo_root: str | Path | None = None,
) -> VisualIconSelection:
    normalized_items = normalize_visual_items(items)
    metadata = Path(metadata_path) if metadata_path else DEFAULT_VISUAL_METADATA_PATH
    icons = load_visual_metadata(metadata)
    model = EmbeddingModel.get(Path(onnx_model_dir) if onnx_model_dir else None)
    index = EmbeddingSearchIndex(
        icons,
        embeddings_path=Path(embeddings_path) if embeddings_path else DEFAULT_EMBEDDINGS_PATH,
        embeddings_index_path=Path(embeddings_index_path)
        if embeddings_index_path
        else DEFAULT_EMBEDDINGS_INDEX_PATH,
        model=model,
    )

    candidate_lists = [
        index.search(
            item,
            limit=per_item_candidates,
            prefer_style=prefer_style,
            allow_material_fallback=allow_material_fallback,
        )
        for item in normalized_items
    ]
    for item, candidates in zip(normalized_items, candidate_lists):
        if not candidates:
            raise ValueError(f"no candidates for item: {item.label or item.text!r}")

    selected = choose_coherent_visual_set(candidate_lists)

    choices: list[VisualIconChoice] = []
    warnings: list[str] = []
    for item, choice, candidates in zip(normalized_items, selected, candidate_lists, strict=True):
        if choice.icon.style != prefer_style:
            warnings.append(f"{item.label or item.text}: selected {choice.icon.style}, not {prefer_style}")
        rationale_parts = []
        if choice.icon.denotation:
            rationale_parts.append(f"Depicts: {'; '.join(choice.icon.denotation[:2])}.")
        if choice.icon.semantic_domains:
            rationale_parts.append(f"Domains: {', '.join(choice.icon.semantic_domains[:3])}.")
        if choice.icon.connotations:
            rationale_parts.append(f"Connotations: {', '.join(choice.icon.connotations[:3])}.")
        rationale_parts.append("; ".join(choice.reasons[:2]))
        choices.append(
            VisualIconChoice(
                item=item,
                icon=choice.icon,
                score=choice.score,
                rationale=" ".join(rationale_parts),
                alternatives=tuple(
                    candidate
                    for candidate in candidates
                    if candidate.icon.unique_name != choice.icon.unique_name
                )[:alternatives],
            )
        )

    return VisualIconSelection(
        choices=tuple(choices),
        warnings=tuple(warnings),
        metadata_path=str(metadata),
        metadata_sha256=sha256_file(metadata),
        repo_commit=git_commit(Path(repo_root) if repo_root else metadata.parents[1]),
        prefer_style=prefer_style,
        allow_material_fallback=allow_material_fallback,
    )
