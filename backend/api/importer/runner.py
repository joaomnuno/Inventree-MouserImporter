from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from inventree_part_import.categories import setup_categories_and_parameters
from inventree_part_import.cli import DryInvenTreeAPI
from inventree_part_import.part_importer import ImportResult, PartImporter
from inventree_part_import.retries import RetryInvenTreeAPI
from inventree_part_import.inventree_helpers import Company
from inventree_part_import.suppliers import get_suppliers, search, setup_supplier_companies
from inventree_part_import.suppliers.base import ApiPart

from .configuration import ImporterConfiguration, ImporterConfigurationError

logger = logging.getLogger(__name__)


@dataclass
class PreviewPayload:
    supplier: str
    supplier_name: str
    supplier_company: Company
    part_number: str
    match_count: int
    api_part: ApiPart
    matched_category: list[str] | None


class ImporterError(RuntimeError):
    pass


class ImporterRunner:
    def __init__(self, configuration: ImporterConfiguration | None = None) -> None:
        self.configuration = configuration or ImporterConfiguration()
        self._category_map = None
        self._parameter_map = None
        self._suppliers_ready = False

    # -----------------
    # Public interface
    # -----------------

    def preview(self, supplier: str, part_number: str) -> PreviewPayload:
        dry_api = DryInvenTreeAPI()
        self._prepare_environment(dry_api, reload_suppliers=False)
        payload = self._fetch_part(supplier, part_number)
        payload.api_part.finalize()
        payload.matched_category = self._match_category(payload.api_part)
        return payload

    def import_part(
        self,
        supplier: str,
        part_number: str,
        overrides: dict[str, Any] | None = None,
    ) -> ImportResult:
        api = self._inventree_api()
        self._prepare_environment(api, reload_suppliers=True)
        importer = PartImporter(api, interactive=False, verbose=False)
        payload = self._fetch_part(supplier, part_number)
        if overrides:
            self._apply_overrides(payload.api_part, overrides)
        result = importer.import_supplier_part(payload.supplier_company, payload.api_part)
        return result

    # -----------------
    # Internal helpers
    # -----------------

    def _prepare_environment(self, inventree_api, reload_suppliers: bool) -> None:
        try:
            self.configuration.ensure()
        except ImporterConfigurationError as exc:
            raise ImporterError(str(exc)) from exc

        force_reload = reload_suppliers or not self._suppliers_ready
        get_suppliers(reload=force_reload)
        self._suppliers_ready = True
        setup_supplier_companies(inventree_api)

        if self._category_map is None or reload_suppliers:
            self._category_map, self._parameter_map = setup_categories_and_parameters(
                inventree_api
            )

    def _fetch_part(self, supplier: str, part_number: str) -> PreviewPayload:
        part_number = part_number.strip()
        if not part_number:
            raise ImporterError("Part number is required")

        results = list(search(part_number, supplier_id=supplier, only_supplier=True))
        if not results:
            raise ImporterError(f"Supplier '{supplier}' is not configured")

        supplier_company, async_result = results[0]
        parts, result_count = async_result.get()
        if not parts:
            raise ImporterError("No parts returned by supplier search")

        api_part = self._select_part(parts, part_number)
        return PreviewPayload(
            supplier=supplier,
            supplier_name=supplier_company.name,
            supplier_company=supplier_company,
            part_number=part_number,
            match_count=result_count,
            api_part=api_part,
            matched_category=None,
        )

    def _select_part(self, candidates: list[ApiPart], query: str) -> ApiPart:
        query_lower = query.lower()
        exact_matches = [
            candidate
            for candidate in candidates
            if candidate.SKU.lower() == query_lower or candidate.MPN.lower() == query_lower
        ]
        if exact_matches:
            return exact_matches[0]
        return candidates[0]

    def _match_category(self, api_part: ApiPart) -> list[str] | None:
        if not self._category_map:
            return None
        for candidate in reversed(api_part.category_path):
            category = self._category_map.get(candidate.lower())
            if category:
                return category.path
        return None

    def _apply_overrides(self, api_part: ApiPart, overrides: dict[str, Any]) -> None:
        if description := overrides.get("description"):
            api_part.description = description
        if manufacturer := overrides.get("manufacturer"):
            api_part.manufacturer = manufacturer
        if mpn := overrides.get("mpn"):
            api_part.MPN = mpn
        if sku := overrides.get("supplier_sku"):
            api_part.SKU = sku
        if category_path := overrides.get("category_path"):
            api_part.category_path = [str(value) for value in category_path if value]
        if datasheet := overrides.get("datasheet_url"):
            api_part.datasheet_url = datasheet
        if image := overrides.get("image_url"):
            api_part.image_url = image
        if parameters := overrides.get("parameters"):
            api_part.parameters = {
                param["name"]: param["value"]
                for param in parameters
                if param.get("name") and param.get("value") is not None
            }
        if price_breaks := overrides.get("price_breaks"):
            api_part.price_breaks = {
                int(item["quantity"]): float(item["price"])
                for item in price_breaks
                if "quantity" in item and "price" in item
            }

    def _inventree_api(self):
        base_url = settings.INVENTREE_BASE_URL
        token = settings.INVENTREE_TOKEN
        if not base_url or not token:
            raise ImporterError("INVENTREE_BASE_URL and INVENTREE_TOKEN are required")
        timeout = settings.IMPORTER_REQUEST_TIMEOUT
        return RetryInvenTreeAPI(host=base_url, token=token, timeout=timeout)


__all__ = ["ImporterRunner", "ImporterError", "PreviewPayload"]
