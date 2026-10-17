from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MasterProductViewSet,
    MerchantShopBrandViewSet,
    MerchantShopCategoryViewSet,
    MerchantShopCustomAttributeViewSet,
    MerchantShopProductViewSet,
    PublicShopBrandListView,
    PublicShopCatalogSummaryView,
    PublicShopCategoryListView,
    PublicShopCustomAttributeListView,
    PublicShopProductDetailView,
    PublicShopProductListView,
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
    path("public/<slug:public_slug>/catalog/", PublicShopCatalogSummaryView.as_view(), name="public-shop-catalog"),
    path("public/<slug:public_slug>/products/", PublicShopProductListView.as_view(), name="public-shop-products-list"),
    path("public/<slug:public_slug>/products/<int:pk>/", PublicShopProductDetailView.as_view(), name="public-shop-products-detail"),
    path("public/<slug:public_slug>/categories/", PublicShopCategoryListView.as_view(), name="public-shop-categories-list"),
    path("public/<slug:public_slug>/brands/", PublicShopBrandListView.as_view(), name="public-shop-brands-list"),
    path("public/<slug:public_slug>/custom-attributes/", PublicShopCustomAttributeListView.as_view(), name="public-shop-custom-attributes-list"),
    path("public/<slug:public_slug>/attributes/", PublicShopCustomAttributeListView.as_view(), name="public-shop-attributes-list"),
    path("", include(router.urls)),
]
