from rest_framework import serializers

from .models import MasterCategory, MasterProduct


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

