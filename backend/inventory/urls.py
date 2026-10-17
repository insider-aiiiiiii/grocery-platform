from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MerchantInventoryViewSet

app_name = "inventory"

router = DefaultRouter()
router.register(r"", MerchantInventoryViewSet, basename="merchant-inventory")

urlpatterns = [
    path("", include(router.urls)),
]
