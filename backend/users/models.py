import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        MERCHANT = "MERCHANT", "Merchant"

    role = models.CharField(max_length=11, choices=Role.choices)
    mobile_number = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(role__in=["SUPER_ADMIN", "MERCHANT"]),
                name="users_user_valid_role",
            ),
            models.UniqueConstraint(
                fields=["email"],
                condition=~Q(email=""),
                name="users_user_email_unique",
            ),
            models.UniqueConstraint(
                fields=["mobile_number"],
                condition=Q(mobile_number__isnull=False) & ~Q(mobile_number=""),
                name="users_user_mobile_unique",
            ),
            models.CheckConstraint(
                check=(
                    ~Q(role="MERCHANT")
                    | (Q(mobile_number__isnull=False) & ~Q(mobile_number=""))
                ),
                name="users_merchant_requires_mobile",
            ),
            models.CheckConstraint(
                check=(
                    ~Q(role="SUPER_ADMIN")
                    | (~Q(email="") | (Q(mobile_number__isnull=False) & ~Q(mobile_number="")))
                ),
                name="users_super_admin_requires_login_id",
            ),
        ]


class Merchant(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DEACTIVATED = "DEACTIVATED", "Deactivated"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="merchant",
    )
    status = models.CharField(
        max_length=11,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    must_change_password = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=["ACTIVE", "DEACTIVATED"]),
                name="users_merchant_valid_status",
            ),
        ]

    def clean(self):
        super().clean()
        if self.user_id:
            if self.user.role != User.Role.MERCHANT:
                raise ValidationError({"user": "Merchant profiles require a MERCHANT user."})
            if not self.user.mobile_number:
                raise ValidationError({"user": "Merchant users require a mobile number."})


class MerchantAuthSession(models.Model):
    """Revocable server-side session metadata; access JWTs are never persisted."""

    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant_auth_sessions",
    )
    refresh_token = models.OneToOneField(
        "token_blacklist.OutstandingToken",
        on_delete=models.CASCADE,
        related_name="merchant_auth_session",
    )
