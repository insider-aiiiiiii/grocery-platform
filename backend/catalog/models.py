from django.db import models


class MasterCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Master Category"
        verbose_name_plural = "Master Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class MasterProduct(models.Model):
    """
    Platform-level reusable product library entity managed by Super Admin.

    Master Product is not itself a Shop sellable product. It serves as a
    reusable template that Merchants may select for their independent Shop
    Catalogs. Master Products do not automatically synchronize to or dictate
    Shop Products.
    """

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        MasterCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="master_products",
        verbose_name="Master Category",
    )
    brand = models.CharField(max_length=255, blank=True, default="")
    image = models.FileField(
        upload_to="catalog/master_products/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Master Product"
        verbose_name_plural = "Master Products"
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["is_active", "name"], name="catalog_mp_act_name_idx"),
        ]

    def __str__(self):
        return self.name

