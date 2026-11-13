import hashlib

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


def _digest(value: str) -> str:
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()[:32]


class _LoginThrottleBase(SimpleRateThrottle):
    def get_rate(self):
        return getattr(settings, "LOGIN_THROTTLE_RATE", "10/min")


class LoginAttemptThrottle(_LoginThrottleBase):
    """Limit guesses against ONE account from one client IP.

    The key uses only the field the endpoint really authenticates with (`account_field`);
    extra junk fields in the body can no longer produce a fresh bucket per request.
    """

    scope = "login"
    account_field = "mobile_number"

    def get_cache_key(self, request, view):
        data = request.data if hasattr(request.data, "get") else {}
        account = str(data.get(self.account_field) or "")
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{self.get_ident(request)}:{_digest(account)}",
        }


class SuperAdminLoginAttemptThrottle(LoginAttemptThrottle):
    scope = "login_admin"
    account_field = "identifier"


class LoginIPThrottle(_LoginThrottleBase):
    """Limit total login attempts from one IP no matter which accounts are tried."""

    scope = "login_ip"

    def get_rate(self):
        return getattr(settings, "LOGIN_IP_THROTTLE_RATE", "30/min")

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class LoginAccountThrottle(_LoginThrottleBase):
    """Limit guesses against one account from ALL IPs (distributed guessing)."""

    scope = "login_account"
    account_field = "mobile_number"

    def get_rate(self):
        return getattr(settings, "LOGIN_ACCOUNT_THROTTLE_RATE", "20/hour")

    def get_cache_key(self, request, view):
        data = request.data if hasattr(request.data, "get") else {}
        account = str(data.get(self.account_field) or "")
        if not account.strip():
            return None
        return self.cache_format % {"scope": self.scope, "ident": _digest(account)}


class SuperAdminLoginAccountThrottle(LoginAccountThrottle):
    scope = "login_account_admin"
    account_field = "identifier"


class PublicReadThrottle(SimpleRateThrottle):
    """Per-IP cap for unauthenticated lookups that could be used to enumerate data."""

    scope = "public_lookup"

    def get_rate(self):
        return getattr(settings, "PUBLIC_LOOKUP_THROTTLE_RATE", "30/min")

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class PublicWriteThrottle(SimpleRateThrottle):
    """Per-IP cap for unauthenticated writes (cart creation, checkout)."""

    scope = "public_write"

    def get_rate(self):
        return getattr(settings, "PUBLIC_WRITE_THROTTLE_RATE", "60/min")

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
