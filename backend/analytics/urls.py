from django.urls import path

from analytics.views import (
    MerchantAnalyticsLowStockView,
    MerchantAnalyticsOverviewView,
    MerchantAnalyticsTopProductsView,
    PlatformAnalyticsOverviewView,
    PlatformAnalyticsTopProductsView,
    PlatformAnalyticsTopShopsView,
)

app_name = "analytics"

urlpatterns = [
    # Merchant Shop-Scoped Analytics
    path("", MerchantAnalyticsOverviewView.as_view(), name="merchant-analytics-overview"),
    path("top-products/", MerchantAnalyticsTopProductsView.as_view(), name="merchant-analytics-top-products"),
    path("low-stock/", MerchantAnalyticsLowStockView.as_view(), name="merchant-analytics-low-stock"),

    # Super Admin Platform-Wide Analytics
    path("platform/", PlatformAnalyticsOverviewView.as_view(), name="platform-analytics-overview"),
    path("platform/overview/", PlatformAnalyticsOverviewView.as_view(), name="platform-analytics-overview-alias"),
    path("platform/top-products/", PlatformAnalyticsTopProductsView.as_view(), name="platform-analytics-top-products"),
    path("platform/top-shops/", PlatformAnalyticsTopShopsView.as_view(), name="platform-analytics-top-shops"),
]

