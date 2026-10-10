from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Shop
from .permissions import IsActiveMerchant
from .serializers import ShopCreateSerializer, ShopSerializer


class MerchantShopDetailView(APIView):
    """API endpoint allowing an authenticated Merchant to retrieve their own Shop profile."""

    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def get(self, request):
        merchant = getattr(request.user, "merchant", None)
        shop = getattr(merchant, "shop", None) if merchant else None
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


class ShopCreateView(APIView):
    """API endpoint allowing an authenticated Merchant to create or retrieve their Shop profile."""

    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def get(self, request):
        return MerchantShopDetailView().get(request)

    def post(self, request):
        merchant = getattr(request.user, "merchant", None)
        if merchant is not None and hasattr(merchant, "shop"):
            return Response(
                {"detail": "Merchant already has a shop.", "code": "SHOP_ALREADY_EXISTS"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ShopCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        shop = serializer.save()

        return Response(ShopSerializer(shop).data, status=status.HTTP_201_CREATED)

