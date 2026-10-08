from django.contrib.auth.models import AbstractUser
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
