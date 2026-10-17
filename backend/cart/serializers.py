from decimal import Decimal

from rest_framework import serializers

from catalog.models import ProductVariant, ShopProduct
from customers.models import Customer, normalize_whatsapp_number
from shops.models import Shop

from .models import Cart, CartItem, validate_positive_quantity


class CartItemProductSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopProduct
        fields = ["id", "name", "price", "sku", "is_available", "is_visible"]


class CartItemVariantSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "name", "price", "sku", "is_available", "is_visible"]


class PublicCartItemSerializer(serializers.ModelSerializer):
    product = CartItemProductSummarySerializer(read_only=True)
    variant = CartItemVariantSummarySerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "variant",
            "quantity",
            "unit_price",
            "line_total",
            "created_at",
            "updated_at",
        ]


class PublicCartCustomerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "whatsapp_number"]


class PublicCartShopSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["id", "name", "public_slug", "delivery_charge", "delivery_fee_type"]


class PublicCartSerializer(serializers.ModelSerializer):
    shop = PublicCartShopSummarySerializer(read_only=True)
    customer = PublicCartCustomerSummarySerializer(read_only=True)
    items = PublicCartItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    total_quantity = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "shop",
            "customer",
            "items",
            "item_count",
            "total_quantity",
            "subtotal",
            "created_at",
            "updated_at",
        ]


class CartItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    variant_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        required=False,
        default=Decimal("1.000"),
    )

    def validate_quantity(self, value):
        return validate_positive_quantity(value)


class CartCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    whatsapp_number = serializers.CharField(required=False, allow_blank=True, default="")
    items = CartItemInputSerializer(many=True, required=False, default=list)

    def validate(self, attrs):
        shop = self.context.get("shop")
        if not shop:
            raise serializers.ValidationError({"shop": "Shop context is required."})

        # Validate customer if customer_id provided
        customer_id = attrs.get("customer_id")
        if customer_id is not None:
            customer = Customer.objects.filter(id=customer_id).first()
            if not customer:
                raise serializers.ValidationError({"customer_id": "Customer not found."})
            if customer.shop_id != shop.id:
                raise serializers.ValidationError({"customer_id": "Customer must belong to the addressed Shop."})
            attrs["resolved_customer"] = customer
        elif attrs.get("whatsapp_number"):
            try:
                wa = normalize_whatsapp_number(attrs["whatsapp_number"])
                customer, _ = Customer.objects.get_or_create(
                    shop=shop,
                    whatsapp_number=wa,
                )
                attrs["resolved_customer"] = customer
            except Exception as e:
                raise serializers.ValidationError({"whatsapp_number": str(e)})
        else:
            attrs["resolved_customer"] = None

        # Validate items
        items_data = attrs.get("items", [])
        validated_items = []
        for idx, item in enumerate(items_data):
            p_id = item["product_id"]
            product = ShopProduct.objects.filter(id=p_id).first()
            if not product:
                raise serializers.ValidationError({f"items[{idx}].product_id": f"Product #{p_id} not found."})
            if product.shop_id != shop.id:
                raise serializers.ValidationError(
                    {f"items[{idx}].product_id": f"Product #{p_id} does not belong to this Shop."}
                )

            v_id = item.get("variant_id")
            variant = None
            if v_id is not None:
                variant = ProductVariant.objects.filter(id=v_id).first()
                if not variant:
                    raise serializers.ValidationError({f"items[{idx}].variant_id": f"Variant #{v_id} not found."})
                if variant.product_id != product.id:
                    raise serializers.ValidationError(
                        {f"items[{idx}].variant_id": f"Variant #{v_id} does not belong to Product #{p_id}."}
                    )
                if variant.product.shop_id != shop.id:
                    raise serializers.ValidationError(
                        {f"items[{idx}].variant_id": f"Variant #{v_id} does not belong to this Shop."}
                    )

            validated_items.append({
                "product": product,
                "variant": variant,
                "quantity": item.get("quantity", Decimal("1.000")),
            })

        attrs["validated_items"] = validated_items
        return attrs

    def create(self, validated_data):
        shop = self.context["shop"]
        customer = validated_data.get("resolved_customer")
        cart = Cart.objects.create(shop=shop, customer=customer)

        for item_info in validated_data.get("validated_items", []):
            CartItem.objects.create(
                cart=cart,
                product=item_info["product"],
                variant=item_info["variant"],
                quantity=item_info["quantity"],
            )

        return cart
