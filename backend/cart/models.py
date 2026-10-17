from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

QUANTITY_PRECISION = Decimal("0.001")


def validate_positive_quantity(value: Decimal | str | int | float) -> Decimal:
    """
    Validates and quantizes a cart item quantity.
    Rejects None, non-numbers, non-positive values, and values with more than 3 decimal places.
    """
    if value is None:
        raise ValidationError("Quantity cannot be None.")
    try:
        dec = Decimal(str(value))
    except Exception as e:
        raise ValidationError(f"Invalid decimal quantity: {value}") from e

    if dec.as_tuple().exponent < -3:
        raise ValidationError("Quantity cannot have more than 3 decimal places.")

    dec = dec.quantize(QUANTITY_PRECISION)
    if dec <= Decimal("0.000"):
        raise ValidationError("Quantity must be greater than zero.")
    return dec


class Cart(models.Model):
    """
    Shop-scoped Cart representation.

    Represents the customer's current shopping state within a specific Shop context.
    A cart belongs to strictly one Shop and cannot contain products from multiple Shops.
    May exist anonymously without a Customer, or be associated with a Shop-specific Customer.
    No persistent relationship exists between Cart and Order.
    """

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="carts",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"
        ordering = ["-updated_at", "id"]
        indexes = [
            models.Index(fields=["shop", "customer"], name="cart_cart_shop_cust_idx"),
            models.Index(fields=["shop", "-updated_at"], name="cart_cart_shop_upd_idx"),
        ]

    def __str__(self) -> str:
        cust_str = f" - Customer: {self.customer_id}" if self.customer_id else " - Anonymous"
        return f"Cart #{self.pk} (Shop: {self.shop_id}{cust_str})"

    def clean(self) -> None:
        super().clean()
        if self.customer_id and self.shop_id:
            if self.customer.shop_id != self.shop_id:
                raise ValidationError({"customer": "Customer must belong to the same Shop as the Cart."})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def item_count(self) -> int:
        """Returns the number of distinct item lines in the cart."""
        return self.items.count()

    @property
    def total_quantity(self) -> Decimal:
        """Returns the sum of all item quantities in the cart."""
        total = Decimal("0.000")
        for item in self.items.all():
            total += item.quantity
        return total

    @property
    def subtotal(self) -> Decimal:
        """Computes subtotal of all items whose price is available."""
        total = Decimal("0.00")
        for item in self.items.select_related("product", "variant"):
            price = item.unit_price
            if price is not None:
                total += (price * item.quantity).quantize(Decimal("0.01"))
        return total


class CartItem(models.Model):
    """
    Shop-scoped Cart Item representation.

    Represents an item line in a Cart.
    Must refer to a ShopProduct belonging to the same Shop as the Cart.
    Optionally references a ProductVariant belonging to that ShopProduct.
    Quantity must be positive and supports up to 3 decimal places.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "catalog.ShopProduct",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart_items",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("1.000"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        ordering = ["cart", "id"]
        constraints = [
            models.CheckConstraint(
                check=Q(quantity__gt=0),
                name="cart_cartitem_quantity_positive",
            ),
            models.UniqueConstraint(
                fields=["cart", "product"],
                condition=Q(variant__isnull=True),
                name="cart_cartitem_unique_cart_product",
            ),
            models.UniqueConstraint(
                fields=["cart", "variant"],
                condition=Q(variant__isnull=False),
                name="cart_cartitem_unique_cart_variant",
            ),
        ]
        indexes = [
            models.Index(fields=["cart", "product"], name="cart_ci_cart_prod_idx"),
            models.Index(fields=["cart", "variant"], name="cart_ci_cart_var_idx"),
        ]

    def __str__(self) -> str:
        var_str = f" (Variant: {self.variant.name})" if self.variant_id else ""
        return f"{self.quantity}x {self.product.name}{var_str} in Cart #{self.cart_id}"

    @property
    def unit_price(self) -> Decimal | None:
        """
        Returns the effective unit price from the variant if selected and priced,
        otherwise falls back to the parent product's price.
        """
        if self.variant_id and self.variant.price is not None:
            return self.variant.price
        return self.product.price

    @property
    def line_total(self) -> Decimal | None:
        """Returns unit_price * quantity quantized to 2 decimal places, or None if price is not set."""
        price = self.unit_price
        if price is None:
            return None
        return (price * self.quantity).quantize(Decimal("0.01"))

    def clean(self) -> None:
        super().clean()
        if self.quantity is not None:
            self.quantity = validate_positive_quantity(self.quantity)

        # Multi-tenancy check: Product must belong to the same Shop as the Cart
        if self.cart_id and self.product_id:
            if self.product.shop_id != self.cart.shop_id:
                raise ValidationError({"product": "Product must belong to the same Shop as the Cart."})

        # Variant integrity check: Variant must belong to the selected Product
        if self.variant_id and self.product_id:
            if self.variant.product_id != self.product_id:
                raise ValidationError({"variant": "Variant must belong to the selected Product."})

    def save(self, *args, **kwargs) -> None:
        if self.quantity is not None:
            self.quantity = validate_positive_quantity(self.quantity)
        self.full_clean()
        super().save(*args, **kwargs)
