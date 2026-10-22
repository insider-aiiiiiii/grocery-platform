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
    Factory resolving the active WhatsApp provider.
    Returns the mock provider instance for testing and local sandbox.
    """
    return _GLOBAL_MOCK_PROVIDER

