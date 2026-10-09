from rest_framework.permissions import BasePermission
from users.models import Merchant, User


class IsActiveMerchant(BasePermission):
    """Permission check ensuring the authenticated user is an active Merchant."""

    message = "Only active merchants can perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "role", None) != User.Role.MERCHANT:
            return False
        merchant = getattr(user, "merchant", None)
        return merchant is not None and merchant.status == Merchant.Status.ACTIVE
