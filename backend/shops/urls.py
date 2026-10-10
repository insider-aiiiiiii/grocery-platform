from django.urls import path

from .views import MerchantShopDetailView, ShopCreateView

app_name = "shops"

urlpatterns = [
    path("", ShopCreateView.as_view(), name="shop-create"),
    path("me/", MerchantShopDetailView.as_view(), name="shop-me"),
]
