from rest_framework.permissions import BasePermission

from .models import User


class IsSuperAdmin(BasePermission):
    """Allow authenticated Super Admins on explicitly privileged API operations."""

    message = "Super Admin authorization is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == User.Role.SUPER_ADMIN
        )


class IsMerchant(BasePermission):
    """Allow authenticated Merchants on explicitly merchant-only operations."""

    message = "This operation is not available for this account."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) == User.Role.MERCHANT
        )
