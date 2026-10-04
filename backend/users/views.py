from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import Merchant, User, UserAuthSession
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RefreshSerializer,
    SuperAdminLoginSerializer,
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
        return Response({
            "access": str(access),
            "refresh": str(refresh),
            "user": {"id": user.pk, "role": user.role, "shop_id": None},
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
            "user": {"id": user.pk, "role": user.role, "shop_id": None},
            "must_change_password": False,
        })


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
            session = UserAuthSession.objects.select_for_update().get(pk=session.pk)
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
            refresh, user, _merchant, session = authorized_refresh(serializer.validated_data["refresh"])
            session = UserAuthSession.objects.select_for_update().get(pk=session.pk)
            if request.auth.get("session_id") != str(session.session_id):
                raise AuthenticationFailed("Invalid refresh token.")
            if session.refresh_token.jti != refresh["jti"]:
                raise AuthenticationFailed("Invalid refresh token.")
            refresh.blacklist()
            session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if user.role != User.Role.MERCHANT:
            raise PermissionDenied("This operation is not available for this account.")
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
