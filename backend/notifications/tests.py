import uuid
from datetime import timedelta
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from notifications.models import NotificationOutbox, NotificationTemplate
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

