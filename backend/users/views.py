from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import Merchant, User, UserAuthSession
from .permissions import IsMerchant, IsSuperAdmin
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    MerchantPasswordRecoveryConfirmSerializer,
    MerchantPasswordRecoveryRequestSerializer,
    RefreshSerializer,
    SuperAdminAdministrativeResetConfirmSerializer,
    SuperAdminAdministrativeResetRequestSerializer,
    SuperAdminCreateMerchantSerializer,
    SuperAdminCreatedMerchantSerializer,
    SuperAdminRecoveryConfirmSerializer,
    SuperAdminRecoveryContactSerializer,
    SuperAdminLoginSerializer,
)
from .recovery import (
    INVALID_CODE_MESSAGE,
    confirm_merchant_password_recovery,
    request_merchant_password_recovery,
)
from .super_admin_recovery import (
    GENERIC_REQUEST_MESSAGE as SUPER_ADMIN_RECOVERY_MESSAGE,
    INVALID_CODE_MESSAGE as SUPER_ADMIN_INVALID_CODE_MESSAGE,
    confirm_super_admin_password_reset,
    request_super_admin_administrative_reset,
    request_super_admin_self_recovery,
)


def refresh_for_user(user, session_id=None, must_change_password=None):
    refresh = RefreshToken.for_user(user)
    if session_id is not None:
        refresh["session_id"] = str(session_id)
    if must_change_password is not None:
        refresh["must_change_password"] = bool(must_change_password)
    return refresh


def authorized_refresh(raw_token, *, require_session=True):
    try:
        refresh = RefreshToken(raw_token)
        user = User.objects.get(pk=refresh["user_id"])
    except (TokenError, User.DoesNotExist, KeyError, TypeError):
        raise AuthenticationFailed("Invalid refresh token.")
    if user.role not in (User.Role.MERCHANT, User.Role.SUPER_ADMIN):
        raise AuthenticationFailed("Invalid refresh token.")
    merchant = None
    if user.role == User.Role.MERCHANT:
        merchant = Merchant.objects.filter(user=user).first()
        if merchant is None or merchant.status != Merchant.Status.ACTIVE:
            raise AuthenticationFailed("Invalid refresh token.")
    elif not user.is_active:
        raise AuthenticationFailed("Invalid refresh token.")
    session = None
    if require_session:
        session = UserAuthSession.objects.filter(
            session_id=refresh.get("session_id"),
            user=user,
            refresh_token__jti=refresh["jti"],
        ).first()
        if session is None:
            raise AuthenticationFailed("Invalid refresh token.")
    return refresh, user, merchant, session


def lock_active_session(session):
    try:
        return UserAuthSession.objects.select_for_update().get(pk=session.pk)
    except UserAuthSession.DoesNotExist:
        raise AuthenticationFailed("Invalid refresh token.")


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        return "Bearer"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            mobile_number=serializer.validated_data["mobile_number"],
            password=serializer.validated_data["password"],
        )
        if user is None or user.role != User.Role.MERCHANT:
            raise AuthenticationFailed("Invalid mobile number or password.")
        merchant = Merchant.objects.filter(user=user, status=Merchant.Status.ACTIVE).first()
        if merchant is None:
            raise AuthenticationFailed("Invalid mobile number or password.")
        session = UserAuthSession(user=user)
        with transaction.atomic():
            refresh = refresh_for_user(user, session.session_id, merchant.must_change_password)
            session.refresh_token = OutstandingToken.objects.get(jti=refresh["jti"])
            session.save()
        access = refresh.access_token
        shop = getattr(merchant, "shop", None)
        shop_id = shop.id if shop else None
        return Response({
            "access": str(access),
            "refresh": str(refresh),
            "user": {"id": user.pk, "role": user.role, "shop_id": shop_id},
            "must_change_password": merchant.must_change_password,
        })


class SuperAdminLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        return "Bearer"

    def post(self, request):
        serializer = SuperAdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            identifier=serializer.validated_data["identifier"],
            password=serializer.validated_data["password"],
        )
        if (
            user is None
            or user.role != User.Role.SUPER_ADMIN
            or not user.is_active
        ):
            raise AuthenticationFailed("Invalid credentials.")

        session = UserAuthSession(user=user)
        with transaction.atomic():
            refresh = refresh_for_user(user, session.session_id, False)
            session.refresh_token = OutstandingToken.objects.get(jti=refresh["jti"])
            session.save()
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.pk,
                "role": user.role,
                "shop_id": None,
                "username": user.username,
                "email": user.email,
                "mobile_number": user.mobile_number,
            },
            "must_change_password": False,
        })


class SuperAdminCreateMerchantView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        serializer = SuperAdminCreateMerchantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        merchant = serializer.save()
        response_data = SuperAdminCreatedMerchantSerializer(merchant).data
        return Response(response_data, status=status.HTTP_201_CREATED)


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        return "Bearer"

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            old_refresh, user, merchant, session = authorized_refresh(serializer.validated_data["refresh"])
            session = lock_active_session(session)
            # Revalidate after acquiring the lock to prevent concurrent rotations.
            if session.refresh_token.jti != old_refresh["jti"]:
                raise AuthenticationFailed("Invalid refresh token.")
            old_refresh.blacklist()
            new_refresh = refresh_for_user(
                user,
                session.session_id,
                merchant.must_change_password if merchant else False,
            )
            session.refresh_token = OutstandingToken.objects.get(jti=new_refresh["jti"])
            session.save(update_fields=["refresh_token"])
        return Response({"access": str(new_refresh.access_token), "refresh": str(new_refresh)})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            refresh, _user, _merchant, session = authorized_refresh(serializer.validated_data["refresh"])
            session = lock_active_session(session)
            if request.auth.get("session_id") != str(session.session_id):
                raise AuthenticationFailed("Invalid refresh token.")
            if session.refresh_token.jti != refresh["jti"]:
                raise AuthenticationFailed("Invalid refresh token.")
            refresh.blacklist()
            session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated, IsMerchant]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            raise ValidationError({"current_password": "Current password is incorrect."})
        try:
            password_validation.validate_password(serializer.validated_data["new_password"], user)
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": list(exc.messages)})
        with transaction.atomic():
            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=["password"])
            merchant = Merchant.objects.select_for_update().get(user=user)
            merchant.must_change_password = False
            merchant.save(update_fields=["must_change_password"])
            outstanding = OutstandingToken.objects.filter(user=user)
            for token in outstanding:
                BlacklistedToken.objects.get_or_create(token=token)
            UserAuthSession.objects.filter(user=user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MerchantPasswordRecoveryRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MerchantPasswordRecoveryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = request_merchant_password_recovery(
            serializer.validated_data["mobile_number"],
            request.META.get("REMOTE_ADDR", ""),
        )
        return Response({"detail": message}, status=status.HTTP_202_ACCEPTED)


class MerchantPasswordRecoveryConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MerchantPasswordRecoveryConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_merchant_password_recovery(
                serializer.validated_data["mobile_number"],
                serializer.validated_data["otp"],
                serializer.validated_data["new_password"],
            )
        except ValueError:
            raise ValidationError({"otp": INVALID_CODE_MESSAGE})
        return Response(status=status.HTTP_204_NO_CONTENT)


class SuperAdminSelfRecoveryRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SuperAdminRecoveryContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_super_admin_self_recovery(
            serializer.validated_data["channel"],
            serializer.validated_data["contact"],
            request.META.get("REMOTE_ADDR", ""),
        )
        return Response({"detail": SUPER_ADMIN_RECOVERY_MESSAGE}, status=status.HTTP_202_ACCEPTED)


class SuperAdminSelfRecoveryConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SuperAdminRecoveryConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_super_admin_password_reset(
                purpose="SELF_RECOVERY",
                **serializer.validated_data,
            )
        except ValueError:
            raise ValidationError({"code": SUPER_ADMIN_INVALID_CODE_MESSAGE})
        return Response(status=status.HTTP_204_NO_CONTENT)


class SuperAdminAdministrativeResetRequestView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        serializer = SuperAdminAdministrativeResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_super_admin_administrative_reset(
            initiator=request.user,
            target_user_id=serializer.validated_data["target_user_id"],
            channel=serializer.validated_data["channel"],
            current_password=serializer.validated_data["current_password"],
            remote_addr=request.META.get("REMOTE_ADDR", ""),
        )
        return Response({"detail": SUPER_ADMIN_RECOVERY_MESSAGE}, status=status.HTTP_202_ACCEPTED)


class SuperAdminAdministrativeResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SuperAdminAdministrativeResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_super_admin_password_reset(
                purpose="ADMIN_RESET",
                **serializer.validated_data,
            )
        except ValueError:
            raise ValidationError({"code": SUPER_ADMIN_INVALID_CODE_MESSAGE})
        return Response(status=status.HTTP_204_NO_CONTENT)
