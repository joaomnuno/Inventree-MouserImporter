from __future__ import annotations

import os
import re
from typing import Any

import requests

MOUSER_URL = "https://api.mouser.com/api/v1/search/partnumber"


def _supplier_company_id() -> int | None:
    value = os.environ.get("INVENTREE_MOUSER_COMPANY_ID")
    return int(value) if value else None


def _require_key() -> str:
    key = os.environ.get("MOUSER_API_KEY")
    if not key:
        raise RuntimeError("MOUSER_API_KEY is not configured")
    return key


def _normalize_part(part: dict[str, Any]) -> dict[str, Any]:
    def _parse_stock(value: str | None) -> int | None:
        if not value:
            return None
        digits = re.findall(r"\d+", value.replace(",", ""))
        if not digits:
            return None
        return int(digits[0])
    price_breaks = [
        {
            "quantity": int(pb.get("Quantity", 0)),
            "price": float(pb.get("Price", 0)),
            "currency": pb.get("Currency", "EUR"),
        }
        for pb in part.get("PriceBreaks", [])
        if pb.get("Quantity")
    ]

    parameters = [
        {"name": param.get("Name", ""), "value": param.get("Value", "")}
        for param in part.get("ProductAttributes", [])
        if param.get("Name") and param.get("Value")
    ]

    category_path = []
    if part.get("Category"):
        category_path = [p.strip() for p in part["Category"].split("->")]

    return {
        "name": part.get("Description", part.get("ManufacturerPartNumber", "")),
        "description": part.get("Description", ""),
        "manufacturer": part.get("Manufacturer", ""),
        "mpn": part.get("ManufacturerPartNumber", ""),
        "supplier": "Mouser",
        "supplier_company_id": _supplier_company_id(),
        "supplier_sku": part.get("MouserPartNumber", ""),
        "category_path": category_path,
        "datasheet_url": part.get("DataSheetUrl", ""),
        "image_url": part.get("ImagePath", ""),
        "stock": _parse_stock(part.get("Availability")),
        "lead_time_weeks": part.get("LeadTimeWeeks"),
        "price_breaks": price_breaks,
        "parameters": parameters,
    }


def search_part(part_number: str) -> dict[str, Any]:
    key = _require_key()
    response = requests.post(
        f"{MOUSER_URL}?apikey={key}",
        json={"SearchByPartNumberRequest": {"mouserPartNumber": part_number}},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    parts = data.get("SearchResults", {}).get("Parts", [])
    if not parts:
        raise ValueError("No Mouser parts were found for the requested number")
    return _normalize_part(parts[0])
