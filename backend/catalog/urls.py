from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MasterProductViewSet,
    MerchantShopBrandViewSet,
    MerchantShopCategoryViewSet,
    MerchantShopCustomAttributeViewSet,
    MerchantShopProductViewSet,
    SuperAdminPromoteShopProductView,
)

app_name = "catalog"

router = DefaultRouter()
router.register(r"master-products", MasterProductViewSet, basename="master-product")
router.register(r"master-catalog/products", MasterProductViewSet, basename="master-catalog-product")
router.register(r"products", MerchantShopProductViewSet, basename="merchant-product")
router.register(r"shop-products", MerchantShopProductViewSet, basename="merchant-shop-product")
router.register(r"categories", MerchantShopCategoryViewSet, basename="merchant-category")
router.register(r"shop-categories", MerchantShopCategoryViewSet, basename="merchant-shop-category")
router.register(r"brands", MerchantShopBrandViewSet, basename="merchant-brand")
router.register(r"shop-brands", MerchantShopBrandViewSet, basename="merchant-shop-brand")
router.register(r"custom-attributes", MerchantShopCustomAttributeViewSet, basename="merchant-custom-attribute")
router.register(r"attributes", MerchantShopCustomAttributeViewSet, basename="merchant-attribute")

# Direct router for /api/v1/master-products/ alias
direct_router = DefaultRouter()
direct_router.register(r"", MasterProductViewSet, basename="master-product-direct")

urlpatterns = [
    path("shop-products/<int:pk>/promote/", SuperAdminPromoteShopProductView.as_view(), name="shop-product-promote"),
    path("", include(router.urls)),
]
