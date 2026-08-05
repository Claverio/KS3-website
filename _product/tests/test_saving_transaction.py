from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from _product.models import SavingTransaction
from _product.tests.factories import make_saving_transaction


class SavingTransactionModelTest(TestCase):
    def test_save_auto_calculates_total_amount(self):
        txn = make_saving_transaction(amount=Decimal("500000"), service_fee=Decimal("2500"), total_amount=Decimal("0"))
        self.assertEqual(txn.total_amount, Decimal("502500"))

    def test_financial_snapshot_is_immutable_after_creation(self):
        txn = make_saving_transaction(amount=Decimal("500000"), service_fee=Decimal("0"))
        self.assertEqual(txn.total_amount, Decimal("500000"))

        txn.amount = Decimal("600000")
        txn.service_fee = Decimal("1000")
        with self.assertRaises(ValidationError):
            txn.save()
        txn.refresh_from_db()
        self.assertEqual(txn.total_amount, Decimal("500000"))

    def test_clean_requires_nomor_anggota_for_existing_member(self):
        txn = make_saving_transaction(is_new_member=False, nomor_anggota='')
        with self.assertRaises(ValidationError):
            txn.clean()

    def test_clean_rejects_nomor_anggota_for_new_member(self):
        txn = make_saving_transaction(is_new_member=True, nomor_anggota='AGT-001')
        with self.assertRaises(ValidationError):
            txn.clean()

    def test_clean_new_member_without_nomor_anggota_is_valid(self):
        txn = make_saving_transaction(is_new_member=True, nomor_anggota='')
        txn.clean()  # Should not raise exception

    def test_masked_nik_returns_last_four(self):
        txn = make_saving_transaction(nik='1234567890123456')
        self.assertTrue(txn.masked_nik.startswith('*'))
        self.assertTrue(txn.masked_nik.endswith('3456'))
        self.assertEqual(len(txn.masked_nik), 16)

    def test_masked_nik_returns_dash_when_empty(self):
        txn = make_saving_transaction(nik='')
        self.assertEqual(txn.masked_nik, '-')

    def test_is_final_for_terminal_statuses(self):
        for status in [
            SavingTransaction.Status.PAID,
            SavingTransaction.Status.EXPIRED,
            SavingTransaction.Status.CANCELED,
            SavingTransaction.Status.FAILED,
        ]:
            txn = make_saving_transaction(status=status)
            self.assertTrue(txn.is_final)

    def test_is_not_final_for_active_statuses(self):
        for status in [
            SavingTransaction.Status.CREATING,
            SavingTransaction.Status.WAITING_PAYMENT,
        ]:
            txn = make_saving_transaction(status=status)
            self.assertFalse(txn.is_final)

    def test_str_returns_transaction_code(self):
        txn = make_saving_transaction(transaction_code="TEST-STR-123")
        self.assertEqual(str(txn), "TEST-STR-123")
