from rest_framework import serializers

from orders.models import Order, OrderDeliveryAddress, OrderItem


class MerchantOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_name_snapshot",
            "variant_name_snapshot",
            "sku_snapshot",
            "unit_snapshot",
            "attributes_snapshot",
            "ordered_quantity",
            "quantity",
            "unit_price_snapshot",
            "line_total",
        ]
        read_only_fields = fields


class MerchantOrderDeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDeliveryAddress
        fields = [
            "recipient_name",
            "recipient_phone",
            "address_line",
            "area",
            "city",
            "state",
            "pincode",
            "landmark",
            "delivery_notes",
        ]
        read_only_fields = fields


class MerchantOrderListSerializer(serializers.ModelSerializer):
    items = MerchantOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "payment_status",
            "fulfillment_type",
            "customer_name_snapshot",
            "customer_phone_snapshot",
            "items",
            "items_subtotal",
            "delivery_charge_snapshot",
            "total_amount",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MerchantOrderDetailSerializer(MerchantOrderListSerializer):
    delivery_address = MerchantOrderDeliveryAddressSerializer(read_only=True, allow_null=True)

    class Meta(MerchantOrderListSerializer.Meta):
        fields = MerchantOrderListSerializer.Meta.fields + [
            "delivery_fee_type_snapshot",
            "delivery_address",
            "accepted_at",
            "rejected_at",
            "completed_at",
            "rejection_actor",
            "rejection_reason_code",
            "rejection_note",
        ]
        read_only_fields = fields
