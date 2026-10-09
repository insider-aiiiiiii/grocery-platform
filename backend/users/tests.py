from django.contrib.auth import authenticate
from django.contrib.auth import get_backends
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import Merchant, User


class AuthenticatedProbe(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework.response import Response
        return Response({"ok": True})


class MerchantAuthenticationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="merchant-auth", mobile_number="+911234567890",
            password="temporary-password", role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(user=self.user)

    def login(self, password="temporary-password"):
        return self.client.post(reverse("auth-login"), {
            "mobile_number": self.user.mobile_number, "password": password,
        }, format="json")

    def test_login_response_has_contract_and_temporary_flag_without_secrets(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"access", "refresh", "user", "must_change_password"})
        self.assertEqual(response.data["user"], {
            "id": self.user.pk, "role": "MERCHANT", "shop_id": None,
        })
        self.assertTrue(response.data["must_change_password"])
        self.assertNotIn("password", response.data)
        self.assertNotIn("password_hash", response.data)

    def test_missing_or_invalid_bearer_token_returns_401(self):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        missing = AuthenticatedProbe.as_view()(factory.get("/api/probe/"))
        invalid = AuthenticatedProbe.as_view()(factory.get(
            "/api/probe/", HTTP_AUTHORIZATION="Bearer invalid-token"
        ))
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(invalid.status_code, 401)

    def test_deactivated_merchant_cannot_login_or_use_existing_access(self):
        tokens = self.login().data
        self.merchant.status = Merchant.Status.DEACTIVATED
        self.merchant.save(update_fields=["status"])
        response = self.login()
        self.assertEqual(response.status_code, 401, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(AuthenticatedProbe.as_view()(self._request("/api/probe/")).status_code, 401)

    def _request(self, path):
        from rest_framework.test import APIRequestFactory
        request = APIRequestFactory().get(path, HTTP_AUTHORIZATION=self.client._credentials.get("HTTP_AUTHORIZATION", ""))
        return request

    def test_temporary_token_restricts_and_password_change_revokes_all_tokens(self):
        first = self.login().data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {first['access']}")
        request = self._request("/api/probe/")
        response = AuthenticatedProbe.as_view()(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, {
            "detail": "Password change required.", "code": "PASSWORD_CHANGE_REQUIRED",
        })
        changed = self.client.post(reverse("auth-change-password"), {
            "current_password": "temporary-password", "new_password": "A-longer-secure-password-2026!",
        }, format="json")
        self.assertEqual(changed.status_code, 204)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {first['access']}")
        self.assertEqual(AuthenticatedProbe.as_view()(self._request("/api/probe/")).status_code, 401)
        refreshed = self.client.post(reverse("auth-refresh"), {"refresh": first["refresh"]}, format="json")
        self.assertEqual(refreshed.status_code, 401, refreshed.data)
        next_login = self.login("A-longer-secure-password-2026!")
        self.assertEqual(next_login.status_code, 200)
        self.assertFalse(next_login.data["must_change_password"])

    def test_refresh_rotation_and_logout_revoke_session(self):
        first = self.login().data
        rotated = self.client.post(reverse("auth-refresh"), {"refresh": first["refresh"]}, format="json")
        self.assertEqual(rotated.status_code, 200)
        self.assertNotEqual(rotated.data["refresh"], first["refresh"])
        reused = self.client.post(reverse("auth-refresh"), {"refresh": first["refresh"]}, format="json")
        self.assertEqual(reused.status_code, 401, reused.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {rotated.data['access']}")
        logged_out = self.client.post(reverse("auth-logout"), {"refresh": rotated.data["refresh"]}, format="json")
        self.assertEqual(logged_out.status_code, 204)
        self.assertEqual(AuthenticatedProbe.as_view()(self._request("/api/probe/")).status_code, 401)


class SuperAdminAuthenticationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_admin = User.objects.create_user(
            username="super-admin-auth",
            email="admin@example.com",
            mobile_number="+919876543210",
            password="admin-password",
            role=User.Role.SUPER_ADMIN,
        )

    def login(self, identifier, password="admin-password"):
        return self.client.post(reverse("auth-super-admin-login"), {
            "identifier": identifier,
            "password": password,
        }, format="json")

    def test_super_admin_can_login_with_email_or_mobile(self):
        for identifier in (self.super_admin.email, self.super_admin.mobile_number):
            response = self.login(identifier)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["user"], {
                "id": self.super_admin.pk,
                "role": "SUPER_ADMIN",
                "shop_id": None,
            })
            self.assertFalse(response.data["must_change_password"])
            self.assertIn("access", response.data)
            self.assertIn("refresh", response.data)
            self.assertNotIn("password", response.data)

    def test_merchant_credentials_are_rejected_from_super_admin_flow(self):
        merchant_user = User.objects.create_user(
            username="merchant-wrong-flow",
            mobile_number="+911234567890",
            password="merchant-password",
            role=User.Role.MERCHANT,
        )
        Merchant.objects.create(user=merchant_user)
        response = self.login(merchant_user.mobile_number, "merchant-password")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"], "Invalid credentials.")

    def test_inactive_super_admin_cannot_login_or_keep_using_existing_tokens(self):
        tokens = self.login(self.super_admin.email).data
        self.super_admin.is_active = False
        self.super_admin.save(update_fields=["is_active"])
        rejected = self.login(self.super_admin.email)
        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(rejected.data["detail"], "Invalid credentials.")
        # Exercise the same DRF authentication stack without adding a production endpoint.
        from rest_framework.test import APIRequestFactory
        response = AuthenticatedProbe.as_view()(APIRequestFactory().get(
            "/api/probe/", HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"
        ))
        self.assertEqual(response.status_code, 401)
        refresh_response = self.client.post(reverse("auth-refresh"), {
            "refresh": tokens["refresh"],
        }, format="json")
        self.assertEqual(refresh_response.status_code, 401)

    def test_super_admin_tokens_support_refresh_logout_and_authentication(self):
        tokens = self.login(self.super_admin.email).data
        access_response = AuthenticatedProbe.as_view()(
            self._request(f"Bearer {tokens['access']}")
        )
        self.assertEqual(access_response.status_code, 200)
        rotated = self.client.post(reverse("auth-refresh"), {
            "refresh": tokens["refresh"],
        }, format="json")
        self.assertEqual(rotated.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {rotated.data['access']}")
        logged_out = self.client.post(reverse("auth-logout"), {
            "refresh": rotated.data["refresh"],
        }, format="json")
        self.assertEqual(logged_out.status_code, 204)
        self.assertEqual(
            AuthenticatedProbe.as_view()(self._request(f"Bearer {rotated.data['access']}")).status_code,
            401,
        )

    def _request(self, authorization):
        from rest_framework.test import APIRequestFactory
        return APIRequestFactory().get(
            "/api/probe/", HTTP_AUTHORIZATION=authorization
        )


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
        self.assertNotIn("shop", {field.name for field in Merchant._meta.fields})
