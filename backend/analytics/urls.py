from django.urls import path

from analytics.views import (
    MerchantAnalyticsLowStockView,
    MerchantAnalyticsOverviewView,
    MerchantAnalyticsTopProductsView,
)

app_name = "analytics"

urlpatterns = [
    path("", MerchantAnalyticsOverviewView.as_view(), name="merchant-analytics-overview"),
    path("top-products/", MerchantAnalyticsTopProductsView.as_view(), name="merchant-analytics-top-products"),
    path("low-stock/", MerchantAnalyticsLowStockView.as_view(), name="merchant-analytics-low-stock"),
]
