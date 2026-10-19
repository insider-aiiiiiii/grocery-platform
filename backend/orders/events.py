from functools import partial

from django.db import transaction
from django.dispatch import Signal

from orders.models import Order


order_notification_requested = Signal()


def request_order_notification(order, event, reason_code=""):
    """Publish a reference-only notification event after its Order transaction commits."""
    transaction.on_commit(
        partial(
            order_notification_requested.send,
            sender=Order,
            order_id=order.pk,
            shop_id=order.shop_id,
            event=event,
            reason_code=reason_code,
        ),
        robust=True,
    )
