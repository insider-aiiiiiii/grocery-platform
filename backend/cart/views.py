from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shops.models import Shop

from .models import Cart, CartItem
from .serializers import (
    CartCreateSerializer,
    CartItemAddSerializer,
    CartItemUpdateSerializer,
    CartValidationResultSerializer,
    PublicCartItemSerializer,
    PublicCartSerializer,
)
from .services import validate_cart_state


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


def resolve_cart_for_request(
    request,
    cart_id: int | None = None,
    public_slug: str | None = None,
    allow_inactive_shop: bool = False,
):
    """
    Resolves and validates a Cart for item operations, enforcing shop activity and tenancy.
    Returns (cart, error_response).
    """
    if public_slug:
        shop = Shop.objects.filter(public_slug=public_slug).first()
        if not shop:
            return None, Response(
                {"detail": "Shop not found.", "code": "SHOP_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not allow_inactive_shop and shop.status != Shop.Status.ACTIVE:
            return None, Response(
                {"detail": "Shop is unavailable.", "code": "SHOP_UNAVAILABLE"},
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        shop = None

    resolved_id = cart_id or request.data.get("cart_id") or request.query_params.get("cart_id") or request.headers.get("X-Cart-ID")
    if not resolved_id:
        return None, Response(
            {"detail": "Cart ID is required.", "code": "CART_ID_REQUIRED"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cart = Cart.objects.filter(id=resolved_id).select_related("shop").first()
    if not cart:
        return None, Response(
            {"detail": "Cart not found.", "code": "CART_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not allow_inactive_shop and cart.shop.status != Shop.Status.ACTIVE:
        return None, Response(
            {"detail": "Cart not found.", "code": "CART_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if shop and cart.shop_id != shop.id:
        return None, Response(
            {"detail": "Cart not found.", "code": "CART_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return cart, None


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


class CartItemListView(APIView):
    """
    Public Cart Item list and add endpoint.
    - GET: Lists all items in the resolved Cart.
    - POST: Adds a product/variant to the Cart (increments quantity if already in Cart).
    - DELETE: Clears all items from the Cart.
    """

    permission_classes = [AllowAny]

    def get(self, request, cart_id: int | None = None, public_slug: str | None = None):
        cart, error_res = resolve_cart_for_request(request, cart_id=cart_id, public_slug=public_slug)
        if error_res:
            return error_res

        items = cart.items.select_related("product", "variant").all()
        return Response(PublicCartItemSerializer(items, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, cart_id: int | None = None, public_slug: str | None = None):
        cart, error_res = resolve_cart_for_request(request, cart_id=cart_id, public_slug=public_slug)
        if error_res:
            return error_res

        serializer = CartItemAddSerializer(
            data=request.data,
            context={"request": request, "cart": cart},
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        # Re-fetch item with relationships for serialization
        item = CartItem.objects.filter(pk=item.pk).select_related("product", "variant").first()
        return Response(PublicCartItemSerializer(item).data, status=status.HTTP_201_CREATED)

    def delete(self, request, cart_id: int | None = None, public_slug: str | None = None):
        cart, error_res = resolve_cart_for_request(request, cart_id=cart_id, public_slug=public_slug)
        if error_res:
            return error_res

        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartItemDetailView(APIView):
    """
    Public Cart Item detail, update, and remove endpoint.
    - GET: Retrieves a single Cart Item.
    - PATCH / PUT: Updates quantity of the Cart Item.
    - DELETE: Removes the Cart Item from the Cart.
    """

    permission_classes = [AllowAny]

    def get(self, request, item_id: int, cart_id: int | None = None, public_slug: str | None = None):
        cart, error_res = resolve_cart_for_request(request, cart_id=cart_id, public_slug=public_slug)
        if error_res:
            return error_res

        item = cart.items.filter(id=item_id).select_related("product", "variant").first()
        if not item:
            return Response(
                {"detail": "Cart item not found.", "code": "CART_ITEM_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(PublicCartItemSerializer(item).data, status=status.HTTP_200_OK)

    def patch(self, request, item_id: int, cart_id: int | None = None, public_slug: str | None = None):
        return self._update_item(request, item_id, cart_id, public_slug)

    def put(self, request, item_id: int, cart_id: int | None = None, public_slug: str | None = None):
        return self._update_item(request, item_id, cart_id, public_slug)

    def _update_item(self, request, item_id: int, cart_id: int | None, public_slug: str | None):
        cart, error_res = resolve_cart_for_request(request, cart_id=cart_id, public_slug=public_slug)
        if error_res:
            return error_res

        item = cart.items.filter(id=item_id).select_related("product", "variant").first()
        if not item:
            return Response(
                {"detail": "Cart item not found.", "code": "CART_ITEM_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CartItemUpdateSerializer(
            data=request.data,
            context={"request": request, "cart_item": item},
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        item = CartItem.objects.filter(pk=item.pk).select_related("product", "variant").first()
        return Response(PublicCartItemSerializer(item).data, status=status.HTTP_200_OK)

    def delete(self, request, item_id: int, cart_id: int | None = None, public_slug: str | None = None):
        cart, error_res = resolve_cart_for_request(request, cart_id=cart_id, public_slug=public_slug)
        if error_res:
            return error_res

        item = cart.items.filter(id=item_id).first()
        if not item:
            return Response(
                {"detail": "Cart item not found.", "code": "CART_ITEM_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicCartValidateView(APIView):
    """
    Public customer-facing Cart validation endpoint.
    Re-validates the entire Cart against real-time Shop, Catalog, and Inventory states.
    - GET: Evaluates and returns cart validity, can_checkout flag, per-item status,
           recalculated subtotal, and orders dependencies demarcation.
    - POST: Supports action-triggered validation checks (e.g. pre-checkout flow).
    """

    permission_classes = [AllowAny]

    def get(self, request, cart_id: int | None = None, public_slug: str | None = None):
        return self._validate(request, cart_id=cart_id, public_slug=public_slug)

    def post(self, request, cart_id: int | None = None, public_slug: str | None = None):
        return self._validate(request, cart_id=cart_id, public_slug=public_slug)

    def _validate(self, request, cart_id: int | None, public_slug: str | None):
        cart, error_res = resolve_cart_for_request(
            request,
            cart_id=cart_id,
            public_slug=public_slug,
            allow_inactive_shop=True,
        )
        if error_res:
            return error_res

        result = validate_cart_state(cart)
        serializer = CartValidationResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)


