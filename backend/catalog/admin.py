from django.contrib import admin
from .models import MasterCategory, MasterProduct, ShopProduct


@admin.register(MasterCategory)
class MasterCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)


@admin.register(MasterProduct)
class MasterProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "brand", "is_active", "created_at")
    search_fields = ("name", "brand")
    list_filter = ("is_active", "category")


@admin.register(ShopProduct)
class ShopProductAdmin(admin.ModelAdmin):
    list_display = ("name", "shop", "price", "is_visible", "is_available", "created_at")
    search_fields = ("name", "brand", "sku")
    list_filter = ("is_visible", "is_available", "shop")
    raw_id_fields = ("shop", "master_product")

