from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.links import get_merchant_order_action_link
from orders.merchant_serializers import (
    MerchantOrderAcceptSerializer,
    MerchantOrderDetailSerializer,
    MerchantOrderEmptyActionSerializer,
    MerchantOrderListSerializer,
    MerchantOrderPaymentSerializer,
    MerchantOrderRejectSerializer,
)
from orders.models import Order
from orders.transitions import (
    expire_pending_order_if_due,
    set_order_payment_status,
    transition_order,
)
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

    def _expire_due_orders(self):
        due_orders = list(self.get_queryset().filter(
            status=Order.Status.PENDING,
            expires_at__lte=timezone.now(),
        ).values_list("shop_id", "pk"))
        for shop_id, order_id in due_orders:
            expire_pending_order_if_due(shop_id, order_id)

    def list(self, request, *args, **kwargs):
        self._expire_due_orders()
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        self._expire_due_orders()
        return super().retrieve(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MerchantOrderDetailSerializer
        return MerchantOrderListSerializer

    def _transition_response(self, request, pk, action_name, input_serializer=None):
        order = self.get_object()
        payload = {}
        if input_serializer:
            serializer = input_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            payload = serializer.validated_data
        order, expired = transition_order(order.shop_id, order.pk, action_name, payload, actor=request.user)
        if expired:
            return Response(
                {"detail": "The pending Order expired and was rejected; reserved stock was released."},
                status=status.HTTP_409_CONFLICT,
            )
        data = MerchantOrderDetailSerializer(order, context=self.get_serializer_context()).data
        action_link = None
        event_type = None
        if action_name == "accept":
            from django.db.models import F
            if order.items.filter(quantity__lt=F("ordered_quantity")).exists():
                event_type = "QUANTITY_REDUCED"
            else:
                event_type = "ORDER_ACCEPTED"
        elif action_name in ("reject", "cancel"):
            event_type = "ORDER_REJECTED"
        elif action_name == "prepare":
            event_type = "ORDER_PREPARING"
        elif action_name == "ready":
            event_type = "ORDER_READY"
        elif action_name == "complete":
            event_type = "ORDER_COMPLETED"

        if event_type:
            lang = request.query_params.get("language", "hinglish")
            action_link = get_merchant_order_action_link(order, event_type, language=lang)

        data["whatsapp_action_link"] = action_link
        return Response(data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        return self._transition_response(request, pk, "accept", MerchantOrderAcceptSerializer)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition_response(request, pk, "reject", MerchantOrderRejectSerializer)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._transition_response(request, pk, "cancel", MerchantOrderRejectSerializer)

    @action(detail=True, methods=["post"])
    def prepare(self, request, pk=None):
        return self._transition_response(request, pk, "prepare", MerchantOrderEmptyActionSerializer)

    @action(detail=True, methods=["post"])
    def ready(self, request, pk=None):
        return self._transition_response(request, pk, "ready", MerchantOrderEmptyActionSerializer)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        return self._transition_response(request, pk, "complete", MerchantOrderEmptyActionSerializer)

    @action(detail=True, methods=["post"], url_path="payment-status")
    def payment_status(self, request, pk=None):
        order = self.get_object()
        serializer = MerchantOrderPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order, expired = set_order_payment_status(
            order.shop_id,
            order.pk,
            serializer.validated_data["payment_status"],
        )
        if expired:
            return Response(
                {"detail": "The pending Order expired and was rejected; reserved stock was released."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(MerchantOrderDetailSerializer(order, context=self.get_serializer_context()).data)
