from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MasterProductViewSet

app_name = "catalog"

router = DefaultRouter()
router.register(r"master-products", MasterProductViewSet, basename="master-product")
router.register(r"master-catalog/products", MasterProductViewSet, basename="master-catalog-product")

# Direct router for /api/v1/master-products/ alias
direct_router = DefaultRouter()
direct_router.register(r"", MasterProductViewSet, basename="master-product-direct")

urlpatterns = [
    path("", include(router.urls)),
]
