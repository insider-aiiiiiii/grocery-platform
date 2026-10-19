from django.urls import path

from orders.views import PublicCheckoutView

urlpatterns = [
    path("shops/public/<slug:public_slug>/orders/", PublicCheckoutView.as_view(), name="public-order-checkout"),
]
