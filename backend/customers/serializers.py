from rest_framework import serializers

from .models import Customer, normalize_whatsapp_number


class PublicCustomerInputSerializer(serializers.Serializer):
    """
    Serializer for public customer profile creation or recognition.
    Strictly validates customer contact input without exposing any internal auth or merchant credentials.
    """

    whatsapp_number = serializers.CharField(
        required=True,
        max_length=32,
        help_text="10-digit Indian mobile number or E.164 (+91XXXXXXXXXX) format.",
    )
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=255,
        help_text="Optional customer name for this Shop.",
    )
    cart_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Optional ID of an active Cart belonging to this Shop to bind to the Customer profile.",
    )

    def validate_whatsapp_number(self, value: str) -> str:
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            return normalize_whatsapp_number(value)
        except DjangoValidationError as err:
            raise serializers.ValidationError(err.messages if hasattr(err, "messages") else str(err))


class PublicCustomerProfileSerializer(serializers.ModelSerializer):
    """
    Public-safe serializer for Shop-specific Customer profile data.
    Never exposes merchant identity, passwords, staff status, or cross-shop information.
    """

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "whatsapp_number",
            "created_at",
        ]
        read_only_fields = fields


class MerchantCustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for Merchant ERP retrieval of Shop-specific Customer profiles.

    Exposes customer profile fields scoped strictly to the merchant's Shop:
    - id
    - shop (ID of the Shop tenant)
    - name (customer name for this Shop)
    - whatsapp_number (normalized E.164 contact identifier)
    - created_at
    - updated_at

    A global contact identity does not make another Shop profile or history accessible.
    Never exposes internal authentication credentials, passwords, or cross-tenant data.
    """

    class Meta:
        model = Customer
        fields = [
            "id",
            "shop",
            "name",
            "whatsapp_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

