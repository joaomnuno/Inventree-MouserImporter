from __future__ import annotations

from django.test import SimpleTestCase

from .serializers import ImportRequestSerializer


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
