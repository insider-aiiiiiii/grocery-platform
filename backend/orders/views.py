import logging

from django.db.models import prefetch_related_objects
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.tokens import tokens_match
from notifications.links import get_customer_order_notification_links
from cart.models import Cart
from orders.models import Order
from orders.serializers import CheckoutSerializer
from orders.services import create_order
from shops.models import Shop
from users.throttles import PublicWriteThrottle

logger = logging.getLogger(__name__)


ORDER_TOKEN_HEADER = "X-Order-Token"
CART_TOKEN_HEADER = "X-Cart-Token"


def _order_not_found():
    return Response(
        {"detail": "Order not found in this shop.", "code": "ORDER_NOT_FOUND"},
        status=404,
    )


def format_public_order_response(order: Order, shop: Shop, include_token: bool = False) -> dict:
    # Load line items and delivery address once; the WhatsApp link builder and the
    # response below then reuse the cached rows instead of querying again.
    prefetch_related_objects([order], "items", "delivery_address")
    if order.shop_id == shop.pk:
        order.shop = shop

    whatsapp_links = None
    try:
        whatsapp_links = get_customer_order_notification_links(order)
    except Exception as exc:
        logger.warning(
            "Failed to generate customer WhatsApp notification links for order %s: %s",
            order.pk,
            exc,
        )

    items_data = [
        {
            "product_name": item.product_name_snapshot,
            "variant_name": item.variant_name_snapshot,
            "sku": item.sku_snapshot,
            "quantity": str(item.quantity),
            "unit_price": str(item.unit_price_snapshot),
            "line_total": str(item.line_total),
        }
        for item in sorted(order.items.all(), key=lambda i: i.pk)
    ]

    addr_data = None
    if getattr(order, "delivery_address", None):
        addr = order.delivery_address
        addr_data = {
            "address_line": addr.address_line,
            "area": addr.area,
            "city": addr.city,
            "state": addr.state,
            "pincode": addr.pincode,
            "landmark": addr.landmark,
            "delivery_notes": addr.delivery_notes,
        }

    data = {
        "id": order.pk,
        "status": order.status,
        "payment_status": order.payment_status,
        "fulfillment_type": order.fulfillment_type,
        "customer_name": order.customer_name_snapshot,
        "customer_phone": order.customer_phone_snapshot,
        "delivery_address": addr_data,
        "shop_name": shop.name,
        "shop_contact_number": shop.contact_number,
        "items_subtotal": str(order.items_subtotal),
        "delivery_charge": str(order.delivery_charge_snapshot),
        "total_amount": str(order.total_amount),
        "expires_at": order.expires_at,
        "items": items_data,
        "whatsapp_notification_links": whatsapp_links,
    }
    if include_token:
        # Only ever returned to the browser that just placed the order.
        data["access_token"] = order.access_token
    return data


class PublicCheckoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PublicWriteThrottle]

    def post(self, request, public_slug):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get("Idempotency-Key", "").strip()
        if not idempotency_key:
            return Response({"detail": "Idempotency-Key header is required."}, status=400)
        if len(idempotency_key) > 64:
            return Response({"detail": "Idempotency-Key must be at most 64 characters."}, status=400)

        shop = Shop.get_by_slug_or_code(public_slug)
        if not shop or shop.status != Shop.Status.ACTIVE:
            return Response(
                {"detail": "Shop not found or unavailable.", "code": "SHOP_UNAVAILABLE"},
                status=404,
            )
        cart = Cart.objects.filter(pk=serializer.validated_data["cart_id"], shop=shop).first()
        if cart is None or not tokens_match(cart.access_token, request.headers.get(CART_TOKEN_HEADER)):
            return Response({"detail": "Cart not found.", "code": "CART_NOT_FOUND"}, status=404)
        order, created = create_order(shop, serializer.validated_data, idempotency_key)
        return Response(
            format_public_order_response(order, shop, include_token=True),
            status=201 if created else 200,
        )


from orders.transitions import OrderTransitionConflict, cancel_pending_order_for_shop


class PublicOrderDetailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, public_slug: str, order_id: int):
        shop = Shop.get_by_slug_or_code(public_slug)
        if not shop or shop.status != Shop.Status.ACTIVE:
            return Response(
                {"detail": "Shop not found or unavailable.", "code": "SHOP_UNAVAILABLE"},
                status=404,
            )

        order = (
            Order.objects.filter(shop=shop, pk=order_id)
            .select_related("delivery_address")
            .prefetch_related("items")
            .first()
        )
        # A wrong or missing token is indistinguishable from a missing order.
        if not order or not tokens_match(order.access_token, request.headers.get(ORDER_TOKEN_HEADER)):
            return _order_not_found()

        return Response(format_public_order_response(order, shop), status=200)

    def post(self, request, public_slug: str, order_id: int):
        return PublicOrderCancelView().post(request, public_slug, order_id)


class PublicOrderCancelView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, public_slug: str, order_id: int):
        shop = Shop.get_by_slug_or_code(public_slug)
        if not shop or shop.status != Shop.Status.ACTIVE:
            return Response(
                {"detail": "Shop not found or unavailable.", "code": "SHOP_UNAVAILABLE"},
                status=404,
            )

        owned = Order.objects.filter(shop=shop, pk=order_id).only("access_token").first()
        if not owned or not tokens_match(owned.access_token, request.headers.get(ORDER_TOKEN_HEADER)):
            return _order_not_found()

        try:
            order, expired = cancel_pending_order_for_shop(shop.id, order_id)
        except OrderTransitionConflict as exc:
            return Response({"detail": str(exc), "code": "INVALID_TRANSITION"}, status=409)
        except Exception as exc:
            logger.warning("Order cancellation failed for shop %s, order %s: %s", shop.id, order_id, exc)
            return Response(
                {"detail": "Order not found or cannot be cancelled.", "code": "CANCEL_FAILED"},
                status=404,
            )

        return Response(format_public_order_response(order, shop), status=200)

