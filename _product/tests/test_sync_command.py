from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase

from backend.services.xendit import XenditAPIError
from _product.models import SavingTransaction
from _product.tests.factories import make_saving_transaction


class SyncUnpaidPaymentsCommandTest(TestCase):
    def test_dry_run_lists_without_api_calls(self):
        txn = make_saving_transaction(status=SavingTransaction.Status.WAITING_PAYMENT, xendit_session_id='ps_123')

        out = StringIO()
        call_command('sync_unpaid_payments', '--dry-run', stdout=out)

        self.assertIn('DRY-RUN', out.getvalue())
        txn.refresh_from_db()
        self.assertEqual(txn.status, SavingTransaction.Status.WAITING_PAYMENT)

    @patch('_product.management.commands.sync_unpaid_payments.XenditService.get_session_status')
    def test_syncs_waiting_payment_records(self, mock_get_session_status):
        txn = make_saving_transaction(status=SavingTransaction.Status.WAITING_PAYMENT, xendit_session_id='ps_123', total_amount=500000)

        mock_get_session_status.return_value = {
            "reference_id": txn.reference_id,
            "status": "COMPLETED",
            "amount": 500000
        }

        out = StringIO()
        call_command('sync_unpaid_payments', stdout=out)

        txn.refresh_from_db()
        self.assertEqual(txn.status, SavingTransaction.Status.PAID)

    @patch('_product.management.commands.sync_unpaid_payments.XenditService.get_session_status')
    def test_skips_already_paid(self, mock_get_session_status):
        txn = make_saving_transaction(status=SavingTransaction.Status.PAID, xendit_session_id='ps_124')

        out = StringIO()
        call_command('sync_unpaid_payments', stdout=out)

        mock_get_session_status.assert_not_called()

    @patch('_product.management.commands.sync_unpaid_payments.XenditService.get_session_status')
    def test_handles_api_errors_gracefully(self, mock_get_session_status):
        txn = make_saving_transaction(status=SavingTransaction.Status.WAITING_PAYMENT, xendit_session_id='ps_125')

        mock_get_session_status.side_effect = XenditAPIError("API Down")

        out = StringIO()
        call_command('sync_unpaid_payments', stdout=out)

        txn.refresh_from_db()
        self.assertEqual(txn.status, SavingTransaction.Status.WAITING_PAYMENT)
