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

    # Contact number mirrors merchant's mobile number
    contact_number = models.CharField(max_length=32)

    # Lifecycle status
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Operational controls: Business hours & temporary closure
    is_temporarily_closed = models.BooleanField(default=False)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    # Fulfillment options
    is_home_delivery_enabled = models.BooleanField(default=True)
    is_pickup_enabled = models.BooleanField(default=True)
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
                check=Q(delivery_charge__gte=0),
                name="shops_shop_delivery_charge_non_negative",
            ),
        ]

    def clean(self):
        super().clean()
        # Contact number must match merchant's mobile number if merchant is assigned
        if self.merchant_id and hasattr(self.merchant, "user") and self.merchant.user.mobile_number:
            if not self.contact_number:
                self.contact_number = self.merchant.user.mobile_number

    def __str__(self):
        return f"{self.name} ({self.status})"
