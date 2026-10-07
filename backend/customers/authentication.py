import hashlib
from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import BasePermission

from customers.models import CustomerSession


class CustomerSessionAuthentication(BaseAuthentication):
    """Authenticate the dedicated opaque Customer cookie, never platform JWTs."""

    def authenticate(self, request):
        from django.conf import settings

        cookie_name = getattr(settings, "CUSTOMER_SESSION_COOKIE_NAME", "customer_session")
        secret = request.COOKIES.get(cookie_name)
        if not secret:
            raise AuthenticationFailed("A valid Customer session is required.")

        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            if not request.META.get("HTTP_ORIGIN"):
                raise PermissionDenied("Origin header is required for Customer state changes.")

        digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        session = (
            CustomerSession.objects.select_related("customer", "customer__shop")
            .filter(
                token_digest=digest,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
                created_at__gt=timezone.now() - timedelta(days=30),
            )
            .first()
        )
        if session is None:
            raise AuthenticationFailed("A valid Customer session is required.")

        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            # DRF APIViews are otherwise CSRF-exempt. Django validates the supplied
            # Origin against same-origin / CSRF_TRUSTED_ORIGINS and checks the token.
            SessionAuthentication().enforce_csrf(request)

        return session.customer, session

    def authenticate_header(self, request):
        return "CustomerSession"


class HasCustomerSession(BasePermission):
    """Allow only requests authenticated by the dedicated Customer session."""

    def has_permission(self, request, view):
        return (
            isinstance(request.auth, CustomerSession)
            and request.user.pk == request.auth.customer_id
            and request.auth.is_active
        )
