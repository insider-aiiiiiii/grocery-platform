from decimal import Decimal

from django.utils.text import slugify
from rest_framework import serializers

from config.request_data import shallow_mutable_copy

from .image_utils import download_external_image_to_storage
from .models import (
    MasterCategory,
    MasterProduct,
    MasterProductImage,
    ProductVariant,
    ShopBrand,
    ShopCategory,
    ShopCustomAttribute,
    ShopProduct,
)


class ShopCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Merchant Shop Categories and subcategories.

    Allows Merchants to:
    - Create categories and subcategories.
    - Full CRUD management within their own Shop.
    - Enforces tenant isolation for parent categories.
    """

    is_subcategory = serializers.BooleanField(read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    subcategories_count = serializers.IntegerField(source="subcategories.count", read_only=True)
    products_count = serializers.IntegerField(source="products.count", read_only=True)
    slug = serializers.SlugField(max_length=255, required=False, allow_blank=True)

    class Meta:
        model = ShopCategory
        fields = [
            "id",
            "shop",
            "parent",
            "parent_name",
            "name",
            "slug",
            "description",
            "is_active",
            "is_subcategory",
            "subcategories_count",
            "products_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "shop",
            "parent_name",
            "is_subcategory",
            "subcategories_count",
            "products_count",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty or whitespace only.")
        return value.strip()

    def validate(self, attrs):
        shop = self.context.get("shop")
        parent = attrs.get("parent")
        name = attrs.get("name")

        # Name requirement on creation
        if not self.instance and not name:
            raise serializers.ValidationError({"name": "Name is required."})

        # Slug generation / validation
        slug = attrs.get("slug")
        if slug is not None:
            slug = slug.strip()
            if slug:
                qs = ShopCategory.objects.filter(shop=shop, slug=slug)
                if self.instance:
                    qs = qs.exclude(id=self.instance.id)
                if qs.exists():
                    raise serializers.ValidationError({"slug": "A category with this slug already exists for this shop."})
            attrs["slug"] = slug
        elif not self.instance:
            # Auto-generate slug from name if not provided on creation
            target_name = attrs.get("name") or ""
            base_slug = slugify(target_name)
            if base_slug:
                candidate = base_slug
                counter = 1
                while ShopCategory.objects.filter(shop=shop, slug=candidate).exists():
                    candidate = f"{base_slug}-{counter}"
                    counter += 1
                attrs["slug"] = candidate

        # Tenant isolation check: parent must belong to the same Shop
        if parent:
            if shop and parent.shop_id != shop.id:
                raise serializers.ValidationError({"parent": "Parent category must belong to the same Shop."})

            if self.instance:
                if parent.id == self.instance.id:
                    raise serializers.ValidationError({"parent": "A category cannot be its own parent."})
                # Check for cyclic parent references
                curr = parent
                while curr is not None:
                    if curr.id == self.instance.id:
                        raise serializers.ValidationError({"parent": "Circular category hierarchy is not allowed."})
                    curr = curr.parent

        return attrs


class ShopBrandSerializer(serializers.ModelSerializer):
    """
    Serializer for Merchant Shop Brands.

    Allows Merchants to:
    - Create, edit, and delete Brands in their Shop Catalog.
    - Full CRUD management within their own Shop.
    - Enforces tenant isolation and slug uniqueness per Shop.
    """

    products_count = serializers.IntegerField(source="products.count", read_only=True)
    slug = serializers.SlugField(max_length=255, required=False, allow_blank=True)

    class Meta:
        model = ShopBrand
        fields = [
            "id",
            "shop",
            "name",
            "slug",
            "description",
            "is_active",
            "products_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "shop",
            "products_count",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty or whitespace only.")
        return value.strip()

    def validate(self, attrs):
        shop = self.context.get("shop")
        name = attrs.get("name")

        # Name requirement on creation
        if not self.instance and not name:
            raise serializers.ValidationError({"name": "Name is required."})

        # Slug generation / validation
        slug = attrs.get("slug")
        if slug is not None:
            slug = slug.strip()
            if slug:
                qs = ShopBrand.objects.filter(shop=shop, slug=slug)
                if self.instance:
                    qs = qs.exclude(id=self.instance.id)
                if qs.exists():
                    raise serializers.ValidationError({"slug": "A brand with this slug already exists for this shop."})
            attrs["slug"] = slug
        elif not self.instance:
            target_name = attrs.get("name") or ""
            base_slug = slugify(target_name)
            if base_slug:
                candidate = base_slug
                counter = 1
                while ShopBrand.objects.filter(shop=shop, slug=candidate).exists():
                    candidate = f"{base_slug}-{counter}"
                    counter += 1
                attrs["slug"] = candidate

        return attrs


class ShopCustomAttributeSerializer(serializers.ModelSerializer):
    """
    Serializer for Merchant Shop Custom Attributes and basic values.

    Allows Merchants to:
    - Create, edit, and delete custom attributes and manage values for their Shop Catalog.
    - Enforces unique attribute names per Shop.
    - Validates values as a list of primitive items (str, int, float, bool).
    """

    values = serializers.JSONField(required=False, default=list)

    class Meta:
        model = ShopCustomAttribute
        fields = [
            "id",
            "shop",
            "name",
            "description",
            "values",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "shop",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty or whitespace only.")
        return value.strip()

    def validate_values(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Values must be a list of attribute values.")
        for item in value:
            if not isinstance(item, (str, int, float, bool)):
                raise serializers.ValidationError("Attribute values must be primitive items.")
        return value

    def validate(self, attrs):
        shop = self.context.get("shop")
        name = attrs.get("name")

        if not self.instance and not name:
            raise serializers.ValidationError({"name": "Name is required."})

        # Name uniqueness within shop
        if name:
            qs = ShopCustomAttribute.objects.filter(shop=shop, name__iexact=name)
            if self.instance:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise serializers.ValidationError({"name": "An attribute with this name already exists for this shop."})

        return attrs


class MasterProductImageSerializer(serializers.ModelSerializer):
    effective_url = serializers.CharField(read_only=True)

    class Meta:
        model = MasterProductImage
        fields = [
            "id",
            "image",
            "image_url",
            "effective_url",
            "sort_order",
            "created_at",
        ]
        read_only_fields = ["id", "effective_url", "created_at"]


class MasterCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for platform-level Master Categories.
    """

    products_count = serializers.IntegerField(source="master_products.count", read_only=True)

    class Meta:
        model = MasterCategory
        fields = ["id", "name", "slug", "description", "is_active", "products_count", "created_at"]
        read_only_fields = ["id", "slug", "products_count", "created_at"]

    def create(self, validated_data):
        name = validated_data["name"].strip()
        slug = slugify(name) or "cat"
        validated_data["slug"] = slug
        return super().create(validated_data)


class MasterProductSerializer(serializers.ModelSerializer):
    """
    Serializer for platform-level Master Catalog products managed by Super Admin.

    Master Products serve as reusable templates for independent Shop Catalogs.
    They do not belong to any specific Shop and remain strictly independent
    of Shop Products. Supports up to 6 photos total per product and auto-downloads
    external image URLs directly to platform S3/media storage.
    """

    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    effective_image = serializers.SerializerMethodField()
    gallery_images = MasterProductImageSerializer(many=True, read_only=True)
    all_images = serializers.SerializerMethodField()
    images = serializers.ListField(
        child=serializers.CharField(max_length=2048),
        required=False,
        write_only=True,
    )
    clear_image = serializers.BooleanField(required=False, write_only=True, default=False)

    class Meta:
        model = MasterProduct
        fields = [
            "id",
            "name",
            "description",
            "category",
            "category_name",
            "brand",
            "image",
            "image_url",
            "effective_image",
            "gallery_images",
            "all_images",
            "images",
            "clear_image",
            "mrp",
            "unit",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category_name",
            "effective_image",
            "gallery_images",
            "all_images",
            "created_at",
            "updated_at",
        ]

    def get_effective_image(self, obj) -> str | None:
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        if obj.image_url:
            return obj.image_url
        return None

    def get_all_images(self, obj) -> list[str]:
        urls = []
        eff = self.get_effective_image(obj)
        if eff:
            urls.append(eff)
        request = self.context.get("request")
        for g_img in obj.gallery_images.all():
            if g_img.image:
                url = request.build_absolute_uri(g_img.image.url) if request else g_img.image.url
            else:
                url = g_img.image_url
            if url and url not in urls:
                urls.append(url)
        return urls[:6]

    def to_internal_value(self, data):
        # Resolve category if passed as a string name or category_name
        if hasattr(data, "_mutable") and not data._mutable:
            data = shallow_mutable_copy(data)
        elif not isinstance(data, dict):
            try:
                data = dict(data)
            except Exception:
                pass

        if isinstance(data, dict):
            cat_val = data.get("category")
            cat_name_val = data.get("category_name")
            target_name = None

            if isinstance(cat_val, str) and cat_val.strip() and not cat_val.strip().isdigit():
                target_name = cat_val.strip()
            elif isinstance(cat_name_val, str) and cat_name_val.strip() and not cat_name_val.strip().isdigit():
                target_name = cat_name_val.strip()

            if target_name:
                slug_base = slugify(target_name) or "cat"
                existing = MasterCategory.objects.filter(name__iexact=target_name).first()
                if not existing:
                    existing = MasterCategory.objects.filter(slug=slug_base).first()
                if not existing:
                    existing = MasterCategory.objects.create(name=target_name, slug=slug_base)
                data["category"] = existing.id

        return super().to_internal_value(data)

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty or whitespace only.")
        return value.strip()

    def validate_images(self, value):
        if value and len(value) > 6:
            raise serializers.ValidationError("A master product can have at most 6 photos.")
        return value

    def _sync_images(self, instance, images_list):
        """
        Processes a list of image URLs (up to 6), downloading external URLs to platform storage
        and attaching the 1st as primary and up to 5 additional as gallery images.
        """
        if images_list is None:
            return

        # Up to 6 images total
        images_to_process = images_list[:6]
        if not images_to_process:
            return

        # If primary image is not already an uploaded file on instance, use first url
        first_url = images_to_process[0]
        if not instance.image and first_url:
            downloaded = download_external_image_to_storage(first_url, filename_prefix=f"master_{instance.id}")
            if downloaded:
                instance.image.save(downloaded.name, downloaded, save=True)
            else:
                instance.image_url = first_url
                instance.save(update_fields=["image_url"])

        # Sync gallery images (indices 1 to 5)
        instance.gallery_images.all().delete()
        for idx, url_str in enumerate(images_to_process[1:], start=1):
            if not url_str or not isinstance(url_str, str):
                continue
            clean_url = url_str.strip()
            downloaded = download_external_image_to_storage(clean_url, filename_prefix=f"master_{instance.id}_g{idx}")
            if downloaded:
                MasterProductImage.objects.create(
                    master_product=instance,
                    image=downloaded,
                    image_url=clean_url,
                    sort_order=idx,
                )
            else:
                MasterProductImage.objects.create(
                    master_product=instance,
                    image_url=clean_url,
                    sort_order=idx,
                )

    def create(self, validated_data):
        images_list = validated_data.pop("images", None)
        validated_data.pop("clear_image", None)
        instance = super().create(validated_data)

        # Auto-download primary image_url if provided and image file was not uploaded
        if not instance.image and instance.image_url:
            downloaded = download_external_image_to_storage(instance.image_url, filename_prefix=f"master_{instance.id}")
            if downloaded:
                instance.image.save(downloaded.name, downloaded, save=True)

        if images_list is not None:
            self._sync_images(instance, images_list)

        return instance

    def update(self, instance, validated_data):
        clear_image = validated_data.pop("clear_image", False)
        images_list = validated_data.pop("images", None)

        if clear_image:
            instance.image = None
            instance.image_url = ""
            instance.gallery_images.all().delete()

        instance = super().update(instance, validated_data)

        # Auto-download primary image_url if updated and image file was not uploaded
        if not clear_image and not instance.image and instance.image_url:
            downloaded = download_external_image_to_storage(instance.image_url, filename_prefix=f"master_{instance.id}")
            if downloaded:
                instance.image.save(downloaded.name, downloaded, save=True)

        if images_list is not None:
            self._sync_images(instance, images_list)

        return instance


class PromoteShopProductSerializer(serializers.Serializer):
    """
    Serializer for Super Admin promoting a Shop Product into Master Catalog.

    Supports optional overrides and category assignment while defaulting
    to the originating Shop Product's metadata.
    """

    shop_product_id = serializers.IntegerField(required=False, min_value=1)
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    brand = serializers.CharField(max_length=255, required=False, allow_blank=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=MasterCategory.objects.all(),
        required=False,
        allow_null=True,
    )
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_name(self, value):
        if value is not None and not value.strip():
            raise serializers.ValidationError("Name cannot be empty or whitespace only.")
        return value.strip() if value else value


class ShopProductSerializer(serializers.ModelSerializer):
    """
    Serializer for Merchant Shop Products.

    Allows Merchants to:
    - Create directly (requiring no Super Admin approval).
    - Select from Master Catalog (reusing master content without automatic synchronization).
    - Enforces tenant isolation for brand_ref and categories.
    """

    effective_brand = serializers.CharField(read_only=True)
    master_product_name = serializers.CharField(source="master_product.name", read_only=True, default=None)
    has_variants = serializers.BooleanField(read_only=True)
    is_uncategorized = serializers.BooleanField(read_only=True)
    name = serializers.CharField(max_length=255, required=False)

    class Meta:
        model = ShopProduct
        fields = [
            "id",
            "shop",
            "master_product",
            "master_product_name",
            "categories",
            "brand_ref",
            "effective_brand",
            "name",
            "description",
            "brand",
            "image",
            "price",
            "sku",
            "unit",
            "attributes",
            "is_visible",
            "is_available",
            "has_variants",
            "is_uncategorized",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "shop",
            "effective_brand",
            "master_product_name",
            "has_variants",
            "is_uncategorized",
            "created_at",
            "updated_at",
        ]

    def to_internal_value(self, data):
        data = shallow_mutable_copy(data)  # .copy() deep-copies uploaded files and fails over 2.5 MB
        if "image" in data and isinstance(data["image"], str):
            if not data["image"] or data["image"].startswith("http") or data["image"].startswith("/"):
                data.pop("image")
        return super().to_internal_value(data)

    def validate(self, attrs):
        shop = self.context.get("shop")
        master_product = attrs.get("master_product")
        name = attrs.get("name")

        # Name requirement logic
        if not self.instance:
            if not master_product and (not name or not name.strip()):
                raise serializers.ValidationError({"name": "Name is required when not selecting from Master Catalog."})

        if name is not None:
            if not name.strip():
                raise serializers.ValidationError({"name": "Name cannot be empty or whitespace only."})
            attrs["name"] = name.strip()

        # Selection from Master Catalog defaults on creation
        if master_product and not self.instance:
            if not attrs.get("name"):
                attrs["name"] = master_product.name
            if "description" not in attrs:
                attrs["description"] = master_product.description
            if "brand" not in attrs:
                attrs["brand"] = master_product.brand
            if "unit" not in attrs and master_product.unit:
                attrs["unit"] = master_product.unit
            if "image" not in attrs and bool(master_product.image):
                attrs["image"] = master_product.image

        # Price validation
        price = attrs.get("price")
        if price is not None and price < Decimal("0.00"):
            raise serializers.ValidationError({"price": "Price cannot be negative."})

        # Tenant isolation checks: brand_ref must belong to merchant's shop
        brand_ref = attrs.get("brand_ref")
        if brand_ref and shop and brand_ref.shop_id != shop.id:
            raise serializers.ValidationError({"brand_ref": "Brand must belong to the same Shop."})

        # Tenant isolation checks: categories must belong to merchant's shop
        categories = attrs.get("categories")
        if categories and shop:
            for cat in categories:
                if cat.shop_id != shop.id:
                    raise serializers.ValidationError({"categories": "All categories must belong to the same Shop."})

        # Attributes validation
        attributes = attrs.get("attributes")
        if attributes is not None:
            if not isinstance(attributes, dict):
                raise serializers.ValidationError({"attributes": "Attributes must be a key-value dictionary."})
            for key, val in attributes.items():
                if not isinstance(key, str) or not key.strip():
                    raise serializers.ValidationError({"attributes": "Attribute names must be non-empty strings."})
                if not isinstance(val, (str, int, float, bool, list)):
                    raise serializers.ValidationError({"attributes": f"Attribute '{key}' value must be a primitive or list of values."})
                if isinstance(val, list):
                    for item in val:
                        if not isinstance(item, (str, int, float, bool)):
                            raise serializers.ValidationError({"attributes": f"Attribute '{key}' list items must be primitive values."})

        return attrs


class PublicProductVariantSerializer(serializers.ModelSerializer):
    """
    Public customer-facing serializer for Product Variants.
    Exposes only approved customer fields, effective images, effective prices,
    inventory availability, and Out of Stock indicators.
    """

    price = serializers.DecimalField(source="effective_price", max_digits=10, decimal_places=2)
    description = serializers.CharField(source="effective_description", read_only=True)
    image = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    stock_quantity = serializers.SerializerMethodField()
    is_out_of_stock = serializers.SerializerMethodField()
    is_orderable = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "name",
            "description",
            "image",
            "price",
            "sku",
            "attributes",
            "is_available",
            "available_quantity",
            "stock_quantity",
            "is_out_of_stock",
            "is_orderable",
            "display_status",
        ]

    def get_image(self, obj):
        effective_img = obj.effective_image
        if bool(effective_img):
            request = self.context.get("request")
            if request is not None:
                return request.build_absolute_uri(effective_img.url)
            return effective_img.url
        return None

    def _get_stock(self, obj):
        stock_map = self.context.get("stock_map")
        if stock_map is not None:
            return stock_map.get((obj.product_id, obj.id), Decimal("0.000"))
        from inventory.models import InventoryItem
        inv = InventoryItem.objects.filter(product_id=obj.product_id, variant_id=obj.id).first()
        return inv.available_quantity if inv else Decimal("0.000")

    def get_available_quantity(self, obj):
        return str(self._get_stock(obj))

    def get_stock_quantity(self, obj):
        return str(self._get_stock(obj))

    def get_is_out_of_stock(self, obj):
        return self._get_stock(obj) <= Decimal("0.000")

    def get_is_orderable(self, obj):
        stock = self._get_stock(obj)
        parent_avail = obj.product.is_available if obj.product_id else True
        return obj.is_customer_visible and obj.is_available and parent_avail and stock > Decimal("0.000")

    def get_display_status(self, obj):
        if not obj.is_customer_visible:
            return "HIDDEN"
        parent_avail = obj.product.is_available if obj.product_id else True
        if not obj.is_available or not parent_avail:
            return "UNAVAILABLE"
        stock = self._get_stock(obj)
        if stock <= Decimal("0.000"):
            return "OUT_OF_STOCK"
        return "AVAILABLE"


class PublicShopCategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopCategory
        fields = ["id", "name", "slug", "parent"]


class PublicShopProductSerializer(serializers.ModelSerializer):
    """
    Public customer-facing serializer for Shop Products.
    Exposes customer-approved fields: name, description, brand, attributes, SKU,
    images, available variants, applicable prices, visibility, and Out of Stock state.
    """

    brand = serializers.CharField(source="effective_brand", read_only=True)
    image = serializers.SerializerMethodField()
    categories = PublicShopCategorySummarySerializer(many=True, read_only=True)
    variants = serializers.SerializerMethodField()
    has_variants = serializers.BooleanField(read_only=True)
    available_quantity = serializers.SerializerMethodField()
    stock_quantity = serializers.SerializerMethodField()
    is_out_of_stock = serializers.SerializerMethodField()
    is_orderable = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()

    class Meta:
        model = ShopProduct
        fields = [
            "id",
            "name",
            "description",
            "brand",
            "image",
            "price",
            "sku",
            "unit",
            "attributes",
            "categories",
            "is_available",
            "has_variants",
            "variants",
            "available_quantity",
            "stock_quantity",
            "is_out_of_stock",
            "is_orderable",
            "display_status",
        ]

    def get_image(self, obj):
        if bool(obj.image):
            request = self.context.get("request")
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def _get_product_stock_info(self, obj):
        stock_map = self.context.get("stock_map")
        visible_variants = [v for v in obj.variants.all() if v.is_visible]

        if visible_variants:
            var_stocks = {}
            for v in visible_variants:
                if stock_map is not None:
                    var_stocks[v.id] = stock_map.get((obj.id, v.id), Decimal("0.000"))
                else:
                    from inventory.models import InventoryItem
                    inv = InventoryItem.objects.filter(product_id=obj.id, variant_id=v.id).first()
                    var_stocks[v.id] = inv.available_quantity if inv else Decimal("0.000")
            total_stock = sum(var_stocks.values(), Decimal("0.000"))
            return total_stock, var_stocks, visible_variants
        else:
            if stock_map is not None:
                stock = stock_map.get((obj.id, None), Decimal("0.000"))
            else:
                from inventory.models import InventoryItem
                inv = InventoryItem.objects.filter(product_id=obj.id, variant__isnull=True).first()
                stock = inv.available_quantity if inv else Decimal("0.000")
            return stock, {}, []

    def get_variants(self, obj):
        visible_variants = [v for v in obj.variants.all() if v.is_visible]
        if not visible_variants:
            return []
        serializer = PublicProductVariantSerializer(visible_variants, many=True, context=self.context)
        return serializer.data

    def get_available_quantity(self, obj):
        stock, _, _ = self._get_product_stock_info(obj)
        return str(stock)

    def get_stock_quantity(self, obj):
        stock, _, _ = self._get_product_stock_info(obj)
        return str(stock)

    def get_is_out_of_stock(self, obj):
        stock, var_stocks, visible_variants = self._get_product_stock_info(obj)
        if visible_variants:
            return all(var_stocks.get(v.id, Decimal("0.000")) <= Decimal("0.000") for v in visible_variants)
        return stock <= Decimal("0.000")

    def get_is_orderable(self, obj):
        if not obj.is_visible or not obj.is_available:
            return False
        stock, var_stocks, visible_variants = self._get_product_stock_info(obj)
        if visible_variants:
            return any(
                v.is_available and var_stocks.get(v.id, Decimal("0.000")) > Decimal("0.000")
                for v in visible_variants
            )
        return stock > Decimal("0.000")

    def get_display_status(self, obj):
        if not obj.is_visible:
            return "HIDDEN"
        if not obj.is_available:
            return "UNAVAILABLE"
        stock, var_stocks, visible_variants = self._get_product_stock_info(obj)
        if visible_variants:
            orderable = any(
                v.is_available and var_stocks.get(v.id, Decimal("0.000")) > Decimal("0.000")
                for v in visible_variants
            )
            if orderable:
                return "AVAILABLE"
            all_manually_unavail = all(not v.is_available for v in visible_variants)
            if all_manually_unavail:
                return "UNAVAILABLE"
            return "OUT_OF_STOCK"
        if stock <= Decimal("0.000"):
            return "OUT_OF_STOCK"
        return "AVAILABLE"


class PublicCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)

    class Meta:
        model = ShopCategory
        fields = ["id", "name", "slug", "description", "parent", "parent_name", "is_subcategory"]


class PublicBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopBrand
        fields = ["id", "name", "slug", "description"]


class PublicCustomAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopCustomAttribute
        fields = ["id", "name", "description", "values"]

