import io
import json
import urllib.error
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from cart.models import Cart, CartItem
from catalog.models import ShopProduct
from customers.models import Customer, normalize_whatsapp_number
from inventory.models import InventoryItem
from notifications.models import NotificationOutbox, NotificationTemplate
from notifications.providers import (
    MetaWhatsAppProvider,
    MockWhatsAppProvider,
    ProviderSendResult,
    get_default_mock_provider,
    get_whatsapp_provider,
)
from notifications.services import (
    dispatch_notification,
    enqueue_order_created_notification,
    get_or_create_default_template,
    process_pending_outbox_batch,
)
from orders.models import Order
from orders.services import create_order
from shops.models import Shop
from users.models import Merchant, User


class NotificationTemplateModelTests(TestCase):
    def test_create_all_approved_event_templates(self):
        """Verifies all 7 approved canonical business events can be instantiated."""
        events = NotificationTemplate.EventType.values
        self.assertEqual(len(events), 7)

        for event in events:
            template = NotificationTemplate.objects.create(
                event_type=event,
                template_name=f"{event.lower()}_v1",
                language_code="en_US",
                body_format="Hello {{shop_name}}, order {{order_number}}",
                is_active=True,
            )
            self.assertEqual(template.event_type, event)
            self.assertTrue(template.is_active)
            self.assertEqual(template.language_code, "en_US")
            self.assertIn(template.template_name, str(template))

    def test_unique_event_type_constraint(self):
        """Duplicate templates for the same event type must raise IntegrityError."""
        NotificationTemplate.objects.create(
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            template_name="new_order_v1",
            body_format="Body 1",
        )
        with self.assertRaises(IntegrityError):
            NotificationTemplate.objects.create(
                event_type=NotificationTemplate.EventType.NEW_ORDER,
                template_name="new_order_v2",
                body_format="Body 2",
            )

    def test_default_values(self):
        """Tests defaults for language_code and is_active."""
        template = NotificationTemplate.objects.create(
            event_type=NotificationTemplate.EventType.ORDER_ACCEPTED,
            template_name="order_accepted_v1",
            body_format="Accepted!",
        )
        self.assertEqual(template.language_code, "en_US")
        self.assertTrue(template.is_active)


class NotificationOutboxModelTests(TestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="shop_merchant",
            email="merchant@example.com",
            password="testpassword123",
            role=User.Role.MERCHANT,
            mobile_number="+919876543210",
        )
        self.merchant = Merchant.objects.create(
            user=self.user,
            status=Merchant.Status.ACTIVE,
            must_change_password=False,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Green Grocers",
            address_line="100 Market Rd",
            area="Sector 4",
            city="Metropolis",
            state="Central",
            pincode="123456",
            contact_number="+919876543210",
            status=Shop.Status.ACTIVE,
        )
        self.template = NotificationTemplate.objects.create(
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            template_name="new_order_v1",
            body_format="New order #{{order_number}} at {{shop_name}}",
        )

    def test_create_outbox_item_defaults(self):
        """Verifies default values and UUID generation on outbox items."""
        order_uuid = uuid.uuid4()
        outbox = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=order_uuid,
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            recipient_type=NotificationOutbox.RecipientType.MERCHANT,
            recipient_phone="+919876543210",
            template=self.template,
            template_context={"order_number": "ORD-001", "shop_name": self.shop.name},
        )
        self.assertIsInstance(outbox.id, uuid.UUID)
        self.assertEqual(outbox.status, NotificationOutbox.Status.PENDING)
        self.assertEqual(outbox.retry_count, 0)
        self.assertIsNone(outbox.next_retry_at)
        self.assertIsNone(outbox.provider_message_id)
        self.assertFalse(outbox.is_terminal)
        self.assertIn("ORD-001", outbox.template_context["order_number"])

    def test_idempotency_constraint_prevents_duplicate_intent(self):
        """Asserts duplicate (order_id, event_type, recipient_phone) raises IntegrityError."""
        order_uuid = uuid.uuid4()
        phone = "+919876543210"
        event = NotificationTemplate.EventType.NEW_ORDER

        NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=order_uuid,
            event_type=event,
            recipient_type=NotificationOutbox.RecipientType.MERCHANT,
            recipient_phone=phone,
            template=self.template,
        )

        with self.assertRaises(IntegrityError):
            NotificationOutbox.objects.create(
                shop=self.shop,
                order_id=order_uuid,
                event_type=event,
                recipient_type=NotificationOutbox.RecipientType.MERCHANT,
                recipient_phone=phone,
                template=self.template,
            )

    def test_same_order_different_events_permitted(self):
        """Same order with different event types must be permitted (e.g. NEW_ORDER then ORDER_ACCEPTED)."""
        order_uuid = uuid.uuid4()
        phone = "+919876543210"

        outbox1 = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=order_uuid,
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            recipient_type=NotificationOutbox.RecipientType.MERCHANT,
            recipient_phone=phone,
        )
        outbox2 = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=order_uuid,
            event_type=NotificationTemplate.EventType.ORDER_ACCEPTED,
            recipient_type=NotificationOutbox.RecipientType.CUSTOMER,
            recipient_phone=phone,
        )
        self.assertNotEqual(outbox1.id, outbox2.id)

    def test_same_order_different_recipients_permitted(self):
        """Same order and event to different recipient phone numbers must be permitted."""
        order_uuid = uuid.uuid4()
        event = NotificationTemplate.EventType.NEW_ORDER

        outbox1 = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=order_uuid,
            event_type=event,
            recipient_type=NotificationOutbox.RecipientType.MERCHANT,
            recipient_phone="+919876543210",
        )
        outbox2 = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=order_uuid,
            event_type=event,
            recipient_type=NotificationOutbox.RecipientType.MERCHANT,
            recipient_phone="+919876543211",
        )
        self.assertNotEqual(outbox1.id, outbox2.id)

    def test_monotonic_status_progression(self):
        """Verifies progression: PENDING -> SUBMITTED -> DELIVERED -> READ."""
        outbox = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=uuid.uuid4(),
            event_type=NotificationTemplate.EventType.ORDER_RECEIVED_CUSTOMER,
            recipient_type=NotificationOutbox.RecipientType.CUSTOMER,
            recipient_phone="+919999900001",
        )
        self.assertEqual(outbox.status, NotificationOutbox.Status.PENDING)
        self.assertFalse(outbox.is_terminal)

        # Submit
        provider_msg_id = "wamid.HBgLMzEwMjM4NDQ1NhUCMR4XFDAyMTA="
        outbox.mark_submitted(provider_msg_id)
        outbox.refresh_from_db()
        self.assertEqual(outbox.status, NotificationOutbox.Status.SUBMITTED)
        self.assertEqual(outbox.provider_message_id, provider_msg_id)
        self.assertIsNotNone(outbox.submitted_at)
        self.assertFalse(outbox.is_terminal)

        # Deliver
        outbox.mark_delivered()
        outbox.refresh_from_db()
        self.assertEqual(outbox.status, NotificationOutbox.Status.DELIVERED)
        self.assertIsNotNone(outbox.delivered_at)
        self.assertTrue(outbox.is_terminal)

        # Read
        outbox.mark_read()
        outbox.refresh_from_db()
        self.assertEqual(outbox.status, NotificationOutbox.Status.READ)
        self.assertTrue(outbox.is_terminal)

    def test_record_failure_transient_exponential_backoff(self):
        """Tests bounded retry calculation: attempt 1 -> 60s, attempt 2 -> 300s, attempt 3 -> 900s, then exhaustion."""
        outbox = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=uuid.uuid4(),
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            recipient_type=NotificationOutbox.RecipientType.MERCHANT,
            recipient_phone="+919876543210",
        )

        now = timezone.now()
        # Attempt 1
        outbox.record_failure({"error": "network timeout"}, is_transient=True)
        outbox.refresh_from_db()
        self.assertEqual(outbox.retry_count, 1)
        self.assertEqual(outbox.status, NotificationOutbox.Status.PENDING)
        self.assertFalse(outbox.is_terminal)
        self.assertTrue(outbox.next_retry_at >= now + timedelta(seconds=55))
        self.assertTrue(outbox.next_retry_at <= now + timedelta(seconds=65))

        # Attempt 2
        outbox.record_failure({"error": "provider 503"}, is_transient=True)
        outbox.refresh_from_db()
        self.assertEqual(outbox.retry_count, 2)
        self.assertEqual(outbox.status, NotificationOutbox.Status.PENDING)
        self.assertFalse(outbox.is_terminal)
        self.assertTrue(outbox.next_retry_at >= now + timedelta(seconds=295))

        # Attempt 3 -> Exhausted
        outbox.record_failure({"error": "rate limit"}, is_transient=True)
        outbox.refresh_from_db()
        self.assertEqual(outbox.retry_count, 3)
        self.assertEqual(outbox.status, NotificationOutbox.Status.FAILED_TRANSIENT_EXHAUSTED)
        self.assertIsNone(outbox.next_retry_at)
        self.assertTrue(outbox.is_terminal)

    def test_record_failure_permanent_immediate_termination(self):
        """Permanent errors immediately fast-fail to FAILED_PERMANENT without scheduling retries."""
        outbox = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=uuid.uuid4(),
            event_type=NotificationTemplate.EventType.ORDER_ACCEPTED,
            recipient_type=NotificationOutbox.RecipientType.CUSTOMER,
            recipient_phone="+919999900001",
        )
        outbox.record_failure({"code": 131026, "message": "Phone not on WhatsApp"}, is_transient=False)
        outbox.refresh_from_db()

        self.assertEqual(outbox.status, NotificationOutbox.Status.FAILED_PERMANENT)
        self.assertEqual(outbox.retry_count, 0)
        self.assertIsNone(outbox.next_retry_at)
        self.assertTrue(outbox.is_terminal)
        self.assertEqual(outbox.provider_error_details["code"], 131026)

    def test_shop_cascade_deletion(self):
        """Permanent Shop deletion must cascade-delete related outbox items."""
        order_uuid = uuid.uuid4()
        outbox = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=order_uuid,
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            recipient_type=NotificationOutbox.RecipientType.MERCHANT,
            recipient_phone="+919876543210",
        )
        outbox_id = outbox.id
        self.shop.delete()

        self.assertFalse(NotificationOutbox.objects.filter(id=outbox_id).exists())

    def test_template_protect_on_delete(self):
        """Deleting a template referenced by an existing outbox item must raise ProtectedError."""
        NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=uuid.uuid4(),
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            recipient_type=NotificationOutbox.RecipientType.MERCHANT,
            recipient_phone="+919876543210",
            template=self.template,
        )
        with self.assertRaises(ProtectedError):
            self.template.delete()

    def test_retention_cutoff_filtering(self):
        """Asserts that 30-day retention query can isolate records older than 30 days."""
        now = timezone.now()
        outbox_recent = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=uuid.uuid4(),
            event_type=NotificationTemplate.EventType.NEW_ORDER,
            recipient_type=NotificationOutbox.RecipientType.MERCHANT,
            recipient_phone="+919876543210",
        )
        outbox_old = NotificationOutbox.objects.create(
            shop=self.shop,
            order_id=uuid.uuid4(),
            event_type=NotificationTemplate.EventType.ORDER_ACCEPTED,
            recipient_type=NotificationOutbox.RecipientType.CUSTOMER,
            recipient_phone="+919876543210",
        )
        # Artificially set created_at for outbox_old to 35 days ago
        NotificationOutbox.objects.filter(id=outbox_old.id).update(
            created_at=now - timedelta(days=35)
        )

        cutoff = now - timedelta(days=30)
        expired_qs = NotificationOutbox.objects.filter(created_at__lt=cutoff)
        self.assertEqual(expired_qs.count(), 1)
        self.assertEqual(expired_qs.first().id, outbox_old.id)


class WhatsAppProviderAdapterTests(TestCase):
    """Tests for MetaWhatsAppProvider and MockWhatsAppProvider adapters."""

    def test_meta_provider_success(self):
        provider = MetaWhatsAppProvider(
            phone_number_id="10987654321",
            access_token="test_meta_token_123",
        )
        fake_response_data = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "919876543210", "wa_id": "919876543210"}],
            "messages": [{"id": "wamid.HBgL1234567890"}],
        }
        fake_response_bytes = json.dumps(fake_response_data).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_response_bytes
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = provider.send_template_message(
                recipient_phone="+919876543210",
                template_name="order_received_v1",
                language_code="en_US",
                components=[{"type": "body", "parameters": [{"type": "text", "text": "Fresh Corner"}]}],
                idempotency_key="idemp-key-123",
            )
            self.assertTrue(result.success)
            self.assertEqual(result.provider_message_id, "wamid.HBgL1234567890")
            self.assertTrue(result.is_transient)

            # Assert request attributes
            mock_urlopen.assert_called_once()
            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.get_header("Authorization"), "Bearer test_meta_token_123")
            self.assertEqual(req.get_header("Content-type"), "application/json")
            self.assertEqual(req.get_header("X-idempotency-key"), "idemp-key-123")

            sent_payload = json.loads(req.data.decode("utf-8"))
            self.assertEqual(sent_payload["to"], "919876543210")
            self.assertEqual(sent_payload["type"], "template")
            self.assertEqual(sent_payload["template"]["name"], "order_received_v1")

    def test_meta_provider_unconfigured_credentials(self):
        provider = MetaWhatsAppProvider(phone_number_id="", access_token="")
        result = provider.send_template_message(
            recipient_phone="+919876543210",
            template_name="test_v1",
            language_code="en_US",
        )
        self.assertFalse(result.success)
        self.assertFalse(result.is_transient)
        self.assertIn("unconfigured", result.error_details["error"])

    def test_meta_provider_transient_http_statuses(self):
        provider = MetaWhatsAppProvider(
            phone_number_id="10987654321",
            access_token="test_token",
        )
        transient_codes = [408, 429, 500, 502, 503, 504]
        for code in transient_codes:
            exc = urllib.error.HTTPError(
                url="https://graph.facebook.com/v20.0/messages",
                code=code,
                msg="Transient Error",
                hdrs={},
                fp=io.BytesIO(b'{"error": {"message": "Service unavailable"}}'),
            )
            with patch("urllib.request.urlopen", side_effect=exc):
                result = provider.send_template_message(
                    recipient_phone="+919876543210",
                    template_name="order_received_v1",
                    language_code="en_US",
                )
                self.assertFalse(result.success)
                self.assertTrue(result.is_transient)
                self.assertEqual(result.error_details["status_code"], code)

    def test_meta_provider_permanent_meta_error_codes(self):
        provider = MetaWhatsAppProvider(
            phone_number_id="10987654321",
            access_token="test_token",
        )
        permanent_codes = [100, 131026, 132000, 132001, 132005, 132015]
        for meta_code in permanent_codes:
            error_json = json.dumps({"error": {"code": meta_code, "message": "Fatal Meta Error"}}).encode("utf-8")
            exc = urllib.error.HTTPError(
                url="https://graph.facebook.com/v20.0/messages",
                code=400,
                msg="Bad Request",
                hdrs={},
                fp=io.BytesIO(error_json),
            )
            with patch("urllib.request.urlopen", side_effect=exc):
                result = provider.send_template_message(
                    recipient_phone="+919876543210",
                    template_name="order_received_v1",
                    language_code="en_US",
                )
                self.assertFalse(result.success)
                self.assertFalse(result.is_transient)
                self.assertEqual(result.error_details["meta_error"]["code"], meta_code)

    def test_meta_provider_rate_limit_meta_error(self):
        provider = MetaWhatsAppProvider(
            phone_number_id="10987654321",
            access_token="test_token",
        )
        error_json = json.dumps({"error": {"code": 130429, "message": "Rate limit exceeded"}}).encode("utf-8")
        exc = urllib.error.HTTPError(
            url="https://graph.facebook.com/v20.0/messages",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=io.BytesIO(error_json),
        )
        with patch("urllib.request.urlopen", side_effect=exc):
            result = provider.send_template_message(
                recipient_phone="+919876543210",
                template_name="order_received_v1",
                language_code="en_US",
            )
            self.assertFalse(result.success)
            self.assertTrue(result.is_transient)

    def test_meta_provider_network_error(self):
        provider = MetaWhatsAppProvider(
            phone_number_id="10987654321",
            access_token="test_token",
        )
        exc = urllib.error.URLError("Connection reset by peer")
        with patch("urllib.request.urlopen", side_effect=exc):
            result = provider.send_template_message(
                recipient_phone="+919876543210",
                template_name="order_received_v1",
                language_code="en_US",
            )
            self.assertFalse(result.success)
            self.assertTrue(result.is_transient)
            self.assertIn("network_error", result.error_details)

    def test_mock_provider_recording_and_reset(self):
        mock_provider = MockWhatsAppProvider()
        mock_provider.reset()
        self.assertEqual(len(mock_provider.sent_messages), 0)

        result = mock_provider.send_template_message(
            recipient_phone="+919876543210",
            template_name="test_template",
            language_code="en_US",
            components=[{"type": "body", "parameters": []}],
            idempotency_key="key-abc",
        )
        self.assertTrue(result.success)
        self.assertTrue(result.provider_message_id.startswith("wamid.mock_"))
        self.assertEqual(len(mock_provider.sent_messages), 1)
        self.assertEqual(mock_provider.sent_messages[0]["recipient_phone"], "+919876543210")

        mock_provider.reset()
        self.assertEqual(len(mock_provider.sent_messages), 0)

    def test_mock_provider_simulated_failures(self):
        mock_provider = MockWhatsAppProvider()

        # Transient failure simulation
        mock_provider.simulate_transient_failure = True
        res_transient = mock_provider.send_template_message(
            recipient_phone="+919876543210",
            template_name="test",
            language_code="en_US",
        )
        self.assertFalse(res_transient.success)
        self.assertTrue(res_transient.is_transient)

        # Permanent failure simulation
        mock_provider.reset()
        mock_provider.simulate_permanent_failure = True
        res_permanent = mock_provider.send_template_message(
            recipient_phone="+919876543210",
            template_name="test",
            language_code="en_US",
        )
        self.assertFalse(res_permanent.success)
        self.assertFalse(res_permanent.is_transient)

    @override_settings(MOCK_WHATSAPP_PROVIDER=True)
    def test_get_whatsapp_provider_returns_mock_when_flag_true(self):
        provider = get_whatsapp_provider()
        self.assertIsInstance(provider, MockWhatsAppProvider)

    @override_settings(
        MOCK_WHATSAPP_PROVIDER=False,
        META_WHATSAPP_PHONE_NUMBER_ID="12345",
        META_WHATSAPP_ACCESS_TOKEN="token_abc",
    )
    def test_get_whatsapp_provider_returns_meta_when_configured(self):
        provider = get_whatsapp_provider()
        self.assertIsInstance(provider, MetaWhatsAppProvider)


class OrderCreatedNotificationIntegrationTests(TestCase):
    """Integration tests verifying Order Created notification enqueueing and dispatch."""

    def setUp(self):
        super().setUp()
        get_default_mock_provider().reset()

        self.merchant_user = User.objects.create_user(
            username="order_notif_merchant",
            email="order_notif_merchant@example.com",
            mobile_number="+919876540001",
            role=User.Role.MERCHANT,
            password="test-password-123",
        )
        self.merchant = Merchant.objects.create(
            user=self.merchant_user,
            status=Merchant.Status.ACTIVE,
        )
        self.shop = Shop.objects.create(
            merchant=self.merchant,
            name="Notification Market",
            address_line="100 Notification Rd",
            area="South",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
            contact_number=self.merchant_user.mobile_number,
            delivery_charge=Decimal("30.00"),
        )
        self.product = ShopProduct.objects.create(
            shop=self.shop,
            name="Organic Bananas",
            sku="BAN-01",
            price=Decimal("40.00"),
            is_visible=True,
            is_available=True,
        )
        self.stock = InventoryItem.objects.get(
            shop=self.shop,
            product=self.product,
            variant__isnull=True,
        )
        self.stock.quantity = Decimal("50.000")
        self.stock.save()

        self.customer = Customer.objects.create(
            shop=self.shop,
            name="Ramesh Kumar",
            whatsapp_number="+919123450001",
        )
        self.cart = Cart.objects.create(shop=self.shop, customer=self.customer)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=Decimal("2.000"),
        )

    def tearDown(self):
        get_default_mock_provider().reset()
        super().tearDown()

    def _create_test_order(self, idempotency_key="test-order-key-1"):
        payload = {
            "cart_id": self.cart.pk,
            "customer_name": "Ramesh Kumar",
            "whatsapp_number": self.customer.whatsapp_number,
            "fulfillment_type": Order.FulfillmentType.PICKUP,
        }
        order, created = create_order(self.shop, payload, idempotency_key)
        return order, created

    def test_order_creation_enqueues_merchant_notification(self):
        """Creating an order atomically enqueues a NEW_ORDER outbox item for shop.contact_number."""
        order, created = self._create_test_order(idempotency_key="notif-order-001")
        self.assertTrue(created)

        outbox_items = NotificationOutbox.objects.filter(order_id=order.id)
        self.assertEqual(outbox_items.count(), 1)

        outbox = outbox_items.first()
        self.assertEqual(outbox.shop, self.shop)
        self.assertEqual(outbox.event_type, NotificationTemplate.EventType.NEW_ORDER)
        self.assertEqual(outbox.recipient_type, NotificationOutbox.RecipientType.MERCHANT)
        self.assertEqual(outbox.recipient_phone, self.shop.contact_number)
        self.assertEqual(outbox.status, NotificationOutbox.Status.PENDING)
        self.assertEqual(outbox.retry_count, 0)
        self.assertIsNone(outbox.next_retry_at)

        # Validate template context contents
        self.assertEqual(outbox.template_context["shop_name"], self.shop.name)
        self.assertEqual(outbox.template_context["order_number"], str(order.id)[:8])
        self.assertEqual(outbox.template_context["total_amount"], str(order.total_amount))
        self.assertEqual(outbox.template_context["item_count"], 1)
        self.assertIn(str(order.id), outbox.template_context["portal_url"])

    def test_order_creation_idempotency_prevents_duplicate_outbox(self):
        """Retrying checkout with the same idempotency key does not duplicate the outbox entry."""
        order1, created1 = self._create_test_order(idempotency_key="idemp-duplicate-001")
        self.assertTrue(created1)

        # Second submission with the exact same idempotency key
        payload = {
            "cart_id": self.cart.pk,
            "customer_name": "Ramesh Kumar",
            "whatsapp_number": self.customer.whatsapp_number,
            "fulfillment_type": Order.FulfillmentType.PICKUP,
        }
        order2, created2 = create_order(self.shop, payload, "idemp-duplicate-001")
        self.assertFalse(created2)
        self.assertEqual(order1.id, order2.id)

        # Confirm exactly 1 outbox record exists
        outbox_items = NotificationOutbox.objects.filter(order_id=order1.id)
        self.assertEqual(outbox_items.count(), 1)

    def test_order_creation_rollback_leaves_no_outbox(self):
        """If order creation fails (e.g. stock reservation exceeds on-hand), no outbox item is saved."""
        self.cart_item.quantity = Decimal("999.000")
        self.cart_item.save()

        with self.assertRaises(ValidationError):
            self._create_test_order(idempotency_key="failed-stock-order")

        self.assertEqual(NotificationOutbox.objects.count(), 0)

    def test_dispatch_order_created_notification_success(self):
        """Dispatching outbox item sends via provider and transitions status to SUBMITTED."""
        order, _ = self._create_test_order(idempotency_key="dispatch-success-001")
        outbox = NotificationOutbox.objects.get(order_id=order.id)

        mock_provider = get_default_mock_provider()
        mock_provider.reset()

        dispatched = dispatch_notification(outbox, provider=mock_provider)
        dispatched.refresh_from_db()

        self.assertEqual(dispatched.status, NotificationOutbox.Status.SUBMITTED)
        self.assertTrue(dispatched.provider_message_id.startswith("wamid.mock_"))
        self.assertIsNotNone(dispatched.submitted_at)
        self.assertEqual(len(mock_provider.sent_messages), 1)

        # Attempting duplicate dispatch on SUBMITTED item is a safe no-op
        dispatch_notification(dispatched, provider=mock_provider)
        self.assertEqual(len(mock_provider.sent_messages), 1)

    def test_dispatch_transient_retry_and_backoff_exhaustion(self):
        """Transient errors retry up to 3 times with backoff, then transition to FAILED_TRANSIENT_EXHAUSTED."""
        order, _ = self._create_test_order(idempotency_key="transient-retry-001")
        outbox = NotificationOutbox.objects.get(order_id=order.id)

        mock_provider = get_default_mock_provider()
        mock_provider.simulate_transient_failure = True

        # Attempt 1
        now = timezone.now()
        dispatch_notification(outbox, provider=mock_provider)
        outbox.refresh_from_db()
        self.assertEqual(outbox.status, NotificationOutbox.Status.PENDING)
        self.assertEqual(outbox.retry_count, 1)
        self.assertGreater(outbox.next_retry_at, now + timedelta(seconds=55))
        self.assertLess(outbox.next_retry_at, now + timedelta(seconds=65))

        # Attempt 2
        dispatch_notification(outbox, provider=mock_provider)
        outbox.refresh_from_db()
        self.assertEqual(outbox.status, NotificationOutbox.Status.PENDING)
        self.assertEqual(outbox.retry_count, 2)
        self.assertGreater(outbox.next_retry_at, now + timedelta(seconds=295))

        # Attempt 3 - Terminal transient exhaustion
        dispatch_notification(outbox, provider=mock_provider)
        outbox.refresh_from_db()
        self.assertEqual(outbox.status, NotificationOutbox.Status.FAILED_TRANSIENT_EXHAUSTED)
        self.assertEqual(outbox.retry_count, 3)
        self.assertIsNone(outbox.next_retry_at)
        self.assertTrue(outbox.is_terminal)

    def test_dispatch_permanent_error_fast_fails(self):
        """Permanent provider errors immediately transition to FAILED_PERMANENT without retry."""
        order, _ = self._create_test_order(idempotency_key="permanent-fail-001")
        outbox = NotificationOutbox.objects.get(order_id=order.id)

        mock_provider = get_default_mock_provider()
        mock_provider.simulate_permanent_failure = True

        dispatch_notification(outbox, provider=mock_provider)
        outbox.refresh_from_db()

        self.assertEqual(outbox.status, NotificationOutbox.Status.FAILED_PERMANENT)
        self.assertEqual(outbox.retry_count, 0)
        self.assertIsNone(outbox.next_retry_at)
        self.assertTrue(outbox.is_terminal)

    def test_process_pending_outbox_batch(self):
        """Batch processor leases and dispatches pending outbox records respecting batch size."""
        # Create 3 orders with outbox entries
        orders = []
        for i in range(3):
            # replenish cart & stock
            cart = Cart.objects.create(shop=self.shop, customer=self.customer)
            CartItem.objects.create(cart=cart, product=self.product, quantity=Decimal("1.000"))
            payload = {
                "cart_id": cart.pk,
                "customer_name": "Ramesh Kumar",
                "whatsapp_number": self.customer.whatsapp_number,
                "fulfillment_type": Order.FulfillmentType.PICKUP,
            }
            order, _ = create_order(self.shop, payload, f"batch-order-{i}")
            orders.append(order)

        self.assertEqual(
            NotificationOutbox.objects.filter(status=NotificationOutbox.Status.PENDING).count(),
            3,
        )

        mock_provider = get_default_mock_provider()
        mock_provider.reset()

        # Process batch of size 2
        processed = process_pending_outbox_batch(batch_size=2, provider=mock_provider)
        self.assertEqual(len(processed), 2)
        self.assertEqual(len(mock_provider.sent_messages), 2)

        self.assertEqual(
            NotificationOutbox.objects.filter(status=NotificationOutbox.Status.SUBMITTED).count(),
            2,
        )
        self.assertEqual(
            NotificationOutbox.objects.filter(status=NotificationOutbox.Status.PENDING).count(),
            1,
        )

