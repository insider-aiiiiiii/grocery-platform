from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.serializers import (
    AnalyticsDateRangeQuerySerializer,
    LowStockItemSerializer,
    MerchantAnalyticsOverviewSerializer,
    TopProductItemSerializer,
)
from analytics.services import (
    get_merchant_analytics_overview,
    get_merchant_low_stock_items,
    get_merchant_top_products,
    parse_date_range,
)
from shops.models import Shop
from shops.permissions import IsActiveMerchant
from users.models import Merchant


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
