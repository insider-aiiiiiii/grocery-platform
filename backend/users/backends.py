from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import Merchant, User


class PlatformAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifiers = {
            identifier
            for identifier in (
                username,
                kwargs.get("email"),
                kwargs.get("mobile_number"),
                kwargs.get("identifier"),
            )
            if identifier
        }
        if not password or len(identifiers) != 1:
            return None

        identifier = identifiers.pop()
        users = User.objects.filter(
            Q(role=User.Role.SUPER_ADMIN)
            & (Q(email=identifier) | Q(mobile_number=identifier))
            | Q(
                role=User.Role.MERCHANT,
                mobile_number=identifier,
                merchant__status=Merchant.Status.ACTIVE,
            )
        ).distinct()

        if users.count() != 1:
            return None

        user = users.first()
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        if not super().user_can_authenticate(user):
            return False
        if user.role == User.Role.SUPER_ADMIN:
            return bool(user.email or user.mobile_number)
        if user.role == User.Role.MERCHANT:
            return Merchant.objects.filter(
                user_id=user.pk,
                status=Merchant.Status.ACTIVE,
            ).exists()
        return False
