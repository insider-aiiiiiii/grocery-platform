from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotAuthenticated, NotFound, PermissionDenied, ValidationError

from inventory.services import (
    deduct_order_acceptance_stock,
    synchronize_order_transition_stock,
)
from orders.events import request_order_notification
from orders.models import Order


class OrderTransitionConflict(APIException):
    status_code = 409
    default_detail = "The requested Order transition is not allowed."
    default_code = "invalid_order_transition"


def _synchronize_rejected_order_stock(order, *, actor=None, reason=""):
    try:
        synchronize_order_transition_stock(
            order.shop,
            order,
            to_status=Order.Status.REJECTED,
            actor=actor,
            reason=reason,
        )
    except DjangoValidationError as exc:
        raise OrderTransitionConflict(
            "Inventory could not be synchronized; contact support before retrying."
        ) from exc


def _release_pending_stock(order, *, actor=None, reason=""):
    return _synchronize_rejected_order_stock(order, actor=actor, reason=reason)


def _restore_accepted_stock(order, *, actor=None, reason=""):
    return _synchronize_rejected_order_stock(order, actor=actor, reason=reason)


def _expire_pending_order(order, now):
    _release_pending_stock(order, reason="TIMEOUT_EXPIRED")
    order.status = Order.Status.REJECTED
    order.rejection_actor = Order.RejectionActor.SYSTEM
    order.rejection_reason_code = "TIMEOUT_EXPIRED"
    order.rejection_note = ""
    order.rejected_at = now
    order.save(update_fields=[
        "status", "rejection_actor", "rejection_reason_code", "rejection_note", "rejected_at", "updated_at",
    ])
    request_order_notification(order, "ORDER_REJECTED", order.rejection_reason_code)


def _locked_order(shop_id, order_id):
    try:
        return (
            Order.objects.select_for_update()
            .select_related("shop")
            .get(pk=order_id, shop_id=shop_id)
        )
    except Order.DoesNotExist:
        raise NotFound("Order was not found for this Shop.")


def _transition(shop_id, order_id, action, *, payload=None, actor=None):
    payload = payload or {}
    if action in {"accept", "reject", "cancel"} and actor is None:
        raise PermissionDenied("An authenticated Merchant is required for this Order transition.")
    with transaction.atomic():
        order = _locked_order(shop_id, order_id)
        now = timezone.now()

        if order.status == Order.Status.PENDING and order.expires_at and now >= order.expires_at:
            _expire_pending_order(order, now)
            return order, True

        if action == "accept":
            if order.status == Order.Status.ACCEPTED:
                return order, False
            if order.status != Order.Status.PENDING:
                raise OrderTransitionConflict("Only PENDING Orders can be accepted.")
            _accept_order(order, payload.get("items", []), now, actor)
        elif action == "reject":
            if (
                order.status == Order.Status.REJECTED
                and order.rejection_actor == Order.RejectionActor.MERCHANT
                and order.rejection_reason_code == "MERCHANT_REJECTED"
            ):
                return order, False
            if order.status != Order.Status.PENDING:
                raise OrderTransitionConflict("Only PENDING Orders can be rejected by a Merchant.")
            _release_pending_stock(order, actor=actor, reason="MERCHANT_REJECTED")
            order.status = Order.Status.REJECTED
            order.rejection_actor = Order.RejectionActor.MERCHANT
            order.rejection_reason_code = "MERCHANT_REJECTED"
            order.rejection_note = payload.get("rejection_note", "")
            order.rejected_at = now
            order.save(update_fields=[
                "status", "rejection_actor", "rejection_reason_code", "rejection_note", "rejected_at", "updated_at",
            ])
            request_order_notification(order, "ORDER_REJECTED", order.rejection_reason_code)
        elif action == "cancel":
            if (
                order.status == Order.Status.REJECTED
                and order.rejection_actor == Order.RejectionActor.MERCHANT
                and order.rejection_reason_code == "MERCHANT_CANCELLED"
            ):
                return order, False
            if order.status != Order.Status.ACCEPTED:
                raise OrderTransitionConflict("Only ACCEPTED Orders may be cancelled by a Merchant.")
            _restore_accepted_stock(order, actor=actor, reason="MERCHANT_CANCELLED")
            order.status = Order.Status.REJECTED
            order.rejection_actor = Order.RejectionActor.MERCHANT
            order.rejection_reason_code = "MERCHANT_CANCELLED"
            order.rejection_note = payload.get("rejection_note", "")
            order.rejected_at = now
            order.save(update_fields=[
                "status", "rejection_actor", "rejection_reason_code", "rejection_note", "rejected_at", "updated_at",
            ])
            request_order_notification(order, "MERCHANT_CANCELLED", order.rejection_reason_code)
        elif action == "prepare":
            if order.status == Order.Status.PREPARING:
                return order, False
            if order.status != Order.Status.ACCEPTED:
                raise OrderTransitionConflict("Only ACCEPTED Orders can enter PREPARING.")
            order.status = Order.Status.PREPARING
            order.save(update_fields=["status", "updated_at"])
        elif action == "ready":
            if order.status == Order.Status.READY:
                return order, False
            if order.status != Order.Status.PREPARING:
                raise OrderTransitionConflict("Only PREPARING Orders can be marked READY.")
            order.status = Order.Status.READY
            order.save(update_fields=["status", "updated_at"])
        elif action == "complete":
            if order.status == Order.Status.COMPLETED:
                return order, False
            if order.status != Order.Status.READY:
                raise OrderTransitionConflict("Only READY Orders can be completed.")
            if order.payment_status != Order.PaymentStatus.PAID:
                raise OrderTransitionConflict("An Order cannot be completed while UNPAID.")
            order.status = Order.Status.COMPLETED
            order.completed_at = now
            order.save(update_fields=["status", "completed_at", "updated_at"])

        return order, False


def _accept_order(order, adjustments, now, actor):
    order_items = {
        item.pk: item
        for item in order.items.select_for_update(of=("self",)).select_related("product", "variant")
    }
    requested = {entry["item_id"]: entry["quantity"] for entry in adjustments}
    unknown_ids = set(requested) - set(order_items)
    if unknown_ids:
        raise ValidationError({"items": "All adjusted item IDs must belong to this Order."})

    entries = []
    changed = False
    for item in order_items.values():
        target = item.variant if item.variant_id else item.product
        if target is None:
            raise OrderTransitionConflict("A Catalog item required by this Order no longer exists.")
        if item.variant_name_snapshot and not item.variant_id:
            raise OrderTransitionConflict("A Catalog variant required by this Order no longer exists.")
        original = item.quantity
        accepted = requested.get(item.pk, original)
        if accepted > original:
            raise ValidationError({
                "items": f"Accepted quantity for item {item.pk} cannot exceed its ordered quantity."
            })
        changed = changed or accepted < original
        entries.append((target, item, original, accepted))

    entries.sort(key=lambda entry: (1 if entry[0]._meta.model_name == "productvariant" else 0, entry[0].pk))
    try:
        deduct_order_acceptance_stock(
            order.shop,
            [(target, original, accepted) for target, _, original, accepted in entries],
            actor=actor,
        )
        for _, item, original, accepted in entries:
            if accepted != original:
                item.quantity = accepted
                item.save(update_fields=["quantity", "line_total", "updated_at"])
    except DjangoValidationError as exc:
        raise OrderTransitionConflict(
            "Reserved inventory could not be deducted; contact support before retrying."
        ) from exc

    if changed:
        order.recalculate_totals()
    order.status = Order.Status.ACCEPTED
    order.accepted_at = now
    update_fields = ["status", "accepted_at", "updated_at"]
    if changed:
        update_fields.extend(["items_subtotal", "total_amount"])
    order.save(update_fields=update_fields)
    request_order_notification(order, "ORDER_ACCEPTED")
    if changed:
        request_order_notification(order, "ORDER_QUANTITY_REDUCED")


def _set_payment_status(shop_id, order_id, payment_status):
    with transaction.atomic():
        order = _locked_order(shop_id, order_id)
        now = timezone.now()
        if order.status == Order.Status.PENDING and order.expires_at and now >= order.expires_at:
            _expire_pending_order(order, now)
            return order, True
        if payment_status == order.payment_status:
            return order, False
        if order.status == Order.Status.COMPLETED and payment_status == Order.PaymentStatus.UNPAID:
            raise OrderTransitionConflict("A COMPLETED Order cannot be marked UNPAID.")
        order.payment_status = payment_status
        order.save(update_fields=["payment_status", "updated_at"])
        return order, False


def transition_order(shop_id, order_id, action, payload=None, *, actor=None):
    return _transition(shop_id, order_id, action, payload=payload, actor=actor)


def set_order_payment_status(shop_id, order_id, payment_status):
    return _set_payment_status(shop_id, order_id, payment_status)


def expire_pending_order_if_due(shop_id, order_id):
    with transaction.atomic():
        order = _locked_order(shop_id, order_id)
        now = timezone.now()
        if order.status != Order.Status.PENDING or not order.expires_at or now < order.expires_at:
            return False
        _expire_pending_order(order, now)
        return True


def cancel_pending_order_as_customer(customer_id, session_id, order_id):
    """Atomically reject this profile's pending Order and release its reservation."""
    from customers.models import CustomerSession

    with transaction.atomic():
        session = (
            CustomerSession.objects.select_for_update()
            .select_related("customer")
            .filter(
                pk=session_id,
                customer_id=customer_id,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
                created_at__gt=timezone.now() - timedelta(days=30),
            )
            .first()
        )
        if session is None:
            raise NotAuthenticated("Customer session is no longer active.")

        try:
            order = (
                Order.objects.select_for_update()
                .select_related("shop")
                .get(pk=order_id, customer_id=customer_id, shop_id=session.customer.shop_id)
            )
        except Order.DoesNotExist:
            raise NotFound("Order was not found for this Customer profile.")

        now = timezone.now()
        if order.status == Order.Status.PENDING and order.expires_at and now >= order.expires_at:
            _expire_pending_order(order, now)
            return order, True
        if order.status != Order.Status.PENDING:
            raise OrderTransitionConflict("Only PENDING Orders can be cancelled by a Customer.")

        _release_pending_stock(order)
        order.status = Order.Status.REJECTED
        order.rejection_actor = Order.RejectionActor.CUSTOMER
        order.rejection_reason_code = "CUSTOMER_CANCELLED"
        order.rejection_note = ""
        order.rejected_at = now
        order.save(update_fields=[
            "status", "rejection_actor", "rejection_reason_code", "rejection_note", "rejected_at", "updated_at",
        ])
        request_order_notification(order, "CUSTOMER_CANCELLED", order.rejection_reason_code)
        return order, False
