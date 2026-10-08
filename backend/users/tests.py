from django.contrib.auth import authenticate
from django.contrib.auth import get_backends
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Merchant, User


class UserRoleTests(TestCase):
    def create_super_admin(self, username, email, mobile_number, password="test-password"):
        return User.objects.create_user(
            username=username,
            email=email,
            mobile_number=mobile_number,
            password=password,
            role=User.Role.SUPER_ADMIN,
        )

    def create_merchant(self, username, mobile_number, email=None):
        user = User.objects.create_user(
            username=username,
            email=email,
            mobile_number=mobile_number,
            password="test-password",
            role=User.Role.MERCHANT,
        )
        return Merchant.objects.create(user=user)

    def test_merchant_user_has_merchant_role(self):
        merchant = self.create_merchant("merchant-one", "+911234567890")

        self.assertEqual(merchant.user.role, User.Role.MERCHANT)
        self.assertFalse(merchant.user.is_staff)

    def test_super_admin_user_has_super_admin_role(self):
        user = self.create_super_admin(
            "platform-admin", "admin@example.com", "+919876543210"
        )

        self.assertEqual(user.role, User.Role.SUPER_ADMIN)
        self.assertFalse(user.is_staff)
        self.assertNotIn("shop", {field.name for field in User._meta.get_fields()})

    def test_multiple_super_admin_accounts_are_supported(self):
        first = self.create_super_admin(
            "platform-admin-one", "one@example.com", "+919876543210"
        )
        second = self.create_super_admin(
            "platform-admin-two", "two@example.com", "+918765432109"
        )

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(User.objects.filter(role=User.Role.SUPER_ADMIN).count(), 2)

    def test_customer_is_not_an_authenticated_user_role(self):
        self.assertEqual(
            User._meta.get_field("role").choices,
            User.Role.choices,
        )
        self.assertEqual(
            [role for role, _label in User.Role.choices],
            ["SUPER_ADMIN", "MERCHANT"],
        )

    def test_email_and_mobile_are_globally_unique_across_roles(self):
        self.create_merchant(
            "merchant-one", "+911234567890", "merchant@example.com"
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_super_admin(
                "platform-admin", "merchant@example.com", "+919876543210"
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_super_admin(
                "platform-admin-two", "admin@example.com", "+911234567890"
            )

    def test_super_admin_can_authenticate_with_email_or_mobile(self):
        user = self.create_super_admin(
            "platform-admin", "admin@example.com", "+919876543210"
        )

        self.assertEqual(
            authenticate(username="admin@example.com", password="test-password"),
            user,
        )
        self.assertEqual(
            authenticate(username="+919876543210", password="test-password"),
            user,
        )

    def test_super_admin_requires_at_least_one_login_identifier(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                username="platform-admin",
                password="test-password",
                role=User.Role.SUPER_ADMIN,
            )


class MerchantProfileTests(TestCase):
    def create_merchant(self, username, mobile_number, email=None):
        user = User.objects.create_user(
            username=username,
            email=email,
            mobile_number=mobile_number,
            password="test-password",
            role=User.Role.MERCHANT,
        )
        return Merchant.objects.create(user=user)

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
        self.assertIsNone(
            authenticate(username="+911234567890", password="test-password")
        )
        self.assertIsNone(get_backends()[0].get_user(merchant.user_id))

    def test_merchant_authenticates_by_mobile_and_password(self):
        merchant = self.create_merchant("merchant-one", "+911234567890")

        self.assertEqual(
            authenticate(username="+911234567890", password="test-password"),
            merchant.user,
        )

    def test_merchant_mobile_can_change_to_an_unused_value(self):
        merchant = self.create_merchant("merchant-one", "+911234567890")
        merchant.user.mobile_number = "+919876543210"
        merchant.user.save(update_fields=["mobile_number"])

        merchant.refresh_from_db()
        self.assertEqual(merchant.user.mobile_number, "+919876543210")

    def test_merchant_mobile_cannot_change_to_another_users_number(self):
        merchant = self.create_merchant("merchant-one", "+911234567890")
        self.create_merchant("merchant-two", "+919876543210")
        merchant.user.mobile_number = "+919876543210"

        with self.assertRaises(IntegrityError), transaction.atomic():
            merchant.user.save(update_fields=["mobile_number"])

    def test_super_admin_cannot_have_a_merchant_profile(self):
        user = User.objects.create_user(
            username="platform-admin",
            email="admin@example.com",
            password="test-password",
            role=User.Role.SUPER_ADMIN,
        )
        merchant = Merchant(user=user)

        with self.assertRaises(ValidationError):
            merchant.full_clean()

    def test_merchant_has_no_shop_fields(self):
        self.assertNotIn("shop", {field.name for field in Merchant._meta.get_fields()})
