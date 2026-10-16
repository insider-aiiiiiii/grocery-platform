from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from catalog.models import ProductVariant, ShopProduct
from .models import InventoryItem, quantize_quantity


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


def _get_target_item_locked(
    shop,
    target: ShopProduct | ProductVariant,
) -> InventoryItem:
    """
    Retrieves and row-locks the authoritative InventoryItem for a given target within a transaction.
    """
    if isinstance(target, ShopProduct):
        if target.shop_id != shop.id:
            raise ValidationError("Target product does not belong to the authorized shop.")
        if target.has_variants:
            raise ValidationError(
                "Independent manual changes to aggregate Product stock for a variant-based product are superseded and not permitted."
            )
        item = InventoryItem.objects.select_for_update().filter(
            shop=shop,
            product=target,
            variant__isnull=True,
        ).first()
        if not item:
            item, _ = InventoryItem.objects.get_or_create(
                shop=shop,
                product=target,
                variant=None,
                defaults={"quantity": Decimal("0.000"), "reserved_quantity": Decimal("0.000")},
            )
            item = InventoryItem.objects.select_for_update().get(id=item.id)
        return item

    if isinstance(target, ProductVariant):
        if target.product.shop_id != shop.id:
            raise ValidationError("Target variant does not belong to the authorized shop.")
        item = InventoryItem.objects.select_for_update().filter(
            shop=shop,
            product=target.product,
            variant=target,
        ).first()
        if not item:
            item, _ = InventoryItem.objects.get_or_create(
                shop=shop,
                product=target.product,
                variant=target,
                defaults={"quantity": Decimal("0.000"), "reserved_quantity": Decimal("0.000")},
            )
            item = InventoryItem.objects.select_for_update().get(id=item.id)
        return item

    raise ValidationError("Target must be a ShopProduct or ProductVariant.")


def adjust_stock(
    shop,
    target: ShopProduct | ProductVariant,
    *,
    set_quantity: Decimal | str | int | float | None = None,
    delta: Decimal | str | int | float | None = None,
) -> InventoryItem:
    """
    Adjusts stock for a non-variant product or an individual variant.
    Enforces tenant boundaries and authoritative variant rules.
    """
    if set_quantity is not None and delta is not None:
        raise ValidationError("Provide either set_quantity or delta, not both.")
    if set_quantity is None and delta is None:
        raise ValidationError("Must provide either set_quantity or delta.")

    with transaction.atomic():
        item = _get_target_item_locked(shop, target)
        if set_quantity is not None:
            item.set_quantity(set_quantity)
        elif delta is not None:
            delta_dec = quantize_quantity(abs(Decimal(str(delta))))
            if Decimal(str(delta)) >= Decimal("0.000"):
                item.add_stock(delta_dec)
            else:
                item.subtract_stock(delta_dec)
        return item


# --- Approved Order Flow Stock Services (Atomic & Concurrency-Safe) ---


def reserve_order_stock(
    shop,
    target: ShopProduct | ProductVariant,
    quantity: Decimal | str | int | float,
) -> InventoryItem:
    """
    Step 1: Order Created -> Required quantity reserved.
    Reserves quantity atomically with row-level locking.
    """
    qty = quantize_quantity(quantity)
    if qty <= Decimal("0.000"):
        raise ValidationError("Reservation quantity must be greater than zero.")

    with transaction.atomic():
        item = _get_target_item_locked(shop, target)
        if item.available_quantity < qty:
            raise ValidationError(
                f"Insufficient available stock for '{target.name}': available {item.available_quantity}, requested {qty}."
            )
        item.reserve_stock(qty)
        return item


def release_order_stock(
    shop,
    target: ShopProduct | ProductVariant,
    quantity: Decimal | str | int | float,
) -> InventoryItem:
    """
    Step 2a: Order Rejected / Expired / Customer Cancelled (while PENDING).
    Releases reserved stock back to available stock.
    """
    qty = quantize_quantity(quantity)
    if qty <= Decimal("0.000"):
        raise ValidationError("Release quantity must be greater than zero.")

    with transaction.atomic():
        item = _get_target_item_locked(shop, target)
        item.release_reserved_stock(qty)
        return item


def deduct_order_stock(
    shop,
    target: ShopProduct | ProductVariant,
    quantity: Decimal | str | int | float,
) -> InventoryItem:
    """
    Step 2b: Merchant Accepts -> Reserved quantity becomes deducted on-hand stock.
    """
    qty = quantize_quantity(quantity)
    if qty <= Decimal("0.000"):
        raise ValidationError("Deduct quantity must be greater than zero.")

    with transaction.atomic():
        item = _get_target_item_locked(shop, target)
        item.deduct_reserved_stock(qty)
        return item


def restore_cancelled_order_stock(
    shop,
    target: ShopProduct | ProductVariant,
    quantity: Decimal | str | int | float,
) -> InventoryItem:
    """
    Step 3: Accepted Order Cancelled before preparation -> Deducted quantity restored.
    Stock is immediately available again.
    """
    qty = quantize_quantity(quantity)
    if qty <= Decimal("0.000"):
        raise ValidationError("Restoration quantity must be greater than zero.")

    with transaction.atomic():
        item = _get_target_item_locked(shop, target)
        item.restore_deducted_stock(qty)
        return item


def reduce_and_accept_order_stock(
    shop,
    target: ShopProduct | ProductVariant,
    *,
    original_reserved: Decimal | str | int | float,
    accepted_quantity: Decimal | str | int | float,
) -> InventoryItem:
    """
    Merchant Manual Quantity Reduction before Acceptance:
    When requested quantity exceeds what can be fulfilled, Merchant manually reduces
    the fulfillable quantity before accepting the Order.
    - The unfulfilled difference (original_reserved - accepted_quantity) is released back to stock.
    - The accepted quantity is deducted from on-hand stock.
    """
    orig = quantize_quantity(original_reserved)
    acc = quantize_quantity(accepted_quantity)

    if acc > orig:
        raise ValidationError("Accepted quantity cannot exceed originally reserved quantity.")
    if acc < Decimal("0.000"):
        raise ValidationError("Accepted quantity cannot be negative.")

    difference = orig - acc

    with transaction.atomic():
        item = _get_target_item_locked(shop, target)
        if difference > Decimal("0.000"):
            item.release_reserved_stock(difference)
        if acc > Decimal("0.000"):
            item.deduct_reserved_stock(acc)
        return item


# --- Batch Order Operations (Atomic Multi-Item Processing) ---


def _sort_items_for_deadlock_prevention(items_with_quantities):
    """
    Sorts target items deterministically to avoid database deadlocks during concurrent writes.
    """
    def sort_key(entry):
        target = entry[0]
        is_var = 1 if isinstance(target, ProductVariant) else 0
        return (is_var, target.id)

    return sorted(items_with_quantities, key=sort_key)


def reserve_order_items_stock(
    shop,
    items_with_quantities: list[tuple[ShopProduct | ProductVariant, Decimal | str | int | float]],
) -> list[InventoryItem]:
    """
    Atomically reserves stock for all line items in an order.
    If ANY line item has insufficient stock, the entire transaction rolls back cleanly.
    """
    if not items_with_quantities:
        return []

    sorted_entries = _sort_items_for_deadlock_prevention(items_with_quantities)

    with transaction.atomic():
        locked_items = []
        # Pre-lock and validate all items first
        for target, raw_qty in sorted_entries:
            qty = quantize_quantity(raw_qty)
            if qty <= Decimal("0.000"):
                raise ValidationError(f"Reservation quantity for '{target.name}' must be greater than zero.")
            item = _get_target_item_locked(shop, target)
            if item.available_quantity < qty:
                raise ValidationError(
                    f"Insufficient stock for '{target.name}': requested {qty}, available {item.available_quantity}."
                )
            locked_items.append((item, qty))

        # Perform reservation on all items
        updated = []
        for item, qty in locked_items:
            item.reserve_stock(qty)
            updated.append(item)

        return updated


def release_order_items_stock(
    shop,
    items_with_quantities: list[tuple[ShopProduct | ProductVariant, Decimal | str | int | float]],
) -> list[InventoryItem]:
    """
    Atomically releases reserved stock for all line items in an order.
    """
    if not items_with_quantities:
        return []

    sorted_entries = _sort_items_for_deadlock_prevention(items_with_quantities)

    with transaction.atomic():
        updated = []
        for target, raw_qty in sorted_entries:
            qty = quantize_quantity(raw_qty)
            item = _get_target_item_locked(shop, target)
            item.release_reserved_stock(qty)
            updated.append(item)
        return updated


def deduct_order_items_stock(
    shop,
    items_with_quantities: list[tuple[ShopProduct | ProductVariant, Decimal | str | int | float]],
) -> list[InventoryItem]:
    """
    Atomically deducts reserved stock for all accepted line items in an order.
    """
    if not items_with_quantities:
        return []

    sorted_entries = _sort_items_for_deadlock_prevention(items_with_quantities)

    with transaction.atomic():
        updated = []
        for target, raw_qty in sorted_entries:
            qty = quantize_quantity(raw_qty)
            item = _get_target_item_locked(shop, target)
            item.deduct_reserved_stock(qty)
            updated.append(item)
        return updated


def restore_order_items_stock(
    shop,
    items_with_quantities: list[tuple[ShopProduct | ProductVariant, Decimal | str | int | float]],
) -> list[InventoryItem]:
    """
    Atomically restores previously deducted stock for cancelled orders before preparation.
    """
    if not items_with_quantities:
        return []

    sorted_entries = _sort_items_for_deadlock_prevention(items_with_quantities)

    with transaction.atomic():
        updated = []
        for target, raw_qty in sorted_entries:
            qty = quantize_quantity(raw_qty)
            item = _get_target_item_locked(shop, target)
            item.restore_deducted_stock(qty)
            updated.append(item)
        return updated
