from django.urls import path

from .views import (
    CartCustomerAssociateView,
    CartItemDetailView,
    CartItemListView,
    PublicCartDetailView,
    PublicCartValidateView,
)

app_name = "cart"

urlpatterns = [
    path("<int:pk>/", PublicCartDetailView.as_view(), name="cart-detail"),
    path("<int:cart_id>/items/", CartItemListView.as_view(), name="cart-items-list"),
    path("<int:cart_id>/items/<int:item_id>/", CartItemDetailView.as_view(), name="cart-item-detail"),
    path("<int:cart_id>/validate/", PublicCartValidateView.as_view(), name="cart-validate"),
    path("<int:cart_id>/customer/", CartCustomerAssociateView.as_view(), name="cart-customer-associate"),
]
