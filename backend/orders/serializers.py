from rest_framework import serializers

from orders.models import Order


class DeliveryAddressInputSerializer(serializers.Serializer):
    recipient_name = serializers.CharField(max_length=255, required=False, allow_blank=False)
    recipient_phone = serializers.CharField(max_length=16, required=False, allow_blank=False)
    address_line = serializers.CharField(max_length=255)
    area = serializers.CharField(max_length=128)
    city = serializers.CharField(max_length=128)
    state = serializers.CharField(max_length=128)
    pincode = serializers.CharField(max_length=16)
    landmark = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    delivery_notes = serializers.CharField(required=False, allow_blank=True, default="")


class CheckoutSerializer(serializers.Serializer):
    cart_id = serializers.IntegerField(min_value=1)
    customer_name = serializers.CharField(max_length=255, allow_blank=False, trim_whitespace=True)
    whatsapp_number = serializers.CharField(max_length=32, allow_blank=False, trim_whitespace=True)
    fulfillment_type = serializers.ChoiceField(choices=Order.FulfillmentType.choices)
    delivery_address = DeliveryAddressInputSerializer(required=False)

    def to_internal_value(self, data):
        allowed = set(self.fields)
        unknown = set(data) - allowed if hasattr(data, "keys") else set()
        if unknown:
            raise serializers.ValidationError({key: "Unknown or unsupported checkout field." for key in unknown})
        return super().to_internal_value(data)

    def validate(self, attrs):
        is_delivery = attrs["fulfillment_type"] == Order.FulfillmentType.HOME_DELIVERY
        if is_delivery and "delivery_address" not in attrs:
            raise serializers.ValidationError({"delivery_address": "This field is required for home delivery."})
        if not is_delivery and "delivery_address" in attrs:
            raise serializers.ValidationError({"delivery_address": "Pickup orders must not include a delivery address."})
        return attrs
