from decimal import Decimal

from rest_framework import serializers

from .models import MasterCategory, MasterProduct, ShopBrand, ShopCategory, ShopProduct


class MasterProductSerializer(serializers.ModelSerializer):
    """
    Serializer for platform-level Master Catalog products managed by Super Admin.

    Master Products serve as reusable templates for independent Shop Catalogs.
    They do not belong to any specific Shop and remain strictly independent
    of Shop Products.
    """

    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

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
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category_name",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty or whitespace only.")
        return value.strip()


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
