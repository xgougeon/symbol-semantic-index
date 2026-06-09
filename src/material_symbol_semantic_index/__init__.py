"""Semantic retrieval and set-aware selection for Google Material Symbols."""

from .catalog import IconRecord, load_catalog
from .search import IconSearchIndex
from .selector import IconSetSelection, SelectionItem, select_icons

__all__ = [
    "IconRecord",
    "IconSearchIndex",
    "IconSetSelection",
    "SelectionItem",
    "load_catalog",
    "select_icons",
]

