from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ["product", "variant"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["id", "shop", "customer", "item_count", "total_quantity", "subtotal", "updated_at"]
    list_filter = ["shop", "updated_at"]
    raw_id_fields = ["shop", "customer"]
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["id", "cart", "product", "variant", "quantity", "unit_price", "line_total", "updated_at"]
    list_filter = ["cart__shop", "updated_at"]
    raw_id_fields = ["cart", "product", "variant"]
