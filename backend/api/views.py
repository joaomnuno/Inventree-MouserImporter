from __future__ import annotations

import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .importer.runner import ImporterError, ImporterRunner
from .serializers import (
    ImportRequestSerializer,
    ImporterCommitSerializer,
    ImporterLookupSerializer,
    PartNumberSerializer,
    PartResponseSerializer,
)
from .services import digikey, inventree, mouser
from inventree_part_import.part_importer import ImportResult

logger = logging.getLogger(__name__)
importer_runner = ImporterRunner()


def _build_preview_response(payload):
    part = payload.api_part
    price_breaks = [
        {
            "quantity": int(quantity),
            "price": float(price),
            "currency": part.currency,
        }
        for quantity, price in sorted((part.price_breaks or {}).items())
    ]
    parameters = [
        {"name": name, "value": value}
        for name, value in sorted((part.parameters or {}).items())
        if name and value
    ]
    stock_value = None
    if part.quantity_available is not None:
        try:
            stock_value = int(part.quantity_available)
        except (TypeError, ValueError):
            stock_value = None

    part_payload = {
        "name": part.MPN or part.description or "",
        "description": part.description or "",
        "manufacturer": part.manufacturer or "",
        "mpn": part.MPN or "",
        "supplier": payload.supplier_name,
        "supplier_company_id": getattr(payload.supplier_company, "pk", None),
        "supplier_sku": part.SKU or "",
        "category_path": part.category_path,
        "datasheet_url": part.datasheet_url or "",
        "image_url": part.image_url or "",
        "supplier_link": getattr(part, "supplier_link", ""),
        "stock": stock_value,
        "price_breaks": price_breaks,
        "parameters": parameters,
    }
    part_response = PartResponseSerializer(part_payload)

    warnings = []
    if payload.match_count > 1:
        warnings.append(
            f"Importer found {payload.match_count} matches; showing the closest result."
        )
    if not payload.matched_category:
        warnings.append("No category mapping matched. Update categories.yaml to map this part.")

    return {
        "supplier": payload.supplier,
        "supplier_name": payload.supplier_name,
        "part_number": payload.part_number,
        "match_count": payload.match_count,
        "part": part_response.data,
        "matched_category": payload.matched_category,
        "warnings": warnings,
    }


@ensure_csrf_cookie
def health_check(_request):
    return JsonResponse(
        {
            "status": "ok",
            "default_country": settings.DEFAULT_COUNTRY,
            "default_currency": settings.DEFAULT_CURRENCY,
        }
    )


class MouserSearchView(APIView):
    def post(self, request):
        serializer = PartNumberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            part = mouser.search_part(serializer.validated_data["part_number"])
        except ValueError as exc:
            logger.warning("Mouser search failed for %s: %s", serializer.validated_data["part_number"], exc)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        response = PartResponseSerializer(part)
        return Response(response.data)


class DigiKeySearchView(APIView):
    def post(self, request):
        serializer = PartNumberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            part = digikey.search_part(serializer.validated_data["part_number"])
        except ValueError as exc:
            logger.warning("Digi-Key search failed for %s: %s", serializer.validated_data["part_number"], exc)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        response = PartResponseSerializer(part)
        return Response(response.data)


class ImportPartView(APIView):
    def post(self, request):
        serializer = ImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        try:
            created_part = inventree.create_part_with_supplier(payload)
        except inventree.InvenTreeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(created_part, status=status.HTTP_201_CREATED)


class ImporterPreviewView(APIView):
    def post(self, request):
        serializer = ImporterLookupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            payload = importer_runner.preview(data["supplier"], data["part_number"])
        except ImporterError as exc:
            logger.warning("Importer preview failed for %s: %s", data["part_number"], exc)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_build_preview_response(payload))


class ImporterCommitView(APIView):
    def post(self, request):
        serializer = ImporterCommitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = importer_runner.import_part(
                data["supplier"], data["part_number"], overrides=data.get("overrides")
            )
        except ImporterError as exc:
            logger.error("Importer run failed for %s: %s", data["part_number"], exc)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        status_map = {
            ImportResult.SUCCESS: (status.HTTP_201_CREATED, "success"),
            ImportResult.INCOMPLETE: (status.HTTP_202_ACCEPTED, "incomplete"),
            ImportResult.FAILURE: (status.HTTP_400_BAD_REQUEST, "failure"),
            ImportResult.ERROR: (status.HTTP_502_BAD_GATEWAY, "error"),
        }
        http_status, label = status_map.get(result, (status.HTTP_200_OK, "unknown"))
        detail_map = {
            "success": "Part imported via inventree-part-import.",
            "incomplete": "Part imported with warnings; check backend logs for details.",
            "failure": "Importer could not create the part. Update configuration or try again.",
            "error": "Importer encountered an unexpected error.",
        }

        return Response({"status": label, "detail": detail_map.get(label)}, status=http_status)
