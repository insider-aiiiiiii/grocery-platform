from django.urls import include, path
from catalog.views import (
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
)

from .views import (
    MerchantShopDeactivationForbiddenView,
    MerchantShopDetailView,
    MerchantShopQRDetailView,
    MerchantShopQRRegenerationForbiddenView,
    MerchantShopReactivationForbiddenView,
    PublicShopDetailView,
    ShopCreateView,
    SuperAdminShopDeactivateView,
    SuperAdminShopDeleteView,
    SuperAdminShopReactivateView,
    SuperAdminShopRegenerateQRView,
)
from customers.views import (
    MerchantCustomerViewSet,
    PublicCustomerCreateOrRecognizeView,
    PublicCustomerRecognizeView,
)
from cart.views import (
    CartItemDetailView,
    CartItemListView,
    PublicShopCartDetailView,
    PublicShopCartView,
)

app_name = "shops"

urlpatterns = [
    path("", ShopCreateView.as_view(), name="shop-create"),
    path("me/", MerchantShopDetailView.as_view(), name="shop-me"),
    path("me/qr/", MerchantShopQRDetailView.as_view(), name="shop-me-qr"),
    path("me/products/", MerchantShopProductViewSet.as_view({"get": "list", "post": "create"}), name="shop-me-products-list"),
    path("me/products/<int:pk>/", MerchantShopProductViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="shop-me-products-detail"),
    path("me/categories/", MerchantShopCategoryViewSet.as_view({"get": "list", "post": "create"}), name="shop-me-categories-list"),
    path("me/categories/<int:pk>/", MerchantShopCategoryViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="shop-me-categories-detail"),
    path("me/brands/", MerchantShopBrandViewSet.as_view({"get": "list", "post": "create"}), name="shop-me-brands-list"),
    path("me/brands/<int:pk>/", MerchantShopBrandViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="shop-me-brands-detail"),
    path("me/custom-attributes/", MerchantShopCustomAttributeViewSet.as_view({"get": "list", "post": "create"}), name="shop-me-custom-attributes-list"),
    path("me/custom-attributes/<int:pk>/", MerchantShopCustomAttributeViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="shop-me-custom-attributes-detail"),
    path("me/inventory/", include("inventory.urls")),
    path("me/customers/", MerchantCustomerViewSet.as_view({"get": "list"}), name="shop-me-customers-list"),
    path("me/customers/<int:pk>/", MerchantCustomerViewSet.as_view({"get": "retrieve"}), name="shop-me-customers-detail"),


    path("me/deactivate/", MerchantShopDeactivationForbiddenView.as_view(), name="shop-me-deactivate"),
    path("deactivate/", MerchantShopDeactivationForbiddenView.as_view(), name="shop-deactivate"),
    path("me/reactivate/", MerchantShopReactivationForbiddenView.as_view(), name="shop-me-reactivate"),
    path("reactivate/", MerchantShopReactivationForbiddenView.as_view(), name="shop-reactivate"),
    path("me/regenerate-qr/", MerchantShopQRRegenerationForbiddenView.as_view(), name="shop-me-regenerate-qr"),
    path("regenerate-qr/", MerchantShopQRRegenerationForbiddenView.as_view(), name="shop-regenerate-qr"),
    path("public/<slug:public_slug>/", PublicShopDetailView.as_view(), name="shop-public-detail"),
    path("public/<slug:public_slug>/catalog/", PublicShopCatalogSummaryView.as_view(), name="shop-public-catalog"),
    path("public/<slug:public_slug>/products/", PublicShopProductListView.as_view(), name="shop-public-products-list"),
    path("public/<slug:public_slug>/products/<int:pk>/", PublicShopProductDetailView.as_view(), name="shop-public-products-detail"),
    path("public/<slug:public_slug>/categories/", PublicShopCategoryListView.as_view(), name="shop-public-categories-list"),
    path("public/<slug:public_slug>/brands/", PublicShopBrandListView.as_view(), name="shop-public-brands-list"),
    path("public/<slug:public_slug>/custom-attributes/", PublicShopCustomAttributeListView.as_view(), name="shop-public-custom-attributes-list"),
    path("public/<slug:public_slug>/attributes/", PublicShopCustomAttributeListView.as_view(), name="shop-public-attributes-list"),
    path("public/<slug:public_slug>/customer/", PublicCustomerCreateOrRecognizeView.as_view(), name="shop-public-customer"),
    path("public/<slug:public_slug>/customer/recognize/", PublicCustomerRecognizeView.as_view(), name="shop-public-customer-recognize"),
    path("public/<slug:public_slug>/customers/", PublicCustomerCreateOrRecognizeView.as_view(), name="shop-public-customers"),
    path("public/<slug:public_slug>/cart/", PublicShopCartView.as_view(), name="shop-public-cart"),
    path("public/<slug:public_slug>/cart/<int:pk>/", PublicShopCartDetailView.as_view(), name="shop-public-cart-detail"),
    path("public/<slug:public_slug>/cart/<int:cart_id>/items/", CartItemListView.as_view(), name="shop-public-cart-items-list"),
    path("public/<slug:public_slug>/cart/<int:cart_id>/items/<int:item_id>/", CartItemDetailView.as_view(), name="shop-public-cart-item-detail"),
    path("public/<slug:public_slug>/cart/items/", CartItemListView.as_view(), name="shop-public-cart-items-query"),
    path("<int:pk>/", SuperAdminShopDeleteView.as_view(), name="shop-admin-delete"),
    path("<int:pk>/deactivate/", SuperAdminShopDeactivateView.as_view(), name="shop-admin-deactivate"),
    path("<int:pk>/reactivate/", SuperAdminShopReactivateView.as_view(), name="shop-admin-reactivate"),
    path("<int:pk>/unsuspend/", SuperAdminShopReactivateView.as_view(), name="shop-admin-unsuspend"),
    path("<int:pk>/regenerate-qr/", SuperAdminShopRegenerateQRView.as_view(), name="shop-admin-regenerate-qr"),
    path("<int:pk>/regenerate-link/", SuperAdminShopRegenerateQRView.as_view(), name="shop-admin-regenerate-link"),
]
