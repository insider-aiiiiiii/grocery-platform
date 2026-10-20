import hashlib
import re
import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


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


class CustomerManager(models.Manager):
    """Custom manager for Shop-specific Customer profiles."""

    def create_or_recognize(
        self,
        shop: models.Model,
        whatsapp_number: str,
        name: str = "",
        cart: models.Model = None,
    ):
        """Domain convenience method to create or recognize a customer for a shop."""
        from .services import create_or_recognize_customer
        return create_or_recognize_customer(shop=shop, whatsapp_number=whatsapp_number, name=name, cart=cart)

    def recognize(
        self,
        shop: models.Model,
        whatsapp_number: str,
    ):
        """Domain convenience method to recognize an existing customer in a shop."""
        from .services import recognize_customer
        return recognize_customer(shop=shop, whatsapp_number=whatsapp_number)


class Customer(models.Model):
    """
    Shop-specific Customer profile.

    Represents a customer's profile within a specific Shop tenant boundary.
    Customer profiles are completely distinct from authenticated User accounts
    and do not have login credentials (passwords, usernames, etc.).
    """

    objects = CustomerManager()

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

        # Global identity boundary: number cannot be claimed by authenticated User (Merchant/Super Admin)
        from users.models import User
        if User.objects.filter(mobile_number=self.whatsapp_number).exists():
            raise ValidationError(
                {"whatsapp_number": "This WhatsApp number is already registered as an authenticated user identity."}
            )

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

        # Global identity boundary check
        from users.models import User
        if User.objects.filter(mobile_number=self.whatsapp_number).exists():
            raise ValidationError(
                {"whatsapp_number": "This WhatsApp number is already registered as an authenticated user identity."}
            )

        super().save(*args, **kwargs)


class CustomerSessionManager(models.Manager):
    """Issue opaque credentials for the one active session of a Shop profile."""

    @transaction.atomic
    def issue_for_profile(self, profile):
        profile = Customer.objects.select_for_update().get(pk=profile.pk)
        now = timezone.now()
        self.filter(customer=profile, revoked_at__isnull=True).update(revoked_at=now)
        secret = secrets.token_urlsafe(32)
        session = self.create(
            customer=profile,
            token_digest=hashlib.sha256(secret.encode("ascii")).hexdigest(),
            expires_at=now + timedelta(days=30),
        )
        return session, secret


class CustomerSession(models.Model):
    """A dedicated, digest-only session bound to exactly one Shop Customer profile."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="sessions")
    token_digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    objects = CustomerSessionManager()

    class Meta:
        indexes = [models.Index(fields=["customer", "revoked_at", "expires_at"], name="customers_sess_scope_exp_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=models.Q(revoked_at__isnull=True),
                name="customers_session_one_active_profile",
            ),
            models.CheckConstraint(check=models.Q(expires_at__gt=models.F("created_at")), name="customers_session_expiry_after_create"),
        ]

    @property
    def is_active(self):
        now = timezone.now()
        return (
            self.revoked_at is None
            and now < self.expires_at
            and now < self.created_at + timedelta(days=30)
        )


class HistoryLinkGrantManager(models.Manager):
    """Issue and atomically consume one-time credentials for a profile's history link."""

    @transaction.atomic
    def issue(self, *, customer, purpose):
        customer = Customer.objects.select_related("shop").get(pk=customer.pk)
        now = timezone.now()
        secret = secrets.token_urlsafe(32)
        grant = self.create(
            customer=customer,
            shop=customer.shop,
            purpose=purpose,
            token_digest=hashlib.sha256(secret.encode("ascii")).hexdigest(),
            expires_at=now + timedelta(minutes=15),
        )
        return grant, secret

    @transaction.atomic
    def consume(self, secret, *, customer, shop, purpose):
        digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        now = timezone.now()
        grant = (
            self.select_for_update()
            .filter(
                token_digest=digest,
                customer=customer,
                shop=shop,
                purpose=purpose,
                consumed_at__isnull=True,
                revoked_at__isnull=True,
                expires_at__gt=now,
            )
            .first()
        )
        if grant is None:
            return None
        grant.consumed_at = now
        grant.save(update_fields=["consumed_at"])
        return grant


class HistoryLinkGrant(models.Model):
    """Digest-only, single-use, short-lived grant bound to one profile and Shop."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="history_link_grants")
    shop = models.ForeignKey("shops.Shop", on_delete=models.CASCADE, related_name="customer_history_grants")
    purpose = models.CharField(max_length=64)
    token_digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    objects = HistoryLinkGrantManager()

    class Meta:
        indexes = [models.Index(fields=["customer", "shop", "purpose", "expires_at"], name="cust_hist_grant_scope_idx")]
        constraints = [
            models.CheckConstraint(check=models.Q(expires_at__gt=models.F("created_at")), name="cust_hist_grant_exp_after_create"),
            models.CheckConstraint(check=~(models.Q(consumed_at__isnull=False) & models.Q(revoked_at__isnull=False)), name="cust_hist_grant_single_terminal_state"),
        ]

    def clean(self):
        super().clean()
        if self.customer_id and self.shop_id and self.customer.shop_id != self.shop_id:
            raise ValidationError({"shop": "History link grants must use the Customer profile's Shop."})

    def save(self, *args, **kwargs):
        if self.customer_id and self.shop_id and self.customer.shop_id != self.shop_id:
            raise ValidationError({"shop": "History link grants must use the Customer profile's Shop."})
        return super().save(*args, **kwargs)

    @property
    def is_active(self):
        now = timezone.now()
        return self.consumed_at is None and self.revoked_at is None and now < self.expires_at
