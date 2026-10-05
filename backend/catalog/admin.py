from django.contrib import admin
from .models import MasterCategory, MasterProduct


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
