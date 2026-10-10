"""Business operations for Merchant password recovery."""

import hashlib
import hmac
import secrets
from datetime import timedelta
import logging

from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string
from rest_framework.exceptions import APIException, ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import (
    Merchant,
    MerchantPasswordRecoveryChallenge,
    MerchantPasswordRecoveryIPThrottle,
    User,
    UserAuthSession,
)


OTP_LIFETIME = timedelta(minutes=5)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_REQUEST_WINDOW = timedelta(hours=1)
OTP_REQUEST_LIMIT = 3
OTP_ATTEMPT_LIMIT = 5
IP_REQUEST_WINDOW = timedelta(minutes=15)
IP_REQUEST_LIMIT = 10
OTP_DIGITS = 7
GENERIC_REQUEST_MESSAGE = "If the account is eligible, a recovery code will be sent."
INVALID_CODE_MESSAGE = "The recovery code is invalid or expired."


class RecoveryUnavailable(APIException):
    status_code = 503
    default_detail = "Password recovery is temporarily unavailable."
    default_code = "password_recovery_unavailable"


def _pepper():
    value = getattr(settings, "MERCHANT_PASSWORD_RECOVERY_OTP_PEPPER", "")
    if not value or len(value.encode("utf-8")) < 32:
        raise RecoveryUnavailable()
    return value.encode("utf-8")


def _digest(purpose, value):
    return hmac.new(_pepper(), f"{purpose}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def _configured_sender():
    path = getattr(settings, "MERCHANT_PASSWORD_RECOVERY_OTP_SENDER", "")
    if not path:
        raise RecoveryUnavailable()
    try:
        sender = import_string(path)
    except (ImportError, AttributeError, ValueError):
        raise RecoveryUnavailable() from None
    if not callable(sender):
        raise RecoveryUnavailable()
    # The adapter must enqueue delivery; waiting on a provider here can reveal
    # account existence through response timing.
    return sender


def _new_otp():
    return f"{secrets.randbelow(10 ** OTP_DIGITS):0{OTP_DIGITS}d}"


def _lock_or_create(model, lookup, defaults):
    """Get a row under a write lock, handling simultaneous first requests."""
    row, _created = model.objects.get_or_create(**lookup, defaults=defaults)
    return model.objects.select_for_update().get(pk=row.pk)


def request_merchant_password_recovery(mobile_number, remote_addr):
    """Create/rotate a challenge while returning the same result for every number."""
    sender = _configured_sender()
    now = timezone.now()
    mobile_hash = _digest("mobile", mobile_number)
    ip_hash = _digest("ip", remote_addr or "unknown")
    otp = _new_otp()
    otp_hash = _digest("otp", otp)
    should_send = False

    with transaction.atomic():
        ip_row = _lock_or_create(
            MerchantPasswordRecoveryIPThrottle,
            {"ip_hash": ip_hash},
            {"window_started_at": now, "request_count": 0},
        )
        if now - ip_row.window_started_at >= IP_REQUEST_WINDOW:
            ip_row.window_started_at = now
            ip_row.request_count = 0
        ip_allowed = ip_row.request_count < IP_REQUEST_LIMIT
        if ip_allowed:
            ip_row.request_count += 1
        ip_row.save(update_fields=["window_started_at", "request_count"])

        challenge = _lock_or_create(
            MerchantPasswordRecoveryChallenge,
            {"mobile_hash": mobile_hash},
            {
                "otp_hash": otp_hash, "created_at": now,
                "expires_at": now, "request_window_started_at": now,
                "request_count": 0,
            },
        )
        if now - challenge.request_window_started_at >= OTP_REQUEST_WINDOW:
            challenge.request_window_started_at = now
            challenge.request_count = 0
        cooldown_elapsed = (
            challenge.last_sent_at is None
            or now - challenge.last_sent_at >= OTP_RESEND_COOLDOWN
        )
        under_limits = (
            ip_allowed
            and challenge.request_count < OTP_REQUEST_LIMIT
            and cooldown_elapsed
        )

        user = User.objects.filter(
            mobile_number=mobile_number,
            role=User.Role.MERCHANT,
            is_active=True,
            merchant__status=Merchant.Status.ACTIVE,
        ).first()
        if under_limits:
            challenge.request_count += 1
            challenge.created_at = now
            challenge.expires_at = now + OTP_LIFETIME
            challenge.failed_attempts = 0
            challenge.last_sent_at = now
            if user is not None:
                challenge.user = user
                challenge.otp_hash = otp_hash
                should_send = True
            else:
                # Unknown numbers receive indistinguishable, unusable state.
                challenge.user = None
                challenge.otp_hash = _digest("otp", _new_otp())
        challenge.save()

    if should_send:
        try:
            sender(mobile_number, otp)
        except Exception:
            # Do not include provider details, the phone number, or the OTP in logs.
            logging.getLogger(__name__).warning("Merchant recovery OTP delivery failed.")
            MerchantPasswordRecoveryChallenge.objects.filter(
                mobile_hash=mobile_hash, otp_hash=otp_hash,
            ).update(
                user=None, expires_at=now,
            )
    return GENERIC_REQUEST_MESSAGE


def confirm_merchant_password_recovery(mobile_number, otp, new_password):
    """Verify one recovery code and reset the password, atomically revoking sessions."""
    mobile_hash = _digest("mobile", mobile_number)
    now = timezone.now()
    valid_code = False
    password_error = None
    with transaction.atomic():
        challenge = MerchantPasswordRecoveryChallenge.objects.select_for_update().filter(
            mobile_hash=mobile_hash,
        ).first()
        if challenge is None:
            raise ValueError(INVALID_CODE_MESSAGE)
        valid_code = (
            challenge.expires_at > now
            and challenge.failed_attempts < OTP_ATTEMPT_LIMIT
            and hmac.compare_digest(challenge.otp_hash, _digest("otp", otp))
        )
        if not valid_code:
            if challenge.expires_at > now and challenge.failed_attempts < OTP_ATTEMPT_LIMIT:
                challenge.failed_attempts += 1
                if challenge.failed_attempts >= OTP_ATTEMPT_LIMIT:
                    challenge.user = None
                challenge.save(update_fields=["failed_attempts", "user"])
        else:
            user = User.objects.select_for_update().filter(
                pk=challenge.user_id,
                mobile_number=mobile_number,
                role=User.Role.MERCHANT,
                is_active=True,
            ).first()
            merchant = Merchant.objects.select_for_update().filter(
                user=user,
                status=Merchant.Status.ACTIVE,
            ).first() if user is not None else None
            if merchant is None:
                valid_code = False
                challenge.failed_attempts = OTP_ATTEMPT_LIMIT
                challenge.user = None
                challenge.save(update_fields=["failed_attempts", "user"])
            else:
                try:
                    password_validation.validate_password(new_password, user)
                except DjangoValidationError as exc:
                    password_error = list(exc.messages)

                if password_error is None:
                    user.set_password(new_password)
                    user.save(update_fields=["password"])
                    merchant.must_change_password = False
                    merchant.save(update_fields=["must_change_password"])

                    for token in OutstandingToken.objects.filter(user=user):
                        BlacklistedToken.objects.get_or_create(token=token)
                    UserAuthSession.objects.filter(user=user).delete()

                    challenge.user = None
                    challenge.otp_hash = _digest("otp", _new_otp())
                    challenge.expires_at = now
                    challenge.save(update_fields=["user", "otp_hash", "expires_at"])

    if password_error is not None:
        raise ValidationError({"new_password": password_error})
    if not valid_code:
        raise ValueError(INVALID_CODE_MESSAGE)
    return None
