from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import Merchant, User, UserAuthSession


class RefreshTokenConcurrencyTests(TransactionTestCase):
    """Exercise session row locking using independent database connections."""

    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(
            username="refresh-lock-merchant",
            mobile_number="+919876541001",
            password="test-password-123",
            role=User.Role.MERCHANT,
        )
        Merchant.objects.create(user=self.user, status=Merchant.Status.ACTIVE)
        login = APIClient().post(
            reverse("auth-login"),
            {
                "mobile_number": self.user.mobile_number,
                "password": "test-password-123",
            },
            format="json",
        )
        self.assertEqual(login.status_code, 200, login.data)
        self.refresh_token = login.data["refresh"]

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_refresh_rotation_accepts_token_only_once(self):
        barrier = Barrier(2)
        from users.views import lock_active_session

        def synchronize_before_lock(session):
            barrier.wait(timeout=10)
            return lock_active_session(session)

        def rotate():
            close_old_connections()
            try:
                client = APIClient()
                response = client.post(
                    reverse("auth-refresh"),
                    {"refresh": self.refresh_token},
                    format="json",
                )
                return response.status_code
            finally:
                close_old_connections()

        with patch("users.views.lock_active_session", side_effect=synchronize_before_lock):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: rotate(), range(2)))

        self.assertCountEqual(results, [200, 401])
        self.assertEqual(UserAuthSession.objects.filter(user=self.user).count(), 1)
        session = UserAuthSession.objects.get(user=self.user)
        self.assertNotEqual(session.refresh_token.token, self.refresh_token)

