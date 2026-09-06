"""Regression checks for removing visitor-owned uploads."""
import datetime as dt
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app


class UploadRemovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.visitor = "a" * 32
        self.patches = [
            patch.object(app, "UPLOADS", self.root / "uploads"),
            patch.object(app, "CASES_DIR", self.root / "cases"),
            patch.object(app.extract, "CACHE", self.root / "cache"),
        ]
        for item in self.patches:
            item.start()
        app.extract.CACHE.mkdir(parents=True)
        self.case = app.new_case(dt.date.today())
        self.case["visitor"] = self.visitor
        self.case["claim_type"] = "tenancy"
        path = app.UPLOADS / self.visitor / "E7" / "receipt.png"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"visitor-owned test file")
        asset = {"id": "E7", "filename": path.name, "kind": "image", "path": str(path),
                 "size_bytes": path.stat().st_size, "viewer_url": "/api/viewer?asset_id=E7&page_index=0",
                 "meta": {"author": "third_party", "dated": True, "has_amount": True}}
        fact = {"asset_id": "E7", "evidence_key": "deposit_paid", "fits": True,
                "fact": "Deposit paid", "category": "payment", "date": "2026-01-02", "amount": 1000}
        self.case["exhibits"] = [{"id": "E7", "kind": "image", "status": "ready",
                                   "title": path.name, "facts": [fact], "assets": [asset]}]
        with patch.object(app.llm, "write_text", return_value="Test text"):
            app.recompute(self.case)
        app.CASES[self.visitor] = self.case
        self.client = TestClient(app.app, cookies={"visitor": self.visitor})

    def tearDown(self):
        app.CASES.pop(self.visitor, None)
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_remove_deletes_file_facts_and_ranked_row(self):
        path = pathlib.Path(self.case["exhibits"][0]["assets"][0]["path"])
        self.assertTrue(self.case["exhibits"][0]["assets"][0]["removable"])
        self.assertEqual(len(self.case["evidence"]), 1)

        response = self.client.post("/api/upload/remove", json={"asset_id": "E7"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(path.exists())
        self.assertEqual(response.json()["exhibits"], [])
        self.assertEqual(response.json()["evidence"], [])
        saved = json.loads((app.CASES_DIR / f"{self.visitor}.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["exhibits"], [])

    def test_bundled_file_cannot_be_removed(self):
        bundled = app.PACK / "WhatsApp_01.png"
        asset = {"id": "sample", "filename": bundled.name, "kind": "image", "path": str(bundled),
                 "size_bytes": bundled.stat().st_size, "viewer_url": "/api/viewer?asset_id=sample&page_index=0",
                 "meta": {}, "removable": False}
        self.case["exhibits"] = [{"id": "sample", "kind": "image", "status": "ready",
                                   "title": bundled.name, "facts": [], "assets": [asset]}]
        self.case["_assessment_version"] = 2

        response = self.client.post("/api/upload/remove", json={"asset_id": "sample"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "not_removable")
        self.assertTrue(bundled.exists())


if __name__ == "__main__":
    unittest.main()
