import os
from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import get_backends
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Merchant,
    MerchantPasswordRecoveryChallenge,
    SuperAdminRecoveryChallenge,
    User,
    UserAuthSession,
)
from . import recovery


class AuthenticatedProbe(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from rest_framework.response import Response
        return Response({"ok": True})


class JWTTechnicalDecisionTests(TestCase):
    def test_bearer_lifetimes_and_environment_signing_key(self):
        self.assertEqual(settings.SIMPLE_JWT["AUTH_HEADER_TYPES"], ("Bearer",))
        self.assertEqual(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"], timedelta(minutes=30))
        self.assertEqual(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"], timedelta(days=30))
        self.assertEqual(settings.SIMPLE_JWT["SIGNING_KEY"], os.environ["JWT_SIGNING_KEY"])

    def test_access_jwt_values_are_not_stored_on_server_sessions(self):
        stored_fields = {field.name for field in UserAuthSession._meta.fields}
        self.assertNotIn("access_token", stored_fields)
        self.assertEqual(stored_fields, {"id", "session_id", "user", "refresh_token"})


class SuperAdminMerchantCreationAPITests(TestCase):
    url = "/api/v1/super-admin/merchants/"

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="merchant-creator-admin",
            email="merchant-creator-admin@example.com",
            mobile_number="+919100000001",
            password="Strong-admin-password-2026!",
            role=User.Role.SUPER_ADMIN,
        )

    def merchant_payload(self, **overrides):
        payload = {
            "username": "new-merchant",
            "mobile_number": "+919100000002",
            "email": "new-merchant@example.com",
            "initial_password": "Strong-merchant-password-2026!",
        }
        payload.update(overrides)
        return payload

    def test_super_admin_creates_merchant_with_forced_password_change(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(self.url, self.merchant_payload(), format="json")

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="new-merchant")
        merchant = Merchant.objects.get(user=user)
        self.assertEqual(user.role, User.Role.MERCHANT)
        self.assertTrue(user.check_password("Strong-merchant-password-2026!"))
        self.assertEqual(merchant.status, Merchant.Status.ACTIVE)
        self.assertTrue(merchant.must_change_password)
        self.assertEqual(response.data["user_id"], user.pk)
        self.assertEqual(response.data["role"], User.Role.MERCHANT)
        self.assertTrue(response.data["must_change_password"])
        self.assertNotIn("initial_password", response.data)

        login_response = self.client.post("/api/v1/auth/login/", {
            "mobile_number": user.mobile_number,
            "password": "Strong-merchant-password-2026!",
        }, format="json")
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.data["must_change_password"])

        merchant_client = APIClient()
        merchant_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        restricted_response = merchant_client.get("/api/v1/shops/me/")
        self.assertEqual(restricted_response.status_code, 403)
        change_response = merchant_client.post("/api/v1/auth/change-password/", {
            "current_password": "Strong-merchant-password-2026!",
            "new_password": "Changed-merchant-password-2026!",
        }, format="json")
        self.assertEqual(change_response.status_code, 204)

    def test_only_super_admin_can_create_merchants(self):
        self.client.force_authenticate(user=self.admin)
        self.assertEqual(
            self.client.post(self.url, self.merchant_payload(), format="json").status_code,
            201,
        )

        merchant_user = User.objects.create_user(
            username="existing-merchant",
            mobile_number="+919100000003",
            password="Strong-merchant-password-2026!",
            role=User.Role.MERCHANT,
        )
        Merchant.objects.create(user=merchant_user)
        self.client.force_authenticate(user=merchant_user)
        response = self.client.post(
            self.url,
            self.merchant_payload(username="another-merchant", mobile_number="+919100000004"),
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="another-merchant").exists())

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.post(self.url, self.merchant_payload(), format="json")

        self.assertEqual(response.status_code, 401)

    def test_duplicate_login_identifiers_and_weak_password_are_rejected(self):
        self.client.force_authenticate(user=self.admin)
        first = self.client.post(self.url, self.merchant_payload(), format="json")
        self.assertEqual(first.status_code, 201)

        duplicate_mobile = self.client.post(
            self.url,
            self.merchant_payload(username="merchant-two", email="merchant-two@example.com"),
            format="json",
        )
        weak_password = self.client.post(
            self.url,
            self.merchant_payload(
                username="merchant-three",
                mobile_number="+919100000005",
                email="merchant-three@example.com",
                initial_password="short",
            ),
            format="json",
        )

        self.assertEqual(duplicate_mobile.status_code, 400)
        self.assertEqual(weak_password.status_code, 400)
        self.assertFalse(User.objects.filter(username="merchant-three").exists())


class MerchantAuthenticationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="merchant-auth", mobile_number="+911234567890",
            password="temporary-password", role=User.Role.MERCHANT,
        )
        self.merchant = Merchant.objects.create(user=self.user)

    def _configure_recovery_sender(self):
        from django.test import override_settings
        self.sent_codes = []
        def sender(mobile_number, otp):
            self.sent_codes.append((mobile_number, otp))
        self.sender_settings = override_settings(
            MERCHANT_PASSWORD_RECOVERY_OTP_PEPPER="test-only-recovery-pepper-with-at-least-32-bytes",
            MERCHANT_PASSWORD_RECOVERY_OTP_SENDER="test.sender",
        )
        self.sender_settings.enable()
        self.sender_patch = patch("users.recovery._configured_sender", return_value=sender)
        self.sender_patch.start()

    def tearDown(self):
        if hasattr(self, "sender_settings"):
            self.sender_patch.stop()
            self.sender_settings.disable()
        super().tearDown()

    def test_recovery_request_is_generic_and_delivery_only_targets_active_merchants(self):
        self._configure_recovery_sender()
        known = self.client.post(reverse("auth-merchant-password-recovery-request"), {
            "mobile_number": self.user.mobile_number,
        }, format="json")
        unknown = self.client.post(reverse("auth-merchant-password-recovery-request"), {
            "mobile_number": "+919999999999",
        }, format="json")
        self.assertEqual(known.status_code, 202)
        self.assertEqual(unknown.status_code, 202)
        self.assertEqual(known.data, unknown.data)
        self.assertEqual(len(self.sent_codes), 1)
        self.assertEqual(self.sent_codes[0][0], self.user.mobile_number)
        self.assertEqual(len(self.sent_codes[0][1]), 7)
        self.assertTrue(self.sent_codes[0][1].isdigit())
        challenge = MerchantPasswordRecoveryChallenge.objects.get(user=self.user)
        self.assertNotEqual(self.sent_codes[0][1], challenge.otp_hash)

    def test_recovery_request_rate_limits_without_revealing_account_existence(self):
        self._configure_recovery_sender()
        url = reverse("auth-merchant-password-recovery-request")
        responses = [self.client.post(url, {"mobile_number": self.user.mobile_number}, format="json")]
        for _ in range(3):
            with self.subTest(request_number=_):
                responses.append(self.client.post(url, {
                    "mobile_number": self.user.mobile_number,
                }, format="json", REMOTE_ADDR="192.0.2.2"))
        self.assertEqual(len({response.status_code for response in responses}), 1)
        self.assertEqual(len({response.data["detail"] for response in responses}), 1)

    def test_recovery_wrong_code_attempts_are_limited_and_code_is_single_use(self):
        self._configure_recovery_sender()
        self.client.post(reverse("auth-merchant-password-recovery-request"), {
            "mobile_number": self.user.mobile_number,
        }, format="json")
        url = reverse("auth-merchant-password-recovery-confirm")
        for _ in range(recovery.OTP_ATTEMPT_LIMIT):
            response = self.client.post(url, {
                "mobile_number": self.user.mobile_number,
                "otp": "0000000",
                "new_password": "A-longer-secure-password-2026!",
            }, format="json")
            self.assertEqual(response.status_code, 400)
        challenge = MerchantPasswordRecoveryChallenge.objects.get()
        self.assertEqual(challenge.failed_attempts, recovery.OTP_ATTEMPT_LIMIT)
        self.assertIsNone(challenge.user)
        self.assertFalse(self.user.check_password("A-longer-secure-password-2026!"))

    def test_recovery_code_expires_after_five_minutes(self):
        self._configure_recovery_sender()
        self.client.post(reverse("auth-merchant-password-recovery-request"), {
            "mobile_number": self.user.mobile_number,
        }, format="json")
        challenge = MerchantPasswordRecoveryChallenge.objects.get(user=self.user)
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save(update_fields=["expires_at"])
        expired = self.client.post(reverse("auth-merchant-password-recovery-confirm"), {
            "mobile_number": self.user.mobile_number,
            "otp": self.sent_codes[0][1],
            "new_password": "A-longer-secure-password-2026!",
        }, format="json")
        self.assertEqual(expired.status_code, 400)
        self.assertFalse(self.user.check_password("A-longer-secure-password-2026!"))

    def test_successful_recovery_resets_password_and_invalidates_every_session(self):
        self._configure_recovery_sender()
        first = self.login().data
        second = self.login().data
        self.client.post(reverse("auth-merchant-password-recovery-request"), {
            "mobile_number": self.user.mobile_number,
        }, format="json")
        otp = self.sent_codes[0][1]
        response = self.client.post(reverse("auth-merchant-password-recovery-confirm"), {
            "mobile_number": self.user.mobile_number,
            "otp": otp,
            "new_password": "A-longer-secure-password-2026!",
        }, format="json")
        self.assertEqual(response.status_code, 204)
        self.user.refresh_from_db()
        self.merchant.refresh_from_db()
        self.assertTrue(self.user.check_password("A-longer-secure-password-2026!"))
        self.assertFalse(self.merchant.must_change_password)
        self.assertEqual(UserAuthSession.objects.filter(user=self.user).count(), 0)
        from rest_framework.test import APIRequestFactory
        revoked_access = AuthenticatedProbe.as_view()(APIRequestFactory().get(
            "/api/probe/", HTTP_AUTHORIZATION=f"Bearer {first['access']}"
        ))
        self.assertEqual(revoked_access.status_code, 401)
        self.assertEqual(self.client.post(reverse("auth-refresh"), {
            "refresh": first["refresh"],
        }, format="json").status_code, 401)
        self.assertEqual(self.client.post(reverse("auth-refresh"), {
            "refresh": second["refresh"],
        }, format="json").status_code, 401)
        reuse = self.client.post(reverse("auth-merchant-password-recovery-confirm"), {
            "mobile_number": self.user.mobile_number,
            "otp": otp,
            "new_password": "Another-secure-password-2026!",
        }, format="json")
        self.assertEqual(reuse.status_code, 400)

    def test_invalid_new_password_does_not_consume_recovery_code(self):
        self._configure_recovery_sender()
        self.client.post(reverse("auth-merchant-password-recovery-request"), {
            "mobile_number": self.user.mobile_number,
        }, format="json")
        otp = self.sent_codes[0][1]
        invalid = self.client.post(reverse("auth-merchant-password-recovery-confirm"), {
            "mobile_number": self.user.mobile_number,
            "otp": otp,
            "new_password": "short",
        }, format="json")
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("new_password", invalid.data)
        self.assertEqual(MerchantPasswordRecoveryChallenge.objects.get().failed_attempts, 0)

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

    def test_merchant_login_rejects_unknown_number_and_wrong_password_without_session(self):
        responses = (
            self.login(password="wrong-password"),
            self.client.post(reverse("auth-login"), {
                "mobile_number": "+919999999999",
                "password": "temporary-password",
            }, format="json"),
        )

        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.data, {"detail": "Invalid mobile number or password."})
                self.assertNotIn("access", response.data)
                self.assertNotIn("refresh", response.data)
        self.assertFalse(UserAuthSession.objects.filter(user=self.user).exists())

    def test_super_admin_is_denied_merchant_password_change_before_validation(self):
        super_admin = User.objects.create_user(
            username="password-change-admin",
            email="password-change-admin@example.com",
            mobile_number="+919876543200",
            password="admin-password",
            role=User.Role.SUPER_ADMIN,
        )
        login = self.client.post(reverse("auth-super-admin-login"), {
            "identifier": super_admin.email,
            "password": "admin-password",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        response = self.client.post(reverse("auth-change-password"), {}, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(super_admin.check_password("admin-password"))

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
        refresh_response = self.client.post(reverse("auth-refresh"), {
            "refresh": tokens["refresh"],
        }, format="json")
        self.assertEqual(refresh_response.status_code, 401)

    def _request(self, path):
        from rest_framework.test import APIRequestFactory
        request = APIRequestFactory().get(path, HTTP_AUTHORIZATION=self.client._credentials.get("HTTP_AUTHORIZATION", ""))
        return request

    def test_temporary_token_restricts_and_password_change_revokes_all_tokens(self):
        first = self.login().data
        second = self.login().data
        original_username = self.user.username
        original_mobile = self.user.mobile_number
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
        self.user.refresh_from_db()
        self.merchant.refresh_from_db()
        self.assertTrue(self.user.check_password("A-longer-secure-password-2026!"))
        self.assertNotEqual(self.user.password, "A-longer-secure-password-2026!")
        self.assertEqual(self.user.username, original_username)
        self.assertEqual(self.user.mobile_number, original_mobile)
        self.assertFalse(self.merchant.must_change_password)
        self.assertEqual(UserAuthSession.objects.filter(user=self.user).count(), 0)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {first['access']}")
        self.assertEqual(AuthenticatedProbe.as_view()(self._request("/api/probe/")).status_code, 401)
        refreshed = self.client.post(reverse("auth-refresh"), {"refresh": first["refresh"]}, format="json")
        self.assertEqual(refreshed.status_code, 401, refreshed.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {second['access']}")
        self.assertEqual(AuthenticatedProbe.as_view()(self._request("/api/probe/")).status_code, 401)
        second_refresh = self.client.post(reverse("auth-refresh"), {"refresh": second["refresh"]}, format="json")
        self.assertEqual(second_refresh.status_code, 401, second_refresh.data)
        next_login = self.login("A-longer-secure-password-2026!")
        self.assertEqual(next_login.status_code, 200)
        self.assertFalse(next_login.data["must_change_password"])

    def test_current_merchant_flag_restricts_tokens_with_a_stale_false_claim(self):
        self.merchant.must_change_password = False
        self.merchant.save(update_fields=["must_change_password"])
        tokens = self.login().data
        self.assertFalse(tokens["must_change_password"])

        # The Merchant is put into the restricted state while this access token is
        # still active. Authorization must follow the current account state, not
        # the value captured when the JWT was issued.
        self.merchant.must_change_password = True
        self.merchant.save(update_fields=["must_change_password"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = AuthenticatedProbe.as_view()(self._request("/api/probe/"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, {
            "detail": "Password change required.", "code": "PASSWORD_CHANGE_REQUIRED",
        })

        change_password = self.client.post(reverse("auth-change-password"), {
            "current_password": "temporary-password",
            "new_password": "A-longer-secure-password-2026!",
        }, format="json")
        self.assertEqual(change_password.status_code, 204)

    def test_refresh_uses_current_temporary_password_state(self):
        self.merchant.must_change_password = False
        self.merchant.save(update_fields=["must_change_password"])
        tokens = self.login().data

        self.merchant.must_change_password = True
        self.merchant.save(update_fields=["must_change_password"])
        refreshed = self.client.post(reverse("auth-refresh"), {
            "refresh": tokens["refresh"],
        }, format="json")

        self.assertEqual(refreshed.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
        restricted = AuthenticatedProbe.as_view()(self._request("/api/probe/"))
        self.assertEqual(restricted.status_code, 403)
        self.assertEqual(restricted.data["code"], "PASSWORD_CHANGE_REQUIRED")

    def test_logout_rejects_missing_or_invalid_refresh_without_revoking_session(self):
        self.merchant.must_change_password = False
        self.merchant.save(update_fields=["must_change_password"])
        tokens = self.login().data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        missing = self.client.post(reverse("auth-logout"), {}, format="json")
        invalid = self.client.post(reverse("auth-logout"), {
            "refresh": "invalid-token",
        }, format="json")

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(UserAuthSession.objects.filter(user=self.user).count(), 1)
        still_refreshable = self.client.post(reverse("auth-refresh"), {
            "refresh": tokens["refresh"],
        }, format="json")
        self.assertEqual(still_refreshable.status_code, 200)

    def test_password_change_rejects_wrong_current_password(self):
        self.merchant.must_change_password = False
        self.merchant.save(update_fields=["must_change_password"])
        tokens = self.login().data
        password_hash = self.user.password
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.client.post(reverse("auth-change-password"), {
            "current_password": "wrong-password",
            "new_password": "A-longer-secure-password-2026!",
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("current_password", response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.password, password_hash)
        self.assertEqual(UserAuthSession.objects.filter(user=self.user).count(), 1)

    def test_password_change_enforces_django_password_rules(self):
        self.merchant.must_change_password = False
        self.merchant.save(update_fields=["must_change_password"])
        tokens = self.login().data
        password_hash = self.user.password
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        for new_password in ("short", "password", "1234567890"):
            with self.subTest(new_password=new_password):
                response = self.client.post(reverse("auth-change-password"), {
                    "current_password": "temporary-password",
                    "new_password": new_password,
                }, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn("new_password", response.data)
                self.user.refresh_from_db()
                self.assertEqual(self.user.password, password_hash)
        self.assertEqual(UserAuthSession.objects.filter(user=self.user).count(), 1)

    def test_refresh_rotation_and_logout_revoke_session(self):
        first = self.login().data
        invalid = self.client.post(reverse("auth-refresh"), {"refresh": "invalid-token"}, format="json")
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(invalid.data, {"detail": "Invalid refresh token."})
        rotated = self.client.post(reverse("auth-refresh"), {"refresh": first["refresh"]}, format="json")
        self.assertEqual(rotated.status_code, 200)
        self.assertNotEqual(rotated.data["refresh"], first["refresh"])
        reused = self.client.post(reverse("auth-refresh"), {"refresh": first["refresh"]}, format="json")
        self.assertEqual(reused.status_code, 401, reused.data)
        self.assertEqual(reused.data, {"detail": "Invalid refresh token."})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {rotated.data['access']}")
        logged_out = self.client.post(reverse("auth-logout"), {"refresh": rotated.data["refresh"]}, format="json")
        self.assertEqual(logged_out.status_code, 204)
        self.assertEqual(AuthenticatedProbe.as_view()(self._request("/api/probe/")).status_code, 401)

    def test_expired_refresh_token_is_rejected_without_issuing_tokens(self):
        tokens = self.login().data
        expired = RefreshToken(tokens["refresh"])
        expired.set_exp(lifetime=timedelta(seconds=-1))

        response = self.client.post(reverse("auth-refresh"), {
            "refresh": str(expired),
        }, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {"detail": "Invalid refresh token."})
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)

    def test_logout_revokes_only_the_matching_device_session(self):
        self.merchant.must_change_password = False
        self.merchant.save(update_fields=["must_change_password"])
        first = self.login().data
        second = self.login().data
        self.assertEqual(UserAuthSession.objects.filter(user=self.user).count(), 2)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {first['access']}")
        mismatched = self.client.post(reverse("auth-logout"), {
            "refresh": second["refresh"],
        }, format="json")
        self.assertEqual(mismatched.status_code, 401)
        self.assertEqual(UserAuthSession.objects.filter(user=self.user).count(), 2)

        logged_out = self.client.post(reverse("auth-logout"), {
            "refresh": first["refresh"],
        }, format="json")
        self.assertEqual(logged_out.status_code, 204)
        self.assertEqual(UserAuthSession.objects.filter(user=self.user).count(), 1)

        from rest_framework.test import APIRequestFactory
        first_access = APIRequestFactory().get(
            "/api/probe/", HTTP_AUTHORIZATION=f"Bearer {first['access']}"
        )
        second_access = APIRequestFactory().get(
            "/api/probe/", HTTP_AUTHORIZATION=f"Bearer {second['access']}"
        )
        self.assertEqual(AuthenticatedProbe.as_view()(first_access).status_code, 401)
        self.assertEqual(AuthenticatedProbe.as_view()(second_access).status_code, 200)

        second_refresh = self.client.post(reverse("auth-refresh"), {
            "refresh": second["refresh"],
        }, format="json")
        self.assertEqual(second_refresh.status_code, 200)


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


class SuperAdminRecoveryAPITests(TestCase):
    def setUp(self):
        from unittest.mock import patch
        from django.test import override_settings

        self.client = APIClient()
        self.sent_codes = []

        def sender(contact, code):
            self.sent_codes.append((contact, code))

        self.sender_settings = override_settings(
            SUPER_ADMIN_RECOVERY_SECRET_PEPPER="a-test-super-admin-recovery-pepper-over-32-bytes",
            SUPER_ADMIN_RECOVERY_EMAIL_SENDER="test.email_sender",
            SUPER_ADMIN_RECOVERY_SMS_SENDER="test.sms_sender",
            SUPER_ADMIN_RECOVERY_CODE_TTL_SECONDS=300,
            SUPER_ADMIN_RECOVERY_REQUEST_LIMIT=3,
            SUPER_ADMIN_RECOVERY_REQUEST_WINDOW_SECONDS=3600,
            SUPER_ADMIN_RECOVERY_ATTEMPT_LIMIT=5,
            SUPER_ADMIN_RECOVERY_REAUTH_ATTEMPT_LIMIT=5,
            SUPER_ADMIN_RECOVERY_IP_REQUEST_LIMIT=10,
            SUPER_ADMIN_RECOVERY_IP_WINDOW_SECONDS=900,
        )
        self.sender_settings.enable()
        self.sender_patch = patch("users.super_admin_recovery._sender", return_value=sender)
        self.sender_patch.start()

        self.admin = self.create_super_admin(
            "admin-recovery", "admin-recovery@example.com", "+911111111111",
        )
        self.second_admin = self.create_super_admin(
            "second-admin-recovery", "second-admin@example.com", "+912222222222",
        )

    def tearDown(self):
        self.sender_patch.stop()
        self.sender_settings.disable()
        super().tearDown()

    def create_super_admin(self, username, email, mobile, password="Current-admin-password-2026!"):
        return User.objects.create_user(
            username=username,
            email=email,
            mobile_number=mobile,
            password=password,
            role=User.Role.SUPER_ADMIN,
        )

    def login(self, user, password="Current-admin-password-2026!"):
        return self.client.post(reverse("auth-super-admin-login"), {
            "identifier": user.email,
            "password": password,
        }, format="json")

    def test_self_recovery_is_generic_for_known_and_unknown_email_and_mobile(self):
        for channel, contact, unknown in (
            ("EMAIL", self.admin.email, "unknown-recovery@example.com"),
            ("MOBILE", self.admin.mobile_number, "+919999999999"),
        ):
            with self.subTest(channel=channel):
                url = reverse("auth-super-admin-recovery-request")
                known = self.client.post(url, {
                    "channel": channel, "contact": contact,
                }, format="json")
                unknown_response = self.client.post(url, {
                    "channel": channel, "contact": unknown,
                }, format="json")
                self.assertEqual(known.status_code, 202)
                self.assertEqual(known.data, unknown_response.data)
                self.assertEqual(self.sent_codes[-1][0], contact)

        challenge = SuperAdminRecoveryChallenge.objects.filter(
            purpose=SuperAdminRecoveryChallenge.Purpose.SELF_RECOVERY,
            subject=self.admin,
        ).latest("requested_at")
        self.assertNotEqual(challenge.code_hash, self.sent_codes[0][1])
        self.assertIsNone(challenge.initiated_by)
        self.assertTrue(SuperAdminRecoveryChallenge.objects.filter(
            subject__isnull=True,
        ).exists())

    def test_self_recovery_code_is_single_use_and_revokes_sessions(self):
        first = self.login(self.admin).data
        second = self.login(self.admin).data
        requested = self.client.post(reverse("auth-super-admin-recovery-request"), {
            "channel": "EMAIL", "contact": self.admin.email,
        }, format="json")
        self.assertEqual(requested.status_code, 202)
        code = self.sent_codes[-1][1]

        reset = self.client.post(reverse("auth-super-admin-recovery-confirm"), {
            "channel": "EMAIL",
            "contact": self.admin.email,
            "code": code,
            "new_password": "A-new-super-admin-password-2026!",
        }, format="json")
        self.assertEqual(reset.status_code, 204)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("A-new-super-admin-password-2026!"))
        self.assertEqual(UserAuthSession.objects.filter(user=self.admin).count(), 0)
        from rest_framework.test import APIRequestFactory
        old_access = AuthenticatedProbe.as_view()(APIRequestFactory().get(
            "/api/probe/", HTTP_AUTHORIZATION=f"Bearer {first['access']}"
        ))
        self.assertEqual(old_access.status_code, 401)
        for tokens in (first, second):
            response = self.client.post(reverse("auth-refresh"), {
                "refresh": tokens["refresh"],
            }, format="json")
            self.assertEqual(response.status_code, 401)
        reused = self.client.post(reverse("auth-super-admin-recovery-confirm"), {
            "channel": "EMAIL",
            "contact": self.admin.email,
            "code": code,
            "new_password": "Another-new-admin-password-2026!",
        }, format="json")
        self.assertEqual(reused.status_code, 400)
        self.assertEqual(self.login(self.admin, "A-new-super-admin-password-2026!").status_code, 200)

    def test_self_recovery_limits_wrong_codes_and_expired_codes(self):
        self.client.post(reverse("auth-super-admin-recovery-request"), {
            "channel": "MOBILE", "contact": self.admin.mobile_number,
        }, format="json")
        wrong_code = "0000000"
        if wrong_code == self.sent_codes[-1][1]:
            wrong_code = "0000001"
        url = reverse("auth-super-admin-recovery-confirm")
        for _ in range(5):
            response = self.client.post(url, {
                "channel": "MOBILE",
                "contact": self.admin.mobile_number,
                "code": wrong_code,
                "new_password": "A-new-super-admin-password-2026!",
            }, format="json")
            self.assertEqual(response.status_code, 400)
        challenge = SuperAdminRecoveryChallenge.objects.get(
            purpose=SuperAdminRecoveryChallenge.Purpose.SELF_RECOVERY,
            subject=self.admin,
        )
        self.assertEqual(challenge.failed_attempts, 5)

        self.client.post(reverse("auth-super-admin-recovery-request"), {
            "channel": "EMAIL", "contact": self.second_admin.email,
        }, format="json")
        expiring = SuperAdminRecoveryChallenge.objects.filter(subject=self.second_admin).get()
        expiring.expires_at = timezone.now() - timedelta(seconds=1)
        expiring.save(update_fields=["expires_at"])
        expired = self.client.post(url, {
            "channel": "EMAIL",
            "contact": self.second_admin.email,
            "code": self.sent_codes[-1][1],
            "new_password": "A-new-super-admin-password-2026!",
        }, format="json")
        self.assertEqual(expired.status_code, 400)
        self.assertFalse(self.second_admin.check_password("A-new-super-admin-password-2026!"))

    def test_administrative_reset_requires_different_admin_and_reauthentication(self):
        initiator_tokens = self.login(self.admin).data
        url = reverse("auth-super-admin-reset-request")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {initiator_tokens['access']}")
        wrong_password = self.client.post(url, {
            "target_user_id": self.second_admin.pk,
            "channel": "MOBILE",
            "current_password": "wrong-password",
        }, format="json")
        self.assertEqual(wrong_password.status_code, 400)
        self.assertFalse(SuperAdminRecoveryChallenge.objects.exists())

        self_reset = self.client.post(url, {
            "target_user_id": self.admin.pk,
            "channel": "EMAIL",
            "current_password": "Current-admin-password-2026!",
        }, format="json")
        self.assertEqual(self_reset.status_code, 400)

        request = self.client.post(url, {
            "target_user_id": self.second_admin.pk,
            "channel": "MOBILE",
            "current_password": "Current-admin-password-2026!",
        }, format="json")
        self.assertEqual(request.status_code, 202)
        self.assertEqual(self.sent_codes[-1][0], self.second_admin.mobile_number)
        challenge = SuperAdminRecoveryChallenge.objects.get(
            purpose=SuperAdminRecoveryChallenge.Purpose.ADMIN_RESET,
            subject=self.second_admin,
        )
        self.assertEqual(challenge.initiated_by, self.admin)
        self.assertIsNotNone(challenge.requested_at)

    def test_merchant_is_denied_super_admin_administrative_reset(self):
        merchant_user = User.objects.create_user(
            username="merchant-admin-reset-denied",
            mobile_number="+913333333333",
            password="merchant-password",
            role=User.Role.MERCHANT,
        )
        Merchant.objects.create(user=merchant_user, must_change_password=False)
        login = self.client.post(reverse("auth-login"), {
            "mobile_number": merchant_user.mobile_number,
            "password": "merchant-password",
        }, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        response = self.client.post(
            reverse("auth-super-admin-reset-request"), {}, format="json"
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(SuperAdminRecoveryChallenge.objects.filter(
            purpose=SuperAdminRecoveryChallenge.Purpose.ADMIN_RESET,
        ).exists())

    def test_administrative_reset_target_sets_password_and_sessions_are_revoked(self):
        initiator_tokens = self.login(self.admin).data
        affected_first = self.login(self.second_admin).data
        affected_second = self.login(self.second_admin).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {initiator_tokens['access']}")
        requested = self.client.post(reverse("auth-super-admin-reset-request"), {
            "target_user_id": self.second_admin.pk,
            "channel": "EMAIL",
            "current_password": "Current-admin-password-2026!",
        }, format="json")
        self.assertEqual(requested.status_code, 202)
        code = self.sent_codes[-1][1]

        self.client.credentials()
        completed = self.client.post(reverse("auth-super-admin-reset-confirm"), {
            "channel": "EMAIL",
            "contact": self.second_admin.email,
            "code": code,
            "new_password": "A-reset-by-affected-admin-2026!",
        }, format="json")
        self.assertEqual(completed.status_code, 204)
        self.second_admin.refresh_from_db()
        self.assertTrue(self.second_admin.check_password("A-reset-by-affected-admin-2026!"))
        self.assertFalse(self.second_admin.check_password("Current-admin-password-2026!"))
        self.assertEqual(UserAuthSession.objects.filter(user=self.second_admin).count(), 0)
        for tokens in (affected_first, affected_second):
            self.assertEqual(self.client.post(reverse("auth-refresh"), {
                "refresh": tokens["refresh"],
            }, format="json").status_code, 401)
        self.assertEqual(self.login(self.admin).status_code, 200)


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
