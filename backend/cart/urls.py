from django.urls import path

from .views import PublicCartDetailView

app_name = "cart"

urlpatterns = [
    path("<int:pk>/", PublicCartDetailView.as_view(), name="cart-detail"),
]
