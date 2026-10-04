from django.test import TestCase

from .models import User


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
