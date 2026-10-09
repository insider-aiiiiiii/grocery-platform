import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from shops.models import Shop
from users.models import Merchant, User


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
