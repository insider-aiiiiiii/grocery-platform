from django.urls import path

from .views import (
    MerchantShopDeactivationForbiddenView,
    MerchantShopDetailView,
    MerchantShopReactivationForbiddenView,
    PublicShopDetailView,
    ShopCreateView,
    SuperAdminShopDeactivateView,
    SuperAdminShopDeleteView,
    SuperAdminShopReactivateView,
)

app_name = "shops"

urlpatterns = [
    path("", ShopCreateView.as_view(), name="shop-create"),
    path("me/", MerchantShopDetailView.as_view(), name="shop-me"),
    path("me/deactivate/", MerchantShopDeactivationForbiddenView.as_view(), name="shop-me-deactivate"),
    path("deactivate/", MerchantShopDeactivationForbiddenView.as_view(), name="shop-deactivate"),
    path("me/reactivate/", MerchantShopReactivationForbiddenView.as_view(), name="shop-me-reactivate"),
    path("reactivate/", MerchantShopReactivationForbiddenView.as_view(), name="shop-reactivate"),
    path("public/<slug:public_slug>/", PublicShopDetailView.as_view(), name="shop-public-detail"),
    path("<int:pk>/", SuperAdminShopDeleteView.as_view(), name="shop-admin-delete"),
    path("<int:pk>/deactivate/", SuperAdminShopDeactivateView.as_view(), name="shop-admin-deactivate"),
    path("<int:pk>/reactivate/", SuperAdminShopReactivateView.as_view(), name="shop-admin-reactivate"),
    path("<int:pk>/unsuspend/", SuperAdminShopReactivateView.as_view(), name="shop-admin-unsuspend"),
]
