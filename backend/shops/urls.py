from django.urls import path

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

app_name = "shops"

urlpatterns = [
    path("", ShopCreateView.as_view(), name="shop-create"),
    path("me/", MerchantShopDetailView.as_view(), name="shop-me"),
    path("me/qr/", MerchantShopQRDetailView.as_view(), name="shop-me-qr"),
    path("me/deactivate/", MerchantShopDeactivationForbiddenView.as_view(), name="shop-me-deactivate"),
    path("deactivate/", MerchantShopDeactivationForbiddenView.as_view(), name="shop-deactivate"),
    path("me/reactivate/", MerchantShopReactivationForbiddenView.as_view(), name="shop-me-reactivate"),
    path("reactivate/", MerchantShopReactivationForbiddenView.as_view(), name="shop-reactivate"),
    path("me/regenerate-qr/", MerchantShopQRRegenerationForbiddenView.as_view(), name="shop-me-regenerate-qr"),
    path("regenerate-qr/", MerchantShopQRRegenerationForbiddenView.as_view(), name="shop-regenerate-qr"),
    path("public/<slug:public_slug>/", PublicShopDetailView.as_view(), name="shop-public-detail"),
    path("<int:pk>/", SuperAdminShopDeleteView.as_view(), name="shop-admin-delete"),
    path("<int:pk>/deactivate/", SuperAdminShopDeactivateView.as_view(), name="shop-admin-deactivate"),
    path("<int:pk>/reactivate/", SuperAdminShopReactivateView.as_view(), name="shop-admin-reactivate"),
    path("<int:pk>/unsuspend/", SuperAdminShopReactivateView.as_view(), name="shop-admin-unsuspend"),
    path("<int:pk>/regenerate-qr/", SuperAdminShopRegenerateQRView.as_view(), name="shop-admin-regenerate-qr"),
    path("<int:pk>/regenerate-link/", SuperAdminShopRegenerateQRView.as_view(), name="shop-admin-regenerate-link"),
]
