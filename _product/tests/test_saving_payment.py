from decimal import Decimal
from django.test import TestCase

from _product.models import SavingTransaction
from _product.services.payment_transition import apply_saving_payment_update, SavingPaymentTransitionError
from _product.tests.factories import make_saving_transaction


class SavingPaymentTransitionTest(TestCase):
    def payload(self, saving_txn, status='COMPLETED', amount=None):
        return {
            "data": {
                "reference_id": saving_txn.reference_id,
                "status": status,
                "amount": amount if amount is not None else int(saving_txn.total_amount),
            }
        }

    def test_completed_is_idempotent(self):
        txn = make_saving_transaction(status=SavingTransaction.Status.WAITING_PAYMENT, amount=Decimal("500000"), service_fee=Decimal("0"), total_amount=Decimal("500000"))

        apply_saving_payment_update(txn, self.payload(txn, 'COMPLETED'))
        txn.refresh_from_db()
        self.assertEqual(txn.status, SavingTransaction.Status.PAID)
        paid_at = txn.paid_at
        self.assertIsNotNone(paid_at)

        # Apply again
        apply_saving_payment_update(txn, self.payload(txn, 'COMPLETED'))
        txn.refresh_from_db()
        self.assertEqual(txn.status, SavingTransaction.Status.PAID)
        self.assertEqual(txn.paid_at, paid_at)

    def test_amount_mismatch_is_rejected(self):
        txn = make_saving_transaction(status=SavingTransaction.Status.WAITING_PAYMENT, amount=Decimal("500000"), service_fee=Decimal("0"), total_amount=Decimal("500000"))

        with self.assertRaises(SavingPaymentTransitionError):
            apply_saving_payment_update(txn, self.payload(txn, 'COMPLETED', amount=1))

    def test_paid_cannot_regress_to_expired(self):
        txn = make_saving_transaction(status=SavingTransaction.Status.WAITING_PAYMENT, amount=Decimal("500000"), service_fee=Decimal("0"), total_amount=Decimal("500000"))

        apply_saving_payment_update(txn, self.payload(txn, 'COMPLETED'))
        txn.refresh_from_db()
        self.assertEqual(txn.status, SavingTransaction.Status.PAID)

        with self.assertRaises(SavingPaymentTransitionError):
            apply_saving_payment_update(txn, self.payload(txn, 'EXPIRED'))

    def test_expired_sets_status(self):
        txn = make_saving_transaction(status=SavingTransaction.Status.WAITING_PAYMENT, amount=Decimal("500000"), service_fee=Decimal("0"), total_amount=Decimal("500000"))

        apply_saving_payment_update(txn, self.payload(txn, 'EXPIRED'))
        txn.refresh_from_db()
        self.assertEqual(txn.status, SavingTransaction.Status.EXPIRED)
