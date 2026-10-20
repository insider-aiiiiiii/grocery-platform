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
