from django.urls import path
from rest_framework.routers import DefaultRouter

from campaigns.views import CampaignViewSet, PublicShopCampaignListView

app_name = "campaigns"

router = DefaultRouter()
router.register("campaigns", CampaignViewSet, basename="campaign")

urlpatterns = [
    path(
        "campaigns/public/<slug:public_slug>/",
        PublicShopCampaignListView.as_view(),
        name="public-shop-campaigns-list",
    ),
] + router.urls

