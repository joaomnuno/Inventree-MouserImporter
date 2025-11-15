from __future__ import annotations

import os
import re
import json
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

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

    def _parse_price(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return None
        cleaned = re.sub(r"[^0-9.,-]", "", value)
        if not cleaned:
            return None
        if "," in cleaned and "." not in cleaned:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            logger.warning("Unable to parse price '%s' from Mouser", value)
            return None
    price_breaks = []
    for pb in part.get("PriceBreaks", []) or []:
        if not pb.get("Quantity"):
            continue
        price_value = _parse_price(pb.get("Price"))
        if price_value is None:
            continue
        price_breaks.append(
            {
                "quantity": int(pb.get("Quantity", 0)),
                "price": price_value,
                "currency": pb.get("Currency", "EUR"),
            }
        )

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

def _format_errors(errors: Any) -> str:
    candidates: list[str] = []

    if isinstance(errors, dict):
        nested = errors.get("Errors") or errors.get("Error")
        if nested:
            errors = nested
        else:
            return json.dumps(errors)

    if isinstance(errors, (list, tuple)):
        for error in errors:
            if isinstance(error, dict):
                code = error.get("Code")
                message = error.get("Message") or error.get("Description")
                info = error.get("AdditionalInformation")
                pieces = [piece for piece in (message, info) if piece]
                summary = ": ".join(pieces) if pieces else "Unknown error"
                candidates.append(f"{code}: {summary}" if code else summary)
            else:
                candidates.append(str(error))
        return "; ".join(candidate for candidate in candidates if candidate) or "Unknown error"

    return str(errors)


def search_part(part_number: str) -> dict[str, Any]:
    key = _require_key()
    payload = {
        "SearchByPartRequest": {
            "mouserPartNumber": part_number,
        }
    }
    logger.info("Mouser request %s -> %s payload=%s", part_number, MOUSER_URL, payload)

    response = requests.post(
        MOUSER_URL,
        params={"apiKey": key},
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    logger.info(
        "Mouser response %s -> status=%s body=%s",
        part_number,
        response.status_code,
        response.text,
    )
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:  # pragma: no cover - defensive
        logger.exception("Failed to parse Mouser response for %s", part_number)
        raise RuntimeError("Unable to parse response from Mouser API") from exc

    if not isinstance(data, dict):
        logger.error("Unexpected Mouser payload type for %s: %s", part_number, type(data))
        raise RuntimeError("Unexpected Mouser API payload")

    errors = data.get("Errors")
    if errors:
        message = _format_errors(errors)
        logger.warning("Mouser API reported errors for %s: %s", part_number, message)
        raise ValueError(f"Mouser API error for {part_number}: {message}")

    search_results = data.get("SearchResults") or {}
    parts = search_results.get("Parts") or []
    if not parts:
        logger.info("Mouser search returned no parts for %s", part_number)
        raise ValueError("No Mouser parts were found for the requested number")
    return _normalize_part(parts[0])
