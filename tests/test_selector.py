from __future__ import annotations

import unittest

from material_symbol_semantic_index import (
    IconSearchIndex,
    SelectionItem,
    VisualSelectionItem,
    load_catalog,
    load_visual_metadata,
    select_icons,
    select_visual_icons,
)


class IconSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.index = IconSearchIndex(cls.catalog)

    def test_loads_full_material_symbols_snapshot(self) -> None:
        self.assertGreater(len(self.catalog), 4000)
        self.assertTrue(any(icon.name == "schema" for icon in self.catalog))

    def test_search_prefers_data_structure_icons(self) -> None:
        results = self.index.search("structured data model and governed taxonomy", limit=12)
        names = [result.icon.name for result in results]
        self.assertTrue({"schema", "database", "account_tree", "category"} & set(names))

    def test_selects_distinct_neighboring_icons(self) -> None:
        selection = select_icons(
            [
                SelectionItem(
                    label="truth",
                    text="Create a single source of truth for governed data products.",
                ),
                SelectionItem(
                    label="workflow",
                    text="Automate workflows so teams can reuse trusted context.",
                ),
                SelectionItem(
                    label="insight",
                    text="Surface insights before quality issues reach customers.",
                ),
            ]
        )
        names = [choice.icon.name for choice in selection.choices]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(selection.choices), 3)
        self.assertTrue(all(choice.alternatives for choice in selection.choices))

    def test_loads_visual_metadata_with_datagalaxy_icons(self) -> None:
        visual_catalog = load_visual_metadata()
        self.assertGreater(len(visual_catalog), 2000)
        self.assertTrue(any(icon.style == "datagalaxy" for icon in visual_catalog))

    def test_visual_selector_prefers_datagalaxy_icons_by_default(self) -> None:
        selection = select_visual_icons(
            [
                VisualSelectionItem(
                    label="truth",
                    text="Create a single source of truth for governed data products.",
                )
            ]
        )
        self.assertEqual(selection.choices[0].icon.style, "datagalaxy")
        self.assertTrue(selection.choices[0].icon.source_path.endswith(".png"))

    def test_visual_selector_can_use_material_fallback_for_insight(self) -> None:
        selection = select_visual_icons(
            ["Surface insights before quality issues reach customers."],
            allow_material_fallback=True,
        )
        self.assertEqual(selection.choices[0].icon.unique_name, "material-symbol:analytics")
        self.assertTrue(selection.warnings)


if __name__ == "__main__":
    unittest.main()
