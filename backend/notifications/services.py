import logging
from typing import List, Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from customers.models import normalize_whatsapp_number
from notifications.models import NotificationOutbox, NotificationTemplate
from notifications.providers import (
    ProviderSendResult,
    WhatsAppProviderBase,
    get_whatsapp_provider,
)

logger = logging.getLogger(__name__)


def get_or_create_default_template(event_type: str) -> NotificationTemplate:
    """Retrieves or creates the standard template configuration for an event type."""
    defaults_map = {
        NotificationTemplate.EventType.NEW_ORDER: {
            "template_name": "order_received_merchant_v1",
            "language_code": "en_US",
            "body_format": "New order #{{order_number}} received for {{shop_name}}. Total: Rs.{{total_amount}}. Items: {{item_count}}.",
        },
        NotificationTemplate.EventType.ORDER_RECEIVED_CUSTOMER: {
            "template_name": "order_received_customer_v1",
            "language_code": "en_US",
            "body_format": "Hi {{customer_name}}, your order #{{order_number}} has been received by {{shop_name}}.",
        },
        NotificationTemplate.EventType.ORDER_ACCEPTED: {
            "template_name": "order_accepted_v1",
            "language_code": "en_US",
            "body_format": "Your order #{{order_number}} has been accepted by {{shop_name}}.",
        },
        NotificationTemplate.EventType.ORDER_REJECTED: {
            "template_name": "order_rejected_v1",
            "language_code": "en_US",
            "body_format": "Your order #{{order_number}} could not be fulfilled by {{shop_name}}.",
        },
        NotificationTemplate.EventType.QUANTITY_REDUCED: {
            "template_name": "quantity_reduced_v1",
            "language_code": "en_US",
            "body_format": "Some items in your order #{{order_number}} were updated by {{shop_name}}.",
        },
        NotificationTemplate.EventType.CUSTOMER_CANCELLATION: {
            "template_name": "customer_cancellation_v1",
            "language_code": "en_US",
            "body_format": "Order #{{order_number}} was cancelled.",
        },
        NotificationTemplate.EventType.MERCHANT_CANCELLATION: {
            "template_name": "merchant_cancellation_v1",
            "language_code": "en_US",
            "body_format": "Order #{{order_number}} was cancelled by the store.",
        },
    }

    defaults = defaults_map.get(
        event_type,
        {
            "template_name": f"{event_type.lower()}_v1",
            "language_code": "en_US",
            "body_format": f"Notification for {event_type}",
        },
    )

    template, _ = NotificationTemplate.objects.get_or_create(
        event_type=event_type,
        defaults=defaults,
    )
    return template


def enqueue_order_created_notification(order) -> Optional[NotificationOutbox]:
    """
    Enqueues a NEW_ORDER notification targeting the Shop's configured Merchant WhatsApp number.
    Must be called within the order creation transaction to guarantee atomic coupling.
    Adheres strictly to tenant isolation, idempotency, and reference-only persistence.
    """
    shop = order.shop
    contact_number = getattr(shop, "contact_number", "")
    if not contact_number:
        logger.warning(
            "Cannot enqueue NEW_ORDER notification for order %s: Shop %s has no contact_number.",
            order.id,
            shop.id,
        )
        return None

    try:
        recipient_phone = normalize_whatsapp_number(contact_number)
    except DjangoValidationError:
        recipient_phone = contact_number.strip()

    template = get_or_create_default_template(NotificationTemplate.EventType.NEW_ORDER)

    template_context = {
        "shop_name": shop.name,
        "order_number": str(order.id)[:8],
        "total_amount": str(order.total_amount),
        "item_count": order.items.count() if hasattr(order, "items") else 0,
        "portal_url": f"/merchant/orders/{order.id}/",
    }

    try:
        outbox_item, created = NotificationOutbox.objects.get_or_create(
            order_id=order.id,
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            recipient_phone=recipient_phone,
            defaults={
                "shop": shop,
                "recipient_type": NotificationOutbox.RecipientType.MERCHANT,
                "template": template,
                "template_context": template_context,
                "status": NotificationOutbox.Status.PENDING,
            },
        )
        return outbox_item
    except IntegrityError:
        return NotificationOutbox.objects.filter(
            order_id=order.id,
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            recipient_phone=recipient_phone,
        ).first()


def dispatch_notification(
    outbox_item: NotificationOutbox,
    provider: Optional[WhatsAppProviderBase] = None,
) -> NotificationOutbox:
    """
    Dispatches a single outbox item through the resolved WhatsApp provider adapter.
    Enforces idempotency: terminal or already-submitted messages are never dispatched twice.
    Updates outbox record state on success or failure with exponential backoff.
    """
    # Prevent re-dispatching if already submitted or terminal
    if outbox_item.is_terminal or outbox_item.status == NotificationOutbox.Status.SUBMITTED:
        return outbox_item

    if provider is None:
        provider = get_whatsapp_provider()

    # Format components according to Meta Cloud API requirements
    components = []
    if outbox_item.template_context:
        parameters = [
            {"type": "text", "text": str(val)}
            for val in outbox_item.template_context.values()
        ]
        components.append({
            "type": "body",
            "parameters": parameters,
        })

    template_name = outbox_item.template.template_name if outbox_item.template else "order_received_merchant_v1"
    language_code = outbox_item.template.language_code if outbox_item.template else "en_US"

    result: ProviderSendResult = provider.send_template_message(
        recipient_phone=outbox_item.recipient_phone,
        template_name=template_name,
        language_code=language_code,
        components=components,
        idempotency_key=str(outbox_item.id),
    )

    if result.success:
        outbox_item.mark_submitted(provider_message_id=result.provider_message_id or "")
    else:
        outbox_item.record_failure(
            error_details=result.error_details or {},
            is_transient=result.is_transient,
        )

    return outbox_item


def process_pending_outbox_batch(
    batch_size: int = 10,
    provider: Optional[WhatsAppProviderBase] = None,
) -> List[NotificationOutbox]:
    """
    Leases and dispatches a batch of eligible PENDING outbox records.
    Uses select_for_update(skip_locked=True) to ensure safe, concurrent worker processing.
    """
    now = timezone.now()
    with transaction.atomic():
        eligible_qs = (
            NotificationOutbox.objects.select_for_update(skip_locked=True)
            .filter(status=NotificationOutbox.Status.PENDING)
            .filter(models.Q(next_retry_at__isnull=True) | models.Q(next_retry_at__lte=now))
            .order_by("created_at")[:batch_size]
        )
        items_to_process = list(eligible_qs)
        for item in items_to_process:
            item.status = NotificationOutbox.Status.LEASED
            item.save(update_fields=["status", "updated_at"])

    dispatched = []
    for item in items_to_process:
        dispatched_item = dispatch_notification(item, provider=provider)
        dispatched.append(dispatched_item)

    return dispatched
