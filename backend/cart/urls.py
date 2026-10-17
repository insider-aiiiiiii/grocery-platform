from django.urls import path

from .views import CartItemDetailView, CartItemListView, PublicCartDetailView

app_name = "cart"

urlpatterns = [
    path("<int:pk>/", PublicCartDetailView.as_view(), name="cart-detail"),
    path("<int:cart_id>/items/", CartItemListView.as_view(), name="cart-items-list"),
    path("<int:cart_id>/items/<int:item_id>/", CartItemDetailView.as_view(), name="cart-item-detail"),
]
