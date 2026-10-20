from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from campaigns.models import Campaign
from campaigns.serializers import CampaignSerializer, PublicCampaignSerializer
from shops.models import Shop
from users.permissions import IsSuperAdmin



class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all().prefetch_related("selected_shops").order_by("id")
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.is_active:
            self.permission_denied(request, message="Super Admin account is inactive.")

        now = timezone.now()
        Campaign.objects.filter(
            status=Campaign.Status.ACTIVE,
            ends_at__lte=now,
        ).update(
            status=Campaign.Status.ENDED,
            updated_at=now,
        )

    def perform_update(self, serializer):
        if serializer.instance.status != Campaign.Status.DRAFT:
            raise serializers.ValidationError(
                "Only Draft campaigns can be edited."
            )
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status != Campaign.Status.DRAFT:
            raise serializers.ValidationError(
                "Only Draft campaigns can be deleted."
            )
        instance.delete()

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        campaign = self.get_object()
        if campaign.status != Campaign.Status.DRAFT:
            raise serializers.ValidationError(
                "Only Draft campaigns can be activated."
            )
        if campaign.ends_at is not None and campaign.ends_at <= timezone.now():
            raise serializers.ValidationError(
                "A campaign cannot be activated after its end time."
            )

        campaign.status = Campaign.Status.ACTIVE
        campaign.save(update_fields=["status", "updated_at"])
        return Response(
            self.get_serializer(campaign).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        campaign = self.get_object()
        if campaign.status != Campaign.Status.ACTIVE:
            raise serializers.ValidationError(
                "Only Active campaigns can be deactivated."
            )

        campaign.status = Campaign.Status.DRAFT
        campaign.save(update_fields=["status", "updated_at"])
        return Response(
            self.get_serializer(campaign).data,
            status=status.HTTP_200_OK,
        )


def get_public_active_shop(public_slug: str):
    """
    Resolve and validate an active Shop by its public_slug for customer-facing requests.
    Returns (shop, error_response).
    """
    shop = Shop.objects.filter(public_slug=public_slug).first()
    if not shop:
        return None, Response(
            {"detail": "Shop not found.", "code": "SHOP_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if shop.status != Shop.Status.ACTIVE:
        return None, Response(
            {"detail": "Shop is unavailable.", "code": "SHOP_UNAVAILABLE"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return shop, None


class PublicShopCampaignListView(APIView):
    """
    Public customer-facing endpoint returning active campaigns applicable to an active Shop.
    A campaign is applicable if:
      - status is ACTIVE
      - current timestamp is within its schedule (starts_at is null or <= now, and ends_at is null or > now)
      - shop_scope is ALL_SHOPS, or SELECTED_SHOPS and the shop is included in selected_shops.
    Expired active campaigns are transitioned to ENDED on request.
    """

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        now = timezone.now()

        # Transition any expired active campaigns to ENDED
        Campaign.objects.filter(
            status=Campaign.Status.ACTIVE,
            ends_at__lte=now,
        ).update(
            status=Campaign.Status.ENDED,
            updated_at=now,
        )

        schedule_filter = (
            (Q(starts_at__isnull=True) | Q(starts_at__lte=now))
            & (Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        )
        scope_filter = (
            Q(shop_scope=Campaign.ShopScope.ALL_SHOPS)
            | (Q(shop_scope=Campaign.ShopScope.SELECTED_SHOPS) & Q(selected_shops=shop))
        )

        campaigns = (
            Campaign.objects.filter(
                Q(status=Campaign.Status.ACTIVE)
                & schedule_filter
                & scope_filter
            )
            .distinct()
            .order_by("id")
        )

        serializer = PublicCampaignSerializer(
            campaigns, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

