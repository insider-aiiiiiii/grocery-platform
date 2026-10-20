from django.contrib import admin
from .models import NotificationOutbox, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("event_type", "template_name", "language_code", "is_active", "updated_at")
    list_filter = ("event_type", "is_active", "language_code")
    search_fields = ("event_type", "template_name", "body_format")
    readonly_fields = ("created_at", "updated_at")


@admin.register(NotificationOutbox)
class NotificationOutboxAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "shop",
        "order_id",
        "event_type",
        "recipient_type",
        "recipient_phone",
        "status",
        "retry_count",
        "provider_message_id",
        "created_at",
    )
    list_filter = ("status", "event_type", "recipient_type", "created_at")
    search_fields = ("id", "order_id", "recipient_phone", "provider_message_id")
    readonly_fields = (
        "id",
        "shop",
        "order_id",
        "event_type",
        "recipient_type",
        "recipient_phone",
        "created_at",
        "updated_at",
        "submitted_at",
        "delivered_at",
    )

