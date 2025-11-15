from __future__ import annotations

import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ImportRequestSerializer,
    PartNumberSerializer,
    PartResponseSerializer,
)
from .services import digikey, inventree, mouser

logger = logging.getLogger(__name__)


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
