from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsActiveMerchant
from .serializers import ShopCreateSerializer, ShopSerializer


class ShopCreateView(APIView):
    """API endpoint allowing an authenticated Merchant to create their Shop profile."""

    permission_classes = [IsAuthenticated, IsActiveMerchant]

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
