from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from campaigns.models import Campaign
from campaigns.serializers import CampaignSerializer
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
