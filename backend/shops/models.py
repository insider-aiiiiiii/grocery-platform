import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


def generate_shop_public_slug() -> str:
    """Generate a random public slug for the shop's public link/QR code."""
    return uuid.uuid4().hex[:12]


class Shop(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DEACTIVATED = "DEACTIVATED", "Deactivated"
        SUSPENDED = "SUSPENDED", "Suspended"

    class DeliveryFeeType(models.TextChoices):
        FIXED = "FIXED", "Fixed Fee"
        CONFIRMED_ON_WHATSAPP = "CONFIRMED_ON_WHATSAPP", "Fee Confirmed on WhatsApp"

    # Enforce 1-to-1 relationship between Merchant and Shop at DB level
    merchant = models.OneToOneField(
        "users.Merchant",
        on_delete=models.CASCADE,
        related_name="shop",
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    logo = models.FileField(upload_to="shops/logos/", blank=True, null=True)

    # Structured address required per domain specification
    address_line = models.CharField(max_length=255)
    area = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=128)
    pincode = models.CharField(max_length=16)

    # Contact number strictly mirrors merchant's mobile number
    contact_number = models.CharField(max_length=32)

    # Platform lifecycle status (controlled solely by Super Admin)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Operational controls: Temporary closure & business hours (Merchant controlled)
    is_temporarily_closed = models.BooleanField(default=False)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    # Fulfillment options (Merchant controlled)
    is_home_delivery_enabled = models.BooleanField(default=True)
    is_pickup_enabled = models.BooleanField(default=True)

    # Option 2 (Flexible): Fixed delivery fee OR Confirmed on WhatsApp
    delivery_fee_type = models.CharField(
        max_length=24,
        choices=DeliveryFeeType.choices,
        default=DeliveryFeeType.FIXED,
    )
    delivery_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Public identifier: used for public shop link and QR resolution (does not expose DB ID)
    public_slug = models.SlugField(
        max_length=64,
        unique=True,
        default=generate_shop_public_slug,
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=["ACTIVE", "DEACTIVATED", "SUSPENDED"]),
                name="shops_shop_valid_status",
            ),
            models.CheckConstraint(
                check=Q(delivery_fee_type__in=["FIXED", "CONFIRMED_ON_WHATSAPP"]),
                name="shops_shop_valid_delivery_fee_type",
            ),
            models.CheckConstraint(
                check=Q(delivery_charge__gte=0),
                name="shops_shop_delivery_charge_non_negative",
            ),
        ]

    def clean(self):
        super().clean()
        # Contact number must strictly mirror merchant's mobile number
        if self.merchant_id and hasattr(self.merchant, "user") and self.merchant.user.mobile_number:
            if not self.contact_number:
                self.contact_number = self.merchant.user.mobile_number
            elif self.contact_number != self.merchant.user.mobile_number:
                raise ValidationError(
                    {"contact_number": "Shop contact number must match the merchant's mobile number."}
                )

        if self.delivery_charge < 0:
            raise ValidationError({"delivery_charge": "Delivery charge cannot be negative."})

    def save(self, *args, **kwargs):
        # Auto-mirror contact number from merchant if empty
        if self.merchant_id and not self.contact_number and hasattr(self.merchant, "user"):
            self.contact_number = self.merchant.user.mobile_number or ""
        super().save(*args, **kwargs)

    # Super Admin lifecycle actions
    def suspend(self, save=True) -> None:
        """Super Admin action: suspend the shop."""
        self.status = self.Status.SUSPENDED
        if save:
            self.save(update_fields=["status", "updated_at"])

    def deactivate(self, save=True) -> None:
        """Super Admin action: deactivate the shop."""
        self.status = self.Status.DEACTIVATED
        if save:
            self.save(update_fields=["status", "updated_at"])

    def reactivate(self, save=True) -> None:
        """Super Admin action: reactivate/unsuspend shop and assign a fresh QR token."""
        self.status = self.Status.ACTIVE
        self.public_slug = generate_shop_public_slug()
        if save:
            self.save(update_fields=["status", "public_slug", "updated_at"])

    def unsuspend(self, save=True) -> None:
        """Alias for reactivate."""
        self.reactivate(save=save)

    def regenerate_public_slug(self, save=True) -> str:
        """Super Admin action: rotate public slug / QR code token."""
        self.public_slug = generate_shop_public_slug()
        if save:
            self.save(update_fields=["public_slug", "updated_at"])
        return self.public_slug

    def get_public_path(self) -> str:
        """Return the relative public endpoint path for this shop."""
        return f"/api/v1/shops/public/{self.public_slug}/"

    def __str__(self):
        return f"{self.name} ({self.status})"
