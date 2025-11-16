from __future__ import annotations

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from inventree_part_import.part_importer import ImportResult
from unittest.mock import patch

from .serializers import ImportRequestSerializer
from .views import ImporterCommitView, ImporterPreviewView


class ImportRequestSerializerTest(SimpleTestCase):
    def test_requires_category_hint(self) -> None:
        serializer = ImportRequestSerializer(data={"name": "test", "supplier": "Mouser", "supplier_sku": "1"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_accepts_category_id(self) -> None:
        serializer = ImportRequestSerializer(
            data={
                "name": "test",
                "supplier": "Mouser",
                "supplier_sku": "1",
                "category_id": 10,
            }
        )
        self.assertTrue(serializer.is_valid())


class ImporterViewTest(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()

    @patch("api.views.importer_runner")
    def test_preview_view_returns_payload(self, importer_runner_mock):
        api_part = type(
            "ApiPart",
            (),
            {
                "MPN": "ABC123",
                "description": "Demo part",
                "manufacturer": "Acme",
                "SKU": "ABC123",
                "category_path": ["Electronics", "Connectors"],
                "datasheet_url": "https://example.com/ds.pdf",
                "image_url": "https://example.com/img.png",
                "supplier_link": "https://supplier/item",
                "quantity_available": 50,
                "price_breaks": {1: 0.5},
                "parameters": {"Voltage": "5V"},
                "currency": "USD",
            },
        )()
        supplier_company = type("Company", (), {"pk": 7, "name": "Mouser"})()
        payload = type(
            "Payload",
            (),
            {
                "supplier": "mouser",
                "supplier_name": "Mouser",
                "supplier_company": supplier_company,
                "part_number": "ABC123",
                "match_count": 1,
                "api_part": api_part,
                "matched_category": ["Electronics", "Connectors"],
            },
        )()
        importer_runner_mock.preview.return_value = payload

        request = self.factory.post(
            "/api/importer/preview/", {"supplier": "mouser", "part_number": "ABC123"}, format="json"
        )
        response = ImporterPreviewView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["part"]["supplier"], "Mouser")
        importer_runner_mock.preview.assert_called_once()

    @patch("api.views.importer_runner")
    def test_commit_view_success(self, importer_runner_mock):
        importer_runner_mock.import_part.return_value = ImportResult.SUCCESS

        request = self.factory.post(
            "/api/importer/import/",
            {"supplier": "mouser", "part_number": "ABC123", "overrides": {"mpn": "ABC123"}},
            format="json",
        )
        response = ImporterCommitView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "success")
        importer_runner_mock.import_part.assert_called_once()
