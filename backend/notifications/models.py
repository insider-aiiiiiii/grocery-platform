import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone


class NotificationTemplate(models.Model):
    """
    Database-driven template configuration strictly mapped to the
    7 approved canonical business events.
    """

    class EventType(models.TextChoices):
        NEW_ORDER = "NEW_ORDER", "New Order"
        ORDER_RECEIVED_CUSTOMER = "ORDER_RECEIVED_CUSTOMER", "Order Received Customer Acknowledgement"
        ORDER_ACCEPTED = "ORDER_ACCEPTED", "Order Accepted"
        ORDER_REJECTED = "ORDER_REJECTED", "Order Rejected"
        QUANTITY_REDUCED = "QUANTITY_REDUCED", "Quantity Reduced"
        CUSTOMER_CANCELLATION = "CUSTOMER_CANCELLATION", "Customer Cancellation"
        MERCHANT_CANCELLATION = "MERCHANT_CANCELLATION", "Merchant Cancellation"

    event_type = models.CharField(
        max_length=50,
        unique=True,
        choices=EventType.choices,
        help_text="Canonical event type matching approved MVP notification matrix.",
    )
    template_name = models.CharField(
        max_length=100,
        help_text="Registered Meta WhatsApp Cloud API template identifier (e.g. order_received_v1).",
    )
    language_code = models.CharField(
        max_length=10,
        default="en_US",
        help_text="BCP-47 language tag for template (e.g., en_US, hi_IN).",
    )
    body_format = models.TextField(
        help_text="Message text template with placeholder variables (e.g., {{shop_name}}, {{order_number}}).",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Controls whether this template is active for outgoing dispatch.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_template"
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
        ordering = ["event_type"]

    def __str__(self):
        return f"{self.get_event_type_display()} ({self.template_name} [{self.language_code}])"


class NotificationOutbox(models.Model):
    """
    Reference-only transactional outbox for outgoing WhatsApp notifications.
    Adheres strictly to AUTH-018: plaintext tokens are never stored in the outbox.
    """

    class RecipientType(models.TextChoices):
        MERCHANT = "MERCHANT", "Merchant"
        CUSTOMER = "CUSTOMER", "Customer"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        LEASED = "LEASED", "Leased"
        SUBMITTED = "SUBMITTED", "Submitted"
        DELIVERED = "DELIVERED", "Delivered"
        READ = "READ", "Read"
        FAILED_TRANSIENT_EXHAUSTED = "FAILED_TRANSIENT_EXHAUSTED", "Failed (Transient Retries Exhausted)"
        FAILED_PERMANENT = "FAILED_PERMANENT", "Failed (Permanent Error)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="notification_outbox_items",
        help_text="Shop tenant boundary for this notification.",
    )
    order_id = models.UUIDField(
        db_index=True,
        help_text="Reference-only identifier of the originating Order.",
    )
    event_type = models.CharField(
        max_length=50,
        choices=NotificationTemplate.EventType.choices,
        help_text="Approved canonical event type.",
    )
    recipient_type = models.CharField(
        max_length=20,
        choices=RecipientType.choices,
    )
    recipient_phone = models.CharField(
        max_length=20,
        help_text="Normalized E.164 phone string (e.g., +919876543210).",
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="outbox_items",
        help_text="Associated template used for formatting/dispatch.",
    )
    template_context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dynamic parameter values for template placeholders. Plaintext secrets are prohibited.",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of transient retry attempts made.",
    )
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled timestamp for next retry attempt (used for worker row-leasing).",
    )
    provider_message_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Meta Cloud API returned message identifier (e.g. wamid.HBgL...).",
    )
    provider_error_details = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Diagnostic error payload returned by provider on failure.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_outbox"
        verbose_name = "Notification Outbox Item"
        verbose_name_plural = "Notification Outbox Items"
        constraints = [
            models.UniqueConstraint(
                fields=["order_id", "event_type", "recipient_phone"],
                name="notif_outbox_order_event_recipient_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "next_retry_at", "created_at"],
                name="notif_outbox_lease_idx",
            ),
            models.Index(
                fields=["shop", "created_at"],
                name="notif_outbox_shop_created_idx",
            ),
            models.Index(
                fields=["created_at"],
                name="notif_outbox_created_idx",
            ),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.status}] {self.event_type} -> {self.recipient_phone} (Order: {self.order_id})"

    @property
    def is_terminal(self) -> bool:
        """Returns True if the notification has reached a terminal outcome."""
        return self.status in {
            self.Status.DELIVERED,
            self.Status.READ,
            self.Status.FAILED_TRANSIENT_EXHAUSTED,
            self.Status.FAILED_PERMANENT,
        }

    def mark_submitted(self, provider_message_id: str) -> None:
        """Transitions status to SUBMITTED upon provider acceptance."""
        self.status = self.Status.SUBMITTED
        self.provider_message_id = provider_message_id
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "provider_message_id", "submitted_at", "updated_at"])

    def mark_delivered(self) -> None:
        """Transitions status to DELIVERED upon verified webhook callback."""
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=["status", "delivered_at", "updated_at"])

    def mark_read(self) -> None:
        """Transitions status to READ upon verified read webhook callback."""
        self.status = self.Status.READ
        self.save(update_fields=["status", "updated_at"])

    def record_failure(self, error_details: dict, is_transient: bool = True) -> None:
        """
        Records failure and determines retry or terminal failure state.
        Exponential backoff: attempt 1 -> 60s, attempt 2 -> 300s, attempt 3 -> 900s.
        """
        self.provider_error_details = error_details
        if not is_transient:
            self.status = self.Status.FAILED_PERMANENT
            self.next_retry_at = None
        else:
            self.retry_count += 1
            if self.retry_count >= 3:
                self.status = self.Status.FAILED_TRANSIENT_EXHAUSTED
                self.next_retry_at = None
            else:
                backoff_seconds = [60, 300, 900][self.retry_count - 1]
                self.status = self.Status.PENDING
                self.next_retry_at = timezone.now() + timedelta(seconds=backoff_seconds)

        self.save(
            update_fields=[
                "status",
                "retry_count",
                "next_retry_at",
                "provider_error_details",
                "updated_at",
            ]
        )
