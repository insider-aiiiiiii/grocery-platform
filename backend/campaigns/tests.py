from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign
from campaigns.serializers import CampaignSerializer
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


class CampaignSerializerTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username="serializer_merchant",
            email="serializer-merchant@example.com",
            mobile_number="+919876543211",
            role=User.Role.MERCHANT,
        )
        merchant = Merchant.objects.create(user=user)
        self.shop = Shop.objects.create(
            merchant=merchant,
            name="Serializer Test Shop",
            address_line="2 Market Road",
            area="Market",
            city="Pune",
            state="Maharashtra",
            pincode="411002",
            contact_number=user.mobile_number,
        )

    def test_rejects_whitespace_only_title(self):
        serializer = CampaignSerializer(data={"title": "   "})

        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_selected_shop_scope_requires_a_shop(self):
        serializer = CampaignSerializer(
            data={
                "title": "Selected Shop Campaign",
                "shop_scope": Campaign.ShopScope.SELECTED_SHOPS,
                "selected_shops": [],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("selected_shops", serializer.errors)

    def test_selected_shop_scope_accepts_a_valid_shop(self):
        serializer = CampaignSerializer(
            data={
                "title": "Selected Shop Campaign",
                "shop_scope": Campaign.ShopScope.SELECTED_SHOPS,
                "selected_shops": [self.shop.pk],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_partial_update_rejects_end_time_before_existing_start(self):
        now = timezone.now()
        campaign = Campaign.objects.create(
            title="Scheduled Campaign",
            starts_at=now + timedelta(hours=1),
            ends_at=now + timedelta(hours=2),
        )
        serializer = CampaignSerializer(
            campaign,
            data={"ends_at": now.isoformat()},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("ends_at", serializer.errors)

    def test_partial_update_preserves_omitted_fields(self):
        now = timezone.now()
        starts_at = now + timedelta(hours=1)
        ends_at = now + timedelta(hours=2)
        campaign = Campaign.objects.create(
            title="Original Campaign",
            starts_at=starts_at,
            ends_at=ends_at,
        )
        serializer = CampaignSerializer(
            campaign,
            data={"title": "Updated Campaign"},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_campaign = serializer.save()

        self.assertEqual(updated_campaign.title, "Updated Campaign")
        self.assertEqual(updated_campaign.starts_at, starts_at)
        self.assertEqual(updated_campaign.ends_at, ends_at)


class CampaignSuperAdminAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.super_admin = User.objects.create_user(
            username="campaign_test_super_admin",
            mobile_number="+919876543212",
            password="adminpassword123",
            role=User.Role.SUPER_ADMIN,
        )
        self.merchant_user = User.objects.create_user(
            username="campaign_test_merchant",
            mobile_number="+919876543213",
            password="merchantpassword123",
            role=User.Role.MERCHANT,
        )
        merchant = Merchant.objects.create(
            user=self.merchant_user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop = Shop.objects.create(
            merchant=merchant,
            name="API Test Shop",
            address_line="3 Market Road",
            area="Market",
            city="Pune",
            state="Maharashtra",
            pincode="411003",
            contact_number=self.merchant_user.mobile_number,
        )
        self.base_url = "/api/v1/campaigns/"

    def _auth_super_admin(self):
        response = self.client.post(
            reverse("auth-super-admin-login"),
            {
                "identifier": self.super_admin.mobile_number,
                "password": "adminpassword123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    def _auth_merchant(self):
        response = self.client.post(
            reverse("auth-login"),
            {
                "mobile_number": self.merchant_user.mobile_number,
                "password": "merchantpassword123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_merchant_request_is_rejected(self):
        self._auth_merchant()

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_creates_campaign_for_selected_shop(self):
        self._auth_super_admin()
        payload = {
            "title": "Selected Shop Campaign",
            "content": "Campaign for one Shop",
            "shop_scope": Campaign.ShopScope.SELECTED_SHOPS,
            "selected_shops": [self.shop.pk],
        }

        response = self.client.post(self.base_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["shop_scope"],
            Campaign.ShopScope.SELECTED_SHOPS,
        )
        self.assertEqual(response.data["selected_shops"], [self.shop.pk])

        campaign = Campaign.objects.get(pk=response.data["id"])
        self.assertEqual(campaign.status, Campaign.Status.DRAFT)
        self.assertEqual(list(campaign.selected_shops.all()), [self.shop])

    def test_super_admin_can_list_and_retrieve_campaigns(self):
        self._auth_super_admin()
        campaign = Campaign.objects.create(
            title="Campaign for retrieval",
            shop_scope=Campaign.ShopScope.SELECTED_SHOPS,
        )
        campaign.selected_shops.add(self.shop)

        list_response = self.client.get(self.base_url)
        detail_response = self.client.get(f"{self.base_url}{campaign.pk}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["id"], campaign.pk)
        self.assertEqual(
            list_response.data[0]["selected_shops"],
            [self.shop.pk],
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["title"], "Campaign for retrieval")
        self.assertEqual(
            detail_response.data["selected_shops"],
            [self.shop.pk],
        )

    def test_super_admin_can_update_draft_campaign_and_targeting(self):
        self._auth_super_admin()
        campaign = Campaign.objects.create(title="Original Draft")

        response = self.client.patch(
            f"{self.base_url}{campaign.pk}/",
            {
                "title": "Updated Draft",
                "shop_scope": Campaign.ShopScope.SELECTED_SHOPS,
                "selected_shops": [self.shop.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated Draft")
        self.assertEqual(
            response.data["shop_scope"],
            Campaign.ShopScope.SELECTED_SHOPS,
        )
        self.assertEqual(response.data["selected_shops"], [self.shop.pk])
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.Status.DRAFT)
        self.assertEqual(list(campaign.selected_shops.all()), [self.shop])

    def test_super_admin_can_delete_draft_campaign(self):
        self._auth_super_admin()
        campaign = Campaign.objects.create(title="Draft to delete")

        response = self.client.delete(f"{self.base_url}{campaign.pk}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Campaign.objects.filter(pk=campaign.pk).exists())

    def test_campaign_creation_rejects_unknown_shop_id(self):
        self._auth_super_admin()

        response = self.client.post(
            self.base_url,
            {
                "title": "Unknown Shop Campaign",
                "shop_scope": Campaign.ShopScope.SELECTED_SHOPS,
                "selected_shops": [self.shop.pk + 9999],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("selected_shops", response.data)

    def test_super_admin_can_activate_draft_campaign(self):
        self._auth_super_admin()
        campaign = Campaign.objects.create(title="Draft Campaign")

        response = self.client.post(
            f"{self.base_url}{campaign.pk}/activate/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.Status.ACTIVE)

    def test_draft_campaign_past_end_time_cannot_be_activated(self):
        self._auth_super_admin()
        campaign = Campaign.objects.create(
            title="Expired Draft Campaign",
            ends_at=timezone.now() - timedelta(seconds=1),
        )

        response = self.client.post(
            f"{self.base_url}{campaign.pk}/activate/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.Status.DRAFT)

    def test_super_admin_can_deactivate_active_campaign_to_draft(self):
        self._auth_super_admin()
        campaign = Campaign.objects.create(
            title="Active Campaign",
            status=Campaign.Status.ACTIVE,
        )

        response = self.client.post(
            f"{self.base_url}{campaign.pk}/deactivate/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.Status.DRAFT)

    def test_ended_campaign_cannot_be_activated(self):
        self._auth_super_admin()
        campaign = Campaign.objects.create(
            title="Ended Campaign",
            status=Campaign.Status.ENDED,
        )

        response = self.client.post(
            f"{self.base_url}{campaign.pk}/activate/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.Status.ENDED)

    def test_expired_active_campaign_transitions_to_ended_on_request(self):
        self._auth_super_admin()
        campaign = Campaign.objects.create(
            title="Expired Campaign",
            status=Campaign.Status.ACTIVE,
            ends_at=timezone.now() - timedelta(seconds=1),
        )

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, Campaign.Status.ENDED)

    def test_active_campaign_cannot_be_edited_or_deleted(self):
        self._auth_super_admin()
        campaign = Campaign.objects.create(
            title="Active Campaign",
            status=Campaign.Status.ACTIVE,
        )

        update_response = self.client.patch(
            f"{self.base_url}{campaign.pk}/",
            {"title": "Modified Campaign"},
            format="json",
        )
        delete_response = self.client.delete(f"{self.base_url}{campaign.pk}/")

        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(delete_response.status_code, status.HTTP_400_BAD_REQUEST)
        campaign.refresh_from_db()
        self.assertEqual(campaign.title, "Active Campaign")
        self.assertEqual(campaign.status, Campaign.Status.ACTIVE)
        self.assertTrue(Campaign.objects.filter(pk=campaign.pk).exists())


class PublicShopCampaignAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create merchants and shops
        user_a = User.objects.create_user(
            username="public_camp_merch_a",
            email="camp_merch_a@example.com",
            mobile_number="+919876543220",
            role=User.Role.MERCHANT,
        )
        merchant_a = Merchant.objects.create(user=user_a)
        self.shop_a = Shop.objects.create(
            merchant=merchant_a,
            name="Alpha Fresh Grocery",
            address_line="10 Alpha St",
            area="North",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=user_a.mobile_number,
            public_slug="slug-alpha-shop",
            status=Shop.Status.ACTIVE,
        )

        user_b = User.objects.create_user(
            username="public_camp_merch_b",
            email="camp_merch_b@example.com",
            mobile_number="+919876543221",
            role=User.Role.MERCHANT,
        )
        merchant_b = Merchant.objects.create(user=user_b)
        self.shop_b = Shop.objects.create(
            merchant=merchant_b,
            name="Beta Daily Mart",
            address_line="20 Beta Ave",
            area="South",
            city="Pune",
            state="Maharashtra",
            pincode="411002",
            contact_number=user_b.mobile_number,
            public_slug="slug-beta-shop",
            status=Shop.Status.ACTIVE,
        )

        user_deact = User.objects.create_user(
            username="public_camp_merch_deact",
            email="camp_merch_deact@example.com",
            mobile_number="+919876543222",
            role=User.Role.MERCHANT,
        )
        merchant_deact = Merchant.objects.create(user=user_deact)
        self.shop_deactivated = Shop.objects.create(
            merchant=merchant_deact,
            name="Deactivated Mart",
            address_line="30 Deact Lane",
            area="West",
            city="Pune",
            state="Maharashtra",
            pincode="411003",
            contact_number=user_deact.mobile_number,
            public_slug="slug-deact-shop",
            status=Shop.Status.DEACTIVATED,
        )

        user_susp = User.objects.create_user(
            username="public_camp_merch_susp",
            email="camp_merch_susp@example.com",
            mobile_number="+919876543223",
            role=User.Role.MERCHANT,
        )
        merchant_susp = Merchant.objects.create(user=user_susp)
        self.shop_suspended = Shop.objects.create(
            merchant=merchant_susp,
            name="Suspended Mart",
            address_line="40 Susp Rd",
            area="East",
            city="Pune",
            state="Maharashtra",
            pincode="411004",
            contact_number=user_susp.mobile_number,
            public_slug="slug-susp-shop",
            status=Shop.Status.SUSPENDED,
        )

        user_closed = User.objects.create_user(
            username="public_camp_merch_closed",
            email="camp_merch_closed@example.com",
            mobile_number="+919876543224",
            role=User.Role.MERCHANT,
        )
        merchant_closed = Merchant.objects.create(user=user_closed)
        self.shop_closed = Shop.objects.create(
            merchant=merchant_closed,
            name="Closed Mart",
            address_line="50 Closed Blvd",
            area="Central",
            city="Pune",
            state="Maharashtra",
            pincode="411005",
            contact_number=user_closed.mobile_number,
            public_slug="slug-closed-shop",
            status=Shop.Status.ACTIVE,
            is_temporarily_closed=True,
        )

    def test_public_unauthenticated_access_allowed(self):
        url = f"/api/v1/shops/public/{self.shop_a.public_slug}/campaigns/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_shop_not_found_returns_404(self):
        url = "/api/v1/shops/public/non-existent-shop-slug/campaigns/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "SHOP_NOT_FOUND")

    def test_deactivated_shop_returns_404_unavailable(self):
        url = f"/api/v1/shops/public/{self.shop_deactivated.public_slug}/campaigns/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "SHOP_UNAVAILABLE")

    def test_suspended_shop_returns_404_unavailable(self):
        url = f"/api/v1/shops/public/{self.shop_suspended.public_slug}/campaigns/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "SHOP_UNAVAILABLE")

    def test_temporarily_closed_shop_returns_applicable_campaigns(self):
        Campaign.objects.create(
            title="Monsoon Sale",
            content="Great discounts for everyone",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )
        url = f"/api/v1/shops/public/{self.shop_closed.public_slug}/campaigns/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Monsoon Sale")

    def test_returns_all_shops_active_campaigns(self):
        camp = Campaign.objects.create(
            title="Platform Mega Deal",
            content="Available across all stores",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )

        res_a = self.client.get(f"/api/v1/shops/public/{self.shop_a.public_slug}/campaigns/")
        res_b = self.client.get(f"/api/v1/shops/public/{self.shop_b.public_slug}/campaigns/")

        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_a.data), 1)
        self.assertEqual(len(res_b.data), 1)
        self.assertEqual(res_a.data[0]["id"], camp.id)
        self.assertEqual(res_b.data[0]["id"], camp.id)

    def test_returns_selected_shops_campaign_only_for_included_shop(self):
        camp = Campaign.objects.create(
            title="Alpha Exclusive Offer",
            content="Only at Alpha Fresh Grocery",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.SELECTED_SHOPS,
        )
        camp.selected_shops.add(self.shop_a)

        res_a = self.client.get(f"/api/v1/shops/public/{self.shop_a.public_slug}/campaigns/")
        res_b = self.client.get(f"/api/v1/shops/public/{self.shop_b.public_slug}/campaigns/")

        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_a.data), 1)
        self.assertEqual(res_a.data[0]["id"], camp.id)
        self.assertEqual(len(res_b.data), 0)

    def test_draft_and_ended_campaigns_are_not_returned(self):
        Campaign.objects.create(
            title="Draft Campaign",
            status=Campaign.Status.DRAFT,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )
        Campaign.objects.create(
            title="Ended Campaign",
            status=Campaign.Status.ENDED,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )

        res = self.client.get(f"/api/v1/shops/public/{self.shop_a.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_future_scheduled_campaign_not_returned(self):
        now = timezone.now()
        Campaign.objects.create(
            title="Upcoming Diwali Fest",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=5),
        )

        res = self.client.get(f"/api/v1/shops/public/{self.shop_a.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_expired_campaign_not_returned_and_transitions_to_ended(self):
        now = timezone.now()
        camp = Campaign.objects.create(
            title="Past Flash Sale",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
            ends_at=now - timedelta(seconds=5),
        )

        res = self.client.get(f"/api/v1/shops/public/{self.shop_a.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.ENDED)

    def test_active_scheduled_campaign_in_range_is_returned(self):
        now = timezone.now()
        camp = Campaign.objects.create(
            title="Active Weekend Promo",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
            starts_at=now - timedelta(hours=2),
            ends_at=now + timedelta(hours=2),
        )

        res = self.client.get(f"/api/v1/shops/public/{self.shop_a.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], camp.id)

    def test_endpoint_parity_between_shops_and_campaigns_routes(self):
        camp = Campaign.objects.create(
            title="Dual Route Promo",
            content="Check both endpoints",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )

        url_shop = f"/api/v1/shops/public/{self.shop_a.public_slug}/campaigns/"
        url_camp = f"/api/v1/campaigns/public/{self.shop_a.public_slug}/"

        res_shop = self.client.get(url_shop)
        res_camp = self.client.get(url_camp)

        self.assertEqual(res_shop.status_code, status.HTTP_200_OK)
        self.assertEqual(res_camp.status_code, status.HTTP_200_OK)
        self.assertEqual(res_shop.data, res_camp.data)
        self.assertEqual(res_shop.data[0]["id"], camp.id)

    def test_payload_structure_and_isolation_no_leakage(self):
        now = timezone.now()
        camp = Campaign.objects.create(
            title="Isolated Campaign",
            content="Strict public schema",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.SELECTED_SHOPS,
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=3),
        )
        camp.selected_shops.add(self.shop_a, self.shop_b)

        res = self.client.get(f"/api/v1/shops/public/{self.shop_a.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

        item = res.data[0]
        self.assertEqual(
            set(item.keys()),
            {"id", "title", "content", "status", "starts_at", "ends_at"},
        )
        self.assertEqual(item["id"], camp.id)
        self.assertEqual(item["title"], "Isolated Campaign")
        self.assertEqual(item["content"], "Strict public schema")
        self.assertEqual(item["status"], "ACTIVE")
        self.assertNotIn("selected_shops", item)
        self.assertNotIn("shop_scope", item)
        self.assertNotIn("created_at", item)
        self.assertNotIn("updated_at", item)

