from rest_framework import serializers

from campaigns.models import Campaign
from shops.models import Shop


class CampaignSerializer(serializers.ModelSerializer):
    selected_shops = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Shop.objects.all(),
        required=False,
    )

    class Meta:
        model = Campaign
        fields = [
            "id",
            "title",
            "content",
            "status",
            "shop_scope",
            "selected_shops",
            "starts_at",
            "ends_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def validate_title(self, value):
        title = value.strip()
        if not title:
            raise serializers.ValidationError(
                "Title cannot be empty or whitespace only."
            )
        return title

    def validate(self, attrs):
        instance = self.instance

        shop_scope = attrs.get(
            "shop_scope",
            instance.shop_scope if instance else Campaign.ShopScope.ALL_SHOPS,
        )
        selected_shops = attrs.get(
            "selected_shops",
            instance.selected_shops.all() if instance else [],
        )

        if (
            shop_scope == Campaign.ShopScope.SELECTED_SHOPS
            and not selected_shops
        ):
            raise serializers.ValidationError(
                {
                    "selected_shops": (
                        "At least one Shop is required for selected-Shop scope."
                    )
                }
            )

        starts_at = attrs.get(
            "starts_at",
            instance.starts_at if instance else None,
        )
        ends_at = attrs.get(
            "ends_at",
            instance.ends_at if instance else None,
        )

        if starts_at is not None and ends_at is not None and starts_at > ends_at:
            raise serializers.ValidationError(
                {"ends_at": "End time must be at or after the start time."}
            )

        return attrs
