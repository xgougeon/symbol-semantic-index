from __future__ import annotations

import unittest

from material_symbol_semantic_index import IconSearchIndex, SelectionItem, load_catalog, select_icons


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


if __name__ == "__main__":
    unittest.main()

