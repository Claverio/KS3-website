from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase

from backend.services.xendit import XenditAPIError
from _product.models import SavingTransaction
from _product.services.saving_workflow import SavingWorkflowError, create_saving_transaction
from _product.tests.factories import make_product
from _setting.models import XenditSetting


class SavingWorkflowTest(TestCase):
    @patch("_product.services.saving_workflow.XenditService.create_invoice")
    def test_creates_xendit_session_and_updates_status(self, create_invoice):
        setting = XenditSetting.load()
        setting.return_base_url = "https://ks3.claverio.com"
        setting.save()
        create_invoice.return_value = {
            "payment_session_id": "ps-1234567890123456789012345",
            "reference_id": "placeholder",
            "status": "ACTIVE",
            "payment_link_url": "https://xen.to/test",
            "expires_at": "2027-01-01T00:00:00Z",
        }
        create_invoice.side_effect = lambda **kwargs: {
            **create_invoice.return_value,
            "reference_id": kwargs["reference_id"],
        }

        product = make_product()
        # save() auto-generates reference_id and transaction_code
        instance = SavingTransaction.objects.create(
            product=product,
            full_name="Budi Santoso",
            phone="081234567890",
            email="budi@example.com",
            is_new_member=True,
            amount=Decimal("500000"),
            service_fee=Decimal("2750"),
            status=SavingTransaction.Status.CREATING,
        )
        self.assertTrue(instance.reference_id.startswith("KS3-SAV-"))
        self.assertTrue(instance.transaction_code.startswith("KS3-STR-"))

        result = create_saving_transaction(saving_txn=instance)

        instance.refresh_from_db()
        self.assertEqual(instance.status, SavingTransaction.Status.WAITING_PAYMENT)
        self.assertEqual(instance.payment_link_url, "https://xen.to/test")
        self.assertEqual(instance.xendit_session_id, "ps-1234567890123456789012345")
        self.assertEqual(instance.total_amount, Decimal("502750"))
        expected_return_url = (
            f"https://ks3.claverio.com/api/product/savings/{instance.public_id}/return/"
        )
        self.assertEqual(
            create_invoice.call_args.kwargs["success_return_url"], expected_return_url
        )
        self.assertEqual(
            create_invoice.call_args.kwargs["cancel_return_url"], expected_return_url
        )
        self.assertEqual(
            create_invoice.call_args.kwargs["allowed_payment_channels"],
            ["BCA_VIRTUAL_ACCOUNT"],
        )
        self.assertEqual(
            [item["type"] for item in create_invoice.call_args.kwargs["items"]],
            ["DIGITAL_SERVICE", "FEE"],
        )
        snapshot = instance.xendit_fee_snapshot
        self.assertEqual(snapshot.charged_fee_total, Decimal("2750"))
        self.assertEqual(snapshot.session_response_snapshot["status"], "ACTIVE")

    @patch("_product.services.saving_workflow.XenditService.create_invoice")
    def test_sets_failed_on_xendit_error(self, create_invoice):
        create_invoice.side_effect = XenditAPIError("API Down")

        product = make_product()
        instance = SavingTransaction.objects.create(
            product=product,
            full_name="Budi Santoso",
            phone="081234567890",
            email="budi@example.com",
            is_new_member=True,
            amount=Decimal("500000"),
            service_fee=Decimal("2750"),
            status=SavingTransaction.Status.CREATING,
        )

        with self.assertRaises(XenditAPIError):
            create_saving_transaction(saving_txn=instance)

        instance.refresh_from_db()
        self.assertEqual(instance.status, SavingTransaction.Status.FAILED)
