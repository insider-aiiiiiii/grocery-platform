from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shops.models import Shop

from .models import Cart
from .serializers import CartCreateSerializer, PublicCartSerializer


def get_public_active_shop(public_slug: str):
    """
    Resolve and validate an active Shop by its public_slug for customer-facing requests.
    Returns (shop, error_response).
    """
    shop = Shop.objects.filter(public_slug=public_slug).first()
    if not shop:
        return None, Response(
            {"detail": "Shop not found.", "code": "SHOP_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if shop.status != Shop.Status.ACTIVE:
        return None, Response(
            {"detail": "Shop is unavailable.", "code": "SHOP_UNAVAILABLE"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return shop, None


class PublicShopCartView(APIView):
    """
    Public customer-facing Cart endpoint for a specific Shop.
    - POST: Creates an anonymous or customer-associated Cart for this Shop.
    - GET: Retrieves a Cart for this Shop using query param `?cart_id=<id>` or header `X-Cart-ID`.
    """

    permission_classes = [AllowAny]

    def post(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        serializer = CartCreateSerializer(
            data=request.data,
            context={"request": request, "shop": shop},
        )
        serializer.is_valid(raise_exception=True)
        cart = serializer.save()

        # Prefetch relations for response serialization
        cart = (
            Cart.objects.filter(pk=cart.pk)
            .select_related("shop", "customer")
            .prefetch_related("items__product", "items__variant")
            .first()
        )
        return Response(PublicCartSerializer(cart).data, status=status.HTTP_201_CREATED)

    def get(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        cart_id = request.query_params.get("cart_id") or request.headers.get("X-Cart-ID")
        if not cart_id:
            return Response(
                {"detail": "Cart ID is required.", "code": "CART_ID_REQUIRED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = (
            Cart.objects.filter(id=cart_id, shop=shop)
            .select_related("shop", "customer")
            .prefetch_related("items__product", "items__variant")
            .first()
        )
        if not cart:
            return Response(
                {"detail": "Cart not found.", "code": "CART_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(PublicCartSerializer(cart).data, status=status.HTTP_200_OK)


class PublicShopCartDetailView(APIView):
    """
    Public customer-facing Cart detail endpoint scoped strictly to the Shop's public slug.
    - GET: Retrieves cart details by PK under the addressed Shop.
    """

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str, pk: int):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        cart = (
            Cart.objects.filter(id=pk, shop=shop)
            .select_related("shop", "customer")
            .prefetch_related("items__product", "items__variant")
            .first()
        )
        if not cart:
            return Response(
                {"detail": "Cart not found.", "code": "CART_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(PublicCartSerializer(cart).data, status=status.HTTP_200_OK)


class PublicCartDetailView(APIView):
    """
    Public customer-facing Cart direct detail endpoint by cart ID.
    - GET: Retrieves cart details by PK, verifying the associated Shop is active.
    """

    permission_classes = [AllowAny]

    def get(self, request, pk: int):
        cart = (
            Cart.objects.filter(id=pk)
            .select_related("shop", "customer")
            .prefetch_related("items__product", "items__variant")
            .first()
        )
        if not cart or cart.shop.status != Shop.Status.ACTIVE:
            return Response(
                {"detail": "Cart not found.", "code": "CART_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(PublicCartSerializer(cart).data, status=status.HTTP_200_OK)
