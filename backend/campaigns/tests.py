from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from campaigns.models import Campaign
from shops.models import Shop
from users.models import Merchant, User


class CampaignModelTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username="campaign_merchant",
            email="campaign-merchant@example.com",
            mobile_number="+919876543210",
            role=User.Role.MERCHANT,
        )
        merchant = Merchant.objects.create(user=user)
        self.shop = Shop.objects.create(
            merchant=merchant,
            name="Campaign Shop",
            address_line="1 Market Road",
            area="Market",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=user.mobile_number,
        )

    def test_campaign_defaults_to_draft_and_all_shops(self):
        campaign = Campaign.objects.create(title="Platform Campaign")

        self.assertEqual(campaign.status, Campaign.Status.DRAFT)
        self.assertEqual(campaign.shop_scope, Campaign.ShopScope.ALL_SHOPS)
        self.assertEqual(campaign.content, "")
        self.assertIsNone(campaign.starts_at)
        self.assertIsNone(campaign.ends_at)
        self.assertTrue(timezone.is_aware(campaign.created_at))

    def test_selected_shop_scope_uses_many_to_many_relationship(self):
        campaign = Campaign.objects.create(
            title="Selected Shop Campaign",
            shop_scope=Campaign.ShopScope.SELECTED_SHOPS,
        )
        campaign.selected_shops.add(self.shop)

        self.assertEqual(list(campaign.selected_shops.all()), [self.shop])

    def test_schedule_requires_start_not_after_end(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Campaign.objects.create(
                    title="Invalid Schedule",
                    starts_at=timezone.now(),
                    ends_at=timezone.now() - timedelta(days=1),
                )

    def test_invalid_status_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Campaign.objects.create(
                    title="Invalid Status Campaign",
                    status="INVALID",
                )

    def test_invalid_shop_scope_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Campaign.objects.create(
                    title="Invalid Shop Scope Campaign",
                    shop_scope="INVALID",
                )
