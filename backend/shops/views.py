from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.permissions import IsSuperAdmin

from .models import Shop
from .permissions import IsActiveMerchant
from .serializers import (
    PublicShopSerializer,
    ShopCreateSerializer,
    ShopSerializer,
    ShopUpdateSerializer,
)


def get_merchant_shop(user):
    """Resolve a Shop only through the authenticated Merchant relationship."""
    merchant = getattr(user, "merchant", None)
    if merchant is None:
        return None
    return Shop.objects.filter(merchant_id=merchant.pk, merchant__user_id=user.pk).first()


def merchant_shop_response(user):
    shop = get_merchant_shop(user)
    if not shop:
        return Response(
            {"detail": "Merchant does not have a shop.", "code": "SHOP_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if shop.status in [Shop.Status.DEACTIVATED, Shop.Status.SUSPENDED]:
        return Response(
            {"detail": "Shop is deactivated or suspended.", "code": "SHOP_INACTIVE"},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response(ShopSerializer(shop).data, status=status.HTTP_200_OK)


def update_merchant_shop(request, partial: bool = True):
    shop = get_merchant_shop(request.user)
    if not shop:
        return Response(
            {"detail": "Merchant does not have a shop.", "code": "SHOP_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if shop.status in [Shop.Status.DEACTIVATED, Shop.Status.SUSPENDED]:
        return Response(
            {"detail": "Shop is deactivated or suspended.", "code": "SHOP_INACTIVE"},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = ShopUpdateSerializer(
        shop,
        data=request.data,
        partial=partial,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    updated_shop = serializer.save()
    return Response(ShopSerializer(updated_shop).data, status=status.HTTP_200_OK)


class MerchantShopDetailView(APIView):
    """API endpoint allowing an authenticated Merchant to retrieve or update their own Shop profile."""

    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def get(self, request):
        return merchant_shop_response(request.user)

    def patch(self, request):
        return update_merchant_shop(request, partial=True)

    def put(self, request):
        return update_merchant_shop(request, partial=False)

    def delete(self, request):
        return Response(
            {
                "detail": "Merchants cannot delete a shop. Only Super Admin can permanently delete a shop.",
                "code": "SHOP_DELETION_NOT_PERMITTED",
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class ShopCreateView(APIView):
    """API endpoint allowing an authenticated Merchant to create, retrieve, or update their Shop profile."""

    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def get(self, request):
        return merchant_shop_response(request.user)

    def patch(self, request):
        return update_merchant_shop(request, partial=True)

    def put(self, request):
        return update_merchant_shop(request, partial=False)

    def post(self, request):
        merchant = getattr(request.user, "merchant", None)
        if merchant is not None and Shop.objects.filter(
            merchant_id=merchant.pk, merchant__user_id=request.user.pk
        ).exists():
            return Response(
                {"detail": "Merchant already has a shop.", "code": "SHOP_ALREADY_EXISTS"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ShopCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        shop = serializer.save()

        return Response(ShopSerializer(shop).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        return Response(
            {
                "detail": "Merchants cannot delete a shop. Only Super Admin can permanently delete a shop.",
                "code": "SHOP_DELETION_NOT_PERMITTED",
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class MerchantShopDeactivationForbiddenView(APIView):
    """Endpoint explicitly informing merchants that Shop deactivation is an administrative lifecycle action."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {
                "detail": "Merchants cannot deactivate a shop. Use temporary closure to stop operations, or contact Super Admin.",
                "code": "SHOP_DEACTIVATION_NOT_PERMITTED",
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class SuperAdminShopDeactivateView(APIView):
    """API endpoint allowing an authenticated Super Admin to deactivate a Shop."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk: int):
        shop = get_object_or_404(Shop, pk=pk)
        if shop.status == Shop.Status.DEACTIVATED:
            return Response(
                {"detail": "Shop is already deactivated.", "code": "SHOP_ALREADY_DEACTIVATED"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        shop.deactivate()
        return Response(ShopSerializer(shop).data, status=status.HTTP_200_OK)


class SuperAdminShopDeleteView(APIView):
    """API endpoint allowing an authenticated Super Admin to permanently delete a Shop."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def delete(self, request, pk: int):
        shop = get_object_or_404(Shop, pk=pk)

        confirm = request.data.get("confirm") if isinstance(request.data, dict) else None
        if confirm is None:
            raw_param = request.query_params.get("confirm")
            confirm = True if raw_param and str(raw_param).lower() in ("true", "1") else False

        if confirm is not True:
            return Response(
                {
                    "detail": "Permanent deletion requires explicit confirmation. All shop data, products, and orders will be permanently removed.",
                    "code": "CONFIRMATION_REQUIRED",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            shop.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicShopDetailView(APIView):
    """API endpoint allowing unauthenticated customers/visitors to retrieve public Shop details via public QR slug."""

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str):
        shop = Shop.objects.filter(public_slug=public_slug).first()
        if not shop:
            return Response(
                {"detail": "Shop not found.", "code": "SHOP_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if shop.status != Shop.Status.ACTIVE:
            return Response(
                {"detail": "Shop is unavailable.", "code": "SHOP_UNAVAILABLE"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PublicShopSerializer(shop, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

