from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.serializers import (
    AnalyticsDateRangeQuerySerializer,
    LowStockItemSerializer,
    MerchantAnalyticsOverviewSerializer,
    PlatformAnalyticsOverviewSerializer,
    PlatformAnalyticsQuerySerializer,
    PlatformTopShopItemSerializer,
    TopProductItemSerializer,
)
from analytics.services import (
    get_merchant_analytics_overview,
    get_merchant_low_stock_items,
    get_merchant_top_products,
    get_platform_analytics_overview,
    get_platform_top_products,
    get_platform_top_shops,
    parse_date_range,
)
from shops.models import Shop
from shops.permissions import IsActiveMerchant
from users.models import Merchant
from users.permissions import IsSuperAdmin


class BaseMerchantAnalyticsView(APIView):
    """Base class enforcing authentication, active merchant permission, and shop resolution."""

    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def get_merchant_shop(self, request) -> Shop:
        """Resolves the active Shop belonging strictly to the authenticated Merchant."""
        shop = Shop.objects.filter(
            merchant__user_id=request.user.pk,
            merchant__status=Merchant.Status.ACTIVE,
            status=Shop.Status.ACTIVE,
        ).first()
        return shop


class MerchantAnalyticsOverviewView(BaseMerchantAnalyticsView):
    """
    GET /api/v1/analytics/
    GET /api/v1/shops/me/analytics/

    Provides real-time, on-demand operational analytics overview for the authenticated Merchant's Shop.
    Supports time periods: today (default), yesterday, this_week, this_month, and custom.
    """

    def get(self, request):
        shop = self.get_merchant_shop(request)
        if not shop:
            return Response(
                {"detail": "Merchant does not have an active shop.", "code": "SHOP_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        query_serializer = AnalyticsDateRangeQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        overview_data = get_merchant_analytics_overview(shop.id, query_serializer.validated_data)
        serializer = MerchantAnalyticsOverviewSerializer(overview_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MerchantAnalyticsTopProductsView(BaseMerchantAnalyticsView):
    """
    GET /api/v1/analytics/top-products/
    GET /api/v1/shops/me/analytics/top-products/

    Provides ranked top-selling products for the authenticated Merchant's Shop in the specified period.
    """

    def get(self, request):
        shop = self.get_merchant_shop(request)
        if not shop:
            return Response(
                {"detail": "Merchant does not have an active shop.", "code": "SHOP_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        query_serializer = AnalyticsDateRangeQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data

        period, start_dt, end_dt = parse_date_range(validated)
        limit = validated.get("limit", 10)

        top_products = get_merchant_top_products(shop.id, start_dt, end_dt, limit=limit)
        serializer = TopProductItemSerializer(top_products, many=True)
        return Response(
            {
                "period": period,
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "top_products": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class MerchantAnalyticsLowStockView(BaseMerchantAnalyticsView):
    """
    GET /api/v1/analytics/low-stock/
    GET /api/v1/shops/me/analytics/low-stock/

    Provides list of items currently Out of Stock (available_quantity <= 0.000) for the Merchant's Shop.
    """

    def get(self, request):
        shop = self.get_merchant_shop(request)
        if not shop:
            return Response(
                {"detail": "Merchant does not have an active shop.", "code": "SHOP_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        items = get_merchant_low_stock_items(shop.id)
        serializer = LowStockItemSerializer(items, many=True)
        return Response(
            {
                "out_of_stock_items_count": len(items),
                "items": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class BasePlatformAnalyticsView(APIView):
    """Base class enforcing authentication and Super Admin authorization."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not getattr(request.user, "is_active", True):
            self.permission_denied(request, message="Super Admin account is inactive.")

    def validate_shop_filter(self, shop_id: int | None):
        """Validates that if shop_id is provided, the shop exists."""
        if shop_id is not None and not Shop.objects.filter(id=shop_id).exists():
            return Response(
                {"detail": f"Shop with id {shop_id} does not exist.", "code": "SHOP_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return None


class PlatformAnalyticsOverviewView(BasePlatformAnalyticsView):
    """
    GET /api/v1/analytics/platform/
    GET /api/v1/analytics/platform/overview/

    Provides operational analytics overview aggregated across the platform for Super Admins.
    Supports optional shop_id filter to scope metrics to a single shop.
    """

    def get(self, request):
        query_serializer = PlatformAnalyticsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data

        shop_error = self.validate_shop_filter(validated.get("shop_id"))
        if shop_error:
            return shop_error

        overview_data = get_platform_analytics_overview(validated)
        serializer = PlatformAnalyticsOverviewSerializer(overview_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PlatformAnalyticsTopProductsView(BasePlatformAnalyticsView):
    """
    GET /api/v1/analytics/platform/top-products/

    Provides ranked top-selling products across all shops on completed orders.
    Supports optional shop_id filter.
    """

    def get(self, request):
        query_serializer = PlatformAnalyticsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data

        shop_id = validated.get("shop_id")
        shop_error = self.validate_shop_filter(shop_id)
        if shop_error:
            return shop_error

        period, start_dt, end_dt = parse_date_range(validated)
        limit = validated.get("limit", 10)

        top_products = get_platform_top_products(start_dt, end_dt, shop_id=shop_id, limit=limit)
        serializer = TopProductItemSerializer(top_products, many=True)
        response_payload = {
            "period": period,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "top_products": serializer.data,
        }
        if shop_id is not None:
            response_payload["filtered_shop_id"] = shop_id

        return Response(response_payload, status=status.HTTP_200_OK)


class PlatformAnalyticsTopShopsView(BasePlatformAnalyticsView):
    """
    GET /api/v1/analytics/platform/top-shops/

    Provides ranked performing shops across the platform by realized sales on completed orders.
    """

    def get(self, request):
        query_serializer = PlatformAnalyticsQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        validated = query_serializer.validated_data

        period, start_dt, end_dt = parse_date_range(validated)
        limit = validated.get("limit", 10)

        top_shops = get_platform_top_shops(start_dt, end_dt, limit=limit)
        serializer = PlatformTopShopItemSerializer(top_shops, many=True)
        return Response(
            {
                "period": period,
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "top_shops": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

