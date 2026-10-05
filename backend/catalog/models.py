from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class MasterCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Master Category"
        verbose_name_plural = "Master Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class MasterProduct(models.Model):
    """
    Platform-level reusable product library entity managed by Super Admin.

    Master Product is not itself a Shop sellable product. It serves as a
    reusable template that Merchants may select for their independent Shop
    Catalogs. Master Products do not automatically synchronize to or dictate
    Shop Products.
    """

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        MasterCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="master_products",
        verbose_name="Master Category",
    )
    brand = models.CharField(max_length=255, blank=True, default="")
    image = models.FileField(
        upload_to="catalog/master_products/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Master Product"
        verbose_name_plural = "Master Products"
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["is_active", "name"], name="catalog_mp_act_name_idx"),
        ]

    def __str__(self):
        return self.name


class ShopProduct(models.Model):
    """
    Shop-specific sellable product representation independently controlled by Merchant.

    A Shop Product may be created directly by a Merchant (requiring no approval)
    or selected from a platform Master Product. In both cases, the Shop Product is
    completely independent: updates or deletion of a Master Product do not alter
    or impair existing Shop Products, nor does any automatic synchronization occur.
    """

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="products",
    )
    master_product = models.ForeignKey(
        MasterProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop_products",
    )
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    brand = models.CharField(max_length=255, blank=True, default="")
    image = models.FileField(
        upload_to="catalog/shop_products/",
        blank=True,
        null=True,
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    sku = models.CharField(max_length=128, blank=True, default="")
    is_visible = models.BooleanField(default=True, db_index=True)
    is_available = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shop Product"
        verbose_name_plural = "Shop Products"
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                check=Q(price__gte=0) | Q(price__isnull=True),
                name="catalog_shopproduct_price_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "is_visible", "is_available"], name="catalog_sp_shop_vis_avail_idx"),
            models.Index(fields=["shop", "name"], name="catalog_sp_shop_name_idx"),
        ]

    def clean(self):
        super().clean()
        if self.price is not None and self.price < Decimal("0.00"):
            raise ValidationError({"price": "Price cannot be negative."})

    def __str__(self):
        return f"{self.name} (Shop: {self.shop_id})"

    @classmethod
    def from_master_product(cls, shop, master_product, **kwargs):
        """
        Factory helper to create an independent Shop Product from a Master Product.
        Copies product metadata into the Shop Product without binding updates.
        """
        data = {
            "shop": shop,
            "master_product": master_product,
            "name": master_product.name,
            "description": master_product.description,
            "brand": master_product.brand,
        }
        data.update(kwargs)
        return cls.objects.create(**data)


# Domain alias
Product = ShopProduct


