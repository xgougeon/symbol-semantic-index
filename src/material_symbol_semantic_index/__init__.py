"""Semantic retrieval and set-aware selection for Google Material Symbols."""

from .catalog import IconRecord, load_catalog
from .search import IconSearchIndex
from .selector import IconSetSelection, SelectionItem, select_icons
from .visual_selector import (
    VisualIconSelection,
    VisualMetadataSearchIndex,
    VisualSelectionItem,
    load_visual_metadata,
    select_visual_icons,
)

__all__ = [
    "IconRecord",
    "IconSearchIndex",
    "IconSetSelection",
    "SelectionItem",
    "VisualIconSelection",
    "VisualMetadataSearchIndex",
    "VisualSelectionItem",
    "load_catalog",
    "load_visual_metadata",
    "select_icons",
    "select_visual_icons",
]
