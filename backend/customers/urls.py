from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MerchantCustomerViewSet,
    PublicCustomerCreateOrRecognizeView,
    PublicCustomerRecognizeView,
)

app_name = "customers"

router = DefaultRouter()
router.register(r"shop-customers", MerchantCustomerViewSet, basename="merchant-shop-customer")
router.register(r"", MerchantCustomerViewSet, basename="merchant-customer")

urlpatterns = [
    path("public/<slug:public_slug>/customer/", PublicCustomerCreateOrRecognizeView.as_view(), name="public-customer-create-recognize"),
    path("public/<slug:public_slug>/customer/recognize/", PublicCustomerRecognizeView.as_view(), name="public-customer-recognize"),
    path("public/<slug:public_slug>/customers/", PublicCustomerCreateOrRecognizeView.as_view(), name="public-customers-create-recognize"),
    path("", include(router.urls)),
]

