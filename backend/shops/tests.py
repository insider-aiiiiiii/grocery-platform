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

    def test_shop_deletion_removes_merchant_and_user(self):
        """Verify permanent deletion of Shop removes the Merchant profile and User credentials."""
        user = User.objects.create_user(
            username="delete_merchant",
            mobile_number="+919988776655",
            password="testpassword123",
            role=User.Role.MERCHANT,
        )
        merchant = Merchant.objects.create(user=user)
        shop = Shop.objects.create(
            merchant=merchant,
            name="Delete Shop",
            address_line="Line 1",
            area="Area 1",
            city="City 1",
            state="State 1",
            pincode="123456",
            contact_number=user.mobile_number,
        )
        shop_id = shop.id
        merchant_id = merchant.id
        user_id = user.id

        shop.delete()

        self.assertFalse(Shop.objects.filter(id=shop_id).exists())
        self.assertFalse(Merchant.objects.filter(id=merchant_id).exists())
        self.assertFalse(User.objects.filter(id=user_id).exists())

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

    def test_merchant_cannot_create_second_shop(self):
        """Enforces one-Shop-per-Merchant invariant: second creation returns 400 SHOP_ALREADY_EXISTS."""
        self.authenticate_user(self.user)
        self.client.post(self.url, self.valid_shop_data(), format="json")

        # Second attempt
        response = self.client.post(self.url, self.valid_shop_data(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("code"), "SHOP_ALREADY_EXISTS")

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


