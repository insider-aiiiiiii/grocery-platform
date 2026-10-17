from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from shops.models import Shop
from shops.permissions import IsActiveMerchant
from users.permissions import IsSuperAdmin

from .models import (
    MasterProduct,
    ShopBrand,
    ShopCategory,
    ShopCustomAttribute,
    ShopProduct,
)
from .serializers import (
    MasterProductSerializer,
    PromoteShopProductSerializer,
    PublicBrandSerializer,
    PublicCategorySerializer,
    PublicCustomAttributeSerializer,
    PublicProductVariantSerializer,
    PublicShopProductSerializer,
    ShopBrandSerializer,
    ShopCategorySerializer,
    ShopCustomAttributeSerializer,
    ShopProductSerializer,
)


def get_authenticated_merchant_shop(request):
    """
    Resolve and validate the Shop owned by the authenticated Merchant.
    Returns (shop, error_response). If valid, error_response is None.
    """
    user = request.user
    merchant = getattr(user, "merchant", None)
    if merchant is None:
        return None, Response(
            {"detail": "Only active merchants can perform this action.", "code": "NOT_A_MERCHANT"},
            status=status.HTTP_403_FORBIDDEN,
        )
    shop = Shop.objects.filter(merchant_id=merchant.pk, merchant__user_id=user.pk).first()
    if not shop:
        return None, Response(
            {"detail": "Merchant does not have a shop.", "code": "SHOP_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if shop.status in (Shop.Status.DEACTIVATED, Shop.Status.SUSPENDED):
        return None, Response(
            {"detail": "Shop is deactivated or suspended.", "code": "SHOP_INACTIVE"},
            status=status.HTTP_403_FORBIDDEN,
        )
    return shop, None


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


class MerchantShopProductViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Merchants managing their own Shop Products.

    - Merchant may create directly or select from Master Catalog.
    - No Super Admin approval workflow is required.
    - Enforces Shop authorization on every protected operation.
    - Isolates tenant data strictly: a merchant can only access their own Shop Products.
    """

    serializer_class = ShopProductSerializer
    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        shop, error_res = get_authenticated_merchant_shop(request)
        self._shop = shop
        self._shop_error = error_res

    def get_queryset(self):
        if getattr(self, "_shop_error", None):
            return ShopProduct.objects.none()
        shop = getattr(self, "_shop", None)
        if not shop:
            return ShopProduct.objects.none()

        queryset = (
            ShopProduct.objects.filter(shop=shop)
            .prefetch_related("categories")
            .select_related("brand_ref", "master_product")
            .order_by("name", "id")
        )

        is_visible = self.request.query_params.get("is_visible")
        if is_visible is not None:
            if is_visible.lower() in ("true", "1"):
                queryset = queryset.filter(is_visible=True)
            elif is_visible.lower() in ("false", "0"):
                queryset = queryset.filter(is_visible=False)

        is_available = self.request.query_params.get("is_available")
        if is_available is not None:
            if is_available.lower() in ("true", "1"):
                queryset = queryset.filter(is_available=True)
            elif is_available.lower() in ("false", "0"):
                queryset = queryset.filter(is_available=False)

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(categories__id=category_id)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(sku__icontains=search) | Q(brand__icontains=search)
            )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = getattr(self, "_shop", None)
        return context

    def list(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(shop=self._shop)


class MerchantShopCategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Merchants managing their own Shop Categories and subcategories.

    - Preserves Shop ownership: all operations are strictly scoped to the authenticated merchant's shop.
    - Supports subcategories via parent-child relationship.
    - Tenant isolation: parent must belong to the same Shop.
    - Deleting a category leaves assigned products intact and uncategorized per domain rules.
    """

    serializer_class = ShopCategorySerializer
    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        shop, error_res = get_authenticated_merchant_shop(request)
        self._shop = shop
        self._shop_error = error_res

    def get_queryset(self):
        if getattr(self, "_shop_error", None):
            return ShopCategory.objects.none()
        shop = getattr(self, "_shop", None)
        if not shop:
            return ShopCategory.objects.none()

        queryset = (
            ShopCategory.objects.filter(shop=shop)
            .select_related("parent")
            .prefetch_related("subcategories", "products")
            .order_by("name", "id")
        )

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1"):
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ("false", "0"):
                queryset = queryset.filter(is_active=False)

        parent_param = self.request.query_params.get("parent")
        if parent_param is not None:
            if parent_param.lower() in ("null", "none", "root"):
                queryset = queryset.filter(parent__isnull=True)
            elif parent_param.isdigit():
                queryset = queryset.filter(parent_id=int(parent_param))

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(slug__icontains=search) | Q(description__icontains=search)
            )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = getattr(self, "_shop", None)
        return context

    def list(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(shop=self._shop)


class MerchantShopBrandViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Merchants managing their own Shop Brands.

    - Preserves Shop ownership: all operations are strictly scoped to the authenticated merchant's shop.
    - Tenant isolation: merchants cannot view, update, or delete other shops' brands.
    - Deleting a brand preserves assigned products, setting brand_ref to NULL per domain rules.
    """

    serializer_class = ShopBrandSerializer
    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        shop, error_res = get_authenticated_merchant_shop(request)
        self._shop = shop
        self._shop_error = error_res

    def get_queryset(self):
        if getattr(self, "_shop_error", None):
            return ShopBrand.objects.none()
        shop = getattr(self, "_shop", None)
        if not shop:
            return ShopBrand.objects.none()

        queryset = (
            ShopBrand.objects.filter(shop=shop)
            .prefetch_related("products")
            .order_by("name", "id")
        )

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1"):
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ("false", "0"):
                queryset = queryset.filter(is_active=False)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(slug__icontains=search) | Q(description__icontains=search)
            )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = getattr(self, "_shop", None)
        return context

    def list(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(shop=self._shop)


class MerchantShopCustomAttributeViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Merchants managing their own Shop Custom Attributes and basic values.

    - Preserves Shop ownership: all operations are strictly scoped to the authenticated merchant's shop.
    - Tenant isolation: merchants cannot view, update, or delete other shops' custom attributes.
    - Manages attribute definitions and allowed basic values without a rigid global taxonomy.
    """

    serializer_class = ShopCustomAttributeSerializer
    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        shop, error_res = get_authenticated_merchant_shop(request)
        self._shop = shop
        self._shop_error = error_res

    def get_queryset(self):
        if getattr(self, "_shop_error", None):
            return ShopCustomAttribute.objects.none()
        shop = getattr(self, "_shop", None)
        if not shop:
            return ShopCustomAttribute.objects.none()

        queryset = (
            ShopCustomAttribute.objects.filter(shop=shop)
            .order_by("name", "id")
        )

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1"):
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ("false", "0"):
                queryset = queryset.filter(is_active=False)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = getattr(self, "_shop", None)
        return context

    def list(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(shop=self._shop)


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


class PublicShopProductListView(APIView):
    """
    Public customer-facing endpoint listing visible products for an addressed active Shop.
    Enforces tenant boundaries; filters out hidden products.
    Inventory determines stock quantities, is_orderable, and Out of Stock indicators.
    """

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        queryset = (
            ShopProduct.objects.filter(shop=shop, is_visible=True)
            .select_related("brand_ref")
            .prefetch_related("categories", "variants")
            .order_by("name", "id")
        )

        category_param = request.query_params.get("category")
        if category_param:
            if category_param.isdigit():
                queryset = queryset.filter(categories__id=int(category_param))
            else:
                queryset = queryset.filter(categories__slug=category_param)

        brand_param = request.query_params.get("brand")
        if brand_param:
            if brand_param.isdigit():
                queryset = queryset.filter(brand_ref_id=int(brand_param))
            else:
                queryset = queryset.filter(Q(brand_ref__slug=brand_param) | Q(brand__iexact=brand_param))

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(sku__icontains=search) | Q(brand__icontains=search)
            )

        from inventory.models import InventoryItem

        inv_items = InventoryItem.objects.filter(shop=shop)
        stock_map = {(item.product_id, item.variant_id): item.available_quantity for item in inv_items}

        serializer = PublicShopProductSerializer(
            queryset,
            many=True,
            context={"request": request, "stock_map": stock_map},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicShopProductDetailView(APIView):
    """
    Public customer-facing endpoint retrieving a single visible product for an active Shop.
    """

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str, pk: int):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        product = (
            ShopProduct.objects.filter(shop=shop, pk=pk, is_visible=True)
            .select_related("brand_ref")
            .prefetch_related("categories", "variants")
            .first()
        )
        if not product:
            return Response(
                {"detail": "Product not found.", "code": "PRODUCT_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

        from inventory.models import InventoryItem

        inv_items = InventoryItem.objects.filter(shop=shop, product=product)
        stock_map = {(item.product_id, item.variant_id): item.available_quantity for item in inv_items}

        serializer = PublicShopProductSerializer(
            product,
            context={"request": request, "stock_map": stock_map},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicShopCategoryListView(APIView):
    """
    Public customer-facing endpoint listing active categories for an active Shop.
    """

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        queryset = (
            ShopCategory.objects.filter(shop=shop, is_active=True)
            .select_related("parent")
            .order_by("name", "id")
        )

        parent_param = request.query_params.get("parent")
        if parent_param is not None:
            if parent_param.lower() in ("null", "none", "root"):
                queryset = queryset.filter(parent__isnull=True)
            elif parent_param.isdigit():
                queryset = queryset.filter(parent_id=int(parent_param))

        serializer = PublicCategorySerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicShopBrandListView(APIView):
    """
    Public customer-facing endpoint listing active brands for an active Shop.
    """

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        queryset = ShopBrand.objects.filter(shop=shop, is_active=True).order_by("name", "id")
        serializer = PublicBrandSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicShopCustomAttributeListView(APIView):
    """
    Public customer-facing endpoint listing active custom attributes for an active Shop.
    """

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        queryset = ShopCustomAttribute.objects.filter(shop=shop, is_active=True).order_by("name", "id")
        serializer = PublicCustomAttributeSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicShopCatalogSummaryView(APIView):
    """
    Public customer-facing endpoint returning an integrated overview of the Shop Catalog:
    active categories, active brands, and visible products with stock/availability status.
    """

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        from inventory.models import InventoryItem

        inv_items = InventoryItem.objects.filter(shop=shop)
        stock_map = {(item.product_id, item.variant_id): item.available_quantity for item in inv_items}

        categories = ShopCategory.objects.filter(shop=shop, is_active=True).order_by("name", "id")
        brands = ShopBrand.objects.filter(shop=shop, is_active=True).order_by("name", "id")
        products = (
            ShopProduct.objects.filter(shop=shop, is_visible=True)
            .select_related("brand_ref")
            .prefetch_related("categories", "variants")
            .order_by("name", "id")
        )

        return Response(
            {
                "shop": {
                    "name": shop.name,
                    "public_slug": shop.public_slug,
                    "is_accepting_orders": shop.is_accepting_orders,
                },
                "categories": PublicCategorySerializer(categories, many=True, context={"request": request}).data,
                "brands": PublicBrandSerializer(brands, many=True, context={"request": request}).data,
                "products": PublicShopProductSerializer(
                    products, many=True, context={"request": request, "stock_map": stock_map}
                ).data,
            },
            status=status.HTTP_200_OK,
        )


