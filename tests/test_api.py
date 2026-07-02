from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

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


if __name__ == "__main__":
    unittest.main()
