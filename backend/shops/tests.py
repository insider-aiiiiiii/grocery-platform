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
                status="INVALID",
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


class SuperAdminShopReactivationTests(TestCase):
    """Test suite for Super Admin Shop reactivation operation (SHOP-009)."""

    def setUp(self):
        self.client = APIClient()
        self.merchant_user = User.objects.create_user(
            username="merchant_reactivate",
            email="merchant_reactivate@example.com",
            mobile_number="+919876543501",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.admin_user = User.objects.create_user(
            username="admin_reactivate",
            email="admin_reactivate@example.com",
            mobile_number="+919876543502",
            password="securepassword123",
            role=User.Role.SUPER_ADMIN,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Reactivate Market",
            description="Testing reactivation lifecycle",
            address_line="500 FC Road",
            area="Deccan",
            city="Pune",
            state="Maharashtra",
            pincode="411004",
            contact_number=self.merchant_user.mobile_number,
            status=Shop.Status.ACTIVE,
            delivery_fee_type=Shop.DeliveryFeeType.FIXED,
            delivery_charge=Decimal("20.00"),
        )
        self.reactivate_url = reverse("shops:shop-admin-reactivate", kwargs={"pk": self.shop.pk})
        self.unsuspend_url = reverse("shops:shop-admin-unsuspend", kwargs={"pk": self.shop.pk})
        self.merchant_reactivate_url = reverse("shops:shop-me-reactivate")
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
            {"identifier": "admin_reactivate@example.com", "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return response.data

    def test_super_admin_can_reactivate_deactivated_shop(self):
        """Super Admin can reactivate a deactivated shop, returning 200 OK and updated ACTIVE status."""
        self.shop.deactivate()
        old_slug = self.shop.public_slug

        self.authenticate_admin()
        response = self.client.post(self.reactivate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ACTIVE")
        self.assertNotEqual(response.data["public_slug"], old_slug)

        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, Shop.Status.ACTIVE)
        self.assertNotEqual(self.shop.public_slug, old_slug)

    def test_super_admin_can_unsuspend_suspended_shop(self):
        """Super Admin can unsuspend a suspended shop using the unsuspend alias URL."""
        self.shop.suspend()
        old_slug = self.shop.public_slug

        self.authenticate_admin()
        response = self.client.post(self.unsuspend_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ACTIVE")
        self.assertNotEqual(response.data["public_slug"], old_slug)

        self.shop.refresh_from_db()
        self.assertEqual(self.shop.status, Shop.Status.ACTIVE)

    def test_reactivate_already_active_shop_returns_400(self):
        """Reactivating an already active shop returns 400 with SHOP_ALREADY_ACTIVE."""
        self.authenticate_admin()
        response = self.client.post(self.reactivate_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("code"), "SHOP_ALREADY_ACTIVE")

    def test_reactivation_rotates_qr_slug_and_old_slug_stops_working(self):
        """Old public slug immediately stops resolving (404) and new public slug resolves (200)."""
        old_slug = self.shop.public_slug
        old_public_url = reverse("shops:shop-public-detail", kwargs={"public_slug": old_slug})

        # Before deactivation, old slug resolves
        res = self.client.get(old_public_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Deactivate shop
        self.shop.deactivate()

        # Reactivate via Super Admin
        self.authenticate_admin()
        response = self.client.post(self.reactivate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_slug = response.data["public_slug"]
        self.assertNotEqual(new_slug, old_slug)

        # Public client resets credentials
        self.client.credentials()

        # Old slug no longer resolves
        old_res = self.client.get(old_public_url)
        self.assertEqual(old_res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(old_res.data.get("code"), "SHOP_NOT_FOUND")

        # New slug resolves successfully
        new_public_url = reverse("shops:shop-public-detail", kwargs={"public_slug": new_slug})
        new_res = self.client.get(new_public_url)
        self.assertEqual(new_res.status_code, status.HTTP_200_OK)
        self.assertEqual(new_res.data["public_slug"], new_slug)

    def test_reactivation_restores_merchant_access(self):
        """Reactivating shop restores merchant profile retrieval and update operations."""
        self.shop.deactivate()

        self.authenticate_merchant()
        me_res = self.client.get(self.merchant_url_me)
        self.assertEqual(me_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(me_res.data.get("code"), "SHOP_INACTIVE")

        # Super admin reactivates shop
        self.authenticate_admin()
        reactivate_res = self.client.post(self.reactivate_url)
        self.assertEqual(reactivate_res.status_code, status.HTTP_200_OK)
        new_slug = reactivate_res.data["public_slug"]

        # Merchant access is now restored
        self.authenticate_merchant()
        restored_res = self.client.get(self.merchant_url_me)
        self.assertEqual(restored_res.status_code, status.HTTP_200_OK)
        self.assertEqual(restored_res.data["status"], "ACTIVE")
        self.assertEqual(restored_res.data["public_slug"], new_slug)

        # Merchant can update shop profile
        patch_res = self.client.patch(
            self.merchant_url_me,
            {"description": "Updated after reactivation"},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["description"], "Updated after reactivation")

    def test_merchant_cannot_reactivate_shop(self):
        """Merchants cannot reactivate shops; attempts return 403 Forbidden."""
        self.shop.deactivate()
        self.authenticate_merchant()

        # Merchant calls /api/v1/shops/<pk>/reactivate/
        res1 = self.client.post(self.reactivate_url)
        self.assertEqual(res1.status_code, status.HTTP_403_FORBIDDEN)

        # Merchant calls /api/v1/shops/me/reactivate/
        res2 = self.client.post(self.merchant_reactivate_url)
        self.assertEqual(res2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res2.data.get("code"), "SHOP_REACTIVATION_NOT_PERMITTED")

        # Merchant calls root /api/v1/shops/reactivate/
        res3 = self.client.post(reverse("shops:shop-reactivate"))
        self.assertEqual(res3.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res3.data.get("code"), "SHOP_REACTIVATION_NOT_PERMITTED")

    def test_anonymous_user_cannot_reactivate_shop(self):
        """Unauthenticated requests to reactivate endpoint return 401 Unauthorized."""
        response = self.client.post(self.reactivate_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reactivate_nonexistent_shop_returns_404(self):
        """Attempting to reactivate a nonexistent shop returns 404 Not Found."""
        self.authenticate_admin()
        nonexistent_url = reverse("shops:shop-admin-reactivate", kwargs={"pk": 999999})
        response = self.client.post(nonexistent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_super_admin_cannot_browse_or_edit_private_shop(self):
        """Super Admin cannot browse or edit private shop profile info directly."""
        self.authenticate_admin()

        # GET /api/v1/shops/<pk>/ is not allowed (only DELETE is defined)
        admin_shop_url = reverse("shops:shop-admin-delete", kwargs={"pk": self.shop.pk})
        get_res = self.client.get(admin_shop_url)
        self.assertEqual(get_res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # PATCH /api/v1/shops/<pk>/ is not allowed
        patch_res = self.client.patch(admin_shop_url, {"name": "Admin Modified"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # PUT /api/v1/shops/<pk>/ is not allowed
        put_res = self.client.put(admin_shop_url, {"name": "Admin Modified"}, format="json")
        self.assertEqual(put_res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # GET /api/v1/shops/me/ denies Super Admin because Super Admin is not a Merchant
        me_res = self.client.get(self.merchant_url_me)
        self.assertEqual(me_res.status_code, status.HTTP_403_FORBIDDEN)


class ShopQRAndPublicLinkTests(TestCase):
    """Test suite for system-generated public Shop QR/link creation and regeneration (SHOP-010)."""

    def setUp(self):
        self.client = APIClient()
        self.merchant_user = User.objects.create_user(
            username="merchant_qr",
            email="merchant_qr@example.com",
            mobile_number="+919876543601",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.admin_user = User.objects.create_user(
            username="admin_qr",
            email="admin_qr@example.com",
            mobile_number="+919876543602",
            password="securepassword123",
            role=User.Role.SUPER_ADMIN,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="QR Grocery Mart",
            description="Testing QR link creation and regeneration",
            address_line="700 JM Road",
            area="Shivajinagar",
            city="Pune",
            state="Maharashtra",
            pincode="411005",
            contact_number=self.merchant_user.mobile_number,
            status=Shop.Status.ACTIVE,
            delivery_fee_type=Shop.DeliveryFeeType.FIXED,
            delivery_charge=Decimal("10.00"),
        )
        self.qr_regenerate_url = reverse("shops:shop-admin-regenerate-qr", kwargs={"pk": self.shop.pk})
        self.link_regenerate_url = reverse("shops:shop-admin-regenerate-link", kwargs={"pk": self.shop.pk})
        self.merchant_qr_url = reverse("shops:shop-me-qr")
        self.merchant_regenerate_qr_url = reverse("shops:shop-me-regenerate-qr")

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
            {"identifier": "admin_qr@example.com", "password": "securepassword123"},
            format="json",
        )
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return response.data

    def test_shop_creation_assigns_public_slug_and_does_not_expose_db_id(self):
        """Shop creation generates a unique 12-char hex public slug; DB ID is not used as public slug."""
        new_user = User.objects.create_user(
            username="merchant_new_qr",
            email="merchant_new_qr@example.com",
            mobile_number="+919876543603",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        Merchant.objects.create(user=new_user, status=Merchant.Status.ACTIVE, must_change_password=False)
        auth_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": new_user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {auth_res.data['access']}")

        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Brand New QR Shop",
                "description": "Unique QR test",
                "address_line": "100 FC Road",
                "area": "Deccan",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411004",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        data = create_res.data
        self.assertIn("public_slug", data)
        self.assertEqual(len(data["public_slug"]), 12)
        self.assertNotEqual(str(data["id"]), data["public_slug"])
        self.assertIn("public_url", data)
        self.assertIn(f"/api/v1/shops/public/{data['public_slug']}/", data["public_url"])

    def test_public_url_included_in_shop_serializers(self):
        """Both ShopSerializer and PublicShopSerializer expose computed public_url."""
        self.authenticate_merchant()
        me_res = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertIn("public_url", me_res.data)
        self.assertIn(self.shop.public_slug, me_res.data["public_url"])

        # Public endpoint
        self.client.credentials()
        public_url = reverse("shops:shop-public-detail", kwargs={"public_slug": self.shop.public_slug})
        pub_res = self.client.get(public_url)
        self.assertEqual(pub_res.status_code, status.HTTP_200_OK)
        self.assertIn("public_url", pub_res.data)
        self.assertIn(self.shop.public_slug, pub_res.data["public_url"])

    def test_merchant_can_retrieve_own_qr_details(self):
        """Authenticated merchant can view their shop's QR details and public link."""
        self.authenticate_merchant()
        response = self.client.get(self.merchant_qr_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["public_slug"], self.shop.public_slug)
        self.assertIn(f"/api/v1/shops/public/{self.shop.public_slug}/", response.data["public_url"])
        self.assertEqual(response.data["qr_data"], response.data["public_url"])

    def test_merchant_cannot_retrieve_qr_for_inactive_shop(self):
        """Merchant receives 403 SHOP_INACTIVE when retrieving QR for a deactivated shop."""
        self.shop.deactivate()
        self.authenticate_merchant()
        response = self.client.get(self.merchant_qr_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get("code"), "SHOP_INACTIVE")

    def test_merchant_with_no_shop_calling_qr_returns_404(self):
        """Merchant without a shop calling /me/qr/ receives 404 SHOP_NOT_FOUND."""
        no_shop_user = User.objects.create_user(
            username="merchant_no_shop_qr",
            email="noshop_qr@example.com",
            mobile_number="+919876543604",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        Merchant.objects.create(user=no_shop_user, status=Merchant.Status.ACTIVE, must_change_password=False)
        auth_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": no_shop_user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {auth_res.data['access']}")
        response = self.client.get(self.merchant_qr_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "SHOP_NOT_FOUND")

    def test_super_admin_can_regenerate_qr(self):
        """Super Admin can regenerate QR/link: rotates slug, invalidates old link, and resolves new link."""
        old_slug = self.shop.public_slug
        old_public_url = reverse("shops:shop-public-detail", kwargs={"public_slug": old_slug})

        # Old link resolves initially
        res_initial = self.client.get(old_public_url)
        self.assertEqual(res_initial.status_code, status.HTTP_200_OK)

        # Super Admin regenerates QR
        self.authenticate_admin()
        response = self.client.post(self.qr_regenerate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_slug = response.data["public_slug"]
        self.assertNotEqual(new_slug, old_slug)
        self.assertEqual(len(new_slug), 12)

        # Old link immediately returns 404 SHOP_NOT_FOUND
        self.client.credentials()
        res_old = self.client.get(old_public_url)
        self.assertEqual(res_old.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res_old.data.get("code"), "SHOP_NOT_FOUND")

        # New link immediately returns 200 OK
        new_public_url = reverse("shops:shop-public-detail", kwargs={"public_slug": new_slug})
        res_new = self.client.get(new_public_url)
        self.assertEqual(res_new.status_code, status.HTTP_200_OK)
        self.assertEqual(res_new.data["name"], self.shop.name)

        # Verify shop mappings preserved in DB
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.public_slug, new_slug)
        self.assertEqual(self.shop.merchant, self.merchant)

    def test_super_admin_regenerate_link_alias_works(self):
        """Super Admin can call /regenerate-link/ alias and successfully rotate the public slug."""
        old_slug = self.shop.public_slug
        self.authenticate_admin()
        response = self.client.post(self.link_regenerate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data["public_slug"], old_slug)

    def test_merchant_cannot_regenerate_qr(self):
        """Merchants cannot regenerate QR codes; attempts return 403 QR_REGENERATION_NOT_PERMITTED."""
        self.authenticate_merchant()

        # Merchant calls /api/v1/shops/<pk>/regenerate-qr/
        res1 = self.client.post(self.qr_regenerate_url)
        self.assertEqual(res1.status_code, status.HTTP_403_FORBIDDEN)

        # Merchant calls /api/v1/shops/me/regenerate-qr/
        res2 = self.client.post(self.merchant_regenerate_qr_url)
        self.assertEqual(res2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res2.data.get("code"), "QR_REGENERATION_NOT_PERMITTED")

        # Merchant calls /api/v1/shops/regenerate-qr/
        res3 = self.client.post(reverse("shops:shop-regenerate-qr"))
        self.assertEqual(res3.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res3.data.get("code"), "QR_REGENERATION_NOT_PERMITTED")

    def test_anonymous_user_cannot_regenerate_qr(self):
        """Unauthenticated requests to regenerate QR return 401 Unauthorized."""
        response = self.client.post(self.qr_regenerate_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regenerate_qr_for_nonexistent_shop_returns_404(self):
        """Super Admin calling regenerate-qr for nonexistent shop receives 404 Not Found."""
        self.authenticate_admin()
        nonexistent_url = reverse("shops:shop-admin-regenerate-qr", kwargs={"pk": 999999})
        response = self.client.post(nonexistent_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_public_endpoint_does_not_resolve_internal_database_id(self):
        """Querying by database ID string in public slug path returns 404 if not matching slug."""
        id_url = reverse("shops:shop-public-detail", kwargs={"public_slug": str(self.shop.pk)})
        response = self.client.get(id_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "SHOP_NOT_FOUND")


class ShopDomainE2EAndCrossTenantAuthorizationTests(TestCase):
    """End-to-End integration and multi-tenant cross-Shop authorization suite (SHOP-011)."""

    def setUp(self):
        self.client = APIClient()

        # Merchant A Setup
        self.user_a = User.objects.create_user(
            username="merchant_tenant_a",
            email="tenant_a@example.com",
            mobile_number="+919876543701",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant_a = Merchant.objects.create(
            user=self.user_a,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop_a = Shop.objects.create(
            merchant=self.merchant_a,
            name="Tenant A Supermarket",
            description="First merchant tenant",
            address_line="100 MG Road",
            area="Camp",
            city="Pune",
            state="Maharashtra",
            pincode="411001",
            contact_number=self.user_a.mobile_number,
            status=Shop.Status.ACTIVE,
            delivery_fee_type=Shop.DeliveryFeeType.FIXED,
            delivery_charge=Decimal("15.00"),
            opening_time=datetime.time(8, 0),
            closing_time=datetime.time(22, 0),
        )

        # Merchant B Setup
        self.user_b = User.objects.create_user(
            username="merchant_tenant_b",
            email="tenant_b@example.com",
            mobile_number="+919876543702",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant_b = Merchant.objects.create(
            user=self.user_b,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop_b = Shop.objects.create(
            merchant=self.merchant_b,
            name="Tenant B Grocery",
            description="Second merchant tenant",
            address_line="200 FC Road",
            area="Deccan",
            city="Pune",
            state="Maharashtra",
            pincode="411004",
            contact_number=self.user_b.mobile_number,
            status=Shop.Status.ACTIVE,
            delivery_fee_type=Shop.DeliveryFeeType.CONFIRMED_ON_WHATSAPP,
            delivery_charge=Decimal("0.00"),
            opening_time=datetime.time(9, 0),
            closing_time=datetime.time(21, 0),
        )

        # Super Admin Setup
        self.admin_user = User.objects.create_user(
            username="admin_e2e_tenant",
            email="admin_tenant@example.com",
            mobile_number="+919876543703",
            password="securepassword123",
            role=User.Role.SUPER_ADMIN,
        )

    def auth_merchant_a(self):
        res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user_a.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def auth_merchant_b(self):
        res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user_b.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def auth_admin(self):
        res = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": "admin_tenant@example.com", "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    # --- 1. Shop Creation & One-to-One Ownership ---
    def test_e2e_merchant_creates_shop_with_all_valid_fields(self):
        """Merchant without a shop creates shop: verifies all fields, phone mirroring, status defaults, and public slug."""
        new_user = User.objects.create_user(
            username="merchant_e2e_new",
            email="e2e_new@example.com",
            mobile_number="+919876543704",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        Merchant.objects.create(user=new_user, status=Merchant.Status.ACTIVE, must_change_password=False)
        auth_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": new_user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {auth_res.data['access']}")

        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "E2E Fresh Store",
                "description": "Comprehensive test store",
                "address_line": "50 Senapati Bapat Road",
                "area": "Shivajinagar",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411016",
                "opening_time": "08:30:00",
                "closing_time": "21:30:00",
                "is_home_delivery_enabled": True,
                "is_pickup_enabled": True,
                "delivery_fee_type": "FIXED",
                "delivery_charge": "25.00",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        data = create_res.data
        self.assertEqual(data["name"], "E2E Fresh Store")
        self.assertEqual(data["contact_number"], new_user.mobile_number)
        self.assertEqual(data["status"], "ACTIVE")
        self.assertEqual(len(data["public_slug"]), 12)
        self.assertNotEqual(str(data["id"]), data["public_slug"])
        self.assertIn("public_url", data)

        # Duplicate creation attempt rejected
        dup_res = self.client.post(reverse("shops:shop-create"), {"name": "Second Store"}, format="json")
        self.assertEqual(dup_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(dup_res.data.get("code"), "SHOP_ALREADY_EXISTS")

    def test_e2e_creation_ignores_client_provided_merchant_id(self):
        """Creation server-side binds authenticated merchant; client provided merchant_id is ignored."""
        new_user = User.objects.create_user(
            username="merchant_e2e_attacker",
            email="e2e_attacker@example.com",
            mobile_number="+919876543705",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        m_attacker = Merchant.objects.create(user=new_user, status=Merchant.Status.ACTIVE, must_change_password=False)
        auth_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": new_user.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {auth_res.data['access']}")

        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "merchant": self.merchant_b.pk,
                "merchant_id": self.merchant_b.pk,
                "name": "Attacker Shop",
                "address_line": "1 Road",
                "area": "Area",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        new_shop = Shop.objects.get(name="Attacker Shop")
        self.assertEqual(new_shop.merchant, m_attacker)
        self.assertNotEqual(new_shop.merchant, self.merchant_b)

    # --- 2. Profile Updates & Validation ---
    def test_e2e_merchant_updates_profile_and_read_only_fields_immutable(self):
        """Merchant updates profile via PATCH and PUT; read-only fields remain immutable."""
        self.auth_merchant_a()
        me_url = reverse("shops:shop-me")

        old_status = self.shop_a.status
        old_slug = self.shop_a.public_slug
        old_contact = self.shop_a.contact_number
        old_id = self.shop_a.pk

        # Attempt to mutate mutable fields and read-only fields
        patch_res = self.client.patch(
            me_url,
            {
                "name": "Updated Tenant A Market",
                "description": "Updated Description",
                "status": "DEACTIVATED",
                "public_slug": "tamperedslug12",
                "contact_number": "+910000000000",
                "id": 999999,
            },
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["name"], "Updated Tenant A Market")
        self.assertEqual(patch_res.data["description"], "Updated Description")
        self.assertEqual(patch_res.data["status"], old_status)
        self.assertEqual(patch_res.data["public_slug"], old_slug)
        self.assertEqual(patch_res.data["contact_number"], old_contact)
        self.assertEqual(patch_res.data["id"], old_id)

        self.shop_a.refresh_from_db()
        self.assertEqual(self.shop_a.name, "Updated Tenant A Market")
        self.assertEqual(self.shop_a.status, old_status)
        self.assertEqual(self.shop_a.public_slug, old_slug)
        self.assertEqual(self.shop_a.contact_number, old_contact)
        self.assertEqual(self.shop_a.pk, old_id)

    # --- 3. Delivery & Pickup Settings ---
    def test_e2e_delivery_and_pickup_policy_transitions(self):
        """Test transitions between FIXED fee and CONFIRMED_ON_WHATSAPP fee types."""
        self.auth_merchant_a()
        me_url = reverse("shops:shop-me")

        # Switch to CONFIRMED_ON_WHATSAPP
        res1 = self.client.patch(
            me_url,
            {"delivery_fee_type": "CONFIRMED_ON_WHATSAPP", "delivery_charge": "0.00"},
            format="json",
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data["delivery_fee_type"], "CONFIRMED_ON_WHATSAPP")
        self.assertEqual(Decimal(str(res1.data["delivery_charge"])), Decimal("0.00"))

        # Negative fee rejected
        res2 = self.client.patch(
            me_url,
            {"delivery_fee_type": "FIXED", "delivery_charge": "-10.00"},
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    # --- 4. Business Hours & Operational Closure ---
    def test_e2e_business_hours_and_temporary_closure_visibility(self):
        """Operational closure marks is_temporarily_closed without deactivating shop; visible to customers."""
        self.auth_merchant_a()
        me_url = reverse("shops:shop-me")

        close_res = self.client.patch(me_url, {"is_temporarily_closed": True}, format="json")
        self.assertEqual(close_res.status_code, status.HTTP_200_OK)
        self.assertTrue(close_res.data["is_temporarily_closed"])
        self.assertEqual(close_res.data["status"], "ACTIVE")

        # Customer public endpoint returns 200 OK with closure flag
        self.client.credentials()
        pub_url = reverse("shops:shop-public-detail", kwargs={"public_slug": self.shop_a.public_slug})
        pub_res = self.client.get(pub_url)
        self.assertEqual(pub_res.status_code, status.HTTP_200_OK)
        self.assertTrue(pub_res.data["is_temporarily_closed"])

    # --- 5. Lifecycle Activation, Deactivation, & Suspension ---
    def test_e2e_lifecycle_deactivate_reactivate_and_unsuspend(self):
        """Super Admin controls lifecycle status transitions; inactive shop blocks merchant access."""
        self.auth_admin()
        deact_url = reverse("shops:shop-admin-deactivate", kwargs={"pk": self.shop_a.pk})
        react_url = reverse("shops:shop-admin-reactivate", kwargs={"pk": self.shop_a.pk})

        # Deactivate
        res_deact = self.client.post(deact_url)
        self.assertEqual(res_deact.status_code, status.HTTP_200_OK)
        self.assertEqual(res_deact.data["status"], "DEACTIVATED")

        # Merchant locked out
        self.auth_merchant_a()
        me_res = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(me_res.data.get("code"), "SHOP_INACTIVE")

        # Public access returns SHOP_UNAVAILABLE
        self.client.credentials()
        pub_url = reverse("shops:shop-public-detail", kwargs={"public_slug": self.shop_a.public_slug})
        pub_res = self.client.get(pub_url)
        self.assertEqual(pub_res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(pub_res.data.get("code"), "SHOP_UNAVAILABLE")

        # Reactivate
        self.auth_admin()
        old_slug = self.shop_a.public_slug
        res_react = self.client.post(react_url)
        self.assertEqual(res_react.status_code, status.HTTP_200_OK)
        self.assertEqual(res_react.data["status"], "ACTIVE")
        new_slug = res_react.data["public_slug"]
        self.assertNotEqual(new_slug, old_slug)

        # Merchant access restored
        self.auth_merchant_a()
        me_restored = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_restored.status_code, status.HTTP_200_OK)
        self.assertEqual(me_restored.data["status"], "ACTIVE")

    # --- 6. Deletion & Replacement Shop Creation ---
    def test_e2e_permanent_deletion_and_replacement_shop_creation(self):
        """Super Admin permanently deletes shop with confirmation; merchant creates replacement shop."""
        self.auth_admin()
        del_url = reverse("shops:shop-admin-delete", kwargs={"pk": self.shop_a.pk})

        # Deletion without confirmation fails
        fail_res = self.client.delete(del_url)
        self.assertEqual(fail_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(fail_res.data.get("code"), "CONFIRMATION_REQUIRED")

        # Confirmed deletion succeeds
        ok_res = self.client.delete(f"{del_url}?confirm=true")
        self.assertEqual(ok_res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Shop.objects.filter(pk=self.shop_a.pk).exists())

        # Merchant credentials and account preserved
        self.user_a.refresh_from_db()
        self.merchant_a.refresh_from_db()
        self.assertTrue(self.user_a.is_active)

        # Merchant creates replacement shop
        self.auth_merchant_a()
        repl_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Tenant A Replacement Shop",
                "description": "New replacement shop identity",
                "address_line": "300 MG Road",
                "area": "Camp",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
            },
            format="json",
        )
        self.assertEqual(repl_res.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(repl_res.data["public_slug"], self.shop_a.public_slug)

    # --- 7. Public Access Data Minimization & ID Isolation ---
    def test_e2e_public_shop_strictly_omits_private_fields(self):
        """Customer accessing public endpoint receives only public store fields, no private DB fields."""
        pub_url = reverse("shops:shop-public-detail", kwargs={"public_slug": self.shop_a.public_slug})
        res = self.client.get(pub_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Public fields present
        self.assertIn("name", res.data)
        self.assertIn("public_slug", res.data)
        self.assertIn("public_url", res.data)
        self.assertIn("address_line", res.data)
        self.assertIn("contact_number", res.data)

        # Private internal fields strictly omitted
        self.assertNotIn("id", res.data)
        self.assertNotIn("merchant", res.data)
        self.assertNotIn("merchant_id", res.data)
        self.assertNotIn("status", res.data)
        self.assertNotIn("created_at", res.data)
        self.assertNotIn("updated_at", res.data)

    # --- 8. QR Behavior ---
    def test_e2e_qr_retrieval_and_regeneration_flow(self):
        """Merchant retrieves QR details; Super Admin regenerates QR and rotates public slug."""
        self.auth_merchant_a()
        qr_res = self.client.get(reverse("shops:shop-me-qr"))
        self.assertEqual(qr_res.status_code, status.HTTP_200_OK)
        self.assertEqual(qr_res.data["public_slug"], self.shop_a.public_slug)
        self.assertEqual(qr_res.data["qr_data"], qr_res.data["public_url"])

        # Super Admin regenerates QR
        self.auth_admin()
        regen_url = reverse("shops:shop-admin-regenerate-qr", kwargs={"pk": self.shop_a.pk})
        regen_res = self.client.post(regen_url)
        self.assertEqual(regen_res.status_code, status.HTTP_200_OK)
        new_slug = regen_res.data["public_slug"]
        self.assertNotEqual(new_slug, self.shop_a.public_slug)

        # Old QR link returns 404 SHOP_NOT_FOUND
        self.client.credentials()
        old_pub_url = reverse("shops:shop-public-detail", kwargs={"public_slug": self.shop_a.public_slug})
        self.assertEqual(self.client.get(old_pub_url).status_code, status.HTTP_404_NOT_FOUND)

        # New QR link returns 200 OK
        new_pub_url = reverse("shops:shop-public-detail", kwargs={"public_slug": new_slug})
        self.assertEqual(self.client.get(new_pub_url).status_code, status.HTTP_200_OK)

    # --- 9. Multi-Tenant Cross-Shop Isolation (CRITICAL) ---
    def test_cross_shop_merchant_a_cannot_view_or_update_merchant_b_shop(self):
        """Merchant A operations resolve only Merchant A's shop; cannot access or mutate Merchant B's shop."""
        self.auth_merchant_a()
        me_res = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data["id"], self.shop_a.pk)
        self.assertNotEqual(me_res.data["id"], self.shop_b.pk)

        # Updating /me/ updates only Shop A
        patch_res = self.client.patch(reverse("shops:shop-me"), {"name": "Tenant A Exclusive"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.shop_a.refresh_from_db()
        self.shop_b.refresh_from_db()
        self.assertEqual(self.shop_a.name, "Tenant A Exclusive")
        self.assertEqual(self.shop_b.name, "Tenant B Grocery")

    def test_cross_shop_body_injection_cannot_reassign_or_compromise_shop(self):
        """Injecting target shop_id or merchant_id in payload cannot reassign or compromise other tenant."""
        self.auth_merchant_a()
        patch_res = self.client.patch(
            reverse("shops:shop-me"),
            {
                "shop_id": self.shop_b.pk,
                "merchant_id": self.merchant_b.pk,
                "merchant": self.merchant_b.pk,
                "name": "Injection Attempt",
            },
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.shop_a.refresh_from_db()
        self.shop_b.refresh_from_db()
        self.assertEqual(self.shop_a.name, "Injection Attempt")
        self.assertEqual(self.shop_a.merchant, self.merchant_a)
        self.assertEqual(self.shop_b.name, "Tenant B Grocery")
        self.assertEqual(self.shop_b.merchant, self.merchant_b)

    def test_cross_shop_merchant_cannot_call_admin_lifecycle_on_other_shop(self):
        """Merchant A calling Super Admin lifecycle or delete endpoints on Shop B is rejected with 403."""
        self.auth_merchant_a()

        deact_b = reverse("shops:shop-admin-deactivate", kwargs={"pk": self.shop_b.pk})
        self.assertEqual(self.client.post(deact_b).status_code, status.HTTP_403_FORBIDDEN)

        react_b = reverse("shops:shop-admin-reactivate", kwargs={"pk": self.shop_b.pk})
        self.assertEqual(self.client.post(react_b).status_code, status.HTTP_403_FORBIDDEN)

        regen_b = reverse("shops:shop-admin-regenerate-qr", kwargs={"pk": self.shop_b.pk})
        self.assertEqual(self.client.post(regen_b).status_code, status.HTTP_403_FORBIDDEN)

        del_b = reverse("shops:shop-admin-delete", kwargs={"pk": self.shop_b.pk})
        self.assertEqual(self.client.delete(f"{del_b}?confirm=true").status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_shop_super_admin_cannot_browse_or_edit_private_shop_profile(self):
        """Super Admin cannot browse or edit private shop profile directly via API."""
        self.auth_admin()
        shop_url = reverse("shops:shop-admin-delete", kwargs={"pk": self.shop_b.pk})

        self.assertEqual(self.client.get(shop_url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.patch(shop_url, {"name": "Admin Hack"}, format="json").status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.put(shop_url, {"name": "Admin Hack"}, format="json").status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_shop_anonymous_user_blocked_from_all_private_endpoints(self):
        """Unauthenticated client cannot access private merchant endpoints."""
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(reverse("shops:shop-me"), {"name": "Anon"}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(reverse("shops:shop-create"), {"name": "Anon"}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(reverse("shops:shop-me-qr")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(reverse("shops:shop-me-deactivate")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(reverse("shops:shop-me-reactivate")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(reverse("shops:shop-me-regenerate-qr")).status_code, status.HTTP_401_UNAUTHORIZED)


class ShopLifecycleStatePermutationTests(TestCase):
    """Exhaustive state-machine and multi-actor permutation test suite.

    Tests every combination of actor (Merchant, Super Admin, Customer/Anon, Cross-Tenant)
    against every Shop state (Pre-creation, Active, Deactivated, Suspended, Reactivated,
    Deleted, Re-created, Inactive User).
    """

    def setUp(self):
        self.client = APIClient()

        # Tenant A
        self.user_a = User.objects.create_user(
            username="perm_merchant_a",
            email="perm_a@example.com",
            mobile_number="+919876543801",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant_a = Merchant.objects.create(
            user=self.user_a,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )

        # Tenant B (independent comparison tenant)
        self.user_b = User.objects.create_user(
            username="perm_merchant_b",
            email="perm_b@example.com",
            mobile_number="+919876543802",
            password="securepassword123",
            role=User.Role.MERCHANT,
        )
        self.merchant_b = Merchant.objects.create(
            user=self.user_b,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop_b = Shop.objects.create(
            merchant=self.merchant_b,
            name="Perm Tenant B Grocery",
            address_line="200 FC Road",
            area="Deccan",
            city="Pune",
            state="Maharashtra",
            pincode="411004",
            contact_number=self.user_b.mobile_number,
            status=Shop.Status.ACTIVE,
        )

        # Super Admin
        self.admin_user = User.objects.create_user(
            username="perm_admin",
            email="perm_admin@example.com",
            mobile_number="+919876543803",
            password="securepassword123",
            role=User.Role.SUPER_ADMIN,
        )

    def auth_merchant_a(self):
        res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user_a.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def auth_merchant_b(self):
        res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user_b.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def auth_admin(self):
        res = self.client.post(
            reverse("auth-super-admin-login"),
            {"identifier": "perm_admin@example.com", "password": "securepassword123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        return res.data

    def test_permutation_complete_lifecycle_step_by_step_multi_actor(self):
        """End-to-end multi-actor state transitions:
        Pre-creation -> Creation -> Active -> Deactivated -> Reactivated -> QR Regenerated -> Deleted -> Re-created.
        At every stage, checks Merchant, Super Admin, and Public visitor permissions.
        """
        # =========================================================================
        # STAGE 1: PRE-CREATION (Merchant A logged in, has NO shop)
        # =========================================================================
        self.auth_merchant_a()

        # Merchant A attempts reads and updates on non-existent shop -> 404 NO_SHOP
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.patch(reverse("shops:shop-me"), {"name": "X"}).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.put(reverse("shops:shop-me"), {"name": "X"}).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(reverse("shops:shop-me-qr")).status_code, status.HTTP_404_NOT_FOUND)

        # Merchant A attempts self-lifecycle actions -> 403 Forbidden
        self.assertEqual(self.client.post(reverse("shops:shop-me-deactivate")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(reverse("shops:shop-me-reactivate")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(reverse("shops:shop-me-regenerate-qr")).status_code, status.HTTP_403_FORBIDDEN)

        # =========================================================================
        # STAGE 2: SHOP CREATION (Merchant A creates shop)
        # =========================================================================
        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Permutation Shop A",
                "description": "Lifecycle testing shop",
                "address_line": "100 MG Road",
                "area": "Camp",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
                "is_home_delivery_enabled": True,
                "is_pickup_enabled": True,
                "delivery_charge": "30.00",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        shop_a_id = create_res.data["id"]
        slug_v1 = create_res.data["public_slug"]

        # Duplicate creation rejected
        dup_res = self.client.post(reverse("shops:shop-create"), {"name": "Dup Shop"}, format="json")
        self.assertEqual(dup_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(dup_res.data.get("code"), "SHOP_ALREADY_EXISTS")

        # =========================================================================
        # STAGE 3: SHOP IS ACTIVE
        # =========================================================================
        # Merchant A can read, patch, put, and view QR
        me_res = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data["status"], "ACTIVE")

        patch_res = self.client.patch(reverse("shops:shop-me"), {"name": "Permutation Shop A (Updated)"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["name"], "Permutation Shop A (Updated)")

        qr_res = self.client.get(reverse("shops:shop-me-qr"))
        self.assertEqual(qr_res.status_code, status.HTTP_200_OK)
        self.assertEqual(qr_res.data["public_slug"], slug_v1)

        # Merchant A cannot call admin operations on own shop
        deact_url = reverse("shops:shop-admin-deactivate", kwargs={"pk": shop_a_id})
        react_url = reverse("shops:shop-admin-reactivate", kwargs={"pk": shop_a_id})
        regen_url = reverse("shops:shop-admin-regenerate-qr", kwargs={"pk": shop_a_id})
        del_url = reverse("shops:shop-admin-delete", kwargs={"pk": shop_a_id})

        self.assertEqual(self.client.post(deact_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(react_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(regen_url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(f"{del_url}?confirm=true").status_code, status.HTTP_403_FORBIDDEN)

        # Super Admin cannot browse private merchant endpoints
        self.auth_admin()
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(reverse("shops:shop-me"), {"name": "Admin"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse("shops:shop-me-qr")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(reverse("shops:shop-create"), {"name": "Admin"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(deact_url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Public customer can access slug_v1
        self.client.credentials()
        pub_res = self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_v1}))
        self.assertEqual(pub_res.status_code, status.HTTP_200_OK)
        self.assertEqual(pub_res.data["name"], "Permutation Shop A (Updated)")

        # =========================================================================
        # STAGE 4: SUPER ADMIN DEACTIVATES SHOP
        # =========================================================================
        self.auth_admin()
        admin_deact = self.client.post(deact_url)
        self.assertEqual(admin_deact.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_deact.data["status"], "DEACTIVATED")

        # Super Admin deactivating already deactivated shop -> 400 SHOP_ALREADY_DEACTIVATED
        admin_deact_repeat = self.client.post(deact_url)
        self.assertEqual(admin_deact_repeat.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(admin_deact_repeat.data.get("code"), "SHOP_ALREADY_DEACTIVATED")

        # Merchant A is locked out of active operations
        self.auth_merchant_a()
        me_locked = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_locked.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(me_locked.data.get("code"), "SHOP_INACTIVE")

        patch_locked = self.client.patch(reverse("shops:shop-me"), {"name": "Bypass"})
        self.assertEqual(patch_locked.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(patch_locked.data.get("code"), "SHOP_INACTIVE")

        qr_locked = self.client.get(reverse("shops:shop-me-qr"))
        self.assertEqual(qr_locked.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(qr_locked.data.get("code"), "SHOP_INACTIVE")

        # Merchant A cannot create another shop while current shop is deactivated
        create_while_deact = self.client.post(reverse("shops:shop-create"), {"name": "Replacement Attempt"}, format="json")
        self.assertEqual(create_while_deact.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(create_while_deact.data.get("code"), "SHOP_ALREADY_EXISTS")

        # Public customer accessing deactivated shop receives 404 SHOP_UNAVAILABLE
        self.client.credentials()
        pub_deact = self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_v1}))
        self.assertEqual(pub_deact.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(pub_deact.data.get("code"), "SHOP_UNAVAILABLE")

        # =========================================================================
        # STAGE 5: SUPER ADMIN REACTIVATES SHOP
        # =========================================================================
        self.auth_admin()
        admin_react = self.client.post(react_url)
        self.assertEqual(admin_react.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_react.data["status"], "ACTIVE")
        slug_v2 = admin_react.data["public_slug"]
        self.assertNotEqual(slug_v2, slug_v1)

        # Super Admin reactivating already active shop -> 400 SHOP_ALREADY_ACTIVE
        admin_react_repeat = self.client.post(react_url)
        self.assertEqual(admin_react_repeat.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(admin_react_repeat.data.get("code"), "SHOP_ALREADY_ACTIVE")

        # Old slug remains 404 SHOP_NOT_FOUND
        self.client.credentials()
        self.assertEqual(
            self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_v1})).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # New slug is accessible 200 OK
        pub_v2 = self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_v2}))
        self.assertEqual(pub_v2.status_code, status.HTTP_200_OK)

        # Merchant A access fully restored
        self.auth_merchant_a()
        me_restored = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_restored.status_code, status.HTTP_200_OK)
        self.assertEqual(me_restored.data["status"], "ACTIVE")

        patch_restored = self.client.patch(reverse("shops:shop-me"), {"description": "Restored shop"}, format="json")
        self.assertEqual(patch_restored.status_code, status.HTTP_200_OK)

        qr_restored = self.client.get(reverse("shops:shop-me-qr"))
        self.assertEqual(qr_restored.status_code, status.HTTP_200_OK)
        self.assertEqual(qr_restored.data["public_slug"], slug_v2)

        # =========================================================================
        # STAGE 6: SUPER ADMIN REGENERATES QR / LINK ON ACTIVE SHOP
        # =========================================================================
        self.auth_admin()
        admin_regen = self.client.post(regen_url)
        self.assertEqual(admin_regen.status_code, status.HTTP_200_OK)
        slug_v3 = admin_regen.data["public_slug"]
        self.assertNotEqual(slug_v3, slug_v2)

        # slug_v2 invalidated
        self.client.credentials()
        self.assertEqual(
            self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_v2})).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # slug_v3 active
        self.assertEqual(
            self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_v3})).status_code,
            status.HTTP_200_OK,
        )

        # Merchant A sees slug_v3
        self.auth_merchant_a()
        qr_v3 = self.client.get(reverse("shops:shop-me-qr"))
        self.assertEqual(qr_v3.data["public_slug"], slug_v3)

        # =========================================================================
        # STAGE 7: SUPER ADMIN PERMANENT DELETION
        # =========================================================================
        self.auth_admin()

        # Delete without confirm fails
        fail_del = self.client.delete(del_url)
        self.assertEqual(fail_del.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(fail_del.data.get("code"), "CONFIRMATION_REQUIRED")

        # Delete with confirm=false fails
        fail_del2 = self.client.delete(f"{del_url}?confirm=false")
        self.assertEqual(fail_del2.status_code, status.HTTP_400_BAD_REQUEST)

        # Confirmed deletion succeeds
        ok_del = self.client.delete(f"{del_url}?confirm=true")
        self.assertEqual(ok_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Shop.objects.filter(pk=shop_a_id).exists())

        # Public access to deleted shop is 404
        self.client.credentials()
        self.assertEqual(
            self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_v3})).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # Super Admin operating on deleted shop ID -> 404
        self.auth_admin()
        self.assertEqual(self.client.post(deact_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post(react_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post(regen_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(f"{del_url}?confirm=true").status_code, status.HTTP_404_NOT_FOUND)

        # Merchant A credentials remain active
        self.user_a.refresh_from_db()
        self.merchant_a.refresh_from_db()
        self.assertTrue(self.user_a.is_active)
        self.assertEqual(self.merchant_a.status, Merchant.Status.ACTIVE)

        # Merchant A calls me -> 404 NO_SHOP
        self.auth_merchant_a()
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_404_NOT_FOUND)

        # =========================================================================
        # STAGE 8: REPLACEMENT SHOP CREATION
        # =========================================================================
        repl_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Permutation Shop A (Replacement)",
                "address_line": "500 FC Road",
                "area": "Shivajinagar",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411005",
            },
            format="json",
        )
        self.assertEqual(repl_res.status_code, status.HTTP_201_CREATED)
        slug_replacement = repl_res.data["public_slug"]
        self.assertNotEqual(slug_replacement, slug_v3)
        self.assertNotEqual(repl_res.data["id"], shop_a_id)

        # Merchant A immediately manages replacement shop
        me_repl = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_repl.status_code, status.HTTP_200_OK)
        self.assertEqual(me_repl.data["name"], "Permutation Shop A (Replacement)")

        # Public customer can access replacement shop
        self.client.credentials()
        self.assertEqual(
            self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_replacement})).status_code,
            status.HTTP_200_OK,
        )

    def test_permutation_suspended_state_and_unsuspend_flow(self):
        """Shop in SUSPENDED state blocks merchant and customer; Super Admin unsuspend restores both."""
        # Create shop for Merchant A
        self.auth_merchant_a()
        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Suspended Test Store",
                "address_line": "12 Law College Road",
                "area": "Erandwane",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411004",
            },
            format="json",
        )
        shop_id = create_res.data["id"]
        slug_v1 = create_res.data["public_slug"]

        # Directly set to SUSPENDED to simulate platform suspension
        shop = Shop.objects.get(pk=shop_id)
        shop.status = Shop.Status.SUSPENDED
        shop.save()

        # Merchant is blocked from reading or mutating suspended shop
        self.auth_merchant_a()
        me_res = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(me_res.data.get("code"), "SHOP_INACTIVE")

        patch_res = self.client.patch(reverse("shops:shop-me"), {"name": "Hack"})
        self.assertEqual(patch_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(patch_res.data.get("code"), "SHOP_INACTIVE")

        qr_res = self.client.get(reverse("shops:shop-me-qr"))
        self.assertEqual(qr_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(qr_res.data.get("code"), "SHOP_INACTIVE")

        # Public access is blocked
        self.client.credentials()
        pub_res = self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_v1}))
        self.assertEqual(pub_res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(pub_res.data.get("code"), "SHOP_UNAVAILABLE")

        # Super Admin calls unsuspend endpoint
        self.auth_admin()
        unsuspend_url = reverse("shops:shop-admin-unsuspend", kwargs={"pk": shop_id})
        unsuspend_res = self.client.post(unsuspend_url)
        self.assertEqual(unsuspend_res.status_code, status.HTTP_200_OK)
        self.assertEqual(unsuspend_res.data["status"], "ACTIVE")
        slug_v2 = unsuspend_res.data["public_slug"]
        self.assertNotEqual(slug_v2, slug_v1)

        # Merchant access is restored
        self.auth_merchant_a()
        me_restored = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_restored.status_code, status.HTTP_200_OK)
        self.assertEqual(me_restored.data["status"], "ACTIVE")

        # Public access restored on new slug
        self.client.credentials()
        self.assertEqual(
            self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_v2})).status_code,
            status.HTTP_200_OK,
        )

    def test_permutation_inactive_merchant_user_account_lifecycle(self):
        """When merchant user account is deactivated, existing token calls fail 401; login fails 401; admin lifecycle still functions."""
        self.auth_merchant_a()
        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Inactive User Store",
                "address_line": "1 Karve Road",
                "area": "Kothrud",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411038",
            },
            format="json",
        )
        shop_id = create_res.data["id"]

        # Deactivate user account while client already holds an issued JWT token
        self.user_a.is_active = False
        self.user_a.save()

        # Existing JWT token is now rejected with 401 Unauthorized across all endpoints
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.patch(reverse("shops:shop-me"), {"name": "X"}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(reverse("shops:shop-me-qr")).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(reverse("shops:shop-create"), {"name": "X"}).status_code, status.HTTP_401_UNAUTHORIZED)

        # New login attempt also rejected
        self.client.credentials()
        login_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user_a.mobile_number, "password": "securepassword123"},
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Super Admin can still manage shop even if merchant user account is inactive
        self.auth_admin()
        deact_res = self.client.post(reverse("shops:shop-admin-deactivate", kwargs={"pk": shop_id}))
        self.assertEqual(deact_res.status_code, status.HTTP_200_OK)

        react_res = self.client.post(reverse("shops:shop-admin-reactivate", kwargs={"pk": shop_id}))
        self.assertEqual(react_res.status_code, status.HTTP_200_OK)

        del_res = self.client.delete(f"{reverse('shops:shop-admin-delete', kwargs={'pk': shop_id})}?confirm=true")
        self.assertEqual(del_res.status_code, status.HTTP_204_NO_CONTENT)

    def test_permutation_asymmetric_cross_tenant_isolation(self):
        """Tenant A in DEACTIVATED state and Tenant B in ACTIVE state.
        Ensures strict tenant isolation even under different status levels.
        """
        # Create shop for Tenant A and deactivate it
        self.auth_merchant_a()
        create_a = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Tenant A Asymmetric",
                "address_line": "10 Bund Garden",
                "area": "Camp",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
            },
            format="json",
        )
        shop_a_id = create_a.data["id"]

        self.auth_admin()
        self.client.post(reverse("shops:shop-admin-deactivate", kwargs={"pk": shop_a_id}))

        # Tenant A is DEACTIVATED; Tenant B is ACTIVE
        # 1. Tenant A cannot read Tenant B's active shop
        self.auth_merchant_a()
        me_a = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_a.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(me_a.data.get("code"), "SHOP_INACTIVE")

        # 2. Tenant A cannot mutate Tenant B via payload injection
        patch_attempt = self.client.patch(
            reverse("shops:shop-me"),
            {"shop_id": self.shop_b.pk, "name": "Tenant B Overwrite Attempt"},
            format="json",
        )
        self.assertEqual(patch_attempt.status_code, status.HTTP_403_FORBIDDEN)
        self.shop_b.refresh_from_db()
        self.assertEqual(self.shop_b.name, "Perm Tenant B Grocery")

        # 3. Tenant A cannot call lifecycle endpoints on Tenant B
        deact_b = reverse("shops:shop-admin-deactivate", kwargs={"pk": self.shop_b.pk})
        self.assertEqual(self.client.post(deact_b).status_code, status.HTTP_403_FORBIDDEN)

        # 4. Tenant B operations are completely undisturbed by Tenant A's deactivation
        self.auth_merchant_b()
        me_b = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_b.status_code, status.HTTP_200_OK)
        self.assertEqual(me_b.data["name"], "Perm Tenant B Grocery")

        patch_b = self.client.patch(reverse("shops:shop-me"), {"name": "Perm Tenant B Grocery (Updated)"}, format="json")
        self.assertEqual(patch_b.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_b.data["name"], "Perm Tenant B Grocery (Updated)")

        # 5. Tenant B cannot reactivate Tenant A's shop
        react_a = reverse("shops:shop-admin-reactivate", kwargs={"pk": shop_a_id})
        self.assertEqual(self.client.post(react_a).status_code, status.HTTP_403_FORBIDDEN)

    def test_permutation_qr_regeneration_on_inactive_shop(self):
        """Super Admin can regenerate QR on an inactive shop; public link remains unavailable until shop is reactivated."""
        self.auth_merchant_a()
        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "QR Inactive Test Store",
                "address_line": "10 North Main Road",
                "area": "Koregaon Park",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411001",
            },
            format="json",
        )
        shop_id = create_res.data["id"]
        slug_initial = create_res.data["public_slug"]

        # Deactivate shop
        self.auth_admin()
        self.client.post(reverse("shops:shop-admin-deactivate", kwargs={"pk": shop_id}))

        # Regenerate QR on deactivated shop -> succeeds with rotated slug
        regen_res = self.client.post(reverse("shops:shop-admin-regenerate-qr", kwargs={"pk": shop_id}))
        self.assertEqual(regen_res.status_code, status.HTTP_200_OK)
        slug_rotated = regen_res.data["public_slug"]
        self.assertNotEqual(slug_rotated, slug_initial)

        # Public access: initial slug is 404 SHOP_NOT_FOUND
        self.client.credentials()
        res_initial = self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_initial}))
        self.assertEqual(res_initial.status_code, status.HTTP_404_NOT_FOUND)

        # Public access: rotated slug is 404 SHOP_UNAVAILABLE (because shop is deactivated!)
        res_rotated = self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_rotated}))
        self.assertEqual(res_rotated.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res_rotated.data.get("code"), "SHOP_UNAVAILABLE")

        # Reactivate shop -> slug rotates again to active slug
        self.auth_admin()
        react_res = self.client.post(reverse("shops:shop-admin-reactivate", kwargs={"pk": shop_id}))
        self.assertEqual(react_res.status_code, status.HTTP_200_OK)
        slug_active = react_res.data["public_slug"]
        self.assertNotEqual(slug_active, slug_rotated)

        # Public access: rotated slug is now 404 SHOP_NOT_FOUND
        self.client.credentials()
        self.assertEqual(
            self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_rotated})).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # Public access: active slug is 200 OK
        self.assertEqual(
            self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug_active})).status_code,
            status.HTTP_200_OK,
        )

    def test_permutation_merchant_actions_while_active_vs_superadmin_actions(self):
        """Permutation: While merchant is actively managing shop, validates Super Admin boundary actions and restrictions."""
        self.auth_merchant_a()
        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Active Matrix Store",
                "address_line": "5 Prabhat Road",
                "area": "Deccan",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411004",
                "delivery_charge": "20.00",
            },
            format="json",
        )
        shop_id = create_res.data["id"]

        # Merchant updates settings successfully
        patch_res = self.client.patch(reverse("shops:shop-me"), {"delivery_charge": "25.00"}, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["delivery_charge"], "25.00")

        # Merchant validation error: negative delivery fee rejected
        neg_res = self.client.patch(reverse("shops:shop-me"), {"delivery_charge": "-10.00"}, format="json")
        self.assertEqual(neg_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Super Admin attempts while shop is ACTIVE:
        self.auth_admin()

        # 1. Unsuspend on already active shop fails with 400 SHOP_ALREADY_ACTIVE
        self.assertEqual(
            self.client.post(reverse("shops:shop-admin-unsuspend", kwargs={"pk": shop_id})).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        # 2. Reactivate on already active shop fails with 400 SHOP_ALREADY_ACTIVE
        self.assertEqual(
            self.client.post(reverse("shops:shop-admin-reactivate", kwargs={"pk": shop_id})).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        # 3. QR regeneration succeeds without modifying active status
        regen_res = self.client.post(reverse("shops:shop-admin-regenerate-qr", kwargs={"pk": shop_id}))
        self.assertEqual(regen_res.status_code, status.HTTP_200_OK)
        self.assertEqual(regen_res.data["status"], "ACTIVE")

        # 4. Deletion without confirmation fails with 400 CONFIRMATION_REQUIRED
        self.assertEqual(
            self.client.delete(reverse("shops:shop-admin-delete", kwargs={"pk": shop_id})).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        # Shop remains active and operational
        self.auth_merchant_a()
        me_check = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_check.status_code, status.HTTP_200_OK)
        self.assertEqual(me_check.data["status"], "ACTIVE")

    def test_permutation_merchant_auth_actions_while_shop_deactivated(self):
        """Permutation: While shop is deactivated, merchant can perform auth actions (password change, refresh, logout)
        but is strictly denied from all shop domain endpoints.
        """
        self.auth_merchant_a()
        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Deact Auth Matrix Store",
                "address_line": "12 Sinhagad Road",
                "area": "Parvati",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411030",
            },
            format="json",
        )
        shop_id = create_res.data["id"]

        # Super Admin deactivates shop
        self.auth_admin()
        self.client.post(reverse("shops:shop-admin-deactivate", kwargs={"pk": shop_id}))

        # Merchant logs in again to test fresh token
        tokens = self.auth_merchant_a()
        access_token = tokens["access"]
        refresh_token = tokens["refresh"]

        # Merchant is blocked from shop domain endpoints
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(reverse("shops:shop-me"), {"name": "X"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse("shops:shop-me-qr")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.post(reverse("shops:shop-create"), {"name": "X"}).status_code, status.HTTP_400_BAD_REQUEST)

        # BUT Merchant CAN change password (user account is intact and active)
        ch_pass_res = self.client.post(
            reverse("auth-change-password"),
            {"current_password": "securepassword123", "new_password": "NewSecurePassword456!"},
            format="json",
        )
        self.assertEqual(ch_pass_res.status_code, status.HTTP_204_NO_CONTENT)

        # Merchant CAN log in with new password
        login_res = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user_a.mobile_number, "password": "NewSecurePassword456!"},
            format="json",
        )
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)
        new_refresh = login_res.data["refresh"]

        # Merchant CAN refresh token (which rotates the refresh token)
        ref_res = self.client.post(reverse("auth-refresh"), {"refresh": new_refresh}, format="json")
        self.assertEqual(ref_res.status_code, status.HTTP_200_OK)
        rotated_refresh = ref_res.data["refresh"]
        rotated_access = ref_res.data["access"]

        # Merchant CAN logout using the active rotated session
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {rotated_access}")
        logout_res = self.client.post(reverse("auth-logout"), {"refresh": rotated_refresh}, format="json")
        self.assertEqual(logout_res.status_code, status.HTTP_204_NO_CONTENT)

    def test_permutation_temporary_closure_vs_deactivation_distinction(self):
        """Permutation: Temporary closure (merchant-operated pause) vs Deactivation (super-admin-operated lifecycle).
        - Temporary closure allows merchant read/update and public read (with closed flag).
        - Deactivation completely shuts down merchant access and returns 404 on public route.
        """
        self.auth_merchant_a()
        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Closure vs Deact Store",
                "address_line": "15 Paud Road",
                "area": "Kothrud",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411038",
            },
            format="json",
        )
        shop_id = create_res.data["id"]
        slug = create_res.data["public_slug"]

        # 1. Merchant marks shop temporarily closed
        close_res = self.client.patch(reverse("shops:shop-me"), {"is_temporarily_closed": True}, format="json")
        self.assertEqual(close_res.status_code, status.HTTP_200_OK)
        self.assertTrue(close_res.data["is_temporarily_closed"])

        # Merchant can STILL read and update profile
        me_res = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data["status"], "ACTIVE")

        # Public visitor CAN access shop, sees is_temporarily_closed=True
        self.client.credentials()
        pub_res = self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug}))
        self.assertEqual(pub_res.status_code, status.HTTP_200_OK)
        self.assertTrue(pub_res.data["is_temporarily_closed"])

        # Merchant reopens shop
        self.auth_merchant_a()
        reopen_res = self.client.patch(reverse("shops:shop-me"), {"is_temporarily_closed": False}, format="json")
        self.assertEqual(reopen_res.status_code, status.HTTP_200_OK)
        self.assertFalse(reopen_res.data["is_temporarily_closed"])

        # 2. In contrast: Super Admin deactivates shop
        self.auth_admin()
        self.client.post(reverse("shops:shop-admin-deactivate", kwargs={"pk": shop_id}))

        # Merchant is completely locked out (403 SHOP_INACTIVE)
        self.auth_merchant_a()
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            self.client.patch(reverse("shops:shop-me"), {"is_temporarily_closed": False}).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        # Public access is blocked (404 SHOP_UNAVAILABLE)
        self.client.credentials()
        self.assertEqual(
            self.client.get(reverse("shops:shop-public-detail", kwargs={"public_slug": slug})).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_permutation_concurrent_shared_merchant_sessions(self):
        """Permutation: Shared merchant staff logins across multiple devices.
        When Super Admin deactivates shop, all concurrent merchant sessions are instantly locked out.
        When Super Admin reactivates shop, all concurrent merchant sessions instantly regain access.
        """
        self.auth_merchant_a()
        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Shared Session Store",
                "address_line": "7 Ferguson Road",
                "area": "Shivajinagar",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411005",
            },
            format="json",
        )
        shop_id = create_res.data["id"]

        # Staff Member 1 logs in (Device 1)
        res1 = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user_a.mobile_number, "password": "securepassword123"},
            format="json",
        )
        token_device_1 = res1.data["access"]

        # Staff Member 2 logs in (Device 2)
        res2 = self.client.post(
            reverse("auth-login"),
            {"mobile_number": self.user_a.mobile_number, "password": "securepassword123"},
            format="json",
        )
        token_device_2 = res2.data["access"]

        # Device 1 updates shop name
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_device_1}")
        dev1_res = self.client.patch(reverse("shops:shop-me"), {"name": "Staff Device 1 Update"}, format="json")
        self.assertEqual(dev1_res.status_code, status.HTTP_200_OK)

        # Device 2 reads updated shop name
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_device_2}")
        dev2_res = self.client.get(reverse("shops:shop-me"))
        self.assertEqual(dev2_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dev2_res.data["name"], "Staff Device 1 Update")

        # Super Admin deactivates shop
        self.auth_admin()
        self.client.post(reverse("shops:shop-admin-deactivate", kwargs={"pk": shop_id}))

        # BOTH Device 1 and Device 2 are immediately locked out
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_device_1}")
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_403_FORBIDDEN)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_device_2}")
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_403_FORBIDDEN)

        # Super Admin reactivates shop
        self.auth_admin()
        self.client.post(reverse("shops:shop-admin-reactivate", kwargs={"pk": shop_id}))

        # BOTH Device 1 and Device 2 immediately regain access
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_device_1}")
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_device_2}")
        self.assertEqual(self.client.get(reverse("shops:shop-me")).status_code, status.HTTP_200_OK)

    def test_permutation_cross_shop_tamper_matrix_all_parameter_types(self):
        """Permutation: Multi-vector tampering attempts by Tenant A targeting Tenant B:
        - Query parameters: ?shop_id=<b_id>, ?merchant_id=<b_id>
        - URL path traversal: /api/v1/shops/<b_id>/
        - Header or body injection: passing Tenant B IDs
        All attacks fail to leak or alter Tenant B's data.
        """
        self.auth_merchant_a()
        create_res = self.client.post(
            reverse("shops:shop-create"),
            {
                "name": "Tenant A Store",
                "address_line": "1 Tilak Road",
                "area": "Swargate",
                "city": "Pune",
                "state": "Maharashtra",
                "pincode": "411030",
            },
            format="json",
        )
        shop_a_id = create_res.data["id"]

        # 1. Query parameter tampering on /me/
        tamper_me = self.client.get(f"{reverse('shops:shop-me')}?shop_id={self.shop_b.pk}&merchant_id={self.merchant_b.pk}")
        self.assertEqual(tamper_me.status_code, status.HTTP_200_OK)
        self.assertEqual(tamper_me.data["id"], shop_a_id)  # Strictly returns Shop A
        self.assertNotEqual(tamper_me.data["id"], self.shop_b.pk)

        # 2. Query parameter tampering on /me/qr/
        tamper_qr = self.client.get(f"{reverse('shops:shop-me-qr')}?shop_id={self.shop_b.pk}")
        self.assertEqual(tamper_qr.status_code, status.HTTP_200_OK)
        self.assertEqual(tamper_qr.data["public_slug"], create_res.data["public_slug"])
        self.assertNotEqual(tamper_qr.data["public_slug"], self.shop_b.public_slug)

        # 3. Direct ID lookup on Shop B via GET /api/v1/shops/<pk>/
        # For Merchant A, admin endpoint denies with 403 Forbidden
        tamper_direct = self.client.get(reverse("shops:shop-admin-delete", kwargs={"pk": self.shop_b.pk}))
        self.assertEqual(tamper_direct.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Direct ID mutation on Shop B via PATCH /api/v1/shops/<pk>/
        # For Merchant A, admin endpoint denies with 403 Forbidden
        tamper_patch_direct = self.client.patch(
            reverse("shops:shop-admin-delete", kwargs={"pk": self.shop_b.pk}),
            {"name": "Hacked B"},
            format="json",
        )
        self.assertEqual(tamper_patch_direct.status_code, status.HTTP_403_FORBIDDEN)

        # For Super Admin, GET/PATCH on delete endpoint returns 405 Method Not Allowed (only DELETE permitted)
        self.auth_admin()
        self.assertEqual(
            self.client.get(reverse("shops:shop-admin-delete", kwargs={"pk": self.shop_b.pk})).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.patch(reverse("shops:shop-admin-delete", kwargs={"pk": self.shop_b.pk}), {"name": "H"}).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        # Return credentials to Merchant A
        self.auth_merchant_a()

        # 5. Body injection on /me/ attempting to repoint ownership or reassign fields
        body_inject = self.client.patch(
            reverse("shops:shop-me"),
            {
                "id": self.shop_b.pk,
                "merchant": self.merchant_b.pk,
                "merchant_id": self.merchant_b.pk,
                "public_slug": self.shop_b.public_slug,
                "name": "Tenant A Renamed",
            },
            format="json",
        )
        self.assertEqual(body_inject.status_code, status.HTTP_200_OK)
        self.assertEqual(body_inject.data["id"], shop_a_id)
        self.assertEqual(body_inject.data["name"], "Tenant A Renamed")

        # Verify Shop B in DB is completely untouched
        self.shop_b.refresh_from_db()
        self.assertEqual(self.shop_b.name, "Perm Tenant B Grocery")
        self.assertEqual(self.shop_b.merchant, self.merchant_b)









