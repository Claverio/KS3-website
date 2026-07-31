from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
import json
from decimal import Decimal

from _setting.models import XenditSetting
from _product.models import SavingTransaction
from _product.tests.factories import make_saving_transaction


class SavingWebhookTest(TestCase):
    def setUp(self):
        cache.clear()
        XenditSetting.objects.create(webhook_verification_token='secret-token')

    def test_invalid_webhook_token_is_rejected(self):
        response = self.client.post(
            reverse('saving_xendit_webhook'),
            data={},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_completed_webhook_and_duplicate_are_safe(self):
        txn = make_saving_transaction(status=SavingTransaction.Status.WAITING_PAYMENT, amount=Decimal("500000"), service_fee=Decimal("0"), total_amount=Decimal("500000"))

        payload = {
            "event": "payment_session.completed",
            "data": {
                "reference_id": txn.reference_id,
                "status": "COMPLETED",
                "amount": 500000,
            }
        }

        headers = {'HTTP_X_CALLBACK_TOKEN': 'secret-token', 'HTTP_WEBHOOK_ID': 'wh_123'}
        response = self.client.post(
            reverse('saving_xendit_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            **headers
        )
        self.assertEqual(response.status_code, 200)

        txn.refresh_from_db()
        self.assertEqual(txn.status, SavingTransaction.Status.PAID)

        # Duplicate
        response = self.client.post(
            reverse('saving_xendit_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            **headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], 'duplicate')

    def test_unsupported_event_returns_400(self):
        payload = {
            "event": "payment_session.other",
            "data": {}
        }
        headers = {'HTTP_X_CALLBACK_TOKEN': 'secret-token', 'HTTP_WEBHOOK_ID': 'wh_124'}
        response = self.client.post(
            reverse('saving_xendit_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            **headers
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_reference_returns_404(self):
        payload = {
            "event": "payment_session.completed",
            "data": {
                "reference_id": "UNKNOWN-REF",
            }
        }
        headers = {'HTTP_X_CALLBACK_TOKEN': 'secret-token', 'HTTP_WEBHOOK_ID': 'wh_125'}
        response = self.client.post(
            reverse('saving_xendit_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            **headers
        )
        self.assertEqual(response.status_code, 404)
