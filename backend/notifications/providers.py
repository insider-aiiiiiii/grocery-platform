import json
import logging
import urllib.error
import urllib.request
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class ProviderSendResult:
    """Standardized result returned by WhatsApp provider adapters."""

    success: bool
    provider_message_id: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    is_transient: bool = True


class WhatsAppProviderBase(ABC):
    """Abstract adapter base for WhatsApp template message providers."""

    @abstractmethod
    def send_template_message(
        self,
        recipient_phone: str,
        template_name: str,
        language_code: str,
        components: Optional[List[Dict[str, Any]]] = None,
        idempotency_key: Optional[str] = None,
    ) -> ProviderSendResult:
        """
        Dispatches a pre-approved template message to recipient_phone.
        """
        pass


class MetaWhatsAppProvider(WhatsAppProviderBase):
    """
    Production adapter calling Meta WhatsApp Cloud API (Graph API v20.0).
    Uses standard library urllib.request to maintain Ponytail anti-bloat principles.
    """

    TRANSIENT_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}
    # Meta WhatsApp error codes that are permanently fatal (no retry will succeed)
    PERMANENT_META_ERROR_CODES = {
        100,     # Invalid parameter
        131026,  # Message undeliverable (e.g. number not registered on WhatsApp)
        132000,  # Template does not exist
        132001,  # Template is paused / disabled
        132005,  # Template hydrated text too long
        132015,  # Template format does not match
    }

    def __init__(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None,
        api_version: str = "v20.0",
        timeout_seconds: float = 10.0,
    ):
        self.phone_number_id = phone_number_id or getattr(settings, "META_WHATSAPP_PHONE_NUMBER_ID", "")
        self.access_token = access_token or getattr(settings, "META_WHATSAPP_ACCESS_TOKEN", "")
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds

    def _build_endpoint_url(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

    def send_template_message(
        self,
        recipient_phone: str,
        template_name: str,
        language_code: str,
        components: Optional[List[Dict[str, Any]]] = None,
        idempotency_key: Optional[str] = None,
    ) -> ProviderSendResult:
        if not self.phone_number_id or not self.access_token:
            return ProviderSendResult(
                success=False,
                error_details={"error": "Meta WhatsApp credentials are unconfigured."},
                is_transient=False,
            )

        endpoint = self._build_endpoint_url()
        # Clean phone number: Meta API expects digits without '+'
        cleaned_phone = recipient_phone.lstrip("+").strip()

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": cleaned_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components or [],
            },
        }

        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = str(idempotency_key)

        req = urllib.request.Request(endpoint, data=body_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                resp_bytes = resp.read()
                data = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
                messages = data.get("messages", [])
                provider_msg_id = messages[0].get("id") if messages else None
                return ProviderSendResult(
                    success=True,
                    provider_message_id=provider_msg_id,
                )
        except urllib.error.HTTPError as exc:
            error_data = {}
            try:
                error_bytes = exc.read()
                error_data = json.loads(error_bytes.decode("utf-8")) if error_bytes else {}
            except Exception:
                error_data = {"raw_error": str(exc)}

            status_code = exc.code
            is_transient = status_code in self.TRANSIENT_HTTP_STATUSES

            # Check Meta error code if available
            meta_error = error_data.get("error", {})
            meta_code = meta_error.get("code")
            if meta_code in self.PERMANENT_META_ERROR_CODES:
                is_transient = False
            elif meta_code == 130429:  # Rate limit exceeded
                is_transient = True

            return ProviderSendResult(
                success=False,
                error_details={
                    "status_code": status_code,
                    "meta_error": meta_error,
                },
                is_transient=is_transient,
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            return ProviderSendResult(
                success=False,
                error_details={"network_error": str(exc)},
                is_transient=True,
            )
        except Exception as exc:
            logger.exception("Unexpected error in MetaWhatsAppProvider: %s", exc)
            return ProviderSendResult(
                success=False,
                error_details={"unexpected_error": str(exc)},
                is_transient=False,
            )


class MockWhatsAppProvider(WhatsAppProviderBase):
    """
    In-memory mock WhatsApp provider for deterministic tests, local dev, and sandbox.
    Tracks all sent template messages and allows test simulations of errors.
    """

    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.should_succeed: bool = True
        self.simulate_transient_failure: bool = False
        self.simulate_permanent_failure: bool = False
        self.custom_error_details: Optional[Dict[str, Any]] = None

    def reset(self):
        self.sent_messages.clear()
        self.should_succeed = True
        self.simulate_transient_failure = False
        self.simulate_permanent_failure = False
        self.custom_error_details = None

    def send_template_message(
        self,
        recipient_phone: str,
        template_name: str,
        language_code: str,
        components: Optional[List[Dict[str, Any]]] = None,
        idempotency_key: Optional[str] = None,
    ) -> ProviderSendResult:
        if self.simulate_permanent_failure:
            return ProviderSendResult(
                success=False,
                error_details=self.custom_error_details or {"mock_error": "Permanent failure simulated"},
                is_transient=False,
            )

        if self.simulate_transient_failure:
            return ProviderSendResult(
                success=False,
                error_details=self.custom_error_details or {"mock_error": "Transient failure simulated"},
                is_transient=True,
            )

        if not self.should_succeed:
            return ProviderSendResult(
                success=False,
                error_details=self.custom_error_details or {"mock_error": "Failure simulated"},
                is_transient=True,
            )

        provider_message_id = f"wamid.mock_{uuid.uuid4().hex}"
        self.sent_messages.append({
            "recipient_phone": recipient_phone,
            "template_name": template_name,
            "language_code": language_code,
            "components": components or [],
            "idempotency_key": idempotency_key,
            "provider_message_id": provider_message_id,
        })

        return ProviderSendResult(
            success=True,
            provider_message_id=provider_message_id,
        )


# Global mock provider singleton for test inspection and reset
_GLOBAL_MOCK_PROVIDER = MockWhatsAppProvider()


def get_default_mock_provider() -> MockWhatsAppProvider:
    return _GLOBAL_MOCK_PROVIDER


def get_whatsapp_provider() -> WhatsAppProviderBase:
    """
    Factory resolving the active WhatsApp provider based on settings.
    Defaults to MockWhatsAppProvider if MOCK_WHATSAPP_PROVIDER is True
    or if Meta credentials are not configured.
    """
    if getattr(settings, "MOCK_WHATSAPP_PROVIDER", True):
        return _GLOBAL_MOCK_PROVIDER

    phone_number_id = getattr(settings, "META_WHATSAPP_PHONE_NUMBER_ID", "")
    access_token = getattr(settings, "META_WHATSAPP_ACCESS_TOKEN", "")

    if not phone_number_id or not access_token:
        return _GLOBAL_MOCK_PROVIDER

    return MetaWhatsAppProvider(
        phone_number_id=phone_number_id,
        access_token=access_token,
    )
