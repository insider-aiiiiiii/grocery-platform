from decimal import Decimal

from rest_framework import serializers

from orders.models import Order, OrderDeliveryAddress, OrderItem


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields) if hasattr(data, "keys") else set()
        if unknown:
            raise serializers.ValidationError({key: "Unknown field." for key in unknown})
        return super().to_internal_value(data)


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
    delivery_address = MerchantOrderDeliveryAddressSerializer(read_only=True, allow_null=True)
    whatsapp_action_link = serializers.SerializerMethodField()

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
            "delivery_address",
            "whatsapp_action_link",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_whatsapp_action_link(self, order):
        from notifications.links import get_merchant_order_action_link
        event_map = {
            Order.Status.PENDING: "ORDER_ACCEPTED",
            Order.Status.ACCEPTED: "ORDER_ACCEPTED",
            Order.Status.PREPARING: "ORDER_PREPARING",
            Order.Status.READY: "ORDER_READY",
            Order.Status.COMPLETED: "ORDER_COMPLETED",
            Order.Status.REJECTED: "ORDER_REJECTED",
        }
        event = event_map.get(order.status, "ORDER_ACCEPTED")
        try:
            return get_merchant_order_action_link(order, event, language="hinglish")
        except Exception:
            return None


class MerchantOrderDetailSerializer(MerchantOrderListSerializer):
    class Meta(MerchantOrderListSerializer.Meta):
        fields = MerchantOrderListSerializer.Meta.fields + [
            "delivery_fee_type_snapshot",
            "accepted_at",
            "rejected_at",
            "completed_at",
            "rejection_actor",
            "rejection_reason_code",
            "rejection_note",
        ]
        read_only_fields = fields


class MerchantOrderItemAdjustmentSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(min_value=1)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.000"))


class MerchantOrderAcceptSerializer(StrictSerializer):
    items = MerchantOrderItemAdjustmentSerializer(many=True, required=False, default=list)

    def validate_items(self, value):
        item_ids = [entry["item_id"] for entry in value]
        if len(item_ids) != len(set(item_ids)):
            raise serializers.ValidationError("Each Order Item may appear only once.")
        return value


class MerchantOrderRejectSerializer(StrictSerializer):
    rejection_note = serializers.CharField(required=False, allow_blank=True, default="")


class MerchantOrderPaymentSerializer(StrictSerializer):
    payment_status = serializers.ChoiceField(choices=Order.PaymentStatus.choices)


class MerchantOrderEmptyActionSerializer(StrictSerializer):
    pass
