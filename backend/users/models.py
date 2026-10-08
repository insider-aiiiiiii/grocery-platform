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

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(role__in=["SUPER_ADMIN", "MERCHANT"]),
                name="users_user_valid_role",
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
    mobile_number = models.CharField(max_length=32, unique=True)
    email = models.EmailField(blank=True, null=True, unique=True)
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
        if self.user_id and self.user.role != User.Role.MERCHANT:
            raise ValidationError({"user": "Merchant profiles require a MERCHANT user."})
