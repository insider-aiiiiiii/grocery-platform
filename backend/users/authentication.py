from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .exceptions import PasswordChangeRequired
from .models import Merchant, MerchantAuthSession, User


ALLOWED_RESTRICTED_PATHS = {
    "/api/v1/auth/change-password/",
    "/api/v1/auth/logout/",
    "/api/v1/auth/refresh/",
}


class MerchantJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        if user.role != User.Role.MERCHANT:
            raise AuthenticationFailed("Invalid authentication credentials.")
        merchant = Merchant.objects.filter(user=user).only("status").first()
        if merchant is None or merchant.status != Merchant.Status.ACTIVE:
            raise AuthenticationFailed("Invalid authentication credentials.")
        session_id = token.get("session_id")
        if not session_id or not MerchantAuthSession.objects.filter(
            session_id=session_id, user=user
        ).exists():
            raise AuthenticationFailed("Invalid authentication credentials.")
        if token.get("must_change_password") and request.path not in ALLOWED_RESTRICTED_PATHS:
            raise PasswordChangeRequired()
        return user, token
