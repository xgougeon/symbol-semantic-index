from __future__ import annotations

import io
import unittest

from fastapi.testclient import TestClient
from PIL import Image

from material_symbol_semantic_index.api.main import app

client = TestClient(app)


class HealthTests(unittest.TestCase):
    def test_health_ok(self) -> None:
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("service_version", body)


class SelectIconTests(unittest.TestCase):
    def test_select_returns_icon_and_metadata(self) -> None:
        response = client.post(
            "/v1/icons/select",
            json={"text": "Establish a single source of truth for governed data products."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["icon"]["icon_id"])
        self.assertIn("asset_ref", body)
        self.assertIsInstance(body["score"], float)
        self.assertIsInstance(body["rationale"], str)
        self.assertIsInstance(body["alternatives"], list)
        self.assertIsInstance(body["warnings"], list)
        self.assertTrue(body["metadata_sha256"])
        self.assertTrue(body["service_version"])

    def test_select_honors_alternatives_and_optional_fields(self) -> None:
        response = client.post(
            "/v1/icons/select",
            json={
                "text": "Automate workflows so teams can reuse trusted context.",
                "tone": "confident",
                "context": "slide about automation",
                "allow_material_fallback": True,
                "avoid": ["security"],
                "alternatives": 2,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertLessEqual(len(body["alternatives"]), 2)

    def test_select_respects_prefer_style(self) -> None:
        response = client.post(
            "/v1/icons/select",
            json={
                "text": "Surface insights before quality issues reach customers.",
                "prefer_style": "material-symbol-rounded",
                "allow_material_fallback": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["icon"]["style"], "material-symbol-rounded")

    def test_missing_text_returns_400(self) -> None:
        response = client.post("/v1/icons/select", json={})
        self.assertEqual(response.status_code, 400)

    def test_blank_text_returns_400(self) -> None:
        response = client.post("/v1/icons/select", json={"text": "   "})
        self.assertEqual(response.status_code, 400)

    def test_text_too_long_returns_400(self) -> None:
        response = client.post("/v1/icons/select", json={"text": "a" * 2001})
        self.assertEqual(response.status_code, 400)

    def test_wrong_type_returns_400(self) -> None:
        response = client.post("/v1/icons/select", json={"text": 123})
        self.assertEqual(response.status_code, 400)


class SelectIconsBatchTests(unittest.TestCase):
    def test_batch_returns_one_choice_per_item_and_is_coherent(self) -> None:
        response = client.post(
            "/v1/icons/select-batch",
            json={
                "items": [
                    {"text": "Establish a single source of truth for governed data products.", "label": "truth"},
                    {"text": "Automate workflows so teams can reuse trusted context.", "label": "workflow"},
                    {"text": "Surface insights before quality issues reach customers.", "label": "insight"},
                ]
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["choices"]), 3)
        labels = [c["label"] for c in body["choices"]]
        self.assertEqual(labels, ["truth", "workflow", "insight"])
        icon_ids = [c["icon"]["icon_id"] for c in body["choices"]]
        self.assertEqual(len(icon_ids), len(set(icon_ids)))  # coherent set: no duplicate icons

    def test_batch_empty_items_returns_400(self) -> None:
        response = client.post("/v1/icons/select-batch", json={"items": []})
        self.assertEqual(response.status_code, 400)

    def test_batch_blank_item_text_returns_400(self) -> None:
        response = client.post("/v1/icons/select-batch", json={"items": [{"text": "   "}]})
        self.assertEqual(response.status_code, 400)


class AssetRecolorTests(unittest.TestCase):
    def _first_asset_path(self) -> str:
        response = client.post(
            "/v1/icons/select",
            json={"text": "Establish a single source of truth for governed data products."},
        )
        asset_ref = response.json()["asset_ref"]
        return "/" + asset_ref.split("/assets/", 1)[1]

    def test_plain_asset_returns_png(self) -> None:
        path = self._first_asset_path()
        response = client.get(f"/assets{path}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")

    def test_recolored_asset_matches_requested_color(self) -> None:
        path = self._first_asset_path()
        response = client.get(f"/assets{path}", params={"color": "red"})
        self.assertEqual(response.status_code, 200)
        image = Image.open(io.BytesIO(response.content)).convert("RGBA")
        opaque_pixels = [p for p in image.getdata() if p[3] > 200]
        self.assertTrue(opaque_pixels)
        self.assertTrue(all(p[:3] == (255, 0, 64) for p in opaque_pixels))

    def test_unknown_color_returns_400(self) -> None:
        path = self._first_asset_path()
        response = client.get(f"/assets{path}", params={"color": "purple"})
        self.assertEqual(response.status_code, 400)

    def test_unknown_asset_returns_404(self) -> None:
        response = client.get("/assets/does/not/exist.png")
        self.assertEqual(response.status_code, 404)

    def test_path_traversal_returns_404(self) -> None:
        response = client.get("/assets/../../pyproject.toml")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
