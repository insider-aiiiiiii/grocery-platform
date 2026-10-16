from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class InventoryItem(models.Model):
    """
    Shop-scoped Inventory representation.

    Tracks current on-hand and reserved stock for a ShopProduct or ProductVariant.
    - A Product without variants uses Product-level stock (variant=None).
    - For a variant-based Product, Variant stock is authoritative and Product-level stock
      is a derived aggregate of its variants, never an independent balance.
    - Preserves decimal quantities with precision up to 3 decimal places.
    - Negative stock is prohibited at both DB constraint and application levels.
    """

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    product = models.ForeignKey(
        "catalog.ShopProduct",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inventory_items",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
    )
    reserved_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        ordering = ["shop", "product", "variant", "id"]
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gte=0),
                name="inventory_quantity_non_negative",
            ),
            models.CheckConstraint(
                check=Q(reserved_quantity__gte=0),
                name="inventory_reserved_quantity_non_negative",
            ),
            models.CheckConstraint(
                check=Q(reserved_quantity__lte=F("quantity")),
                name="inventory_reserved_lte_quantity",
            ),
            models.UniqueConstraint(
                fields=["shop", "product"],
                condition=Q(variant__isnull=True),
                name="inventory_unique_shop_product_stock",
            ),
            models.UniqueConstraint(
                fields=["shop", "variant"],
                condition=Q(variant__isnull=False),
                name="inventory_unique_shop_variant_stock",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "product"], name="inv_item_shop_prod_idx"),
            models.Index(fields=["shop", "variant"], name="inv_item_shop_var_idx"),
        ]

    def clean(self):
        super().clean()

        if self.product_id and self.shop_id:
            if self.product.shop_id != self.shop_id:
                raise ValidationError({"shop": "InventoryItem shop must match the product's shop."})

        if self.variant_id:
            if self.variant.product_id != self.product_id:
                raise ValidationError({"variant": "Variant must belong to the specified product."})
            if self.variant.product.shop_id != self.shop_id:
                raise ValidationError({"variant": "Variant's product must belong to the same shop."})
        elif self.product_id:
            # Check if this product has variants
            if self.product.variants.exists():
                raise ValidationError({
                    "product": "Variant-based products cannot have an independent product-level inventory record. Variant stock is authoritative."
                })

        if self.quantity is not None and self.quantity < Decimal("0.000"):
            raise ValidationError({"quantity": "Stock quantity cannot be negative."})

        if self.reserved_quantity is not None and self.reserved_quantity < Decimal("0.000"):
            raise ValidationError({"reserved_quantity": "Reserved quantity cannot be negative."})

        if (
            self.quantity is not None
            and self.reserved_quantity is not None
            and self.reserved_quantity > self.quantity
        ):
            raise ValidationError({
                "reserved_quantity": "Reserved quantity cannot exceed total on-hand quantity."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.variant_id:
            return f"{self.product.name} ({self.variant.name}) - Qty: {self.quantity} (Shop: {self.shop_id})"
        return f"{self.product.name} - Qty: {self.quantity} (Shop: {self.shop_id})"

    @property
    def available_quantity(self) -> Decimal:
        """Returns the quantity available for purchase (on-hand minus reserved)."""
        return max(Decimal("0.000"), self.quantity - self.reserved_quantity)

    @property
    def is_out_of_stock(self) -> bool:
        """True if available quantity is zero or less."""
        return self.available_quantity <= Decimal("0.000")

    def set_quantity(self, amount: Decimal):
        """Sets the exact stock quantity."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if amount < Decimal("0.000"):
            raise ValidationError("Stock quantity cannot be negative.")
        if amount < self.reserved_quantity:
            raise ValidationError("Cannot set quantity lower than currently reserved quantity.")
        self.quantity = amount
        self.save()

    def add_stock(self, amount: Decimal):
        """Adds stock to on-hand inventory."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if amount < Decimal("0.000"):
            raise ValidationError("Stock amount to add must be non-negative.")
        self.quantity += amount
        self.save()

    def subtract_stock(self, amount: Decimal):
        """Subtracts stock from on-hand inventory."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if amount < Decimal("0.000"):
            raise ValidationError("Stock amount to subtract must be non-negative.")
        if self.quantity - amount < self.reserved_quantity:
            raise ValidationError("Cannot subtract stock below reserved quantity.")
        self.quantity -= amount
        self.save()

    def reserve_stock(self, amount: Decimal):
        """Reserves stock when an order is created."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if amount < Decimal("0.000"):
            raise ValidationError("Reservation amount must be non-negative.")
        if amount > self.available_quantity:
            raise ValidationError("Cannot reserve more than currently available stock.")
        self.reserved_quantity += amount
        self.save()

    def release_reserved_stock(self, amount: Decimal):
        """Releases reserved stock when an order is rejected or cancelled before acceptance."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if amount < Decimal("0.000"):
            raise ValidationError("Release amount must be non-negative.")
        if amount > self.reserved_quantity:
            raise ValidationError("Cannot release more than currently reserved stock.")
        self.reserved_quantity -= amount
        self.save()

    def deduct_reserved_stock(self, amount: Decimal):
        """Deducts stock when an order is accepted (reserved becomes deducted)."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if amount < Decimal("0.000"):
            raise ValidationError("Deduct amount must be non-negative.")
        if amount > self.reserved_quantity:
            raise ValidationError("Cannot deduct more than currently reserved stock.")
        if amount > self.quantity:
            raise ValidationError("Cannot deduct more than total stock.")
        self.reserved_quantity -= amount
        self.quantity -= amount
        self.save()

    def restore_deducted_stock(self, amount: Decimal):
        """Restores deducted stock when an accepted order is cancelled."""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        if amount < Decimal("0.000"):
            raise ValidationError("Restoration amount must be non-negative.")
        self.quantity += amount
        self.save()
