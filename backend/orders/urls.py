from django.urls import path
from rest_framework.routers import SimpleRouter

from orders.merchant_views import MerchantOrderViewSet
from orders.views import PublicCheckoutView

router = SimpleRouter()
router.register("orders", MerchantOrderViewSet, basename="merchant-order")

urlpatterns = [
    path("shops/public/<slug:public_slug>/orders/", PublicCheckoutView.as_view(), name="public-order-checkout"),
] + router.urls
