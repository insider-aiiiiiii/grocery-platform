from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
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
    SuperAdminShopDirectorySerializer,
)
from .services import permanently_delete_shop



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
    parser_classes = [MultiPartParser, FormParser, JSONParser]

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


class MerchantShopReactivationForbiddenView(APIView):
    """Endpoint explicitly informing merchants that Shop reactivation is an administrative lifecycle action."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {
                "detail": "Merchants cannot reactivate a shop. Only Super Admin can reactivate a deactivated or suspended shop.",
                "code": "SHOP_REACTIVATION_NOT_PERMITTED",
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class MerchantShopQRRegenerationForbiddenView(APIView):
    """Endpoint explicitly informing merchants that QR code regeneration is restricted to Super Admin."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {
                "detail": "Merchants cannot regenerate the shop QR code. The QR code remains fixed to preserve printed materials. Contact Super Admin if compromised.",
                "code": "QR_REGENERATION_NOT_PERMITTED",
            },
            status=status.HTTP_403_FORBIDDEN,
        )


class MerchantShopQRDetailView(APIView):
    """API endpoint allowing an authenticated Merchant to view their own Shop's QR details and public link."""

    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def get(self, request):
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
        path = f"/api/v1/shops/public/{shop.public_slug}/"
        public_url = request.build_absolute_uri(path) if request else path
        return Response(
            {
                "public_slug": shop.public_slug,
                "public_url": public_url,
                "qr_data": public_url,
            },
            status=status.HTTP_200_OK,
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
        return Response(ShopSerializer(shop, context={"request": request}).data, status=status.HTTP_200_OK)


class SuperAdminShopReactivateView(APIView):
    """API endpoint allowing an authenticated Super Admin to reactivate or unsuspend a Shop."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk: int):
        shop = get_object_or_404(Shop, pk=pk)
        if shop.status == Shop.Status.ACTIVE:
            return Response(
                {"detail": "Shop is already active.", "code": "SHOP_ALREADY_ACTIVE"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        shop.reactivate()
        return Response(ShopSerializer(shop, context={"request": request}).data, status=status.HTTP_200_OK)


class SuperAdminShopRegenerateQRView(APIView):
    """API endpoint allowing an authenticated Super Admin to regenerate a Shop's QR code / public link."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk: int):
        shop = get_object_or_404(Shop, pk=pk)
        shop.regenerate_public_slug()
        return Response(ShopSerializer(shop, context={"request": request}).data, status=status.HTTP_200_OK)


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
            permanently_delete_shop(shop, requested_by=request.user)

        return Response(status=status.HTTP_204_NO_CONTENT)


class SuperAdminShopListView(generics.ListAPIView):
    """API endpoint allowing an authenticated Super Admin to list all platform shops and provisioned merchants."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = SuperAdminShopDirectorySerializer
    queryset = Shop.objects.all().select_related("merchant__user").order_by("-created_at")

    def list(self, request, *args, **kwargs):
        from users.models import Merchant

        shops = self.get_queryset()
        shop_data = self.get_serializer(shops, many=True).data

        # Also include provisioned merchants who have not yet set up a shop
        merchants_with_shops = Shop.objects.values_list("merchant_id", flat=True)
        pending_merchants = (
            Merchant.objects.exclude(id__in=merchants_with_shops)
            .select_related("user")
            .order_by("-user__date_joined")
        )

        pending_data = []
        for m in pending_merchants:
            status_val = "PENDING_PASSWORD_CHANGE" if m.must_change_password else m.status
            pending_data.append({
                "id": -(m.id),
                "shop_id": None,
                "merchant_id": m.id,
                "name": f"{m.user.username}'s Store (Pending Setup)",
                "public_slug": "",
                "status": status_val,
                "city": "Pending Setup",
                "owner__username": m.user.username,
                "owner__mobile_number": m.user.mobile_number,
                "owner_username": m.user.username,
                "owner_mobile_number": m.user.mobile_number,
                "catalog_items_count": 0,
                "monthly_volume": "₹0",
                "created_at": m.user.date_joined.isoformat() if m.user.date_joined else None,
            })

        return Response(shop_data + pending_data, status=status.HTTP_200_OK)


class PublicShopDetailView(APIView):
    """API endpoint allowing unauthenticated customers/visitors to retrieve public Shop details via public QR slug."""

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str):
        shop = Shop.get_by_slug_or_code(public_slug)
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

