from __future__ import annotations

import os
from typing import Any

import requests


class InvenTreeError(RuntimeError):
    pass


def _config() -> tuple[str, str]:
    base_url = os.environ.get("INVENTREE_BASE_URL")
    token = os.environ.get("INVENTREE_TOKEN")
    if not base_url or not token:
        raise InvenTreeError("Inventree API credentials are missing")
    return base_url.rstrip("/"), token


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    base_url, token = _config()
    response = requests.post(f"{base_url}{path}", json=payload, headers=_headers(token), timeout=30)
    if response.status_code >= 400:
        raise InvenTreeError(response.text)
    return response.json()


def _ensure_category(category_path: list[str] | None) -> int | None:
    # In a minimal implementation, expect category_id to be passed in.
    # The hook is provided for future automatic creation.
    return None


def create_part_with_supplier(payload: dict[str, Any]) -> dict[str, Any]:
    category_id = payload.get("category_id") or _ensure_category(payload.get("category_path"))
    if not category_id:
        raise InvenTreeError("Category id is required to create a part in InvenTree")

    part_body = {
        "name": payload.get("name"),
        "description": payload.get("description"),
        "category": category_id,
        "purchaseable": payload.get("purchaseable", True),
        "trackable": payload.get("trackable", False),
    }

    created_part = _post("/api/part/", part_body)
    part_id = created_part.get("pk") or created_part.get("id")

    supplier_company_id = payload.get("supplier_company_id")
    supplier_sku = payload.get("supplier_sku")
    if supplier_company_id and supplier_sku:
        supplier_body = {
            "part": part_id,
            "SKU": supplier_sku,
            "supplier": supplier_company_id,
            "MPN": payload.get("mpn"),
        }
        _post("/api/company/part/", supplier_body)

    for parameter in payload.get("parameters", []):
        param_body = {
            "part": part_id,
            "name": parameter.get("name"),
            "data": parameter.get("value"),
        }
        _post("/api/part/parameter/", param_body)

    return created_part
