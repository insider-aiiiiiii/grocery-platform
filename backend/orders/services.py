from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from cart.models import Cart
from cart.validators import validate_product_orderable_and_available
from customers.models import Customer, normalize_whatsapp_number
from inventory.services import reserve_order_creation_stock
from orders.models import Order, OrderDeliveryAddress, OrderItem
from shops.models import Shop


def _get_idempotent_order(shop, key):
    if not key:
        return None
    return Order.objects.filter(shop=shop, idempotency_key=key).first()


def _create_order(shop, payload, idempotency_key):
    try:
        normalized_phone = normalize_whatsapp_number(payload["whatsapp_number"])
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

    with transaction.atomic():
        existing = _get_idempotent_order(shop, idempotency_key)
        if existing:
            return existing, False

        try:
            cart = Cart.objects.select_for_update().get(pk=payload["cart_id"], shop=shop)
        except Cart.DoesNotExist:
            raise NotFound("Cart was not found for this Shop.")

        if cart.customer_id:
            if cart.customer.whatsapp_number != normalized_phone:
                raise ValidationError({"whatsapp_number": "This cart belongs to a different customer identity."})
            customer = cart.customer
            if not customer.name and payload["customer_name"].strip():
                customer.name = payload["customer_name"].strip()
                customer.save(update_fields=["name", "updated_at"])
        else:
            try:
                customer, _ = Customer.objects.create_or_recognize(
                    shop=shop,
                    whatsapp_number=normalized_phone,
                    name=payload["customer_name"],
                )
            except DjangoValidationError as exc:
                raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
            cart.customer = customer
            cart.save(update_fields=["customer", "updated_at"])

        fulfillment = payload["fulfillment_type"]
        if fulfillment == Order.FulfillmentType.PICKUP and not shop.is_pickup_enabled:
            raise ValidationError({"fulfillment_type": "Pickup is not available at this Shop."})
        if fulfillment == Order.FulfillmentType.HOME_DELIVERY and not shop.is_home_delivery_enabled:
            raise ValidationError({"fulfillment_type": "Home delivery is not available at this Shop."})

        cart_items = list(
            cart.items.select_for_update(of=("self",))
            .select_related("product", "variant", "variant__product")
            .order_by("pk")
        )
        if not cart_items:
            raise ValidationError({"cart_id": "Cannot checkout an empty cart."})

        inventory_entries = []
        snapshots = []
        for cart_item in cart_items:
            product = cart_item.product
            variant = cart_item.variant
            try:
                validate_product_orderable_and_available(
                    shop=shop,
                    product=product,
                    variant=variant,
                    requested_quantity=cart_item.quantity,
                    current_item_quantity=Decimal("0.000"),
                )
            except ValidationError:
                raise

            unit_price = variant.effective_price if variant else product.price
            if unit_price is None:
                raise ValidationError({"cart_id": f"A current price is not set for {product.name}."})
            target = variant if variant else product
            inventory_entries.append((target, cart_item.quantity))
            snapshots.append({
                "cart_item": cart_item,
                "product": product,
                "variant": variant,
                "unit_price": Decimal(str(unit_price)).quantize(Decimal("0.01")),
            })

        try:
            reserve_order_creation_stock(shop, inventory_entries)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

        delivery_charge = Decimal("0.00")
        if (
            fulfillment == Order.FulfillmentType.HOME_DELIVERY
            and shop.delivery_fee_type == Shop.DeliveryFeeType.FIXED
        ):
            delivery_charge = shop.delivery_charge

        order = Order.objects.create(
            shop=shop,
            customer=customer,
            status=Order.Status.PENDING,
            payment_status=Order.PaymentStatus.UNPAID,
            fulfillment_type=fulfillment,
            customer_name_snapshot=payload["customer_name"].strip(),
            customer_phone_snapshot=normalized_phone,
            delivery_fee_type_snapshot=shop.delivery_fee_type,
            delivery_charge_snapshot=delivery_charge,
            items_subtotal=Decimal("0.00"),
            total_amount=delivery_charge,
            idempotency_key=idempotency_key or None,
            expires_at=timezone.now() + timedelta(minutes=shop.pending_order_timeout_minutes),
        )

        for snapshot in snapshots:
            item = snapshot["cart_item"]
            product = snapshot["product"]
            variant = snapshot["variant"]
            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                product_name_snapshot=product.name,
                variant_name_snapshot=variant.name if variant else "",
                sku_snapshot=(variant.sku or product.sku) if variant else product.sku,
                unit_snapshot="",
                attributes_snapshot=variant.attributes if variant else product.attributes,
                ordered_quantity=item.quantity,
                quantity=item.quantity,
                unit_price_snapshot=snapshot["unit_price"],
                line_total=(snapshot["unit_price"] * item.quantity).quantize(Decimal("0.01")),
            )

        if fulfillment == Order.FulfillmentType.HOME_DELIVERY:
            address = payload["delivery_address"]
            try:
                recipient_phone = normalize_whatsapp_number(
                    address.get("recipient_phone", normalized_phone)
                )
            except DjangoValidationError as exc:
                raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
            OrderDeliveryAddress.objects.create(
                order=order,
                recipient_name=address.get("recipient_name", payload["customer_name"]).strip(),
                recipient_phone=recipient_phone,
                address_line=address["address_line"],
                area=address["area"],
                city=address["city"],
                state=address["state"],
                pincode=address["pincode"],
                landmark=address.get("landmark", ""),
                delivery_notes=address.get("delivery_notes", ""),
            )

        order.recalculate_totals(save=True)
        cart.items.all().delete()
        return order, True


def create_order(shop, payload, idempotency_key):
    try:
        return _create_order(shop, payload, idempotency_key)
    except IntegrityError:
        # A simultaneous request may win the unique idempotency constraint.
        existing = _get_idempotent_order(shop, idempotency_key)
        if existing:
            return existing, False
        raise
    except DjangoValidationError:
        # Model full_clean() can detect the unique key after a concurrent request commits,
        # before the database insert reaches the IntegrityError path above.
        existing = _get_idempotent_order(shop, idempotency_key)
        if existing:
            return existing, False
        raise
