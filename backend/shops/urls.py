from django.urls import path

from .views import ShopCreateView

app_name = "shops"

urlpatterns = [
    path("", ShopCreateView.as_view(), name="shop-create"),
]
