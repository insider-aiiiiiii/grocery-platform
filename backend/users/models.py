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


class UserAuthSession(models.Model):
    """Revocable session metadata for authenticated users; access JWTs are not persisted."""

    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auth_sessions",
    )
    refresh_token = models.OneToOneField(
        "token_blacklist.OutstandingToken",
        on_delete=models.CASCADE,
        related_name="auth_session",
    )


class MerchantPasswordRecoveryChallenge(models.Model):
    """Single-use recovery state; the submitted mobile and OTP are never stored raw."""

    mobile_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="password_recovery_challenges",
    )
    otp_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    request_window_started_at = models.DateTimeField()
    request_count = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)


class MerchantPasswordRecoveryIPThrottle(models.Model):
    """Short-lived request counter keyed by an HMAC of the source IP address."""

    ip_hash = models.CharField(max_length=64, unique=True)
    window_started_at = models.DateTimeField()
    request_count = models.PositiveSmallIntegerField(default=0)


class SuperAdminRecoveryThrottle(models.Model):
    """Hashed contact/IP key used to limit Super Admin recovery requests."""

    fingerprint = models.CharField(max_length=64, unique=True)
    window_started_at = models.DateTimeField()
    request_count = models.PositiveSmallIntegerField(default=0)


class SuperAdminRecoveryChallenge(models.Model):
    class Purpose(models.TextChoices):
        SELF_RECOVERY = "SELF_RECOVERY", "Self recovery"
        ADMIN_RESET = "ADMIN_RESET", "Administrative reset"

    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        MOBILE = "MOBILE", "Mobile"

    purpose = models.CharField(max_length=16, choices=Purpose.choices)
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="super_admin_recovery_challenges",
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="initiated_super_admin_resets",
    )
    channel = models.CharField(max_length=6, choices=Channel.choices)
    contact_fingerprint = models.CharField(max_length=64)
    code_hash = models.CharField(max_length=64)
    requested_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
