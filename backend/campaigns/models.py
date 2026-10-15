from django.db import models
from django.db.models import F, Q


class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    class ShopScope(models.TextChoices):
        ALL_SHOPS = "ALL_SHOPS", "All Shops"
        SELECTED_SHOPS = "SELECTED_SHOPS", "Selected Shops"

    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=6,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    shop_scope = models.CharField(
        max_length=14,
        choices=ShopScope.choices,
        default=ShopScope.ALL_SHOPS,
    )
    selected_shops = models.ManyToManyField(
        "shops.Shop",
        blank=True,
        related_name="display_campaigns",
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["DRAFT", "ACTIVE", "ENDED"]),
                name="campaigns_valid_status",
            ),
            models.CheckConstraint(
                condition=Q(shop_scope__in=["ALL_SHOPS", "SELECTED_SHOPS"]),
                name="campaigns_valid_shop_scope",
            ),
            models.CheckConstraint(
                condition=(
                    Q(starts_at__isnull=True)
                    | Q(ends_at__isnull=True)
                    | Q(starts_at__lte=F("ends_at"))
                ),
                name="campaigns_valid_schedule",
            ),
        ]

    def __str__(self):
        return self.title
