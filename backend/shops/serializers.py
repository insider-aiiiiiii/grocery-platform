from rest_framework import serializers

from .models import Shop


class ShopSerializer(serializers.ModelSerializer):
    """Serializer representing full Shop profile details."""

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

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        merchant = user.merchant

        # Explicitly bind merchant, mirror contact number, and set status to ACTIVE
        validated_data["merchant"] = merchant
        validated_data["contact_number"] = user.mobile_number
        validated_data["status"] = Shop.Status.ACTIVE

        return super().create(validated_data)
