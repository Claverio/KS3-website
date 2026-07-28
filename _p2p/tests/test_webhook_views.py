from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from _p2p.models import P2PPurchase
from _setting.models import XenditSetting
from .factories import make_project, make_purchase


class WebhookAndViewTests(TestCase):
    def setUp(self):
        cache.clear()
        setting = XenditSetting.load()
        setting.webhook_verification_token = "secret-token"
        setting.save()

    def test_invalid_webhook_token_is_rejected(self):
        response = self.client.post(
            reverse("xendit_payment_session_webhook"),
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_completed_webhook_and_duplicate_are_safe(self):
        purchase = make_purchase()
        payload = {
            "event": "payment_session.completed",
            "data": {
                "payment_session_id": purchase.xendit_session_id,
                "reference_id": purchase.reference_id,
                "amount": str(purchase.total_amount),
                "currency": "IDR",
                "status": "COMPLETED",
            },
        }
        kwargs = {
            "data": payload,
            "content_type": "application/json",
            "headers": {"x-callback-token": "secret-token", "webhook-id": "evt-1"},
        }
        self.assertEqual(self.client.post(reverse("xendit_payment_session_webhook"), **kwargs).status_code, 200)
        self.assertEqual(self.client.post(reverse("xendit_payment_session_webhook"), **kwargs).json()["status"], "duplicate")
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, P2PPurchase.Status.PAID)

    @patch("_p2p.views.status.synchronize_xendit_purchase")
    def test_status_endpoint_reconciles_without_exposing_pii(self, synchronize):
        purchase = make_purchase()
        synchronize.return_value = purchase
        response = self.client.get(reverse("p2p_purchase_status", kwargs={"public_id": purchase.public_id}))
        synchronize.assert_called_once()
        body = response.content.decode()
        self.assertNotIn(purchase.email, body)
        self.assertNotIn(purchase.nik, body)

    def test_dynamic_list_and_detail_render(self):
        project = make_project()
        self.assertContains(self.client.get(reverse("p2p_list")), project.title)
        self.assertContains(self.client.get(project.get_absolute_url()), project.summary)

    def test_xendit_return_is_iframe_safe_and_notifies_parent(self):
        purchase = make_purchase()
        response = self.client.get(
            reverse("p2p_xendit_return", kwargs={"public_id": purchase.public_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Frame-Options", response.headers)
        self.assertContains(response, "p2p-payment-return")
