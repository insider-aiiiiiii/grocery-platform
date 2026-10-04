from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Merchant, User


class UserRoleTests(TestCase):
    def test_merchant_user_has_merchant_role(self):
        user = User.objects.create_user(
            username="merchant-one",
            password="test-password",
            role=User.Role.MERCHANT,
        )

        self.assertEqual(user.role, User.Role.MERCHANT)
        self.assertFalse(user.is_staff)

    def test_super_admin_user_has_super_admin_role(self):
        user = User.objects.create_user(
            username="platform-admin",
            password="test-password",
            role=User.Role.SUPER_ADMIN,
        )

        self.assertEqual(user.role, User.Role.SUPER_ADMIN)
        self.assertFalse(user.is_staff)

    def test_customer_is_not_an_authenticated_user_role(self):
        self.assertEqual(
            User._meta.get_field("role").choices,
            User.Role.choices,
        )
        self.assertEqual(
            [role for role, _label in User.Role.choices],
            ["SUPER_ADMIN", "MERCHANT"],
        )


class MerchantProfileTests(TestCase):
    def create_merchant(self, username, mobile_number, email=None):
        user = User.objects.create_user(
            username=username,
            password="test-password",
            role=User.Role.MERCHANT,
        )
        return Merchant.objects.create(
            user=user,
            mobile_number=mobile_number,
            email=email,
        )

    def test_profile_defaults_to_active_and_requires_initial_password_change(self):
        merchant = self.create_merchant("merchant-one", "+911234567890")

        self.assertEqual(merchant.status, Merchant.Status.ACTIVE)
        self.assertTrue(merchant.must_change_password)
        self.assertTrue(merchant.user.check_password("test-password"))

    def test_status_can_be_deactivated(self):
        merchant = self.create_merchant("merchant-one", "+911234567890")
        merchant.status = Merchant.Status.DEACTIVATED
        merchant.save(update_fields=["status"])

        merchant.refresh_from_db()
        self.assertEqual(merchant.status, Merchant.Status.DEACTIVATED)

    def test_mobile_number_is_unique_across_merchants(self):
        self.create_merchant("merchant-one", "+911234567890")
        user = User.objects.create_user(
            username="merchant-two",
            password="test-password",
            role=User.Role.MERCHANT,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Merchant.objects.create(user=user, mobile_number="+911234567890")

    def test_mobile_number_can_change_to_an_unused_value(self):
        merchant = self.create_merchant("merchant-one", "+911234567890")
        merchant.mobile_number = "+919876543210"
        merchant.save(update_fields=["mobile_number"])

        merchant.refresh_from_db()
        self.assertEqual(merchant.mobile_number, "+919876543210")

    def test_mobile_number_cannot_change_to_another_merchants_number(self):
        merchant = self.create_merchant("merchant-one", "+911234567890")
        self.create_merchant("merchant-two", "+919876543210")
        merchant.mobile_number = "+919876543210"

        with self.assertRaises(IntegrityError), transaction.atomic():
            merchant.save(update_fields=["mobile_number"])

    def test_email_is_unique_across_merchants(self):
        self.create_merchant(
            "merchant-one", "+911234567890", "merchant@example.com"
        )
        user = User.objects.create_user(
            username="merchant-two",
            password="test-password",
            role=User.Role.MERCHANT,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Merchant.objects.create(
                user=user,
                mobile_number="+919876543210",
                email="merchant@example.com",
            )

    def test_super_admin_cannot_have_a_merchant_profile(self):
        user = User.objects.create_user(
            username="platform-admin",
            password="test-password",
            role=User.Role.SUPER_ADMIN,
        )
        merchant = Merchant(user=user, mobile_number="+911234567890")

        with self.assertRaises(ValidationError):
            merchant.full_clean()

    def test_merchant_has_no_shop_fields(self):
        self.assertNotIn("shop", {field.name for field in Merchant._meta.get_fields()})
