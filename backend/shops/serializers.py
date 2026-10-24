from decimal import Decimal

from rest_framework import serializers

from .models import Shop


class ShopSerializer(serializers.ModelSerializer):
    """Serializer representing full Shop profile details."""

    public_url = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "description",
            "logo",
            "address_line",
            "area",
            "city",
            "state",
            "pincode",
            "contact_number",
            "status",
            "is_temporarily_closed",
            "opening_time",
            "closing_time",
            "is_home_delivery_enabled",
            "is_pickup_enabled",
            "delivery_fee_type",
            "delivery_charge",
            "pending_order_timeout_minutes",
            "public_slug",
            "public_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "contact_number",
            "status",
            "public_slug",
            "public_url",
            "created_at",
            "updated_at",
        ]

    def get_public_url(self, obj) -> str:
        request = self.context.get("request")
        path = f"/api/v1/shops/public/{obj.public_slug}/"
        if request is not None:
            return request.build_absolute_uri(path)
        return path


class PublicShopSerializer(serializers.ModelSerializer):
    """Serializer exposing only customer-facing Shop details for public QR / link access."""

    public_url = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = [
            "public_slug",
            "public_url",
            "name",
            "description",
            "logo",
            "address_line",
            "area",
            "city",
            "state",
            "pincode",
            "contact_number",
            "is_temporarily_closed",
            "opening_time",
            "closing_time",
            "is_home_delivery_enabled",
            "is_pickup_enabled",
            "delivery_fee_type",
            "delivery_charge",
        ]
        read_only_fields = fields

    def get_public_url(self, obj) -> str:
        request = self.context.get("request")
        path = f"/api/v1/shops/public/{obj.public_slug}/"
        if request is not None:
            return request.build_absolute_uri(path)
        return path


class ShopCreateSerializer(serializers.ModelSerializer):
    """Serializer used for initial Shop profile creation by an authenticated Merchant."""

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "description",
            "logo",
            "address_line",
            "area",
            "city",
            "state",
            "pincode",
            "contact_number",
            "status",
            "is_temporarily_closed",
            "opening_time",
            "closing_time",
            "is_home_delivery_enabled",
            "is_pickup_enabled",
            "delivery_fee_type",
            "delivery_charge",
            "pending_order_timeout_minutes",
            "public_slug",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "contact_number",
            "status",
            "public_slug",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "address_line": {"required": True, "allow_blank": False},
            "area": {"required": True, "allow_blank": False},
            "city": {"required": True, "allow_blank": False},
            "state": {"required": True, "allow_blank": False},
            "pincode": {"required": True, "allow_blank": False},
        }

    def validate_delivery_charge(self, value):
        if value < 0:
            raise serializers.ValidationError("Delivery charge cannot be negative.")
        return value

    def validate_pending_order_timeout_minutes(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Pending order timeout must be greater than zero minutes.")
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        merchant = user.merchant

        # Explicitly bind merchant, mirror contact number, and set status to ACTIVE
        validated_data["merchant"] = merchant
        validated_data["contact_number"] = user.mobile_number
        validated_data["status"] = Shop.Status.ACTIVE

        return super().create(validated_data)


class ShopUpdateSerializer(serializers.ModelSerializer):
    """Serializer used for Shop profile updates by the authenticated Merchant."""

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "description",
            "logo",
            "address_line",
            "area",
            "city",
            "state",
            "pincode",
            "contact_number",
            "status",
            "is_temporarily_closed",
            "opening_time",
            "closing_time",
            "is_home_delivery_enabled",
            "is_pickup_enabled",
            "delivery_fee_type",
            "delivery_charge",
            "pending_order_timeout_minutes",
            "public_slug",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "contact_number",
            "status",
            "public_slug",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "name": {"required": False, "allow_blank": False},
            "address_line": {"required": False, "allow_blank": False},
            "area": {"required": False, "allow_blank": False},
            "city": {"required": False, "allow_blank": False},
            "state": {"required": False, "allow_blank": False},
            "pincode": {"required": False, "allow_blank": False},
        }

    def validate_delivery_charge(self, value):
        if value < 0:
            raise serializers.ValidationError("Delivery charge cannot be negative.")
        return value

    def validate_pending_order_timeout_minutes(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Pending order timeout must be greater than zero minutes.")
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        # 1. Fulfillment validation: At least one option must be enabled
        is_home_delivery = attrs.get(
            "is_home_delivery_enabled",
            instance.is_home_delivery_enabled if instance else True,
        )
        is_pickup = attrs.get(
            "is_pickup_enabled",
            instance.is_pickup_enabled if instance else True,
        )
        if not is_home_delivery and not is_pickup:
            raise serializers.ValidationError(
                {"fulfillment": "At least one fulfillment option (home delivery or pickup) must be enabled."}
            )

        # 2. Delivery fee normalization: If CONFIRMED_ON_WHATSAPP, charge is 0.00
        fee_type = attrs.get(
            "delivery_fee_type",
            instance.delivery_fee_type if instance else Shop.DeliveryFeeType.FIXED,
        )
        if fee_type == Shop.DeliveryFeeType.CONFIRMED_ON_WHATSAPP:
            attrs["delivery_charge"] = Decimal("0.00")

        # 3. Business hours validation
        opening_time = attrs.get(
            "opening_time",
            instance.opening_time if instance else None,
        )
        closing_time = attrs.get(
            "closing_time",
            instance.closing_time if instance else None,
        )
        if (opening_time is not None and closing_time is None) or (closing_time is not None and opening_time is None):
            raise serializers.ValidationError(
                {"business_hours": "Both opening time and closing time must be provided together."}
            )
        if opening_time is not None and closing_time is not None and opening_time == closing_time:
            raise serializers.ValidationError(
                {"business_hours": "Opening time and closing time cannot be the same."}
            )

        return attrs


class SuperAdminShopDirectorySerializer(serializers.ModelSerializer):
    """Serializer for Super Admin platform shop directory."""

    owner__username = serializers.CharField(source="merchant.user.username", read_only=True)
    owner__mobile_number = serializers.CharField(source="merchant.user.mobile_number", read_only=True)
    owner_username = serializers.CharField(source="merchant.user.username", read_only=True)
    owner_mobile_number = serializers.CharField(source="merchant.user.mobile_number", read_only=True)
    catalog_items_count = serializers.SerializerMethodField()
    monthly_volume = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "public_slug",
            "status",
            "city",
            "owner__username",
            "owner__mobile_number",
            "owner_username",
            "owner_mobile_number",
            "catalog_items_count",
            "monthly_volume",
            "created_at",
        ]

    def get_catalog_items_count(self, obj) -> int:
        if hasattr(obj, "products"):
            return obj.products.count()
        return 0

    def get_monthly_volume(self, obj) -> str:
        return "₹0"

