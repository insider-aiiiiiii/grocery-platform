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


def initialize_product_stock(product: ShopProduct) -> InventoryItem | None:
    """
    Initializes stock at zero (0.000) for a newly created ShopProduct without variants.
    If the product has variants, raises a ValidationError because variant stock is authoritative.
    """
    if product.has_variants:
        raise ValidationError(
            "Variant-based products cannot have an independent product-level inventory record. Variant stock is authoritative."
        )
    item, _ = InventoryItem.objects.get_or_create(
        shop=product.shop,
        product=product,
        variant=None,
        defaults={
            "quantity": Decimal("0.000"),
            "reserved_quantity": Decimal("0.000"),
        },
    )
    return item


def initialize_variant_stock(variant: ProductVariant) -> InventoryItem:
    """
    Initializes stock at zero (0.000) for a newly created ProductVariant.
    For variant-based products, variant stock is authoritative.
    Any obsolete independent product-level stock record for the parent product is removed.
    """
    item, _ = InventoryItem.objects.get_or_create(
        shop=variant.product.shop,
        product=variant.product,
        variant=variant,
        defaults={
            "quantity": Decimal("0.000"),
            "reserved_quantity": Decimal("0.000"),
        },
    )
    # Remove any obsolete independent product-level stock record
    InventoryItem.objects.filter(
        product=variant.product,
        variant__isnull=True,
    ).delete()
    return item


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


def validate_shop_merchant_authorization(shop, actor=None):
    """
    Validates that the actor (if provided) is authorized to modify inventory for the shop.
    - Super Admins are explicitly forbidden from modifying merchant inventory in MVP (Section 3).
    - Actor must be an active Merchant.
    - Merchant must be the owner of the specified shop.
    - Shop must not be deactivated or suspended.
    """
    if actor is None:
        return

    from users.models import Merchant, User
    from shops.models import Shop

    if isinstance(actor, User):
        user = actor
        if getattr(user, "role", None) == User.Role.SUPER_ADMIN:
            raise ValidationError("Super Admin is not authorized to modify Merchant inventory.")
        if getattr(user, "role", None) != User.Role.MERCHANT:
            raise ValidationError("Only authorized merchants can modify shop inventory.")
        merchant = getattr(user, "merchant", None)
        if not merchant or merchant.status != Merchant.Status.ACTIVE:
            raise ValidationError("Only active merchants can modify shop inventory.")
    elif isinstance(actor, Merchant):
        merchant = actor
        if merchant.status != Merchant.Status.ACTIVE:
            raise ValidationError("Only active merchants can modify shop inventory.")
    else:
        raise ValidationError("Invalid actor for inventory modification.")

    if shop.merchant_id != merchant.id:
        raise ValidationError("Merchant is not authorized to modify inventory for this shop.")

    if getattr(shop, "status", None) in (Shop.Status.DEACTIVATED, Shop.Status.SUSPENDED):
        raise ValidationError("Cannot modify inventory for a deactivated or suspended shop.")


def adjust_stock(
    shop,
    target: ShopProduct | ProductVariant,
    *,
    set_quantity: Decimal | str | int | float | None = None,
    delta: Decimal | str | int | float | None = None,
    actor=None,
) -> InventoryItem:
    """
    Adjusts stock for a non-variant product or an individual variant.
    Enforces tenant boundaries, authoritative variant rules, and non-negative stock.
    No adjustment reason is required and no persistent movement history is created in MVP.
    """
    validate_shop_merchant_authorization(shop, actor)
    if set_quantity is not None and delta is not None:
        raise ValidationError("Provide either set_quantity or delta, not both.")
    if set_quantity is None and delta is None:
        raise ValidationError("Must provide either set_quantity or delta.")

    with transaction.atomic():
        item = _get_target_item_locked(shop, target)
        if set_quantity is not None:
            set_dec = quantize_quantity(set_quantity)
            if set_dec < item.reserved_quantity:
                raise ValidationError("Cannot set quantity lower than currently reserved quantity.")
            item.set_quantity(set_dec)
        elif delta is not None:
            delta_val = Decimal(str(delta))
            if delta_val >= Decimal("0.000"):
                delta_dec = quantize_quantity(delta_val)
                item.add_stock(delta_dec)
            else:
                delta_dec = quantize_quantity(abs(delta_val))
                if delta_dec > item.quantity:
                    raise ValidationError("Cannot subtract stock below zero.")
                if item.quantity - delta_dec < item.reserved_quantity:
                    raise ValidationError("Cannot subtract stock below reserved quantity.")
                item.subtract_stock(delta_dec)
        return item


def add_stock(
    shop,
    target: ShopProduct | ProductVariant,
    quantity: Decimal | str | int | float,
    *,
    actor=None,
) -> InventoryItem:
    """
    Adds stock to a non-variant ShopProduct or an authoritative ProductVariant.
    Enforces Shop authorization, validates positive quantity, and preserves decimal precision.
    No adjustment reason is required and no persistent movement history is created.
    """
    validate_shop_merchant_authorization(shop, actor)
    try:
        dec = Decimal(str(quantity))
    except Exception as e:
        raise ValidationError(f"Invalid decimal quantity: {quantity}") from e
    if dec <= Decimal("0.000"):
        raise ValidationError("Quantity to add must be greater than zero.")
    qty = quantize_quantity(dec)
    return adjust_stock(shop, target, delta=qty, actor=actor)


def subtract_stock(
    shop,
    target: ShopProduct | ProductVariant,
    quantity: Decimal | str | int | float,
    *,
    actor=None,
) -> InventoryItem:
    """
    Subtracts stock from a non-variant ShopProduct or an authoritative ProductVariant.
    Enforces Shop authorization, strictly prevents negative resulting stock, prevents
    reducing stock below currently reserved stock, and preserves decimal precision.
    No adjustment reason is required and no persistent movement history is created.
    """
    validate_shop_merchant_authorization(shop, actor)
    try:
        dec = Decimal(str(quantity))
    except Exception as e:
        raise ValidationError(f"Invalid decimal quantity: {quantity}") from e
    if dec <= Decimal("0.000"):
        raise ValidationError("Quantity to subtract must be greater than zero.")
    qty = quantize_quantity(dec)
    return adjust_stock(shop, target, delta=-qty, actor=actor)


def set_stock(
    shop,
    target: ShopProduct | ProductVariant,
    quantity: Decimal | str | int | float,
    *,
    actor=None,
) -> InventoryItem:
    """
    Sets the exact stock quantity for a non-variant ShopProduct or an authoritative ProductVariant.
    Enforces Shop authorization, validates non-negative quantity and <=3 decimal places,
    strictly prevents setting stock below currently reserved stock, and enforces
    authoritative variant granularity rules.
    No adjustment reason is required and no persistent movement history is created in MVP.
    """
    validate_shop_merchant_authorization(shop, actor)
    qty = quantize_quantity(quantity)
    return adjust_stock(shop, target, set_quantity=qty, actor=actor)


update_exact_stock = set_stock
set_exact_stock = set_stock


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
            if qty <= Decimal("0.000"):
                raise ValidationError(f"Deduct quantity for '{target.name}' must be greater than zero.")
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


def reserve_order_creation_stock(
    shop,
    items_or_cart,
) -> list[InventoryItem]:
    """
    Integrates Inventory reservation with Order creation.

    - Reserves requested quantities atomically when an Order is created.
    - Checkout does NOT deduct stock: only reserved_quantity is incremented;
      on-hand quantity remains constant until Merchant acceptance.
    - If ANY requested quantity exceeds availability, raises ValidationError
      without automatic quantity reduction.
    - Supports both a Cart instance (extracting its constituent items) and
      a sequence of (target, quantity) tuples.
    - Enforces strict Shop tenant boundaries and deadlock-free deterministic lock sorting.
    """
    # Duck-type check for Cart instance with shop and items
    if hasattr(items_or_cart, "items") and hasattr(items_or_cart, "shop"):
        cart = items_or_cart
        if cart.shop_id != shop.id:
            raise ValidationError("Cart does not belong to the specified shop.")
        cart_items = list(cart.items.all())
        if not cart_items:
            raise ValidationError("Cannot reserve inventory for an empty cart.")

        items_with_quantities = []
        for c_item in cart_items:
            target = c_item.variant if c_item.variant_id else c_item.product
            # Verify shop ownership of the target
            if c_item.variant_id:
                if c_item.variant.product.shop_id != shop.id:
                    raise ValidationError("Cart item variant does not belong to the specified shop.")
            elif c_item.product_id:
                if c_item.product.shop_id != shop.id:
                    raise ValidationError("Cart item product does not belong to the specified shop.")
            items_with_quantities.append((target, c_item.quantity))
    elif isinstance(items_or_cart, (list, tuple)):
        items_with_quantities = list(items_or_cart)
        if not items_with_quantities:
            raise ValidationError("Cannot reserve inventory for an empty order item list.")
    else:
        raise ValidationError("items_or_cart must be a Cart instance or a list of (target, quantity) tuples.")

    return reserve_order_items_stock(shop, items_with_quantities)


def reduce_and_accept_order_items_stock(
    shop,
    items_with_adjustments: list[tuple[ShopProduct | ProductVariant, Decimal | str | int | float, Decimal | str | int | float]],
) -> list[InventoryItem]:
    """
    Merchant Manual Partial-Quantity Reduction before Acceptance (Batch / Multi-Item):

    When requested quantities exceed what can be fulfilled across an Order's items,
    the Merchant may manually reduce fulfillable quantities before accepting the Order.
    - For each item:
      - The unfulfilled difference (original_reserved - accepted_quantity) is released back to available stock.
      - The accepted quantity is deducted from on-hand stock (reserved becomes deducted).
    - Preserves approved Merchant-controlled behavior without inventing customer confirmation
      or automatic quantity reduction.
    - Executes atomically inside a single transaction with deadlock-preventing deterministic lock sorting.
    """
    if not items_with_adjustments:
        return []

    def sort_key(entry):
        target = entry[0]
        is_var = 1 if isinstance(target, ProductVariant) else 0
        return (is_var, target.id)

    sorted_entries = sorted(items_with_adjustments, key=sort_key)

    with transaction.atomic():
        updated = []
        for target, orig_raw, acc_raw in sorted_entries:
            orig = quantize_quantity(orig_raw)
            acc = quantize_quantity(acc_raw)

            if acc > orig:
                raise ValidationError(
                    f"Accepted quantity for '{target.name}' cannot exceed originally reserved quantity."
                )
            if acc < Decimal("0.000"):
                raise ValidationError(
                    f"Accepted quantity for '{target.name}' cannot be negative."
                )

            difference = orig - acc
            item = _get_target_item_locked(shop, target)
            if difference > Decimal("0.000"):
                item.release_reserved_stock(difference)
            if acc > Decimal("0.000"):
                item.deduct_reserved_stock(acc)
            updated.append(item)

        return updated


def deduct_order_acceptance_stock(
    shop,
    items_or_order,
    *,
    actor=None,
) -> list[InventoryItem]:
    """
    Integrates stock deduction with Merchant Order acceptance (INV-009).

    - Triggered strictly when an authorized Merchant accepts an Order.
    - Deducts the reserved quantity on acceptance, NOT at checkout.
    - Preserves available/reserved semantics:
      - Full acceptance: reserved quantity is deducted from on-hand quantity,
        leaving available stock for other customers untouched.
      - Partial acceptance: unfulfilled difference (original_reserved - accepted_qty)
        is released back to available stock, and accepted_qty is deducted from on-hand quantity.
    - Validates merchant authorization: actor must be an active Merchant owning the shop.
      Super Admins and unauthorized merchants are rejected.
    - Deadlock-free deterministic lock sorting: items sorted by (is_variant, target.id).
    - Database safety floor: non-negative check constraints prevent illegal balances.
    """
    validate_shop_merchant_authorization(shop, actor)

    # Duck-type check for Order or container instance with shop and items
    if hasattr(items_or_order, "items") and hasattr(items_or_order, "shop"):
        order = items_or_order
        if order.shop_id != shop.id:
            raise ValidationError("Order does not belong to the specified shop.")
        order_items = list(order.items.all())
        if not order_items:
            raise ValidationError("Cannot deduct inventory for an empty order.")

        # Check if line items specify partial adjustments or standard quantities
        adjustments = []
        full_items = []
        has_partial = False

        for oi in order_items:
            target = getattr(oi, "variant", None) or getattr(oi, "product", None)
            if not target:
                raise ValidationError("Order item must reference a product or variant.")

            orig = getattr(oi, "ordered_quantity", None) or getattr(oi, "reserved_quantity", None)
            acc = getattr(oi, "accepted_quantity", None) or getattr(oi, "quantity", None)

            if orig is not None and acc is not None and orig != acc:
                has_partial = True
                adjustments.append((target, orig, acc))
            elif orig is not None and acc is not None:
                adjustments.append((target, orig, acc))
            else:
                qty = acc if acc is not None else orig
                full_items.append((target, qty))

        if has_partial or (adjustments and not full_items):
            return reduce_and_accept_order_items_stock(shop, adjustments)
        return deduct_order_items_stock(shop, full_items)

    elif isinstance(items_or_order, (list, tuple)):
        items_list = list(items_or_order)
        if not items_list:
            raise ValidationError("Cannot deduct inventory for an empty item list.")

        # Inspect first element to determine 2-tuple (target, qty) vs 3-tuple (target, orig, acc)
        first_entry = items_list[0]
        if len(first_entry) == 3:
            return reduce_and_accept_order_items_stock(shop, items_list)
        elif len(first_entry) == 2:
            return deduct_order_items_stock(shop, items_list)
        else:
            raise ValidationError("Items must be 2-tuples (target, qty) or 3-tuples (target, orig, acc).")

    raise ValidationError("items_or_order must be an Order instance or a list of item tuples.")


