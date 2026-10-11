import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from shops.models import Shop
from users.models import Merchant, User, UserAuthSession


class ShopModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="merchant_1",
            email="merchant1@example.com",
            mobile_number="+919876543210",
            role=User.Role.MERCHANT,
            password="testpassword123",
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
        )

    def test_shop_creation_successful(self):
        """Test successful creation of a shop linked to a merchant."""
        shop = Shop.objects.create(
            merchant=self.merchant,
            name="Fresh Supermarket",
            description="Best grocery in town",
            address_line="123 Market St",
            area="Central Market",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=self.user.mobile_number,
            status=Shop.Status.ACTIVE,
            delivery_charge=Decimal("25.00"),
        )
        self.assertEqual(shop.merchant, self.merchant)
        self.assertEqual(self.merchant.shop, shop)
        self.assertEqual(shop.status, Shop.Status.ACTIVE)
        self.assertEqual(shop.delivery_fee_type, Shop.DeliveryFeeType.FIXED)
        self.assertTrue(bool(shop.public_slug))
        self.assertTrue(shop.is_home_delivery_enabled)
        self.assertTrue(shop.is_pickup_enabled)
        self.assertFalse(shop.is_temporarily_closed)

    def test_merchant_one_to_one_relationship_enforced_at_db_level(self):
        """Ensure a single merchant cannot own multiple shops (enforced by DB unique constraint)."""
        Shop.objects.create(
            merchant=self.merchant,
            name="First Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=self.user.mobile_number,
        )
        with self.assertRaises(IntegrityError):
            Shop.objects.create(
                merchant=self.merchant,
                name="Second Shop",
                address_line="Line 2",
                area="Area 2",
                city="City 2",
                state="State 2",
                pincode="123456",
                contact_number=self.user.mobile_number,
            )

    def test_shop_status_choices_and_suspended_support(self):
        """Verify shop supports ACTIVE, DEACTIVATED, and SUSPENDED statuses."""
        shop = Shop.objects.create(
            merchant=self.merchant,
            name="Test Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=self.user.mobile_number,
            status=Shop.Status.SUSPENDED,
        )
        self.assertEqual(shop.status, "SUSPENDED")

        shop.status = Shop.Status.DEACTIVATED
        shop.save()
        self.assertEqual(shop.status, "DEACTIVATED")

    def test_invalid_status_rejected_by_constraint(self):
        """Ensure invalid status values fail DB CheckConstraint."""
        with self.assertRaises(IntegrityError):
            Shop.objects.create(
                merchant=self.merchant,
                name="Invalid Status Shop",
                address_line="Line 1",
                area="Area 1",
                city="City 1",
                state="State 1",
                pincode="123456",
                contact_number=self.user.mobile_number,
                status="UNKNOWN_STATUS",
            )

    def test_delivery_fee_types_fixed_and_whatsapp_confirmed(self):
        """Verify Option 2 flexible delivery policy: FIXED vs CONFIRMED_ON_WHATSAPP."""
        shop = Shop.objects.create(
            merchant=self.merchant,
            name="Flexible Delivery Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=self.user.mobile_number,
            delivery_fee_type=Shop.DeliveryFeeType.CONFIRMED_ON_WHATSAPP,
            delivery_charge=Decimal("0.00"),
        )
        self.assertEqual(shop.delivery_fee_type, "CONFIRMED_ON_WHATSAPP")
        self.assertEqual(shop.delivery_charge, Decimal("0.00"))

    def test_invalid_delivery_fee_type_rejected_by_constraint(self):
        """Ensure invalid delivery_fee_type fails DB CheckConstraint."""
        with self.assertRaises(IntegrityError):
            Shop.objects.create(
                merchant=self.merchant,
                name="Bad Fee Type Shop",
                address_line="Line 1",
                area="Area 1",
                city="City 1",
                state="State 1",
                pincode="123456",
                contact_number=self.user.mobile_number,
                delivery_fee_type="INVALID_TYPE",
            )

    def test_delivery_charge_non_negative_constraint(self):
        """Ensure negative delivery charges fail DB CheckConstraint."""
        with self.assertRaises(IntegrityError):
            Shop.objects.create(
                merchant=self.merchant,
                name="Negative Delivery Shop",
                address_line="Line 1",
                area="Area 1",
                city="City 1",
                state="State 1",
                pincode="123456",
                contact_number=self.user.mobile_number,
                delivery_charge=Decimal("-5.00"),
            )

    def test_clean_enforces_contact_number_matches_merchant_mobile(self):
        """Ensure clean() raises ValidationError if contact number diverges from merchant mobile."""
        shop = Shop(
            merchant=self.merchant,
            name="Mismatch Contact Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number="+910000000000",
        )
        with self.assertRaises(ValidationError) as ctx:
            shop.clean()
        self.assertIn("contact_number", ctx.exception.message_dict)

    def test_clean_and_save_auto_populates_contact_number(self):
        """Ensure clean() and save() automatically populate contact_number from merchant mobile if blank."""
        shop = Shop.objects.create(
            merchant=self.merchant,
            name="Auto Contact Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number="",
        )
        self.assertEqual(shop.contact_number, self.user.mobile_number)

    def test_super_admin_suspend_and_deactivate_methods(self):
        """Verify Super Admin suspend() and deactivate() methods update status cleanly."""
        shop = Shop.objects.create(
            merchant=self.merchant,
            name="Lifecycle Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=self.user.mobile_number,
        )
        shop.suspend()
        shop.refresh_from_db()
        self.assertEqual(shop.status, Shop.Status.SUSPENDED)

        shop.deactivate()
        shop.refresh_from_db()
        self.assertEqual(shop.status, Shop.Status.DEACTIVATED)

    def test_super_admin_reactivate_rotates_public_slug_and_preserves_data(self):
        """Verify reactivating/unsuspending a shop assigns a fresh QR token while preserving existing data."""
        shop = Shop.objects.create(
            merchant=self.merchant,
            name="Reactivated Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=self.user.mobile_number,
            status=Shop.Status.SUSPENDED,
        )
        initial_slug = shop.public_slug
        initial_id = shop.id

        shop.reactivate()
        shop.refresh_from_db()

        self.assertEqual(shop.status, Shop.Status.ACTIVE)
        self.assertEqual(shop.id, initial_id)
        self.assertEqual(shop.name, "Reactivated Shop")
        self.assertNotEqual(shop.public_slug, initial_slug)

    def test_super_admin_regenerate_public_slug(self):
        """Verify Super Admin regenerate_public_slug() rotates the public QR slug."""
        shop = Shop.objects.create(
            merchant=self.merchant,
            name="QR Rotation Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=self.user.mobile_number,
        )
        old_slug = shop.public_slug
        new_slug = shop.regenerate_public_slug()

        shop.refresh_from_db()
        self.assertNotEqual(old_slug, new_slug)
        self.assertEqual(shop.public_slug, new_slug)

    def test_operational_controls_and_business_hours(self):
        """Verify single daily business hours and temporary closed toggle."""
        shop = Shop.objects.create(
            merchant=self.merchant,
            name="Hours Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=self.user.mobile_number,
            is_temporarily_closed=True,
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(21, 0),
        )
        self.assertTrue(shop.is_temporarily_closed)
        self.assertEqual(shop.opening_time, datetime.time(9, 0))
        self.assertEqual(shop.closing_time, datetime.time(21, 0))

    def test_shop_deletion_preserves_merchant_and_user_credentials(self):
        """Deleting a Shop removes only the Shop and retains its Merchant login."""
        shop = Shop.objects.create(
            merchant=self.merchant,
            name="Delete Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=self.user.mobile_number,
        )
        shop_id = shop.pk
        merchant_id = self.merchant.pk
        user_id = self.user.pk

        shop.delete()

        self.assertFalse(Shop.objects.filter(pk=shop_id).exists())
        self.assertTrue(Merchant.objects.filter(pk=merchant_id).exists())
        self.assertTrue(User.objects.filter(pk=user_id).exists())
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpassword123"))

    def test_merchant_deletion_cascades_to_shop(self):
        """Verify deleting Merchant cascades and deletes the associated Shop."""
        user = User.objects.create_user(
            username="cascade_merchant",
            mobile_number="+919988776644",
            password="testpassword123",
            role=User.Role.MERCHANT,
        )
        merchant = Merchant.objects.create(user=user)
        shop = Shop.objects.create(
            merchant=merchant,
            name="Cascade Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=user.mobile_number,
        )
        shop_id = shop.id

        merchant.delete()

        self.assertFalse(Shop.objects.filter(id=shop_id).exists())


class ShopCreateAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="merchant_creator",
            email="creator@example.com",
            mobile_number="+919876543219",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.url = reverse("shops:shop-create")

    def authenticate_user(self, user):
        response = self.client.post(
            reverse("auth-login"),
            {"mobile_number": user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return response.data

    def valid_shop_data(self):
        return {
            "name": "Super Daily Grocery",
            "description": "All organic vegetables and groceries",
            "address_line": "Shop 4, Sunrise Heights",
            "area": "Kothrud",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411038",
            "delivery_fee_type": "FIXED",
            "delivery_charge": "30.00",
            "is_home_delivery_enabled": True,
            "is_pickup_enabled": True,
        }

    def test_unauthenticated_user_cannot_create_shop(self):
        """Unauthenticated requests must return 401 Unauthorized."""
        response = self.client.post(self.url, self.valid_shop_data(), format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_super_admin_cannot_create_shop(self):
        """Super Admin is forbidden from creating a merchant shop."""
        admin_user = User.objects.create_user(
            username="admin_user",
            email="admin@example.com",
            mobile_number="+919876543218",
            password="securepassword123",
            role=User.Role.SUPER_ADMIN,
        )
        response = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": "admin@example.com", "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post(self.url, self.valid_shop_data(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_merchant_must_change_password_is_blocked(self):
        """Merchant who hasn't changed their initial password receives 403 PasswordChangeRequired."""
        self.merchant.must_change_password = True
        self.merchant.save()

        self.authenticate_user(self.user)
        response = self.client.post(self.url, self.valid_shop_data(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get("code"), "PASSWORD_CHANGE_REQUIRED")

    def test_merchant_creates_shop_successfully(self):
        """Active merchant creates shop: returns 201 Created, ACTIVE status, and public slug."""
        self.authenticate_user(self.user)
        data = self.valid_shop_data()

        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], data["name"])
        self.assertEqual(response.data["address_line"], data["address_line"])
        self.assertEqual(response.data["city"], data["city"])
        self.assertEqual(response.data["status"], "ACTIVE")
        self.assertEqual(response.data["contact_number"], self.user.mobile_number)
        self.assertTrue(bool(response.data["public_slug"]))
        self.assertEqual(len(response.data["public_slug"]), 12)

        shop = Shop.objects.get(merchant=self.merchant)
        self.assertEqual(shop.status, Shop.Status.ACTIVE)
        self.assertEqual(shop.contact_number, self.user.mobile_number)

    def test_shop_creation_ignores_client_supplied_shop_id_for_ownership(self):
        """A forged tenant identifier cannot select or assign the created Shop's owner."""
        other_user = User.objects.create_user(
            username="other_shop_owner",
            email="other_shop_owner@example.com",
            mobile_number="+919876543217",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        other_merchant = Merchant.objects.create(user=other_user, status=Merchant.Status.ACTIVE)
        other_shop = Shop.objects.create(
            merchant=other_merchant,
            name="Other Shop",
            address_line="1 Other Street",
            area="Camp",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=other_user.mobile_number,
        )

        self.authenticate_user(self.user)
        payload = self.valid_shop_data()
        payload["shop_id"] = other_shop.pk
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_shop = Shop.objects.get(pk=response.data["id"])
        self.assertEqual(created_shop.merchant_id, self.merchant.pk)
        self.assertNotEqual(created_shop.pk, other_shop.pk)

    def test_merchant_cannot_create_second_shop(self):
        """Enforces one-Shop-per-Merchant invariant: second creation returns 400 SHOP_ALREADY_EXISTS."""
        self.authenticate_user(self.user)
        self.client.post(self.url, self.valid_shop_data(), format="json")

        # Second attempt
        response = self.client.post(self.url, self.valid_shop_data(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("code"), "SHOP_ALREADY_EXISTS")

    def test_merchant_can_create_replacement_shop_after_deletion(self):
        """Deleting a Shop preserves the login and permits a fresh Shop identity."""
        self.authenticate_user(self.user)
        original_response = self.client.post(self.url, self.valid_shop_data(), format="json")
        self.assertEqual(original_response.status_code, status.HTTP_201_CREATED)
        original_shop_id = original_response.data["id"]
        original_public_slug = original_response.data["public_slug"]

        Shop.objects.get(pk=original_shop_id).delete()

        self.assertTrue(Merchant.objects.filter(pk=self.merchant.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(self.user.check_password("securepassword123"))

        replacement_data = self.valid_shop_data()
        replacement_data["name"] = "Replacement Grocery"
        replacement_response = self.client.post(self.url, replacement_data, format="json")

        self.assertEqual(replacement_response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(replacement_response.data["id"], original_shop_id)
        self.assertNotEqual(replacement_response.data["public_slug"], original_public_slug)
        self.assertFalse(Shop.objects.filter(pk=original_shop_id).exists())
        replacement_shop = Shop.objects.get(pk=replacement_response.data["id"])
        self.assertEqual(replacement_shop.merchant_id, self.merchant.pk)
        self.assertEqual(Shop.objects.filter(merchant=self.merchant).count(), 1)

    def test_missing_required_fields_rejected(self):
        """Missing required address or name fields return 400 with validation errors."""
        self.authenticate_user(self.user)
        incomplete_data = {
            "name": "",
            "area": "Kothrud",
        }
        response = self.client.post(self.url, incomplete_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)
        self.assertIn("address_line", response.data)
        self.assertIn("city", response.data)
        self.assertIn("state", response.data)
        self.assertIn("pincode", response.data)

    def test_negative_delivery_charge_rejected(self):
        """Negative delivery charge returns 400 validation error."""
        self.authenticate_user(self.user)
        data = self.valid_shop_data()
        data["delivery_charge"] = "-10.00"

        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery_charge", response.data)

    def test_login_returns_shop_id_dynamically(self):
        """Before shop creation login returns shop_id: null; after creation login returns shop_id."""
        login_res_1 = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.assertIsNone(login_res_1.data["user"]["shop_id"])

        # Create shop
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_res_1.data['access']}")
        create_res = self.client.post(self.url, self.valid_shop_data(), format="json")
        created_shop_id = create_res.data["id"]

        # Login again
        login_res_2 = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.assertEqual(login_res_2.data["user"]["shop_id"], created_shop_id)


class MerchantShopRetrievalAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="merchant_retriever",
            email="retriever@example.com",
            mobile_number="+919876543201",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.url_me = reverse("shops:shop-me")
        self.url_root = reverse("shops:shop-create")

    def authenticate_user(self, user):
        response = self.client.post(
            reverse("auth-login"),
            {"mobile_number": user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return response.data

    def create_shop(self, merchant, name="Retriever Shop", status_val=Shop.Status.ACTIVE):
        return Shop.objects.create(
            merchant=merchant,
            name=name,
            description="High quality groceries",
            address_line="101 MG Road",
            area="Camp",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=merchant.user.mobile_number,
            status=status_val,
            delivery_fee_type=Shop.DeliveryFeeType.FIXED,
            delivery_charge=Decimal("20.00"),
        )

    def test_unauthenticated_request_returns_401(self):
        """Unauthenticated requests must return 401 Unauthorized."""
        res_me = self.client.get(self.url_me)
        self.assertEqual(res_me.status_code, status.HTTP_401_UNAUTHORIZED)

        res_root = self.client.get(self.url_root)
        self.assertEqual(res_root.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_super_admin_cannot_retrieve_merchant_shop_returns_403(self):
        """Super Admin cannot access merchant shop retrieval API."""
        admin_user = User.objects.create_user(
            username="admin_retriever",
            email="admin_retriever@example.com",
            mobile_number="+919876543202",
            password="securepassword123",
            role=User.Role.SUPER_ADMIN,
        )
        response = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": "admin_retriever@example.com", "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_merchant_with_temporary_password_returns_403_password_change_required(self):
        """Merchant who hasn't changed initial password receives 403 PasswordChangeRequired."""
        self.merchant.must_change_password = True
        self.merchant.save()

        self.authenticate_user(self.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get("code"), "PASSWORD_CHANGE_REQUIRED")

    def test_merchant_without_shop_returns_404(self):
        """Merchant without a shop receives 404 SHOP_NOT_FOUND."""
        self.authenticate_user(self.user)
        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "SHOP_NOT_FOUND")

    def test_merchant_retrieves_active_shop_successfully(self):
        """Active merchant retrieves their shop successfully with all approved fields."""
        shop = self.create_shop(self.merchant)
        self.authenticate_user(self.user)

        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Validate approved fields
        self.assertEqual(response.data["id"], shop.id)
        self.assertEqual(response.data["name"], shop.name)
        self.assertEqual(response.data["description"], shop.description)
        self.assertEqual(response.data["address_line"], shop.address_line)
        self.assertEqual(response.data["area"], shop.area)
        self.assertEqual(response.data["city"], shop.city)
        self.assertEqual(response.data["state"], shop.state)
        self.assertEqual(response.data["pincode"], shop.pincode)
        self.assertEqual(response.data["contact_number"], shop.contact_number)
        self.assertEqual(response.data["status"], "ACTIVE")
        self.assertEqual(response.data["delivery_fee_type"], "FIXED")
        self.assertEqual(Decimal(str(response.data["delivery_charge"])), Decimal("20.00"))
        self.assertEqual(response.data["public_slug"], shop.public_slug)
        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)

        # Internal merchant foreign key must not be exposed
        self.assertNotIn("merchant", response.data)
        self.assertNotIn("merchant_id", response.data)

        # Also verify GET /api/v1/shops/ alias returns the identical data
        res_alias = self.client.get(self.url_root)
        self.assertEqual(res_alias.status_code, status.HTTP_200_OK)
        self.assertEqual(res_alias.data["id"], shop.id)

    def test_deactivated_shop_returns_403_forbidden(self):
        """Deactivated shop cannot be accessed by the merchant."""
        self.create_shop(self.merchant, status_val=Shop.Status.DEACTIVATED)
        self.authenticate_user(self.user)

        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get("code"), "SHOP_INACTIVE")

    def test_suspended_shop_returns_403_forbidden(self):
        """Suspended shop cannot be accessed by the merchant."""
        self.create_shop(self.merchant, status_val=Shop.Status.SUSPENDED)
        self.authenticate_user(self.user)

        response = self.client.get(self.url_me)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get("code"), "SHOP_INACTIVE")

    def test_merchant_cannot_query_arbitrary_shop_id_via_params(self):
        """Passing arbitrary shop_id in query parameters is ignored; server derives context."""
        shop = self.create_shop(self.merchant)

        # Another merchant and shop exist
        other_user = User.objects.create_user(
            username="other_merchant",
            email="other@example.com",
            mobile_number="+919876543203",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        other_merchant = Merchant.objects.create(user=other_user, status=Merchant.Status.ACTIVE)
        other_shop = self.create_shop(other_merchant, name="Other Shop")

        self.authenticate_user(self.user)

        # Attempt to supply other_shop.id in query params
        response = self.client.get(f"{self.url_me}?shop_id={other_shop.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], shop.id)
        self.assertNotEqual(response.data["id"], other_shop.id)

    def test_cross_merchant_isolation(self):
        """Ensures complete tenant isolation between two active merchants."""
        shop1 = self.create_shop(self.merchant, name="Merchant 1 Shop")

        user2 = User.objects.create_user(
            username="merchant_2",
            email="merchant2@example.com",
            mobile_number="+919876543204",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        merchant2 = Merchant.objects.create(
            user=user2,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        shop2 = self.create_shop(merchant2, name="Merchant 2 Shop")

        # Authenticate as user 1
        self.authenticate_user(self.user)
        res1 = self.client.get(self.url_me)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data["id"], shop1.id)
        self.assertEqual(res1.data["name"], "Merchant 1 Shop")

        # Authenticate as user 2
        self.authenticate_user(user2)
        res2 = self.client.get(self.url_me)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["id"], shop2.id)
        self.assertEqual(res2.data["name"], "Merchant 2 Shop")


class MerchantShopUpdateAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="merchant_updater",
            email="updater@example.com",
            mobile_number="+919876543301",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.url_me = reverse("shops:shop-me")
        self.url_root = reverse("shops:shop-create")

    def authenticate_user(self, user):
        response = self.client.post(
            reverse("auth-login"),
            {"mobile_number": user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return response.data

    def create_shop(self, merchant, name="Original Shop", status_val=Shop.Status.ACTIVE):
        return Shop.objects.create(
            merchant=merchant,
            name=name,
            description="Original description",
            address_line="100 Original St",
            area="Old Area",
            city="Old City",
            state="Old State",
            pincode="111111",
            contact_number=merchant.user.mobile_number,
            status=status_val,
            is_temporarily_closed=False,
            is_home_delivery_enabled=True,
            is_pickup_enabled=True,
            delivery_fee_type=Shop.DeliveryFeeType.FIXED,
            delivery_charge=Decimal("15.00"),
        )

    def test_unauthenticated_patch_and_put_returns_401(self):
        """Unauthenticated PATCH or PUT requests must return 401 Unauthorized."""
        res_patch = self.client.patch(self.url_me, {"name": "New Name"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_401_UNAUTHORIZED)

        res_put = self.client.put(self.url_me, {"name": "New Name"}, format="json")
        self.assertEqual(res_put.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_super_admin_cannot_update_merchant_shop_returns_403(self):
        """Super Admin cannot update a merchant's shop."""
        admin_user = User.objects.create_user(
            username="admin_updater",
            email="admin_updater@example.com",
            mobile_number="+919876543302",
            password="securepassword123",
            role=User.Role.SUPER_ADMIN,
        )
        response = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": "admin_updater@example.com", "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        res = self.client.patch(self.url_me, {"name": "Admin Hijack"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_merchant_with_temporary_password_returns_403(self):
        """Merchant who hasn't changed initial password receives 403 PasswordChangeRequired."""
        self.merchant.must_change_password = True
        self.merchant.save()

        self.authenticate_user(self.user)
        res = self.client.patch(self.url_me, {"name": "New Name"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data.get("code"), "PASSWORD_CHANGE_REQUIRED")

    def test_merchant_without_shop_returns_404(self):
        """Merchant without a shop receives 404 SHOP_NOT_FOUND on update."""
        self.authenticate_user(self.user)
        res = self.client.patch(self.url_me, {"name": "New Name"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data.get("code"), "SHOP_NOT_FOUND")

    def test_deactivated_or_suspended_shop_cannot_be_updated(self):
        """Deactivated or suspended shop returns 403 SHOP_INACTIVE."""
        shop = self.create_shop(self.merchant, status_val=Shop.Status.DEACTIVATED)
        self.authenticate_user(self.user)

        res_patch = self.client.patch(self.url_me, {"name": "Updated Name"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_patch.data.get("code"), "SHOP_INACTIVE")

        # Suspended
        shop.status = Shop.Status.SUSPENDED
        shop.save()
        res_put = self.client.put(self.url_me, {"name": "Updated Name"}, format="json")
        self.assertEqual(res_put.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_put.data.get("code"), "SHOP_INACTIVE")

    def test_successful_partial_update_patch_allowed_fields(self):
        """Merchant updates allowed fields via PATCH successfully."""
        shop = self.create_shop(self.merchant)
        self.authenticate_user(self.user)

        update_payload = {
            "name": "Updated Super Fresh",
            "description": "Newly renovated store with organic goods",
            "address_line": "200 New Market St",
            "area": "Kothrud South",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411038",
            "is_temporarily_closed": True,
            "delivery_charge": "25.00",
        }
        response = self.client.patch(self.url_me, update_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], update_payload["name"])
        self.assertEqual(response.data["description"], update_payload["description"])
        self.assertEqual(response.data["address_line"], update_payload["address_line"])
        self.assertEqual(response.data["area"], update_payload["area"])
        self.assertEqual(response.data["pincode"], update_payload["pincode"])
        self.assertTrue(response.data["is_temporarily_closed"])
        self.assertEqual(Decimal(str(response.data["delivery_charge"])), Decimal("25.00"))

        shop.refresh_from_db()
        self.assertEqual(shop.name, "Updated Super Fresh")
        self.assertTrue(shop.is_temporarily_closed)
        self.assertEqual(shop.delivery_charge, Decimal("25.00"))

    def test_successful_full_update_put(self):
        """Merchant updates shop via PUT successfully."""
        shop = self.create_shop(self.merchant)
        self.authenticate_user(self.user)

        put_payload = {
            "name": "Completely Renovated Shop",
            "description": "Brand new description",
            "address_line": "500 Grand Road",
            "area": "Deccan",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411004",
            "is_temporarily_closed": False,
            "is_home_delivery_enabled": True,
            "is_pickup_enabled": False,
            "delivery_fee_type": "FIXED",
            "delivery_charge": "40.00",
        }
        response = self.client.put(self.url_me, put_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], put_payload["name"])
        self.assertFalse(response.data["is_pickup_enabled"])
        self.assertTrue(response.data["is_home_delivery_enabled"])

        shop.refresh_from_db()
        self.assertEqual(shop.name, "Completely Renovated Shop")
        self.assertFalse(shop.is_pickup_enabled)

    def test_contact_number_cannot_be_modified(self):
        """Shop contact number strictly mirrors merchant mobile and cannot be modified."""
        shop = self.create_shop(self.merchant)
        self.authenticate_user(self.user)

        response = self.client.patch(
            self.url_me,
            {"contact_number": "+910000000000", "name": "Name Change"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["contact_number"], self.user.mobile_number)

        shop.refresh_from_db()
        self.assertEqual(shop.contact_number, self.user.mobile_number)

    def test_status_and_public_slug_cannot_be_modified(self):
        """Merchant cannot modify platform lifecycle status or public_slug."""
        shop = self.create_shop(self.merchant)
        original_slug = shop.public_slug
        self.authenticate_user(self.user)

        response = self.client.patch(
            self.url_me,
            {"status": "SUSPENDED", "public_slug": "tampered_slug_123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ACTIVE")
        self.assertEqual(response.data["public_slug"], original_slug)

        shop.refresh_from_db()
        self.assertEqual(shop.status, Shop.Status.ACTIVE)
        self.assertEqual(shop.public_slug, original_slug)

    def test_negative_delivery_charge_rejected(self):
        """Negative delivery charges fail serializer validation."""
        self.create_shop(self.merchant)
        self.authenticate_user(self.user)

        response = self.client.patch(self.url_me, {"delivery_charge": "-10.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery_charge", response.data)

    def test_disabling_both_pickup_and_delivery_rejected(self):
        """Disabling both home delivery and pickup fails validation."""
        self.create_shop(self.merchant)
        self.authenticate_user(self.user)

        response = self.client.patch(
            self.url_me,
            {"is_home_delivery_enabled": False, "is_pickup_enabled": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fulfillment", response.data)

    def test_confirmed_on_whatsapp_normalizes_delivery_charge(self):
        """CONFIRMED_ON_WHATSAPP delivery fee type automatically normalizes delivery charge to 0.00."""
        shop = self.create_shop(self.merchant)
        self.authenticate_user(self.user)

        response = self.client.patch(
            self.url_me,
            {
                "delivery_fee_type": "CONFIRMED_ON_WHATSAPP",
                "delivery_charge": "50.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["delivery_fee_type"], "CONFIRMED_ON_WHATSAPP")
        self.assertEqual(Decimal(str(response.data["delivery_charge"])), Decimal("0.00"))

        shop.refresh_from_db()
        self.assertEqual(shop.delivery_charge, Decimal("0.00"))

    def test_business_hours_validation(self):
        """Verify business hours validation for valid hours, mismatched nulls, and identical times."""
        shop = self.create_shop(self.merchant)
        self.authenticate_user(self.user)

        # 1. Valid business hours
        res1 = self.client.patch(
            self.url_me,
            {"opening_time": "08:30:00", "closing_time": "21:30:00"},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data["opening_time"], "08:30:00")
        self.assertEqual(res1.data["closing_time"], "21:30:00")

        # 2. Identical opening and closing times rejected
        res2 = self.client.patch(
            self.url_me,
            {"opening_time": "10:00:00", "closing_time": "10:00:00"},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("business_hours", res2.data)

        # 3. Only opening time provided while closing time is set to null
        res3 = self.client.patch(
            self.url_me,
            {"opening_time": "10:00:00", "closing_time": None},
            format="json",
        )
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("business_hours", res3.data)

        # 4. Clearing both hours is allowed
        res4 = self.client.patch(
            self.url_me,
            {"opening_time": None, "closing_time": None},
            format="json",
        )
        self.assertEqual(res4.status_code, status.HTTP_200_OK)
        self.assertIsNone(res4.data["opening_time"])
        self.assertIsNone(res4.data["closing_time"])

    def test_cross_merchant_update_isolation(self):
        """Ensures Merchant 1 cannot update Merchant 2's shop."""
        shop1 = self.create_shop(self.merchant, name="Shop 1")

        user2 = User.objects.create_user(
            username="merchant_other",
            email="other_merchant@example.com",
            mobile_number="+919876543303",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        merchant2 = Merchant.objects.create(
            user=user2,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        shop2 = self.create_shop(merchant2, name="Shop 2")

        # Authenticate as user 1 and update
        self.authenticate_user(self.user)
        res = self.client.patch(self.url_me, {"name": "Shop 1 Modified"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        shop1.refresh_from_db()
        shop2.refresh_from_db()
        self.assertEqual(shop1.name, "Shop 1 Modified")
        self.assertEqual(shop2.name, "Shop 2")


class ShopLifecycleAndDeletionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.merchant_user = User.objects.create_user(
            username="merchant_lifecycle",
            email="merchant_lifecycle@example.com",
            mobile_number="+919876543401",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.admin_user = User.objects.create_user(
            username="admin_lifecycle",
            email="admin_lifecycle@example.com",
            mobile_number="+919876543402",
            password="securepassword123",
            role=User.Role.SUPER_ADMIN,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Lifecycle Shop",
            description="Testing deactivation and deletion",
            address_line="202 MG Road",
            area="Camp",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=self.merchant_user.mobile_number,
            status=Shop.Status.ACTIVE,
            delivery_fee_type=Shop.DeliveryFeeType.FIXED,
            delivery_charge=Decimal("15.00"),
        )
        self.deactivate_url = reverse("shops:shop-admin-deactivate", kwargs={"pk": self.shop.pk})
        self.delete_url = reverse("shops:shop-admin-delete", kwargs={"pk": self.shop.pk})
        self.merchant_deactivate_url = reverse("shops:shop-me-deactivate")
        self.merchant_url_me = reverse("shops:shop-me")

    def authenticate_merchant(self):
        response = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.merchant_user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return response.data

    def authenticate_admin(self):
        response = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": "admin_lifecycle@example.com", "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return response.data

    def test_super_admin_can_deactivate_shop(self):
        """Super Admin can deactivate an active shop."""
        self.authenticate_admin()
        response = self.client.post(self.deactivate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "DEACTIVATED")

        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, Shop.Status.DEACTIVATED)

        # Deactivated shop blocks merchant from reading or updating profile
        self.authenticate_merchant()
        get_res = self.client.get(self.merchant_url_me)
        self.assertEqual(get_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(get_res.data.get("code"), "SHOP_INACTIVE")

        patch_res = self.client.patch(self.merchant_url_me, {"name": "New Name"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(patch_res.data.get("code"), "SHOP_INACTIVE")

    def test_super_admin_deactivating_already_deactivated_shop_returns_400(self):
        """Deactivating an already deactivated shop returns 400 Bad Request."""
        self.shop.deactivate()
        self.authenticate_admin()
        response = self.client.post(self.deactivate_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("code"), "SHOP_ALREADY_DEACTIVATED")

    def test_super_admin_deactivating_nonexistent_shop_returns_404(self):
        """Deactivating a nonexistent shop returns 404 Not Found."""
        self.authenticate_admin()
        non_existent_url = reverse("shops:shop-admin-deactivate", kwargs={"pk": 999999})
        response = self.client.post(non_existent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_merchant_cannot_deactivate_shop(self):
        """Merchants cannot deactivate shops; requests are rejected with 403."""
        self.authenticate_merchant()

        # Merchant calls /me/deactivate/
        res1 = self.client.post(self.merchant_deactivate_url)
        self.assertEqual(res1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res1.data.get("code"), "SHOP_DEACTIVATION_NOT_PERMITTED")

        # Merchant calls root /deactivate/
        res2 = self.client.post(reverse("shops:shop-deactivate"))
        self.assertEqual(res2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res2.data.get("code"), "SHOP_DEACTIVATION_NOT_PERMITTED")

        # Merchant calls admin endpoint
        res3 = self.client.post(self.deactivate_url)
        self.assertEqual(res3.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_deactivate_shop(self):
        """Unauthenticated requests to deactivate endpoint return 401."""
        response = self.client.post(self.deactivate_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_super_admin_permanent_delete_requires_confirmation(self):
        """Super Admin cannot delete a shop without explicit confirmation safeguard."""
        self.authenticate_admin()

        # Missing confirmation
        res1 = self.client.delete(self.delete_url)
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res1.data.get("code"), "CONFIRMATION_REQUIRED")

        # Confirmation false
        res2 = self.client.delete(self.delete_url, {"confirm": False}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res2.data.get("code"), "CONFIRMATION_REQUIRED")

        # Shop still exists
        self.assertTrue(Shop.objects.filter(pk=self.shop.pk).exists())

    def test_super_admin_permanent_delete_with_confirmation_succeeds(self):
        """Super Admin deletes shop with confirmation; merchant account is preserved."""
        self.authenticate_admin()
        shop_id = self.shop.pk
        merchant_id = self.merchant.pk
        user_id = self.merchant_user.pk

        response = self.client.delete(self.delete_url, {"confirm": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Shop is permanently removed
        self.assertFalse(Shop.objects.filter(pk=shop_id).exists())

        # Merchant and User credentials remain intact
        self.assertTrue(Merchant.objects.filter(pk=merchant_id).exists())
        self.assertTrue(User.objects.filter(pk=user_id).exists())

        # Merchant can log in and create a replacement shop
        self.authenticate_merchant()
        replacement_data = {
            "name": "Fresh Replacement Shop",
            "address_line": "303 MG Road",
            "area": "Camp",
            "city": "Pune",
            "state": "Maharashtra",
            "pincode": "411001",
        }
        create_res = self.client.post(reverse("shops:shop-create"), replacement_data, format="json")
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(create_res.data["id"], shop_id)

    def test_super_admin_permanent_delete_with_query_param_confirmation(self):
        """Super Admin can provide confirmation via query parameter ?confirm=true."""
        self.authenticate_admin()
        response = self.client.delete(f"{self.delete_url}?confirm=true")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Shop.objects.filter(pk=self.shop.pk).exists())

    def test_super_admin_permanent_delete_nonexistent_shop_returns_404(self):
        """Super Admin deleting nonexistent shop returns 404."""
        self.authenticate_admin()
        non_existent_url = reverse("shops:shop-admin-delete", kwargs={"pk": 999999})
        response = self.client.delete(f"{non_existent_url}?confirm=true")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_merchant_cannot_delete_shop(self):
        """Merchants cannot delete shops; requests return 403."""
        self.authenticate_merchant()

        res1 = self.client.delete(self.merchant_url_me)
        self.assertEqual(res1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res1.data.get("code"), "SHOP_DELETION_NOT_PERMITTED")

        res2 = self.client.delete(reverse("shops:shop-create"))
        self.assertEqual(res2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res2.data.get("code"), "SHOP_DELETION_NOT_PERMITTED")

        res3 = self.client.delete(self.delete_url)
        self.assertEqual(res3.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_delete_shop(self):
        """Unauthenticated requests to delete endpoint return 401."""
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PublicShopAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="merchant_public",
            email="merchant_public@example.com",
            mobile_number="+919876543501",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Public Corner Grocery",
            description="Fresh daily produce and staples",
            address_line="505 Market Road",
            area="Kothrud",
            city="Pune",
            state="Maharashtra",
            pincode="411038",
            contact_number=self.user.mobile_number,
            status=Shop.Status.ACTIVE,
            is_temporarily_closed=False,
            opening_time=datetime.time(8, 0),
            closing_time=datetime.time(22, 0),
            is_home_delivery_enabled=True,
            is_pickup_enabled=True,
            delivery_fee_type=Shop.DeliveryFeeType.FIXED,
            delivery_charge=Decimal("25.00"),
        )
        self.public_url = reverse("shops:shop-public-detail", kwargs={"public_slug": self.shop.public_slug})

    def test_anonymous_customer_can_retrieve_active_shop_details(self):
        """Unauthenticated customer retrieves public shop details via public slug."""
        response = self.client.get(self.public_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Approved public fields
        self.assertEqual(response.data["public_slug"], self.shop.public_slug)
        self.assertEqual(response.data["name"], self.shop.name)
        self.assertEqual(response.data["description"], self.shop.description)
        self.assertEqual(response.data["address_line"], self.shop.address_line)
        self.assertEqual(response.data["area"], self.shop.area)
        self.assertEqual(response.data["city"], self.shop.city)
        self.assertEqual(response.data["state"], self.shop.state)
        self.assertEqual(response.data["pincode"], self.shop.pincode)
        self.assertEqual(response.data["contact_number"], self.shop.contact_number)
        self.assertFalse(response.data["is_temporarily_closed"])
        self.assertEqual(response.data["opening_time"], "08:00:00")
        self.assertEqual(response.data["closing_time"], "22:00:00")
        self.assertTrue(response.data["is_home_delivery_enabled"])
        self.assertTrue(response.data["is_pickup_enabled"])
        self.assertEqual(response.data["delivery_fee_type"], "FIXED")
        self.assertEqual(Decimal(str(response.data["delivery_charge"])), Decimal("25.00"))

        # Strictly private/internal fields MUST be omitted
        self.assertNotIn("id", response.data)
        self.assertNotIn("merchant", response.data)
        self.assertNotIn("merchant_id", response.data)
        self.assertNotIn("status", response.data)
        self.assertNotIn("created_at", response.data)
        self.assertNotIn("updated_at", response.data)

    def test_temporary_closed_shop_returns_200_with_closed_flag(self):
        """When shop is temporarily closed, customer receives 200 with is_temporarily_closed=True."""
        self.shop.is_temporarily_closed = True
        self.shop.save(update_fields=["is_temporarily_closed"])

        response = self.client.get(self.public_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_temporarily_closed"])
        self.assertEqual(response.data["name"], self.shop.name)

    def test_deactivated_shop_returns_404_shop_unavailable(self):
        """Customer accessing deactivated shop receives 404 with SHOP_UNAVAILABLE."""
        self.shop.deactivate()

        response = self.client.get(self.public_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "SHOP_UNAVAILABLE")

    def test_suspended_shop_returns_404_shop_unavailable(self):
        """Customer accessing suspended shop receives 404 with SHOP_UNAVAILABLE."""
        self.shop.suspend()

        response = self.client.get(self.public_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "SHOP_UNAVAILABLE")

    def test_nonexistent_public_slug_returns_404_shop_not_found(self):
        """Accessing nonexistent public slug returns 404 SHOP_NOT_FOUND."""
        nonexistent_url = reverse("shops:shop-public-detail", kwargs={"public_slug": "nonexistent99"})
        response = self.client.get(nonexistent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "SHOP_NOT_FOUND")

    def test_database_id_cannot_be_used_in_public_endpoint(self):
        """Querying by database ID string in public slug path returns 404 if not matching slug."""
        id_url = reverse("shops:shop-public-detail", kwargs={"public_slug": str(self.shop.pk)})
        response = self.client.get(id_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_user_accessing_public_api_receives_only_public_data(self):
        """Authenticated users (merchants/admins) accessing public API receive only public fields."""
        auth_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        token = auth_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(self.public_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("id", response.data)
        self.assertNotIn("merchant", response.data)
        self.assertNotIn("status", response.data)




