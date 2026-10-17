"""
Domain services for the Cart application.

Provides Cart validation against current Shop Catalog and Inventory state.
Enforces multi-tenancy, catalog visibility, manual availability, variant integrity,
and real-time stock availability without deciding unresolved Orders-domain rules.
"""
from decimal import Decimal
from typing import Any, Dict, List

from catalog.models import ProductVariant, ShopProduct
from inventory.models import InventoryItem
from shops.models import Shop

from .models import Cart, CartItem


ORDERS_DEPENDENCIES_NOTE = {
    "price_snapshot_strategy": (
        "Historical purchase price snapshotting is owned by the Orders domain at Order creation. "
        "Cart validation uses the current valid Shop Catalog price for live total recalculation."
    ),
    "cart_expiration": (
        "Cart expiration duration and persistence/cleanup mechanics are unresolved in Cart "
        "and deferred to platform configuration and the Orders design."
    ),
    "quantity_limits": (
        "Per-order or per-customer maximum quantity limits and fractional quantity policies "
        "remain unresolved in Cart and will be enforced by Orders/Catalog specifications."
    ),
    "checkout_fulfillment": (
        "Fulfillment eligibility (Pickup vs Home Delivery, valid delivery address, and delivery charge applicability) "
        "is owned by the Orders and Shops checkout design."
    ),
    "stock_reservation": (
        "Cart validation verifies real-time stock availability only. "
        "Stock is NOT reserved during cart validation; reservation occurs upon Order creation."
    ),
    "cart_clearing": (
        "Cart clearing occurs only upon successful Order creation. "
        "Failed checkout or cart validation leaves the cart intact."
    ),
}


def validate_cart_state(cart: Cart) -> Dict[str, Any]:
    """
    Validates the entire state of a Cart against current Shop, Catalog, and Inventory states:
    1. Shop Status: The shop must exist and be ACTIVE.
    2. Empty Cart Check: A cart without items cannot be checked out.
    3. Item-by-item Validation:
       - Existence & Multi-tenancy: Product and variant must exist and belong to the Cart's Shop.
       - Variant Integrity: Products with variants require a variant; products without variants prohibit variants.
       - Catalog Visibility: Product must be visible (is_visible=True); variant must be customer visible.
       - Catalog Manual Availability: Product and variant must be manually available (is_available=True).
       - Inventory Availability: Stock must be > 0 and available_quantity >= requested_quantity.
       - Catalog Pricing: Valid positive decimal price must be present.
    4. Current Subtotal Recalculation:
       - Computes subtotal using the latest valid Shop Catalog prices.
    5. Orders Dependencies Demarcation:
       - Attaches explicit notes documenting boundaries deferred to the Orders design.
    """
    errors: List[str] = []
    shop = cart.shop

    # 1. Shop validation
    if not shop:
        errors.append("SHOP_NOT_FOUND")
    elif shop.status != Shop.Status.ACTIVE:
        errors.append("SHOP_UNAVAILABLE")

    # 2. Cart empty check
    cart_items = list(
        cart.items.select_related("product", "variant").all()
    )
    if not cart_items:
        errors.append("CART_EMPTY")

    item_details: List[Dict[str, Any]] = []
    current_subtotal = Decimal("0.00")
    total_quantity = Decimal("0.000")
    valid_item_count = 0
    invalid_item_count = 0

    # 3. Item-by-item validation
    for item in cart_items:
        issues: List[str] = []
        product = item.product
        variant = item.variant
        requested_qty = item.quantity
        total_quantity += requested_qty

        # Product Existence & Tenancy
        if not product:
            issues.append("PRODUCT_NOT_FOUND")
        else:
            if product.shop_id != shop.id:
                issues.append("PRODUCT_SHOP_MISMATCH")

            # Variant integrity
            if product.has_variants:
                if not variant:
                    issues.append("VARIANT_REQUIRED")
                elif variant.product_id != product.id:
                    issues.append("VARIANT_MISMATCH")
                elif variant.product.shop_id != shop.id:
                    issues.append("VARIANT_SHOP_MISMATCH")
            else:
                if variant:
                    issues.append("VARIANT_NOT_ALLOWED")

            # Catalog Visibility
            if not product.is_visible:
                issues.append("PRODUCT_HIDDEN")
            if variant and not variant.is_customer_visible:
                issues.append("VARIANT_HIDDEN")

            # Catalog Manual Availability
            if not product.is_available:
                issues.append("PRODUCT_UNAVAILABLE")
            if variant and (not variant.is_available or not product.is_available):
                issues.append("VARIANT_UNAVAILABLE")

            # Price check
            unit_price = item.unit_price
            if unit_price is None or unit_price < Decimal("0.00"):
                issues.append("PRICE_INVALID")
            else:
                line_total = (unit_price * requested_qty).quantize(Decimal("0.01"))
                current_subtotal += line_total

        # Inventory Availability
        if product:
            if variant:
                inv = InventoryItem.objects.filter(shop=shop, variant=variant).first()
            else:
                inv = InventoryItem.objects.filter(shop=shop, product=product, variant__isnull=True).first()

            available_stock = inv.available_quantity if inv else Decimal("0.000")

            if available_stock <= Decimal("0.000"):
                issues.append("OUT_OF_STOCK")
            elif requested_qty > available_stock:
                issues.append("INSUFFICIENT_STOCK")
        else:
            available_stock = Decimal("0.000")

        item_is_valid = len(issues) == 0
        if item_is_valid:
            valid_item_count += 1
        else:
            invalid_item_count += 1

        unit_price = item.unit_price if product else None
        line_total = (unit_price * requested_qty).quantize(Decimal("0.01")) if unit_price is not None else None

        item_details.append({
            "item_id": item.id,
            "product_id": product.id if product else None,
            "product_name": product.name if product else "",
            "variant_id": variant.id if variant else None,
            "variant_name": variant.name if variant else None,
            "requested_quantity": requested_qty,
            "available_quantity": available_stock,
            "current_unit_price": unit_price,
            "line_total": line_total,
            "is_valid": item_is_valid,
            "issues": issues,
        })

    is_overall_valid = (len(errors) == 0) and (invalid_item_count == 0) and (len(cart_items) > 0)

    return {
        "cart_id": cart.id,
        "shop_id": shop.id if shop else None,
        "is_valid": is_overall_valid,
        "can_checkout": is_overall_valid,
        "errors": errors,
        "items": item_details,
        "summary": {
            "item_count": len(cart_items),
            "valid_item_count": valid_item_count,
            "invalid_item_count": invalid_item_count,
            "total_quantity": total_quantity,
            "current_subtotal": current_subtotal,
        },
        "orders_dependencies": ORDERS_DEPENDENCIES_NOTE,
    }
