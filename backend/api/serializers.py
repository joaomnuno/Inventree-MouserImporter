from __future__ import annotations

from typing import Any

from rest_framework import serializers


class PriceBreakSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.FloatField(min_value=0)
    currency = serializers.CharField()


class ParameterSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.CharField()


class PartResponseSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    manufacturer = serializers.CharField(allow_blank=True, required=False)
    mpn = serializers.CharField(allow_blank=True, required=False)
    supplier = serializers.CharField()
    supplier_company_id = serializers.IntegerField(required=False)
    supplier_sku = serializers.CharField(allow_blank=True, required=False)
    category_path = serializers.ListField(child=serializers.CharField(), required=False)
    datasheet_url = serializers.CharField(allow_blank=True, required=False)
    image_url = serializers.CharField(allow_blank=True, required=False)
    stock = serializers.IntegerField(required=False)
    lead_time_weeks = serializers.IntegerField(required=False)
    price_breaks = PriceBreakSerializer(many=True, required=False)
    parameters = ParameterSerializer(many=True, required=False)


class PartNumberSerializer(serializers.Serializer):
    part_number = serializers.CharField()


class ImportRequestSerializer(PartResponseSerializer):
    category_id = serializers.IntegerField(required=False)
    purchaseable = serializers.BooleanField(default=True)
    trackable = serializers.BooleanField(default=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)
        if not attrs.get("category_id") and not attrs.get("category_path"):
            raise serializers.ValidationError(
                "Either category_id or category_path must be provided so the part can be placed in InvenTree."
            )
        return attrs
