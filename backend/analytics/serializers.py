from rest_framework import serializers


class AnalyticsDateRangeQuerySerializer(serializers.Serializer):
    """Validates incoming query parameters for analytics date ranges."""

    PERIOD_CHOICES = ["today", "yesterday", "this_week", "this_month", "custom"]

    period = serializers.ChoiceField(
        choices=PERIOD_CHOICES,
        default="today",
        required=False,
    )
    start_date = serializers.DateField(
        required=False,
        allow_null=True,
    )
    end_date = serializers.DateField(
        required=False,
        allow_null=True,
    )
    limit = serializers.IntegerField(
        min_value=1,
        max_value=50,
        default=10,
        required=False,
    )

    def validate(self, attrs):
        period = attrs.get("period", "today")
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")

        if period == "custom":
            if not start_date or not end_date:
                raise serializers.ValidationError(
                    "Both 'start_date' and 'end_date' are required when period='custom'."
                )
            if start_date > end_date:
                raise serializers.ValidationError(
                    "'start_date' cannot be after 'end_date'."
                )

        return attrs


class TopProductItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(allow_null=True)
    variant_id = serializers.IntegerField(allow_null=True)
    product_name = serializers.CharField()
    variant_name = serializers.CharField(allow_blank=True)
    sku = serializers.CharField(allow_blank=True)
    units_sold = serializers.CharField()
    total_revenue = serializers.CharField()


class LowStockItemSerializer(serializers.Serializer):
    inventory_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    sku = serializers.CharField()
    quantity = serializers.CharField()
    reserved_quantity = serializers.CharField()
    available_quantity = serializers.CharField()
    is_out_of_stock = serializers.BooleanField(default=True)


class OrderStatusDistributionSerializer(serializers.Serializer):
    PENDING = serializers.IntegerField()
    ACCEPTED = serializers.IntegerField()
    PREPARING = serializers.IntegerField()
    READY = serializers.IntegerField()
    COMPLETED = serializers.IntegerField()
    REJECTED = serializers.IntegerField()


class OrdersMetricSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    rejected_orders = serializers.IntegerField()
    status_distribution = OrderStatusDistributionSerializer()


class SalesMetricSerializer(serializers.Serializer):
    realized_sales = serializers.CharField()
    average_order_value = serializers.CharField()


class CustomersMetricSerializer(serializers.Serializer):
    ordering_customers = serializers.IntegerField()
    returning_customers = serializers.IntegerField()


class InventoryMetricSerializer(serializers.Serializer):
    out_of_stock_items_count = serializers.IntegerField()


class MerchantAnalyticsOverviewSerializer(serializers.Serializer):
    period = serializers.CharField()
    start_time = serializers.CharField()
    end_time = serializers.CharField()
    orders = OrdersMetricSerializer()
    sales = SalesMetricSerializer()
    customers = CustomersMetricSerializer()
    inventory = InventoryMetricSerializer()
    top_products = TopProductItemSerializer(many=True)
