from django.urls import path
from rest_framework.routers import SimpleRouter

from orders.merchant_views import MerchantOrderViewSet
from orders.views import PublicCheckoutView, PublicOrderCancelView, PublicOrderDetailView

router = SimpleRouter()
router.register("orders", MerchantOrderViewSet, basename="merchant-order")

urlpatterns = [
    path("shops/public/<slug:public_slug>/orders/", PublicCheckoutView.as_view(), name="public-order-checkout"),
    path("shops/public/<slug:public_slug>/orders/<int:order_id>/", PublicOrderDetailView.as_view(), name="public-order-detail"),
    path("shops/public/<slug:public_slug>/orders/<int:order_id>/cancel/", PublicOrderCancelView.as_view(), name="public-order-cancel"),
] + router.urls

