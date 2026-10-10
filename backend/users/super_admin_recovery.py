"""Super Admin self-recovery and peer-initiated password reset workflows."""

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string
from rest_framework.exceptions import APIException, PermissionDenied, Throttled, ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import (
    SuperAdminRecoveryChallenge,
    SuperAdminRecoveryThrottle,
    User,
    UserAuthSession,
)

logger = logging.getLogger(__name__)

GENERIC_REQUEST_MESSAGE = "If the account is eligible, recovery instructions will be sent."
INVALID_CODE_MESSAGE = "The verification code is invalid or expired."
CODE_DIGITS = 7


class RecoveryUnavailable(APIException):
    status_code = 503
    default_detail = "Password recovery is temporarily unavailable."
    default_code = "password_recovery_unavailable"


def _config(name):
    value = getattr(settings, name, None)
    if not isinstance(value, int) or value < 1:
        raise RecoveryUnavailable()
    return value


def _pepper():
    value = getattr(settings, "SUPER_ADMIN_RECOVERY_SECRET_PEPPER", "")
    if not value or len(value.encode("utf-8")) < 32:
        raise RecoveryUnavailable()
    return value.encode("utf-8")


def _digest(purpose, value):
    return hmac.new(
        _pepper(), f"{purpose}:{value}".encode("utf-8"), hashlib.sha256,
    ).hexdigest()


def _sender(channel):
    setting_name = (
        "SUPER_ADMIN_RECOVERY_EMAIL_SENDER"
        if channel == SuperAdminRecoveryChallenge.Channel.EMAIL
        else "SUPER_ADMIN_RECOVERY_SMS_SENDER"
    )
    path = getattr(settings, setting_name, "")
    if not path:
        raise RecoveryUnavailable()
    try:
        sender = import_string(path)
    except (ImportError, AttributeError, ValueError):
        raise RecoveryUnavailable() from None
    if not callable(sender):
        raise RecoveryUnavailable()
    # Adapters enqueue delivery and return promptly to avoid enumeration by timing.
    return sender


def _new_code():
    return f"{secrets.randbelow(10 ** CODE_DIGITS):0{CODE_DIGITS}d}"


def _contact_value(user, channel):
    if channel == SuperAdminRecoveryChallenge.Channel.EMAIL:
        return user.email or ""
    return user.mobile_number or ""


def _user_for_contact(channel, contact):
    if channel == SuperAdminRecoveryChallenge.Channel.EMAIL:
        lookup = {"email": contact}
    else:
        lookup = {"mobile_number": contact}
    return User.objects.filter(
        role=User.Role.SUPER_ADMIN,
        **lookup,
    ).first()


def _lock_throttle(fingerprint, now, window_seconds):
    row, _created = SuperAdminRecoveryThrottle.objects.get_or_create(
        fingerprint=fingerprint,
        defaults={"window_started_at": now, "request_count": 0},
    )
    row = SuperAdminRecoveryThrottle.objects.select_for_update().get(pk=row.pk)
    if now - row.window_started_at >= timedelta(seconds=window_seconds):
        row.window_started_at = now
        row.request_count = 0
    return row


def _allowed_and_increment(fingerprint, now, limit, window_seconds):
    with transaction.atomic():
        row = _lock_throttle(fingerprint, now, window_seconds)
        allowed = row.request_count < limit
        if allowed:
            row.request_count += 1
            row.save(update_fields=["window_started_at", "request_count"])
        return allowed


def _issue_challenge(
    *, purpose, user, channel, initiated_by, remote_addr, contact=None,
):
    sender = _sender(channel)
    _pepper()
    ttl = _config("SUPER_ADMIN_RECOVERY_CODE_TTL_SECONDS")
    contact_limit = _config("SUPER_ADMIN_RECOVERY_REQUEST_LIMIT")
    ip_limit = _config("SUPER_ADMIN_RECOVERY_IP_REQUEST_LIMIT")
    contact_window = _config("SUPER_ADMIN_RECOVERY_REQUEST_WINDOW_SECONDS")
    ip_window = _config("SUPER_ADMIN_RECOVERY_IP_WINDOW_SECONDS")
    now = timezone.now()
    contact = contact if contact is not None else _contact_value(user, channel)
    contact_fingerprint = _digest("contact", f"{channel}:{contact}")
    ip_fingerprint = _digest("throttle-ip", remote_addr or "unknown")
    code = _new_code()

    with transaction.atomic():
        contact_allowed = _allowed_and_increment(
            _digest("throttle-contact", contact_fingerprint),
            now,
            contact_limit,
            contact_window,
        )
        ip_allowed = _allowed_and_increment(ip_fingerprint, now, ip_limit, ip_window)
        if not contact_allowed or not ip_allowed:
            return False

        # A new request invalidates older unused codes for the same contact/channel.
        SuperAdminRecoveryChallenge.objects.filter(
            purpose=purpose,
            channel=channel,
            contact_fingerprint=contact_fingerprint,
            consumed_at__isnull=True,
            expires_at__gt=now,
        ).update(expires_at=now)
        delivered_code = code if user is not None else _new_code()
        challenge = SuperAdminRecoveryChallenge.objects.create(
            purpose=purpose,
            subject=user,
            initiated_by=initiated_by,
            channel=channel,
            contact_fingerprint=contact_fingerprint,
            code_hash=_digest("code", delivered_code),
            expires_at=now + timedelta(seconds=ttl),
        )

    if user is not None:
        try:
            sender(contact, code)
        except Exception:
            logger.warning("Super Admin recovery delivery failed.")
            SuperAdminRecoveryChallenge.objects.filter(
                pk=challenge.pk,
                code_hash=_digest("code", code),
            ).update(expires_at=now)
        else:
            if purpose == SuperAdminRecoveryChallenge.Purpose.ADMIN_RESET:
                logger.info(
                    "Super Admin password reset requested",
                    extra={
                        "reset_request_id": challenge.pk,
                        "initiating_super_admin_id": initiated_by.pk,
                        "affected_super_admin_id": user.pk,
                        "requested_at": challenge.requested_at.isoformat(),
                    },
                )
    return True


def request_super_admin_self_recovery(channel, contact, remote_addr):
    """Start self-recovery without indicating whether the submitted contact exists."""
    channel = SuperAdminRecoveryChallenge.Channel(channel)
    # Resolve the provider before looking up a contact so unconfigured provider
    # behavior is independent of whether an account matches.
    _sender(channel)
    _pepper()
    now = timezone.now()
    user = _user_for_contact(channel, contact)
    _issue_challenge(
        purpose=SuperAdminRecoveryChallenge.Purpose.SELF_RECOVERY,
        user=user,
        channel=channel,
        initiated_by=None,
        remote_addr=remote_addr,
        contact=contact,
    )
    return GENERIC_REQUEST_MESSAGE


def request_super_admin_administrative_reset(
    *, initiator, target_user_id, channel, current_password, remote_addr,
):
    """Require a different authenticated Super Admin to reauthenticate and initiate."""
    if initiator.role != User.Role.SUPER_ADMIN or not initiator.is_active:
        raise PermissionDenied("Super Admin authorization is required.")
    now = timezone.now()
    if not _allowed_and_increment(
        _digest("throttle-admin-reauth", initiator.pk),
        now,
        _config("SUPER_ADMIN_RECOVERY_REAUTH_ATTEMPT_LIMIT"),
        _config("SUPER_ADMIN_RECOVERY_REQUEST_WINDOW_SECONDS"),
    ):
        raise Throttled()
    if not initiator.check_password(current_password):
        raise ValidationError({"current_password": "Current password is incorrect."})
    try:
        channel = SuperAdminRecoveryChallenge.Channel(channel)
    except ValueError:
        raise ValidationError({"channel": "Select a valid contact channel."}) from None

    target = User.objects.filter(
        pk=target_user_id,
        role=User.Role.SUPER_ADMIN,
    ).first()
    if target is None:
        raise ValidationError({"target_user_id": "Super Admin account was not found."})
    if target.pk == initiator.pk:
        raise ValidationError({
            "target_user_id": "Use self-recovery to reset your own password.",
        })
    if not _contact_value(target, channel):
        raise ValidationError({"channel": "The selected contact channel is unavailable."})

    issued = _issue_challenge(
        purpose=SuperAdminRecoveryChallenge.Purpose.ADMIN_RESET,
        user=target,
        channel=channel,
        initiated_by=initiator,
        remote_addr=remote_addr,
    )
    return issued


def confirm_super_admin_password_reset(*, purpose, channel, contact, code, new_password):
    """Verify a single-use code, update the password, and revoke every session."""
    purpose = SuperAdminRecoveryChallenge.Purpose(purpose)
    channel = SuperAdminRecoveryChallenge.Channel(channel)
    attempt_limit = _config("SUPER_ADMIN_RECOVERY_ATTEMPT_LIMIT")
    contact_fingerprint = _digest("contact", f"{channel}:{contact}")
    code_hash = _digest("code", code)
    now = timezone.now()
    password_errors = None
    valid_code = False

    with transaction.atomic():
        challenge = SuperAdminRecoveryChallenge.objects.select_for_update().filter(
            purpose=purpose,
            channel=channel,
            contact_fingerprint=contact_fingerprint,
            consumed_at__isnull=True,
        ).order_by("-requested_at").first()
        if challenge is None:
            raise ValueError(INVALID_CODE_MESSAGE)
        valid_code = (
            challenge.expires_at > now
            and challenge.failed_attempts < attempt_limit
            and hmac.compare_digest(challenge.code_hash, code_hash)
        )
        if not valid_code:
            if challenge.expires_at > now and challenge.failed_attempts < attempt_limit:
                challenge.failed_attempts += 1
                challenge.save(update_fields=["failed_attempts"])
        else:
            user = User.objects.select_for_update().filter(
                pk=challenge.subject_id,
                role=User.Role.SUPER_ADMIN,
            ).first()
            if user is None:
                valid_code = False
                challenge.failed_attempts = attempt_limit
                challenge.save(update_fields=["failed_attempts"])
            else:
                try:
                    password_validation.validate_password(new_password, user)
                except DjangoValidationError as exc:
                    password_errors = list(exc.messages)

                if password_errors is None:
                    user.set_password(new_password)
                    user.save(update_fields=["password"])
                    for token in OutstandingToken.objects.filter(user=user):
                        BlacklistedToken.objects.get_or_create(token=token)
                    UserAuthSession.objects.filter(user=user).delete()
                    challenge.consumed_at = now
                    challenge.save(update_fields=["consumed_at"])

    if password_errors is not None:
        raise ValidationError({"new_password": password_errors})
    if not valid_code:
        raise ValueError(INVALID_CODE_MESSAGE)
