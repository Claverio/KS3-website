from django.test import TestCase

from _p2p.models import P2PPurchase
from _p2p.services.payment_transition import PaymentTransitionError, apply_xendit_payment_update
from .factories import make_purchase


class PaymentTransitionTests(TestCase):
    def payload(self, purchase, status="COMPLETED", amount=None):
        return {
            "event": "payment_session.completed",
            "data": {
                "payment_session_id": purchase.xendit_session_id,
                "reference_id": purchase.reference_id,
                "amount": str(amount or purchase.total_amount),
                "currency": purchase.currency,
                "status": status,
                "updated": "2026-07-29T12:00:00Z",
                "payment_id": "py-test",
            },
        }

    def test_completed_is_idempotent(self):
        purchase = make_purchase()
        purchase = apply_xendit_payment_update(purchase, self.payload(purchase))
        paid_at = purchase.paid_at
        purchase = apply_xendit_payment_update(purchase, self.payload(purchase))
        self.assertEqual(purchase.status, P2PPurchase.Status.PAID)
        self.assertEqual(purchase.paid_at, paid_at)

    def test_amount_mismatch_is_rejected(self):
        purchase = make_purchase()
        with self.assertRaises(PaymentTransitionError):
            apply_xendit_payment_update(purchase, self.payload(purchase, amount="1"))
