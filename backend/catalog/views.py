from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.permissions import IsSuperAdmin

from .models import MasterProduct, ShopProduct
from .serializers import MasterProductSerializer, PromoteShopProductSerializer


def promote_shop_product_to_master(shop_product, validated_data=None):
    """
    Promote a Merchant-created Shop Product into the Master Catalog.

    Promotion makes reusable Master Catalog content available to other Merchants
    but does not link, replace, update, or merge the originating Shop Product:
    - Creates a new independent MasterProduct entity.
    - Preserves originating ShopProduct without modifying its fields or linking
      its master_product foreign key.
    """
    validated_data = validated_data or {}

    name = validated_data.get("name") or shop_product.name
    description = validated_data.get("description") if "description" in validated_data else shop_product.description
    brand = validated_data.get("brand") or shop_product.effective_brand
    category = validated_data.get("category", None)
    is_active = validated_data.get("is_active", True)
    image = shop_product.image if bool(shop_product.image) else None

    with transaction.atomic():
        master_product = MasterProduct.objects.create(
            name=name,
            description=description,
            brand=brand,
            category=category,
            is_active=is_active,
            image=image,
        )

    return master_product


class MasterProductViewSet(viewsets.ModelViewSet):
    """
    CRUD API for platform-level Master Catalog products.

    Only platform-authorized Super Admin operations are allowed.
    Master Catalog records remain strictly independent of Shop Products:
    - Master Products do not belong to any Shop.
    - Creating, updating, or deleting Master Products does not alter or impair
      existing Shop Products.
    """

    queryset = MasterProduct.objects.all().select_related("category").order_by("name", "id")
    serializer_class = MasterProductSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1"):
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ("false", "0"):
                queryset = queryset.filter(is_active=False)

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset

    @action(detail=False, methods=["post"], url_path="promote")
    def promote(self, request):
        """
        Promote a Shop Product into Master Catalog via POST /api/v1/catalog/master-products/promote/.
        Payload must include `shop_product_id`.
        """
        serializer = PromoteShopProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        shop_product_id = serializer.validated_data.get("shop_product_id")
        if not shop_product_id:
            return Response(
                {"shop_product_id": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shop_product = ShopProduct.objects.filter(pk=shop_product_id).first()
        if not shop_product:
            return Response(
                {"detail": "Shop Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        master_product = promote_shop_product_to_master(shop_product, serializer.validated_data)
        response_serializer = MasterProductSerializer(master_product, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class SuperAdminPromoteShopProductView(APIView):
    """
    API endpoint allowing an authenticated Super Admin to promote a Shop Product
    into the Master Catalog via /api/v1/catalog/shop-products/<int:pk>/promote/.

    Only platform-authorized Super Admin operations are allowed.
    The originating Shop Product is not linked, replaced, updated, or merged.
    """

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk: int):
        shop_product = ShopProduct.objects.filter(pk=pk).first()
        if not shop_product:
            return Response(
                {"detail": "Shop Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PromoteShopProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        master_product = promote_shop_product_to_master(shop_product, serializer.validated_data)
        response_serializer = MasterProductSerializer(master_product, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
