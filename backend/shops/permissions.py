from users.models import Merchant
from users.permissions import IsMerchant


class IsActiveMerchant(IsMerchant):
    """Permission check ensuring the authenticated user is an active Merchant."""

    message = "Only active merchants can perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not super().has_permission(request, view):
            return False
        merchant = getattr(user, "merchant", None)
        return merchant is not None and merchant.status == Merchant.Status.ACTIVE
