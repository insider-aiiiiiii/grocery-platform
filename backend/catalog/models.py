from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


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


class ShopCategory(models.Model):
    """
    Shop-owned Category representation fully controlled by the Merchant.

    Merchants can create, edit, delete categories, and create subcategories.
    Deleting a category preserves all assigned products, leaving them uncategorized
    per the finalized Catalog specification.
    """

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="categories",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shop Category"
        verbose_name_plural = "Shop Categories"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "slug"],
                condition=~Q(slug=""),
                name="catalog_shopcategory_unique_shop_slug",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "is_active"], name="catalog_sc_shop_act_idx"),
            models.Index(fields=["shop", "name"], name="catalog_sc_shop_name_idx"),
        ]

    def clean(self):
        super().clean()
        if self.parent_id:
            if self.parent_id == self.id:
                raise ValidationError({"parent": "A category cannot be its own parent."})
            if self.parent.shop_id != self.shop_id:
                raise ValidationError({"parent": "Parent category must belong to the same Shop."})

    @property
    def is_subcategory(self) -> bool:
        return self.parent_id is not None

    def __str__(self):
        if self.parent_id:
            return f"{self.parent.name} > {self.name} (Shop: {self.shop_id})"
        return f"{self.name} (Shop: {self.shop_id})"


class ShopBrand(models.Model):
    """
    Shop-owned Brand representation fully controlled by the Merchant.

    Merchants can create, edit, deactivate, and delete brands for their Shop
    Catalog. Deleting a brand preserves all assigned products, leaving their
    brand reference cleared per domain rules.
    """

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="brands",
    )
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shop Brand"
        verbose_name_plural = "Shop Brands"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "slug"],
                condition=~Q(slug=""),
                name="catalog_shopbrand_unique_shop_slug",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "is_active"], name="catalog_sb_shop_act_idx"),
            models.Index(fields=["shop", "name"], name="catalog_sb_shop_name_idx"),
        ]

    def __str__(self):
        return f"{self.name} (Shop: {self.shop_id})"


class ShopCustomAttribute(models.Model):
    """
    Shop-owned Custom Attribute representation controlled by the Merchant.

    Merchants can create, edit, and delete custom attributes and manage
    associated basic values/options for their Shop Catalog without any
    fixed global attribute taxonomy.
    """

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="custom_attributes",
    )
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    values = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shop Custom Attribute"
        verbose_name_plural = "Shop Custom Attributes"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["shop", "name"],
                name="catalog_shopcustomattribute_unique_shop_name",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "is_active"], name="catalog_sca_shop_act_idx"),
            models.Index(fields=["shop", "name"], name="catalog_sca_shop_name_idx"),
        ]

    def clean(self):
        super().clean()
        if not isinstance(self.values, list):
            raise ValidationError({"values": "Values must be a list of attribute values."})
        for item in self.values:
            if not isinstance(item, (str, int, float, bool)):
                raise ValidationError({"values": "Attribute values must be primitive items."})

    def add_value(self, value):
        if not isinstance(self.values, list):
            self.values = []
        if value not in self.values:
            self.values.append(value)

    def remove_value(self, value):
        if isinstance(self.values, list) and value in self.values:
            self.values.remove(value)

    def __str__(self):
        return f"{self.name} (Shop: {self.shop_id})"


class ShopProduct(models.Model):
    """
    Shop-specific sellable product representation independently controlled by Merchant.

    A Shop Product may be created directly by a Merchant (requiring no approval)
    or selected from a platform Master Product. In both cases, the Shop Product is
    completely independent: updates or deletion of a Master Product do not alter
    or impair existing Shop Products, nor does any automatic synchronization occur.
    """

    shop = models.ForeignKey(
        "shops.Shop",
        on_delete=models.CASCADE,
        related_name="products",
    )
    master_product = models.ForeignKey(
        MasterProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop_products",
    )
    categories = models.ManyToManyField(
        ShopCategory,
        blank=True,
        related_name="products",
    )
    brand_ref = models.ForeignKey(
        ShopBrand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="Shop Brand",
    )
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    brand = models.CharField(max_length=255, blank=True, default="")
    image = models.FileField(
        upload_to="catalog/shop_products/",
        blank=True,
        null=True,
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    sku = models.CharField(max_length=128, blank=True, default="")
    attributes = models.JSONField(default=dict, blank=True)
    is_visible = models.BooleanField(default=True, db_index=True)
    is_available = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shop Product"
        verbose_name_plural = "Shop Products"
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                check=Q(price__gte=0) | Q(price__isnull=True),
                name="catalog_shopproduct_price_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["shop", "is_visible", "is_available"], name="catalog_sp_shop_vis_avail_idx"),
            models.Index(fields=["shop", "name"], name="catalog_sp_shop_name_idx"),
            models.Index(fields=["shop", "sku"], name="catalog_sp_shop_sku_idx"),
        ]

    def clean(self):
        super().clean()
        if self.price is not None and self.price < Decimal("0.00"):
            raise ValidationError({"price": "Price cannot be negative."})
        if self.brand_ref_id and self.brand_ref.shop_id != self.shop_id:
            raise ValidationError({"brand_ref": "Brand must belong to the same Shop."})
        if not isinstance(self.attributes, dict):
            raise ValidationError({"attributes": "Attributes must be a key-value dictionary."})
        for key, val in self.attributes.items():
            if not isinstance(key, str) or not key.strip():
                raise ValidationError({"attributes": "Attribute names must be non-empty strings."})
            if not isinstance(val, (str, int, float, bool, list)):
                raise ValidationError({"attributes": f"Attribute '{key}' value must be a primitive or list of values."})
            if isinstance(val, list):
                for item in val:
                    if not isinstance(item, (str, int, float, bool)):
                        raise ValidationError({"attributes": f"Attribute '{key}' list items must be primitive values."})

    def __str__(self):
        return f"{self.name} (Shop: {self.shop_id})"

    @property
    def shop_brand(self):
        return self.brand_ref

    @shop_brand.setter
    def shop_brand(self, value):
        self.brand_ref = value

    @property
    def effective_brand(self) -> str:
        """
        Returns the assigned ShopBrand name if present, falling back to
        the free-form brand text or Master Product brand.
        """
        if self.brand_ref_id:
            return self.brand_ref.name
        return self.brand

    @property
    def has_image(self) -> bool:
        """Returns True if the product has an image assigned."""
        return bool(self.image)

    @property
    def is_customer_visible(self) -> bool:
        """
        True if the product is visible in customer-facing catalog.
        Hidden products are never visible to customers.
        Out-of-stock and manually unavailable products remain visible.
        """
        return self.is_visible

    def is_orderable(self, stock_quantity: int | None = None) -> bool:
        """
        Determines if this product can be ordered by a customer.
        Must be visible AND manually available AND in stock (if stock_quantity provided).
        Zero inventory or manually unavailable products cannot be ordered.
        """
        if not self.is_visible or not self.is_available:
            return False
        if stock_quantity is not None and stock_quantity <= 0:
            return False
        return True

    def get_display_status(self, stock_quantity: int | None = None, variant_stock_map: dict | None = None) -> str:
        """
        Computes customer-facing catalog display state preserving the strict distinction
        between catalog visibility (hidden vs visible), manual availability (unavailable),
        and inventory availability (out of stock).
        """
        if not self.is_visible:
            return "HIDDEN"
        if not self.is_available:
            return "UNAVAILABLE"
        if self.has_variants:
            visible_variants = self.get_visible_variants()
            if not visible_variants.exists():
                return "HIDDEN"
            all_unavail_or_oos = True
            for var in visible_variants:
                var_stock = variant_stock_map.get(var.id) if variant_stock_map else None
                if var.is_orderable(stock_quantity=var_stock):
                    all_unavail_or_oos = False
                    break
            if all_unavail_or_oos:
                return "OUT_OF_STOCK"
            return "AVAILABLE"
        if stock_quantity is not None and stock_quantity <= 0:
            return "OUT_OF_STOCK"
        return "AVAILABLE"

    @property
    def has_variants(self) -> bool:
        """Returns True if this product has defined variants."""
        return self.variants.exists()

    @property
    def is_uncategorized(self) -> bool:
        """Returns True if the product is not assigned to any category."""
        return not self.categories.exists()

    def get_visible_variants(self):
        """Returns variants that are visible to customers."""
        return self.variants.filter(is_visible=True)

    def get_available_variants(self, stock_map: dict | None = None):
        """
        Returns variants that are both visible and manually available.
        If stock_map is supplied, filters out variants with zero inventory.
        """
        qs = self.variants.filter(is_visible=True, is_available=True)
        if stock_map is not None:
            available_ids = [v.id for v in qs if stock_map.get(v.id, 0) > 0]
            return qs.filter(id__in=available_ids)
        return qs

    def get_attribute(self, name: str, default=None):
        """Returns the value(s) for a given attribute name."""
        return self.attributes.get(name, default)

    def set_attribute(self, name: str, value):
        """Sets an attribute with a single value or list of values."""
        if not isinstance(self.attributes, dict):
            self.attributes = {}
        self.attributes[name] = value

    def add_attribute_value(self, name: str, value):
        """
        Adds a value to an attribute's list of values. If the attribute
        has a single scalar value, converts it into a list containing both.
        """
        if not isinstance(self.attributes, dict):
            self.attributes = {}
        current = self.attributes.get(name)
        if current is None:
            self.attributes[name] = [value]
        elif isinstance(current, list):
            if value not in current:
                current.append(value)
        else:
            if current != value:
                self.attributes[name] = [current, value]
            else:
                self.attributes[name] = [current]

    def remove_attribute(self, name: str):
        """Removes an attribute from product attributes."""
        if isinstance(self.attributes, dict) and name in self.attributes:
            del self.attributes[name]

    @classmethod
    def from_master_product(cls, shop, master_product, **kwargs):
        """
        Factory helper to create an independent Shop Product from a Master Product.
        Copies product metadata into the Shop Product without binding updates.
        """
        data = {
            "shop": shop,
            "master_product": master_product,
            "name": master_product.name,
            "description": master_product.description,
            "brand": master_product.brand,
        }
        data.update(kwargs)
        return cls.objects.create(**data)


class ProductVariant(models.Model):
    """
    Shop-specific variant representation belonging to a Shop Product.

    Merchants can create, edit, and delete variants, configuring variant name,
    image, price, SKU, description, and custom attributes. Duplicate SKUs are allowed.
    If a variant has no image, it falls back to the parent product's image.
    """

    product = models.ForeignKey(
        ShopProduct,
        on_delete=models.CASCADE,
        related_name="variants",
    )
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    image = models.FileField(
        upload_to="catalog/variants/",
        blank=True,
        null=True,
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    sku = models.CharField(max_length=128, blank=True, default="")
    attributes = models.JSONField(default=dict, blank=True)
    is_visible = models.BooleanField(default=True, db_index=True)
    is_available = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"
        ordering = ["product", "name", "id"]
        constraints = [
            models.CheckConstraint(
                check=Q(price__gte=0) | Q(price__isnull=True),
                name="catalog_productvariant_price_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "is_visible", "is_available"], name="catalog_pv_prod_vis_avail_idx"),
            models.Index(fields=["product", "name"], name="catalog_pv_prod_name_idx"),
            models.Index(fields=["sku"], name="catalog_pv_sku_idx"),
        ]

    def clean(self):
        super().clean()
        if self.price is not None and self.price < Decimal("0.00"):
            raise ValidationError({"price": "Variant price cannot be negative."})
        if not isinstance(self.attributes, dict):
            raise ValidationError({"attributes": "Attributes must be a key-value dictionary."})
        for key, val in self.attributes.items():
            if not isinstance(key, str) or not key.strip():
                raise ValidationError({"attributes": "Attribute names must be non-empty strings."})
            if not isinstance(val, (str, int, float, bool, list)):
                raise ValidationError({"attributes": f"Attribute '{key}' value must be a primitive or list of values."})
            if isinstance(val, list):
                for item in val:
                    if not isinstance(item, (str, int, float, bool)):
                        raise ValidationError({"attributes": f"Attribute '{key}' list items must be primitive values."})

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def has_image(self) -> bool:
        """Returns True if the variant has its own image or effective parent image."""
        return bool(self.effective_image)

    @property
    def effective_image(self):
        """
        When a variant has no image, fallback to parent product image
        per domain specification.
        """
        if bool(self.image):
            return self.image
        return self.product.image if self.product_id else None

    @property
    def effective_price(self):
        """
        Returns variant price if set; otherwise falls back to parent product price.
        """
        if self.price is not None:
            return self.price
        return self.product.price if self.product_id else None

    @property
    def effective_description(self) -> str:
        """
        Returns variant description if set; otherwise falls back to parent product description.
        """
        if self.description:
            return self.description
        return self.product.description if self.product_id else ""

    @property
    def effective_brand(self) -> str:
        """
        Returns parent product's effective brand.
        """
        return self.product.effective_brand if self.product_id else ""

    @property
    def is_customer_visible(self) -> bool:
        """
        A variant is customer-visible only if both it and its parent product are visible.
        """
        if not self.is_visible:
            return False
        return self.product.is_visible if self.product_id else True

    def is_orderable(self, stock_quantity: int | None = None) -> bool:
        """
        A variant can only be ordered if both it and its parent product are visible,
        both are manually available, and it is in stock (if stock_quantity provided).
        """
        if not self.is_customer_visible:
            return False
        if not self.is_available:
            return False
        if self.product_id and not self.product.is_available:
            return False
        if stock_quantity is not None and stock_quantity <= 0:
            return False
        return True

    def get_display_status(self, stock_quantity: int | None = None) -> str:
        """
        Computes customer display state for this variant preserving the distinction
        between catalog visibility (hidden), manual availability (unavailable),
        and inventory availability (out of stock).
        """
        if not self.is_customer_visible:
            return "HIDDEN"
        if not self.is_available or (self.product_id and not self.product.is_available):
            return "UNAVAILABLE"
        if stock_quantity is not None and stock_quantity <= 0:
            return "OUT_OF_STOCK"
        return "AVAILABLE"

    def get_attribute(self, name: str, default=None):
        """Returns the value(s) for a given attribute name."""
        return self.attributes.get(name, default)

    def set_attribute(self, name: str, value):
        """Sets a variant attribute with a single value or list of values."""
        if not isinstance(self.attributes, dict):
            self.attributes = {}
        self.attributes[name] = value

    def add_attribute_value(self, name: str, value):
        """Adds a value to a variant attribute's list of values."""
        if not isinstance(self.attributes, dict):
            self.attributes = {}
        current = self.attributes.get(name)
        if current is None:
            self.attributes[name] = [value]
        elif isinstance(current, list):
            if value not in current:
                current.append(value)
        else:
            if current != value:
                self.attributes[name] = [current, value]
            else:
                self.attributes[name] = [current]

    def remove_attribute(self, name: str):
        """Removes an attribute from variant attributes."""
        if isinstance(self.attributes, dict) and name in self.attributes:
            del self.attributes[name]


# Domain aliases
Category = ShopCategory
Product = ShopProduct
Variant = ProductVariant
ShopProductVariant = ProductVariant
Brand = ShopBrand
ShopProductBrand = ShopBrand
ShopAttribute = ShopCustomAttribute
CustomAttribute = ShopCustomAttribute
Attribute = ShopCustomAttribute
