from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from catalog.models import ProductVariant, ShopProduct
from .models import InventoryItem


def get_product_stock(product: ShopProduct) -> dict:
    """
    Returns current stock information for a ShopProduct.

    - If the product has variants, Product stock is a derived aggregate
      of its variants (is_derived=True), and variant stock is authoritative.
    - If the product has no variants, Product-level stock is returned (is_derived=False).
    """
    if product.has_variants:
        agg = product.inventory_items.filter(variant__isnull=False).aggregate(
            total_quantity=Sum("quantity"),
            total_reserved=Sum("reserved_quantity"),
        )
        quantity = agg["total_quantity"] or Decimal("0.000")
        reserved_quantity = agg["total_reserved"] or Decimal("0.000")
        available_quantity = max(Decimal("0.000"), quantity - reserved_quantity)
        return {
            "product_id": product.id,
            "shop_id": product.shop_id,
            "has_variants": True,
            "is_derived": True,
            "quantity": quantity,
            "reserved_quantity": reserved_quantity,
            "available_quantity": available_quantity,
            "is_out_of_stock": available_quantity <= Decimal("0.000"),
        }

    item = product.inventory_items.filter(variant__isnull=True).first()
    quantity = item.quantity if item else Decimal("0.000")
    reserved_quantity = item.reserved_quantity if item else Decimal("0.000")
    available_quantity = max(Decimal("0.000"), quantity - reserved_quantity)

    return {
        "product_id": product.id,
        "shop_id": product.shop_id,
        "has_variants": False,
        "is_derived": False,
        "quantity": quantity,
        "reserved_quantity": reserved_quantity,
        "available_quantity": available_quantity,
        "is_out_of_stock": available_quantity <= Decimal("0.000"),
    }


def get_variant_stock(variant: ProductVariant) -> dict:
    """
    Returns authoritative stock information for an individual ProductVariant.
    """
    item = variant.inventory_items.first()
    quantity = item.quantity if item else Decimal("0.000")
    reserved_quantity = item.reserved_quantity if item else Decimal("0.000")
    available_quantity = max(Decimal("0.000"), quantity - reserved_quantity)

    return {
        "variant_id": variant.id,
        "product_id": variant.product_id,
        "shop_id": variant.product.shop_id,
        "quantity": quantity,
        "reserved_quantity": reserved_quantity,
        "available_quantity": available_quantity,
        "is_out_of_stock": available_quantity <= Decimal("0.000"),
    }


def adjust_stock(
    shop,
    target: ShopProduct | ProductVariant,
    *,
    set_quantity: Decimal | None = None,
    delta: Decimal | None = None,
) -> InventoryItem:
    """
    Adjusts stock for a non-variant product or an individual variant.
    Enforces tenant boundaries and authoritative variant rules.
    """
    if isinstance(target, ShopProduct):
        if target.shop_id != shop.id:
            raise ValidationError("Target product does not belong to the authorized shop.")
        if target.has_variants:
            raise ValidationError(
                "Independent manual changes to aggregate Product stock for a variant-based product are superseded and not permitted."
            )
        item, _ = InventoryItem.objects.get_or_create(
            shop=shop,
            product=target,
            variant=None,
            defaults={"quantity": Decimal("0.000"), "reserved_quantity": Decimal("0.000")},
        )
    elif isinstance(target, ProductVariant):
        if target.product.shop_id != shop.id:
            raise ValidationError("Target variant does not belong to the authorized shop.")
        item, _ = InventoryItem.objects.get_or_create(
            shop=shop,
            product=target.product,
            variant=target,
            defaults={"quantity": Decimal("0.000"), "reserved_quantity": Decimal("0.000")},
        )
    else:
        raise ValidationError("Target must be a ShopProduct or ProductVariant.")

    if set_quantity is not None and delta is not None:
        raise ValidationError("Provide either set_quantity or delta, not both.")

    if set_quantity is not None:
        item.set_quantity(set_quantity)
    elif delta is not None:
        if not isinstance(delta, Decimal):
            delta = Decimal(str(delta))
        if delta >= Decimal("0.000"):
            item.add_stock(delta)
        else:
            item.subtract_stock(abs(delta))
    else:
        raise ValidationError("Must provide either set_quantity or delta.")

    return item
