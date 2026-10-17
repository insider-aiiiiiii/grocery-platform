from decimal import Decimal

from rest_framework import serializers

from catalog.models import ProductVariant, ShopProduct
from inventory.models import InventoryItem
from shops.models import Shop


def validate_product_orderable_and_available(
    shop: Shop,
    product: ShopProduct,
    variant: ProductVariant | None = None,
    requested_quantity: Decimal = Decimal("1.000"),
    current_item_quantity: Decimal = Decimal("0.000"),
) -> None:
    """
    Validates that a product/variant is valid for ordering in the specified Shop context:
    1. Multi-tenancy: product and variant must belong to the cart's Shop.
    2. Variant integrity: variant must belong to product; variant required if product has variants;
       variant prohibited if product has no variants.
    3. Catalog visibility: product and variant must be visible (not hidden).
    4. Catalog manual availability: product and variant must be manually available.
    5. Inventory stock: must be in stock (available_quantity > 0) and total requested quantity
       (current_item_quantity + requested_quantity) must not exceed available stock.
    """
    # 1. Multi-tenancy check
    if product.shop_id != shop.id:
        raise serializers.ValidationError({"product_id": f"Product #{product.id} does not belong to this Shop."})

    # 2. Variant integrity
    if product.has_variants:
        if not variant:
            raise serializers.ValidationError({"variant_id": "A variant must be selected for this product."})
        if variant.product_id != product.id:
            raise serializers.ValidationError({"variant_id": f"Variant #{variant.id} does not belong to Product #{product.id}."})
        if variant.product.shop_id != shop.id:
            raise serializers.ValidationError({"variant_id": f"Variant #{variant.id} does not belong to this Shop."})
    else:
        if variant:
            raise serializers.ValidationError({"variant_id": "Variants cannot be specified for products without variants."})

    # 3. Catalog visibility
    if not product.is_visible:
        raise serializers.ValidationError({"product_id": "Product is not visible and cannot be ordered."})
    if variant and not variant.is_customer_visible:
        raise serializers.ValidationError({"variant_id": "Variant is not visible and cannot be ordered."})

    # 4. Catalog manual availability
    if not product.is_available:
        raise serializers.ValidationError({"product_id": "Product is currently unavailable and cannot be ordered."})
    if variant and (not variant.is_available or not product.is_available):
        raise serializers.ValidationError({"variant_id": "Variant is currently unavailable and cannot be ordered."})

    # 5. Inventory availability
    if variant:
        inv = InventoryItem.objects.filter(shop=shop, variant=variant).first()
    else:
        inv = InventoryItem.objects.filter(shop=shop, product=product, variant__isnull=True).first()

    available_stock = inv.available_quantity if inv else Decimal("0.000")

    if available_stock <= Decimal("0.000"):
        target_name = "Variant" if variant else "Product"
        raise serializers.ValidationError({"stock": f"{target_name} is out of stock."})

    total_target_quantity = current_item_quantity + requested_quantity
    if total_target_quantity > available_stock:
        raise serializers.ValidationError({
            "quantity": f"Requested quantity ({total_target_quantity}) exceeds available stock ({available_stock})."
        })
