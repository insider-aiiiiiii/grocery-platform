from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import F, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from catalog.models import ProductVariant, ShopProduct
from catalog.views import get_authenticated_merchant_shop
from shops.permissions import IsActiveMerchant

from .models import InventoryItem
from .serializers import (
    MerchantInventoryItemSerializer,
    MerchantStockUpdateSerializer,
    ProductInventoryDetailSerializer,
)
from .services import (
    add_stock,
    adjust_stock,
    get_product_stock,
    get_variant_stock,
    set_stock,
    subtract_stock,
)


class MerchantInventoryViewSet(viewsets.ModelViewSet):
    """
    Standardized DRF ViewSet for Merchant Inventory retrieval and updates.

    - Scope: Strictly isolated to the authenticated Merchant's Shop.
    - Visibility: Returns current quantity, reserved quantity, available quantity,
      and out-of-stock indicators. No thresholds, alerts, or movement ledgers.
    - Updates: Supports exact stock updates, additions, and subtractions.
      Validates non-negative resulting stock, reserved-stock invariants, and variant granularity.
    """

    serializer_class = MerchantInventoryItemSerializer
    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        shop, error_res = get_authenticated_merchant_shop(request)
        self._shop = shop
        self._shop_error = error_res

    def get_queryset(self):
        if getattr(self, "_shop_error", None):
            return InventoryItem.objects.none()
        shop = getattr(self, "_shop", None)
        if not shop:
            return InventoryItem.objects.none()

        qs = (
            InventoryItem.objects.filter(shop=shop)
            .select_related("product", "variant")
            .order_by("product__name", "variant__name", "id")
        )

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(product__name__icontains=search)
                | Q(variant__name__icontains=search)
                | Q(product__sku__icontains=search)
                | Q(variant__sku__icontains=search)
            )

        is_out_of_stock = self.request.query_params.get("is_out_of_stock")
        if is_out_of_stock is not None:
            if is_out_of_stock.lower() in ("true", "1"):
                qs = qs.filter(quantity__lte=F("reserved_quantity"))
            elif is_out_of_stock.lower() in ("false", "0"):
                qs = qs.filter(quantity__gt=F("reserved_quantity"))

        product_id = self.request.query_params.get("product_id") or self.request.query_params.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)

        return qs

    def list(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Direct creation of inventory records is prohibited; stock initializes with Catalog products."""
        return Response(
            {"detail": "Direct creation of inventory records is not permitted. Stock initializes with Catalog products and variants."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """Direct deletion of inventory records is prohibited; inventory lifecycle follows Catalog items."""
        return Response(
            {"detail": "Direct deletion of inventory records is not permitted. Stock lifecycle follows Catalog products and variants."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _apply_stock_update(self, target, action_type: str, qty: Decimal, request):
        """Dispatches stock modification to domain services and translates Django ValidationErrors."""
        try:
            if action_type == MerchantStockUpdateSerializer.ACTION_ADD:
                return add_stock(self._shop, target, qty, actor=request.user)
            elif action_type == MerchantStockUpdateSerializer.ACTION_SUBTRACT:
                return subtract_stock(self._shop, target, qty, actor=request.user)
            else:
                return set_stock(self._shop, target, qty, actor=request.user)
        except DjangoValidationError as e:
            msg = e.messages[0] if hasattr(e, "messages") and e.messages else str(e)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        item = self.get_object()
        target = item.variant if item.variant else item.product

        serializer = MerchantStockUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_type = serializer.validated_data["effective_action"]
        qty = serializer.validated_data["effective_quantity"]

        result = self._apply_stock_update(target, action_type, qty, request)
        if isinstance(result, Response):
            return result

        item.refresh_from_db()
        return Response(MerchantInventoryItemSerializer(item).data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="set-stock")
    def set_stock_action(self, request, pk=None):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        item = self.get_object()
        target = item.variant if item.variant else item.product

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["action"] = MerchantStockUpdateSerializer.ACTION_SET
        serializer = MerchantStockUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        qty = serializer.validated_data["effective_quantity"]
        result = self._apply_stock_update(target, MerchantStockUpdateSerializer.ACTION_SET, qty, request)
        if isinstance(result, Response):
            return result

        item.refresh_from_db()
        return Response(MerchantInventoryItemSerializer(item).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="add-stock")
    def add_stock_action(self, request, pk=None):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        item = self.get_object()
        target = item.variant if item.variant else item.product

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["action"] = MerchantStockUpdateSerializer.ACTION_ADD
        serializer = MerchantStockUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        qty = serializer.validated_data["effective_quantity"]
        result = self._apply_stock_update(target, MerchantStockUpdateSerializer.ACTION_ADD, qty, request)
        if isinstance(result, Response):
            return result

        item.refresh_from_db()
        return Response(MerchantInventoryItemSerializer(item).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="subtract-stock")
    def subtract_stock_action(self, request, pk=None):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        item = self.get_object()
        target = item.variant if item.variant else item.product

        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        data["action"] = MerchantStockUpdateSerializer.ACTION_SUBTRACT
        serializer = MerchantStockUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        qty = serializer.validated_data["effective_quantity"]
        result = self._apply_stock_update(target, MerchantStockUpdateSerializer.ACTION_SUBTRACT, qty, request)
        if isinstance(result, Response):
            return result

        item.refresh_from_db()
        return Response(MerchantInventoryItemSerializer(item).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get", "post"], url_path="products/(?P<product_id>[^/.]+)")
    def product_stock(self, request, product_id=None):
        if getattr(self, "_shop_error", None):
            return self._shop_error

        product = ShopProduct.objects.filter(shop=self._shop, id=product_id).first()
        if not product:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "GET":
            stock_data = get_product_stock(product)
            stock_data["product_name"] = product.name
            if product.has_variants:
                variants_list = []
                for var in product.variants.all().order_by("name", "id"):
                    var_stock = get_variant_stock(var)
                    var_stock["variant_name"] = var.name
                    var_stock["sku"] = var.sku
                    variants_list.append(var_stock)
                stock_data["variants"] = variants_list
            serializer = ProductInventoryDetailSerializer(stock_data)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # POST: update non-variant product stock
        if product.has_variants:
            return Response(
                {"detail": "Independent manual changes to aggregate Product stock for a variant-based product are superseded and not permitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MerchantStockUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_type = serializer.validated_data["effective_action"]
        qty = serializer.validated_data["effective_quantity"]

        result = self._apply_stock_update(product, action_type, qty, request)
        if isinstance(result, Response):
            return result

        stock_data = get_product_stock(product)
        stock_data["product_name"] = product.name
        return Response(ProductInventoryDetailSerializer(stock_data).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get", "post"], url_path="variants/(?P<variant_id>[^/.]+)")
    def variant_stock(self, request, variant_id=None):
        if getattr(self, "_shop_error", None):
            return self._shop_error

        variant = ProductVariant.objects.filter(product__shop=self._shop, id=variant_id).first()
        if not variant:
            return Response({"detail": "Variant not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.method == "GET":
            stock_data = get_variant_stock(variant)
            stock_data["variant_name"] = variant.name
            stock_data["sku"] = variant.sku
            return Response(stock_data, status=status.HTTP_200_OK)

        serializer = MerchantStockUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_type = serializer.validated_data["effective_action"]
        qty = serializer.validated_data["effective_quantity"]

        result = self._apply_stock_update(variant, action_type, qty, request)
        if isinstance(result, Response):
            return result

        stock_data = get_variant_stock(variant)
        stock_data["variant_name"] = variant.name
        stock_data["sku"] = variant.sku
        return Response(stock_data, status=status.HTTP_200_OK)
