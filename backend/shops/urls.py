from django.urls import path

from .views import (
    MerchantShopDeactivationForbiddenView,
    MerchantShopDetailView,
    ShopCreateView,
    SuperAdminShopDeactivateView,
    SuperAdminShopDeleteView,
)

app_name = "shops"

urlpatterns = [
    path("", ShopCreateView.as_view(), name="shop-create"),
    path("me/", MerchantShopDetailView.as_view(), name="shop-me"),
    path("me/deactivate/", MerchantShopDeactivationForbiddenView.as_view(), name="shop-me-deactivate"),
    path("deactivate/", MerchantShopDeactivationForbiddenView.as_view(), name="shop-deactivate"),
    path("<int:pk>/", SuperAdminShopDeleteView.as_view(), name="shop-admin-delete"),
    path("<int:pk>/deactivate/", SuperAdminShopDeactivateView.as_view(), name="shop-admin-deactivate"),
]
