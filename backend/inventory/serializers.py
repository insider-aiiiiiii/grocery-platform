from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from catalog.models import ProductVariant, ShopProduct
from .models import InventoryItem, quantize_quantity


class MerchantInventoryItemSerializer(serializers.ModelSerializer):
    """
    Serializer for Merchant view of an InventoryItem.
    Exposes only approved fields: quantity, reserved_quantity, available_quantity,
    is_out_of_stock, and target references.
    No movement history, thresholds, or alerts are exposed in MVP.
    """

    product_name = serializers.CharField(source="product.name", read_only=True)
    variant_name = serializers.CharField(source="variant.name", read_only=True, default=None)
    sku = serializers.SerializerMethodField()
    available_quantity = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    has_variants = serializers.BooleanField(source="product.has_variants", read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "product",
            "product_name",
            "variant",
            "variant_name",
            "sku",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "is_out_of_stock",
            "has_variants",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "product",
            "product_name",
            "variant",
            "variant_name",
            "sku",
            "reserved_quantity",
            "available_quantity",
            "is_out_of_stock",
            "has_variants",
            "created_at",
            "updated_at",
        ]

    def get_sku(self, obj) -> str | None:
        if obj.variant and obj.variant.sku:
            return obj.variant.sku
        return obj.product.sku


class MerchantStockUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating Merchant inventory.
    Supports setting exact stock, adding stock, or subtracting stock.
    """

    ACTION_SET = "set"
    ACTION_ADD = "add"
    ACTION_SUBTRACT = "subtract"

    ACTION_CHOICES = [
        (ACTION_SET, "Set exact stock quantity"),
        (ACTION_ADD, "Add to stock"),
        (ACTION_SUBTRACT, "Subtract from stock"),
    ]

    action = serializers.ChoiceField(choices=ACTION_CHOICES, default=ACTION_SET)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        required=False,
        allow_null=True,
    )
    set_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        required=False,
        allow_null=True,
    )
    delta = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        action = attrs.get("action", self.ACTION_SET)
        quantity = attrs.get("quantity")
        set_quantity = attrs.get("set_quantity")
        delta = attrs.get("delta")

        # Determine effective quantity based on parameters provided
        if set_quantity is not None:
            action = self.ACTION_SET
            qty = set_quantity
        elif delta is not None:
            if delta >= Decimal("0.000"):
                action = self.ACTION_ADD
                qty = delta
            else:
                action = self.ACTION_SUBTRACT
                qty = abs(delta)
        elif quantity is not None:
            qty = quantity
        else:
            raise serializers.ValidationError(
                {"quantity": "Must provide 'quantity', 'set_quantity', or 'delta'."}
            )

        try:
            qty = quantize_quantity(qty)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"quantity": list(e.messages)}) from e

        if action in (self.ACTION_ADD, self.ACTION_SUBTRACT) and qty <= Decimal("0.000"):
            msg = (
                "Quantity to add must be greater than zero."
                if action == self.ACTION_ADD
                else "Quantity to subtract must be greater than zero."
            )
            raise serializers.ValidationError({"quantity": msg})

        attrs["effective_action"] = action
        attrs["effective_quantity"] = qty
        return attrs


class ProductVariantInventorySerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    variant_name = serializers.CharField()
    sku = serializers.CharField(allow_null=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    reserved_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    available_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    is_out_of_stock = serializers.BooleanField()


class ProductInventoryDetailSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    has_variants = serializers.BooleanField()
    is_derived = serializers.BooleanField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    reserved_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    available_quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    is_out_of_stock = serializers.BooleanField()
    variants = ProductVariantInventorySerializer(many=True, required=False)
