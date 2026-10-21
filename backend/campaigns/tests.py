from decimal import Decimal
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from campaigns.models import Campaign
from campaigns.serializers import CampaignSerializer, PublicCampaignSerializer
from cart.models import Cart, CartItem
from catalog.models import ShopProduct
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
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


class CampaignScopeAndTargetingTests(TestCase):
    """
    CAM-006: Comprehensive tests for campaign scope (ALL_SHOPS vs SELECTED_SHOPS),
    shop targeting, dynamic updates, and tenant isolation / non-ownership boundaries.
    """

    def setUp(self):
        self.client = APIClient()
        self.super_admin = User.objects.create_user(
            username="cam006_scope_admin",
            email="cam006_scope_admin@example.com",
            mobile_number="+919876543301",
            role=User.Role.SUPER_ADMIN,
        )

        # Merchant 1 & Shop 1
        user_1 = User.objects.create_user(
            username="cam006_merchant_1",
            email="cam006_merchant_1@example.com",
            mobile_number="+919876543311",
            role=User.Role.MERCHANT,
        )
        self.merchant_1 = Merchant.objects.create(user=user_1)
        self.shop_1 = Shop.objects.create(
            merchant=self.merchant_1,
            name="Shop One",
            address_line="1 Main Road",
            area="North",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=user_1.mobile_number,
            public_slug="cam006-slug-shop-1",
            status=Shop.Status.ACTIVE,
        )

        # Merchant 2 & Shop 2
        user_2 = User.objects.create_user(
            username="cam006_merchant_2",
            email="cam006_merchant_2@example.com",
            mobile_number="+919876543312",
            role=User.Role.MERCHANT,
        )
        self.merchant_2 = Merchant.objects.create(user=user_2)
        self.shop_2 = Shop.objects.create(
            merchant=self.merchant_2,
            name="Shop Two",
            address_line="2 Main Road",
            area="South",
            city="Pune",
            state="Maharashtra",
            pincode="411002",
            contact_number=user_2.mobile_number,
            public_slug="cam006-slug-shop-2",
            status=Shop.Status.ACTIVE,
        )

        # Merchant 3 & Shop 3
        user_3 = User.objects.create_user(
            username="cam006_merchant_3",
            email="cam006_merchant_3@example.com",
            mobile_number="+919876543313",
            role=User.Role.MERCHANT,
        )
        self.merchant_3 = Merchant.objects.create(user=user_3)
        self.shop_3 = Shop.objects.create(
            merchant=self.merchant_3,
            name="Shop Three",
            address_line="3 Main Road",
            area="East",
            city="Pune",
            state="Maharashtra",
            pincode="411003",
            contact_number=user_3.mobile_number,
            public_slug="cam006-slug-shop-3",
            status=Shop.Status.ACTIVE,
        )

    def _auth_super_admin(self):
        self.client.force_authenticate(user=self.super_admin)

    def _auth_merchant(self, merchant_user):
        self.client.force_authenticate(user=merchant_user)

    def test_all_shops_scope_displayed_to_all_active_shops(self):
        camp = Campaign.objects.create(
            title="Global Platform Deal",
            content="Visible on every active storefront",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )

        for shop in [self.shop_1, self.shop_2, self.shop_3]:
            res = self.client.get(f"/api/v1/shops/public/{shop.public_slug}/campaigns/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(len(res.data), 1)
            self.assertEqual(res.data[0]["id"], camp.id)

    def test_all_shops_automatically_covers_newly_onboarded_shop(self):
        camp = Campaign.objects.create(
            title="Standing All-Shop Campaign",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )

        # Onboard a brand new merchant and shop after campaign was created
        new_user = User.objects.create_user(
            username="cam006_merchant_4",
            email="cam006_merchant_4@example.com",
            mobile_number="+919876543314",
            role=User.Role.MERCHANT,
        )
        new_merchant = Merchant.objects.create(user=new_user)
        new_shop = Shop.objects.create(
            merchant=new_merchant,
            name="Shop Four",
            address_line="4 New Road",
            area="West",
            city="Pune",
            state="Maharashtra",
            pincode="411004",
            contact_number=new_user.mobile_number,
            public_slug="cam006-slug-shop-4",
            status=Shop.Status.ACTIVE,
        )

        res = self.client.get(f"/api/v1/shops/public/{new_shop.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], camp.id)

    def test_selected_shops_scope_requires_at_least_one_shop_via_api(self):
        self._auth_super_admin()
        res = self.client.post(
            "/api/v1/campaigns/",
            {
                "title": "Selected Campaign Without Shops",
                "shop_scope": Campaign.ShopScope.SELECTED_SHOPS,
                "selected_shops": [],
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("selected_shops", res.data)

    def test_selected_shops_displayed_only_to_targeted_shops(self):
        camp = Campaign.objects.create(
            title="Targeted 1 and 2 Only",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.SELECTED_SHOPS,
        )
        camp.selected_shops.add(self.shop_1, self.shop_2)

        res_1 = self.client.get(f"/api/v1/shops/public/{self.shop_1.public_slug}/campaigns/")
        res_2 = self.client.get(f"/api/v1/shops/public/{self.shop_2.public_slug}/campaigns/")
        res_3 = self.client.get(f"/api/v1/shops/public/{self.shop_3.public_slug}/campaigns/")

        self.assertEqual(res_1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_1.data), 1)
        self.assertEqual(res_1.data[0]["id"], camp.id)

        self.assertEqual(res_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_2.data), 1)
        self.assertEqual(res_2.data[0]["id"], camp.id)

        self.assertEqual(res_3.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_3.data), 0)

    def test_selected_shops_dynamic_update_reflects_immediately(self):
        self._auth_super_admin()
        create_res = self.client.post(
            "/api/v1/campaigns/",
            {
                "title": "Dynamic Targeting Promo",
                "shop_scope": Campaign.ShopScope.SELECTED_SHOPS,
                "selected_shops": [self.shop_1.id],
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        camp_id = create_res.data["id"]

        # Re-target from Shop 1 to Shop 2 & Shop 3 while in Draft
        patch_res = self.client.patch(
            f"/api/v1/campaigns/{camp_id}/",
            {"selected_shops": [self.shop_2.id, self.shop_3.id]},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)

        # Activate
        act_res = self.client.post(f"/api/v1/campaigns/{camp_id}/activate/")
        self.assertEqual(act_res.status_code, status.HTTP_200_OK)

        # Shop 1 should no longer see it
        res_1 = self.client.get(f"/api/v1/shops/public/{self.shop_1.public_slug}/campaigns/")
        self.assertEqual(res_1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_1.data), 0)

        # Shop 2 & 3 must now see it
        res_2 = self.client.get(f"/api/v1/shops/public/{self.shop_2.public_slug}/campaigns/")
        res_3 = self.client.get(f"/api/v1/shops/public/{self.shop_3.public_slug}/campaigns/")
        self.assertEqual(len(res_2.data), 1)
        self.assertEqual(len(res_3.data), 1)
        self.assertEqual(res_2.data[0]["id"], camp_id)
        self.assertEqual(res_3.data[0]["id"], camp_id)

    def test_shop_inclusion_does_not_grant_merchant_campaign_control(self):
        camp = Campaign.objects.create(
            title="Targeted to Shop 1",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.SELECTED_SHOPS,
        )
        camp.selected_shops.add(self.shop_1)

        # Authenticate as merchant who owns Shop 1
        self._auth_merchant(self.merchant_1.user)

        # Merchant cannot access or manipulate the campaign via Super Admin APIs
        self.assertEqual(self.client.get("/api/v1/campaigns/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(f"/api/v1/campaigns/{camp.id}/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(f"/api/v1/campaigns/{camp.id}/", {"title": "Hacked"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(f"/api/v1/campaigns/{camp.id}/deactivate/").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(f"/api/v1/campaigns/{camp.id}/").status_code, status.HTTP_403_FORBIDDEN)

    def test_public_response_never_leaks_target_shops_or_scope(self):
        camp = Campaign.objects.create(
            title="Privacy Guarded Promo",
            content="Customer copy",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.SELECTED_SHOPS,
        )
        camp.selected_shops.add(self.shop_1, self.shop_2)

        res = self.client.get(f"/api/v1/shops/public/{self.shop_1.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        item = res.data[0]

        # Confirm only approved customer-facing fields are returned
        self.assertEqual(set(item.keys()), {"id", "title", "content", "status", "starts_at", "ends_at"})
        self.assertNotIn("selected_shops", item)
        self.assertNotIn("shop_scope", item)
        self.assertNotIn(str(self.shop_2.id), str(item))

    def test_shop_deletion_does_not_break_campaign_for_remaining_shops(self):
        camp = Campaign.objects.create(
            title="Multi-Target Promo",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.SELECTED_SHOPS,
        )
        camp.selected_shops.add(self.shop_1, self.shop_2)

        # Delete shop 1
        self.shop_1.delete()

        # Campaign persists
        camp.refresh_from_db()
        self.assertTrue(Campaign.objects.filter(id=camp.id).exists())

        # Shop 2 still retrieves the campaign
        res_2 = self.client.get(f"/api/v1/shops/public/{self.shop_2.public_slug}/campaigns/")
        self.assertEqual(res_2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_2.data), 1)
        self.assertEqual(res_2.data[0]["id"], camp.id)


class CampaignActivationAndExpiryLifecycleTests(TestCase):
    """
    CAM-006: Comprehensive lifecycle tests covering state transitions, prohibition of
    reactivating ended campaigns, draft-only edits/deletes, and lazy expiry evaluation.
    """

    def setUp(self):
        self.client = APIClient()
        self.super_admin = User.objects.create_user(
            username="cam006_life_admin",
            email="cam006_life_admin@example.com",
            mobile_number="+919876543320",
            role=User.Role.SUPER_ADMIN,
        )
        merchant_user = User.objects.create_user(
            username="cam006_life_merchant",
            email="cam006_life_merchant@example.com",
            mobile_number="+919876543321",
            role=User.Role.MERCHANT,
        )
        merchant = Merchant.objects.create(user=merchant_user)
        self.shop = Shop.objects.create(
            merchant=merchant,
            name="Lifecycle Shop",
            address_line="5 Life Way",
            area="Center",
            city="Pune",
            state="Maharashtra",
            pincode="411005",
            contact_number=merchant_user.mobile_number,
            public_slug="cam006-slug-life-shop",
            status=Shop.Status.ACTIVE,
        )

    def _auth_super_admin(self):
        self.client.force_authenticate(user=self.super_admin)

    def test_draft_to_active_activation_and_deactivation_cycle(self):
        self._auth_super_admin()
        camp = Campaign.objects.create(title="Lifecycle Cycle Test")

        # Draft -> Active
        act_res = self.client.post(f"/api/v1/campaigns/{camp.id}/activate/")
        self.assertEqual(act_res.status_code, status.HTTP_200_OK)
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.ACTIVE)

        # Active -> Draft (deactivation)
        deact_res = self.client.post(f"/api/v1/campaigns/{camp.id}/deactivate/")
        self.assertEqual(deact_res.status_code, status.HTTP_200_OK)
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.DRAFT)

        # Draft -> Active again
        act2_res = self.client.post(f"/api/v1/campaigns/{camp.id}/activate/")
        self.assertEqual(act2_res.status_code, status.HTTP_200_OK)
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.ACTIVE)

    def test_ended_campaign_cannot_be_reactivated(self):
        self._auth_super_admin()
        camp = Campaign.objects.create(title="Ended Campaign", status=Campaign.Status.ENDED)

        res = self.client.post(f"/api/v1/campaigns/{camp.id}/activate/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.ENDED)

    def test_ended_campaign_cannot_be_deactivated(self):
        self._auth_super_admin()
        camp = Campaign.objects.create(title="Ended Campaign", status=Campaign.Status.ENDED)

        res = self.client.post(f"/api/v1/campaigns/{camp.id}/deactivate/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.ENDED)

    def test_draft_with_expired_end_time_cannot_be_activated(self):
        self._auth_super_admin()
        camp = Campaign.objects.create(
            title="Past Due Draft",
            status=Campaign.Status.DRAFT,
            ends_at=timezone.now() - timedelta(minutes=10),
        )

        res = self.client.post(f"/api/v1/campaigns/{camp.id}/activate/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.DRAFT)

    def test_active_and_ended_campaigns_cannot_be_edited_or_deleted(self):
        self._auth_super_admin()
        active_camp = Campaign.objects.create(title="Active Imm", status=Campaign.Status.ACTIVE)
        ended_camp = Campaign.objects.create(title="Ended Imm", status=Campaign.Status.ENDED)

        # Cannot edit or delete Active
        self.assertEqual(
            self.client.patch(f"/api/v1/campaigns/{active_camp.id}/", {"title": "Edited"}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/campaigns/{active_camp.id}/").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        # Cannot edit or delete Ended
        self.assertEqual(
            self.client.patch(f"/api/v1/campaigns/{ended_camp.id}/", {"title": "Edited"}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/campaigns/{ended_camp.id}/").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_expired_campaign_transitions_to_ended_on_super_admin_request(self):
        self._auth_super_admin()
        now = timezone.now()
        camp = Campaign.objects.create(
            title="Expiring Admin Campaign",
            status=Campaign.Status.ACTIVE,
            ends_at=now - timedelta(seconds=1),
        )

        res = self.client.get("/api/v1/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.ENDED)

    def test_expired_campaign_transitions_to_ended_on_public_shop_request(self):
        now = timezone.now()
        camp = Campaign.objects.create(
            title="Expiring Public Campaign",
            status=Campaign.Status.ACTIVE,
            ends_at=now - timedelta(seconds=1),
        )

        res = self.client.get(f"/api/v1/shops/public/{self.shop.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.ENDED)

    def test_null_end_time_campaign_remains_active_indefinitely(self):
        camp = Campaign.objects.create(
            title="Evergreen Campaign",
            status=Campaign.Status.ACTIVE,
            ends_at=None,
        )

        res = self.client.get(f"/api/v1/shops/public/{self.shop.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.ACTIVE)


class CampaignVisibilityAndSchedulingTests(TestCase):
    """
    CAM-006: Comprehensive tests for campaign visibility across all schedule combinations
    and shop lifecycle states.
    """

    def setUp(self):
        self.client = APIClient()
        user = User.objects.create_user(
            username="cam006_vis_merchant",
            email="cam006_vis_merchant@example.com",
            mobile_number="+919876543331",
            role=User.Role.MERCHANT,
        )
        merchant = Merchant.objects.create(user=user)
        self.shop_active = Shop.objects.create(
            merchant=merchant,
            name="Vis Active Shop",
            address_line="6 Vis Rd",
            area="VisArea",
            city="Pune",
            state="Maharashtra",
            pincode="411006",
            contact_number=user.mobile_number,
            public_slug="cam006-slug-vis-active",
            status=Shop.Status.ACTIVE,
        )

        user_closed = User.objects.create_user(
            username="cam006_vis_closed",
            email="cam006_vis_closed@example.com",
            mobile_number="+919876543332",
            role=User.Role.MERCHANT,
        )
        merchant_closed = Merchant.objects.create(user=user_closed)
        self.shop_closed = Shop.objects.create(
            merchant=merchant_closed,
            name="Vis Closed Shop",
            address_line="7 Vis Rd",
            area="VisArea",
            city="Pune",
            state="Maharashtra",
            pincode="411007",
            contact_number=user_closed.mobile_number,
            public_slug="cam006-slug-vis-closed",
            status=Shop.Status.ACTIVE,
            is_temporarily_closed=True,
        )

        user_deact = User.objects.create_user(
            username="cam006_vis_deact",
            email="cam006_vis_deact@example.com",
            mobile_number="+919876543333",
            role=User.Role.MERCHANT,
        )
        merchant_deact = Merchant.objects.create(user=user_deact)
        self.shop_deact = Shop.objects.create(
            merchant=merchant_deact,
            name="Vis Deact Shop",
            address_line="8 Vis Rd",
            area="VisArea",
            city="Pune",
            state="Maharashtra",
            pincode="411008",
            contact_number=user_deact.mobile_number,
            public_slug="cam006-slug-vis-deact",
            status=Shop.Status.DEACTIVATED,
        )

        user_susp = User.objects.create_user(
            username="cam006_vis_susp",
            email="cam006_vis_susp@example.com",
            mobile_number="+919876543334",
            role=User.Role.MERCHANT,
        )
        merchant_susp = Merchant.objects.create(user=user_susp)
        self.shop_susp = Shop.objects.create(
            merchant=merchant_susp,
            name="Vis Susp Shop",
            address_line="9 Vis Rd",
            area="VisArea",
            city="Pune",
            state="Maharashtra",
            pincode="411009",
            contact_number=user_susp.mobile_number,
            public_slug="cam006-slug-vis-susp",
            status=Shop.Status.SUSPENDED,
        )

    def test_visibility_matrix_unbounded_schedule(self):
        camp = Campaign.objects.create(
            title="Unbounded Promo",
            status=Campaign.Status.ACTIVE,
            starts_at=None,
            ends_at=None,
        )
        res = self.client.get(f"/api/v1/shops/public/{self.shop_active.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], camp.id)

    def test_visibility_matrix_future_starts_at_is_hidden(self):
        now = timezone.now()
        Campaign.objects.create(
            title="Future Starts At",
            status=Campaign.Status.ACTIVE,
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=5),
        )
        res = self.client.get(f"/api/v1/shops/public/{self.shop_active.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_visibility_matrix_past_starts_at_with_null_end_is_visible(self):
        now = timezone.now()
        camp = Campaign.objects.create(
            title="Started In Past No End",
            status=Campaign.Status.ACTIVE,
            starts_at=now - timedelta(days=2),
            ends_at=None,
        )
        res = self.client.get(f"/api/v1/shops/public/{self.shop_active.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], camp.id)

    def test_visibility_matrix_within_active_window_is_visible(self):
        now = timezone.now()
        camp = Campaign.objects.create(
            title="In Active Window",
            status=Campaign.Status.ACTIVE,
            starts_at=now - timedelta(hours=3),
            ends_at=now + timedelta(hours=3),
        )
        res = self.client.get(f"/api/v1/shops/public/{self.shop_active.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], camp.id)

    def test_visibility_matrix_past_ends_at_is_hidden_and_ended(self):
        now = timezone.now()
        camp = Campaign.objects.create(
            title="Past End Time",
            status=Campaign.Status.ACTIVE,
            starts_at=now - timedelta(days=3),
            ends_at=now - timedelta(hours=1),
        )
        res = self.client.get(f"/api/v1/shops/public/{self.shop_active.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])
        camp.refresh_from_db()
        self.assertEqual(camp.status, Campaign.Status.ENDED)

    def test_visibility_matrix_draft_and_ended_always_hidden(self):
        Campaign.objects.create(title="Draft Hidden", status=Campaign.Status.DRAFT)
        Campaign.objects.create(title="Ended Hidden", status=Campaign.Status.ENDED)

        res = self.client.get(f"/api/v1/shops/public/{self.shop_active.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_visibility_on_temporarily_closed_shop(self):
        camp = Campaign.objects.create(
            title="Promo for Closed Shop",
            status=Campaign.Status.ACTIVE,
        )
        res = self.client.get(f"/api/v1/shops/public/{self.shop_closed.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], camp.id)

    def test_visibility_on_deactivated_shop_returns_unavailable(self):
        Campaign.objects.create(title="Active Promo", status=Campaign.Status.ACTIVE)
        res = self.client.get(f"/api/v1/shops/public/{self.shop_deact.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data.get("code"), "SHOP_UNAVAILABLE")

    def test_visibility_on_suspended_shop_returns_unavailable(self):
        Campaign.objects.create(title="Active Promo", status=Campaign.Status.ACTIVE)
        res = self.client.get(f"/api/v1/shops/public/{self.shop_susp.public_slug}/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data.get("code"), "SHOP_UNAVAILABLE")

    def test_visibility_on_nonexistent_shop_returns_not_found(self):
        Campaign.objects.create(title="Active Promo", status=Campaign.Status.ACTIVE)
        res = self.client.get("/api/v1/shops/public/does-not-exist-slug/campaigns/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data.get("code"), "SHOP_NOT_FOUND")


class CampaignNoDiscountBehaviorTests(TestCase):
    """
    CAM-006: Rigorous cross-domain tests asserting that Campaigns domain acts strictly
    as promotional marketing content and never introduces or mutates product prices,
    inventory availability, cart totals, or order totals.
    """

    def setUp(self):
        self.client = APIClient()
        self.super_admin = User.objects.create_user(
            username="cam006_nodisc_admin",
            email="cam006_nodisc_admin@example.com",
            mobile_number="+919876543340",
            role=User.Role.SUPER_ADMIN,
        )
        merchant_user = User.objects.create_user(
            username="cam006_nodisc_merchant",
            email="cam006_nodisc_merchant@example.com",
            mobile_number="+919876543341",
            role=User.Role.MERCHANT,
        )
        merchant = Merchant.objects.create(user=merchant_user)
        self.shop = Shop.objects.create(
            merchant=merchant,
            name="Grocery Pricing Test Shop",
            address_line="10 Market St",
            area="Koramangala",
            city="Bengaluru",
            state="Karnataka",
            pincode="560034",
            contact_number=merchant_user.mobile_number,
            public_slug="cam006-slug-pricing-shop",
            delivery_charge=Decimal("40.00"),
            delivery_fee_type=Shop.DeliveryFeeType.FIXED,
            status=Shop.Status.ACTIVE,
        )

        # Catalog product at regular price
        self.product = ShopProduct.objects.create(
            shop=self.shop,
            name="Shimla Red Apples",
            sku="SHM-APP-001",
            price=Decimal("150.00"),
            is_available=True,
            is_visible=True,
        )

        # Retrieve auto-initialized InventoryItem (created via post_save signal)
        self.inventory_item = InventoryItem.objects.get(
            shop=self.shop,
            product=self.product,
            variant__isnull=True,
        )
        self.inventory_item.quantity = Decimal("50.000")
        self.inventory_item.save(update_fields=["quantity", "updated_at"])


    def test_campaign_model_has_no_discount_fields(self):
        field_names = [f.name for f in Campaign._meta.get_fields()]
        discount_terms = ["discount", "coupon", "percent", "voucher", "deduction", "rebate", "min_order"]
        for term in discount_terms:
            for field in field_names:
                self.assertNotIn(
                    term,
                    field.lower(),
                    f"Campaign model must not define discount field '{field}'.",
                )

    def test_campaign_serializers_ignore_unapproved_discount_payloads(self):
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.post(
            "/api/v1/campaigns/",
            {
                "title": "Super Saver Week",
                "content": "Special promotional copy",
                "discount_percentage": 50,
                "coupon_code": "SAVE50",
                "discount_amount": "25.00",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        camp = Campaign.objects.get(id=res.data["id"])

        # Model instance has no discount fields
        self.assertFalse(hasattr(camp, "discount_percentage"))
        self.assertFalse(hasattr(camp, "coupon_code"))

        # Serializer outputs contain no discount data
        self.assertNotIn("discount_percentage", res.data)
        self.assertNotIn("coupon_code", res.data)
        self.assertNotIn("discount_amount", res.data)

        # Public serializer also contains no discount data
        pub_serializer = PublicCampaignSerializer(camp)
        self.assertNotIn("discount_percentage", pub_serializer.data)
        self.assertNotIn("coupon_code", pub_serializer.data)

    def test_promotional_copy_mentioning_discount_does_not_alter_catalog_price(self):
        # Create an active campaign promising 50% discount on Shimla Red Apples
        Campaign.objects.create(
            title="50% Off Apples Promo",
            content="Flat 50% discount on Shimla Red Apples! Save big today!",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )

        # Catalog product price remains strictly unchanged
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("150.00"))

        # Public catalog product endpoint also returns 150.00
        res = self.client.get(
            f"/api/v1/shops/public/{self.shop.public_slug}/products/{self.product.id}/"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(res.data["price"])), Decimal("150.00"))

    def test_promotional_copy_mentioning_discount_does_not_alter_cart_total(self):
        # Create active campaign claiming discount
        Campaign.objects.create(
            title="Cart Discount Ad",
            content="Get Rs. 50 OFF at checkout with code GROCERY50",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )

        # Customer creates a cart with 2 units of the product
        cart = Cart.objects.create(shop=self.shop)
        item = CartItem.objects.create(cart=cart, product=self.product, quantity=Decimal("2.000"))

        # Unit price is strictly catalog price (150.00)
        self.assertEqual(item.unit_price, Decimal("150.00"))

        # Subtotal is strictly 2 * 150.00 = 300.00 without any campaign deduction
        self.assertEqual(cart.subtotal, Decimal("300.00"))

        # Public cart endpoint also reflects strict catalog total
        res = self.client.get(f"/api/v1/shops/public/{self.shop.public_slug}/cart/{cart.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(res.data["subtotal"])), Decimal("300.00"))

    def test_promotional_copy_mentioning_discount_does_not_alter_order_total(self):
        # Create active campaign
        Campaign.objects.create(
            title="Order Free Delivery Ad",
            content="Free Delivery and 20% discount on all orders!",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )

        from customers.models import Customer

        customer = Customer.objects.create(
            shop=self.shop,
            name="Priya Patel",
            whatsapp_number="+919876543349",
        )


        # Create Order: 2 units * 150.00 = 300.00 + 40.00 delivery = 340.00
        order = Order.objects.create(
            shop=self.shop,
            customer=customer,
            customer_name_snapshot="Priya Patel",
            customer_phone_snapshot="+919876543349",
            delivery_fee_type_snapshot=Order.DeliveryFeeType.FIXED,
            delivery_charge_snapshot=Decimal("40.00"),
            items_subtotal=Decimal("300.00"),
            total_amount=Decimal("340.00"),
            status=Order.Status.PENDING,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name_snapshot=self.product.name,
            unit_price_snapshot=Decimal("150.00"),
            ordered_quantity=Decimal("2.000"),
            quantity=Decimal("2.000"),
            line_total=Decimal("300.00"),
        )


        # Order totals are strictly based on items and delivery snapshot
        order.refresh_from_db()
        self.assertEqual(order.items_subtotal, Decimal("300.00"))
        self.assertEqual(order.delivery_charge_snapshot, Decimal("40.00"))
        self.assertEqual(order.total_amount, Decimal("340.00"))

        # Verify Order model has no discount or campaign attributes
        self.assertFalse(hasattr(order, "discount_amount"))
        self.assertFalse(hasattr(order, "campaign"))

    def test_active_campaign_does_not_alter_inventory_quantities(self):
        initial_available = self.inventory_item.available_quantity
        initial_reserved = self.inventory_item.reserved_quantity

        # Create active campaign mentioning inventory clearance
        Campaign.objects.create(
            title="Stock Clearance Ad",
            content="Clearing all apple stocks at massive discounts!",
            status=Campaign.Status.ACTIVE,
            shop_scope=Campaign.ShopScope.ALL_SHOPS,
        )

        # Inventory quantity is strictly preserved
        self.inventory_item.refresh_from_db()
        self.assertEqual(self.inventory_item.available_quantity, initial_available)
        self.assertEqual(self.inventory_item.reserved_quantity, initial_reserved)


