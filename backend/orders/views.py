from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from orders.serializers import CheckoutSerializer
from orders.services import create_order
from shops.models import Shop


class PublicCheckoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, public_slug):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get("Idempotency-Key", "").strip()
        if not idempotency_key:
            return Response({"detail": "Idempotency-Key header is required."}, status=400)
        if len(idempotency_key) > 64:
            return Response({"detail": "Idempotency-Key must be at most 64 characters."}, status=400)

        shop = get_object_or_404(Shop, public_slug=public_slug, status=Shop.Status.ACTIVE)
        order, created = create_order(shop, serializer.validated_data, idempotency_key)

        response = {
            "id": order.pk,
            "status": order.status,
            "payment_status": order.payment_status,
            "fulfillment_type": order.fulfillment_type,
            "items_subtotal": str(order.items_subtotal),
            "delivery_charge": str(order.delivery_charge_snapshot),
            "total_amount": str(order.total_amount),
            "expires_at": order.expires_at,
        }
        return Response(response, status=201 if created else 200)
