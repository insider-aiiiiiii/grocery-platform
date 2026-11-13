import hashlib

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class LoginAttemptThrottle(SimpleRateThrottle):
    """Limit login attempts per client IP and submitted account identifier."""

    scope = "login"

    def get_rate(self):
        return getattr(settings, "LOGIN_THROTTLE_RATE", "10/min")

    def get_cache_key(self, request, view):
        data = request.data if hasattr(request.data, "get") else {}
        account = str(data.get("mobile_number") or data.get("identifier") or "").strip().lower()
        digest = hashlib.sha256(account.encode()).hexdigest()[:32]
        return self.cache_format % {"scope": self.scope, "ident": f"{self.get_ident(request)}:{digest}"}
