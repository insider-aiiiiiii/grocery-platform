from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from orders.merchant_serializers import MerchantOrderDetailSerializer, MerchantOrderListSerializer
from orders.models import Order
from shops.models import Shop
from shops.permissions import IsActiveMerchant
from users.models import Merchant


class MerchantOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ERP access to orders belonging to the authenticated Merchant's Shop."""

    permission_classes = [IsAuthenticated, IsActiveMerchant]
    lookup_field = "pk"

    def get_queryset(self):
        shop = Shop.objects.filter(
            merchant__user_id=self.request.user.pk,
            merchant__status=Merchant.Status.ACTIVE,
            status=Shop.Status.ACTIVE,
        ).only("id").first()
        if shop is None:
            return Order.objects.none()

        return (
            Order.objects.filter(shop_id=shop.pk)
            .select_related("delivery_address")
            .prefetch_related("items")
            .order_by("-created_at", "-pk")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MerchantOrderDetailSerializer
        return MerchantOrderListSerializer
