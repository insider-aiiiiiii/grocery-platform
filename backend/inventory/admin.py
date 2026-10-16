from django.contrib import admin

from .models import InventoryItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "shop",
        "product",
        "variant",
        "quantity",
        "reserved_quantity",
        "available_quantity",
        "updated_at",
    )
    list_filter = ("shop", "created_at")
    search_fields = ("product__name", "variant__name", "shop__name")
    readonly_fields = ("created_at", "updated_at", "available_quantity")

    def available_quantity(self, obj):
        return obj.available_quantity
    available_quantity.short_description = "Available"
