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



