from django.urls import path

from .views import PublicCustomerCreateOrRecognizeView, PublicCustomerRecognizeView

app_name = "customers"

urlpatterns = [
    path("public/<slug:public_slug>/customer/", PublicCustomerCreateOrRecognizeView.as_view(), name="public-customer-create-recognize"),
    path("public/<slug:public_slug>/customer/recognize/", PublicCustomerRecognizeView.as_view(), name="public-customer-recognize"),
    path("public/<slug:public_slug>/customers/", PublicCustomerCreateOrRecognizeView.as_view(), name="public-customers-create-recognize"),
]
