from django.contrib import admin
from .models import Order, OrderItem, OrderDeliveryAddress


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = [
        "product_name_snapshot",
        "variant_name_snapshot",
        "sku_snapshot",
        "unit_snapshot",
        "unit_price_snapshot",
        "ordered_quantity",
        "line_total",
        "created_at",
    ]


class OrderDeliveryAddressInline(admin.StackedInline):
    model = OrderDeliveryAddress
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "shop",
        "customer",
        "status",
        "payment_status",
        "fulfillment_type",
        "total_amount",
        "created_at",
    ]
    list_filter = ["status", "payment_status", "fulfillment_type", "shop"]
    search_fields = ["id", "customer_name_snapshot", "customer_phone_snapshot", "idempotency_key"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "customer_name_snapshot",
        "customer_phone_snapshot",
        "delivery_charge_snapshot",
        "items_subtotal",
        "total_amount",
    ]
    inlines = [OrderItemInline, OrderDeliveryAddressInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order",
        "product_name_snapshot",
        "quantity",
        "unit_price_snapshot",
        "line_total",
    ]
    list_filter = ["order__shop"]
    search_fields = ["product_name_snapshot", "sku_snapshot", "order__id"]


@admin.register(OrderDeliveryAddress)
class OrderDeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "recipient_name", "city", "pincode"]
    search_fields = ["recipient_name", "recipient_phone", "address_line", "pincode"]
