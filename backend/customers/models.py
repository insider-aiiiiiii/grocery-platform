import re

from django.core.exceptions import ValidationError
from django.db import models


def normalize_whatsapp_number(value: str) -> str:
    """
    Validate and normalize Indian mobile numbers to E.164 format (+91XXXXXXXXXX).

    Accepts:
      - 10-digit Indian mobile number starting with 6, 7, 8, or 9 (e.g. '7896547658')
      - Number with '+91' country code prefix (e.g. '+917685432278')
      - Optional whitespace or hyphens between prefix and digits

    Rejects:
      - Numbers with invalid lengths (e.g. 9 or 11 digits)
      - Numbers with invalid characters (e.g. alphabetic or special characters)
      - Numbers starting with invalid digits (e.g. 0-5)
      - Arbitrary international numbers (e.g. +1..., +44...)
    """
    if not isinstance(value, str):
        raise ValidationError({"whatsapp_number": "WhatsApp number must be a string."})

    cleaned = value.strip().replace(" ", "").replace("-", "")
    match = re.fullmatch(r"^(\+91)?([6-9]\d{9})$", cleaned)
    if not match:
        raise ValidationError(
            {"whatsapp_number": "Enter a valid 10-digit Indian mobile number (e.g., 7896547658 or +917685432278)."}
        )

    return f"+91{match.group(2)}"


class Customer(models.Model):
    """
    Shop-specific Customer profile.

    Represents a customer's profile within a specific Shop tenant boundary.
    Customer profiles are completely distinct from authenticated User accounts
    and do not have login credentials (passwords, usernames, etc.).
    """

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="customers",
    )
    name = models.CharField(max_length=255, blank=True, default="")
    whatsapp_number = models.CharField(max_length=16)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ["-created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "whatsapp_number"],
                name="customers_customer_unique_shop_whatsapp",
            ),
            models.CheckConstraint(
                check=~models.Q(whatsapp_number=""),
                name="customers_customer_whatsapp_not_empty",
            ),
        ]
        indexes = [
            models.Index(
                fields=["shop", "whatsapp_number"],
                name="customers_cust_shop_wa_idx",
            ),
        ]

    def __str__(self) -> str:
        name_str = f" - {self.name}" if self.name else ""
        return f"Customer {self.whatsapp_number}{name_str} (Shop: {self.shop_id})"

    def clean(self) -> None:
        super().clean()
        if not self.whatsapp_number:
            raise ValidationError({"whatsapp_number": "WhatsApp number is required."})

        self.whatsapp_number = normalize_whatsapp_number(self.whatsapp_number)

        # CUS-002: Preserve one-Shop profile scope - prevent reassigning shop
        if self.pk:
            orig = Customer.objects.filter(pk=self.pk).values("shop_id").first()
            if orig and orig["shop_id"] != self.shop_id:
                raise ValidationError({"shop": "Cannot reassign a Customer profile to a different Shop."})

        if self.shop_id:
            qs = Customer.objects.filter(shop_id=self.shop_id, whatsapp_number=self.whatsapp_number)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    {"whatsapp_number": "A customer with this WhatsApp number already exists in this shop."}
                )

    def save(self, *args, **kwargs) -> None:
        if not self.whatsapp_number:
            raise ValidationError({"whatsapp_number": "WhatsApp number is required."})
        self.whatsapp_number = normalize_whatsapp_number(self.whatsapp_number)
        if self.pk:
            orig = Customer.objects.filter(pk=self.pk).values("shop_id").first()
            if orig and orig["shop_id"] != self.shop_id:
                raise ValidationError({"shop": "Cannot reassign a Customer profile to a different Shop."})
        super().save(*args, **kwargs)
