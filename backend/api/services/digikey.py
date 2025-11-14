from __future__ import annotations

import os
import time
from typing import Any

import requests

TOKEN_URL = os.environ.get("DIGIKEY_TOKEN_URL", "https://api.digikey.com/v1/token")
PRODUCT_DETAILS_URL = os.environ.get(
    "DIGIKEY_PRODUCT_DETAILS_URL", "https://api.digikey.com/services/products/v4/productdetails"
)

_access_token: str | None = None
_token_expiry: float = 0.0


def _supplier_company_id() -> int | None:
    value = os.environ.get("INVENTREE_DIGIKEY_COMPANY_ID")
    return int(value) if value else None


def _credentials() -> tuple[str, str]:
    client_id = os.environ.get("DIGIKEY_CLIENT_ID")
    client_secret = os.environ.get("DIGIKEY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Digi-Key credentials are not configured")
    return client_id, client_secret


def _refresh_token() -> None:
    global _access_token, _token_expiry
    client_id, client_secret = _credentials()
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    _access_token = payload["access_token"]
    _token_expiry = time.time() + payload.get("expires_in", 1800) - 30


def _token() -> str:
    global _access_token, _token_expiry
    if not _access_token or time.time() >= _token_expiry:
        _refresh_token()
    assert _access_token
    return _access_token


def _normalize_part(part: dict[str, Any]) -> dict[str, Any]:
    parameters = [
        {"name": spec.get("Parameter"), "value": spec.get("Value")}
        for spec in part.get("ProductAttributes", [])
        if spec.get("Parameter") and spec.get("Value")
    ]

    price_breaks = [
        {
            "quantity": int(price.get("BreakQuantity", 0)),
            "price": float(price.get("Price", 0)),
            "currency": price.get("Currency", "EUR"),
        }
        for price in part.get("StandardPricing", [])
        if price.get("BreakQuantity")
    ]

    return {
        "name": part.get("ProductDescription", part.get("ManufacturerPartNumber", "")),
        "description": part.get("ProductDescription", ""),
        "manufacturer": part.get("ManufacturerName", ""),
        "mpn": part.get("ManufacturerPartNumber", ""),
        "supplier": "Digi-Key",
        "supplier_company_id": _supplier_company_id(),
        "supplier_sku": part.get("DigiKeyPartNumber", ""),
        "category_path": [c.get("Name", "") for c in part.get("Categories", []) if c.get("Name")],
        "datasheet_url": part.get("PrimaryDatasheet", ""),
        "image_url": (part.get("PrimaryPhoto") or {}).get("Href", ""),
        "stock": part.get("QuantityAvailable"),
        "lead_time_weeks": part.get("LeadTime", {}).get("Value"),
        "price_breaks": price_breaks,
        "parameters": parameters,
    }


def search_part(part_number: str) -> dict[str, Any]:
    client_id, _ = _credentials()
    token = _token()
    response = requests.get(
        f"{PRODUCT_DETAILS_URL}/{part_number}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-DIGIKEY-Client-Id": client_id,
        },
        timeout=30,
    )
    if response.status_code == 404:
        raise ValueError("Digi-Key part not found")
    response.raise_for_status()
    return _normalize_part(response.json())
