from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from _p2p.models import P2PPurchase
from _p2p.services.purchase_workflow import create_p2p_purchase
from _p2p.tests.factories import make_project, make_purchase
from _payment.models import (
    XenditFeeAdjustment,
    XenditFeeRate,
    XenditPaymentChannel,
    XenditTransactionFee,
)
from _payment.services import (
    create_fee_snapshot,
    post_adjustment_fifo,
    reconcile_transaction_fee,
)
from _payment.services.reconciliation import refresh_reconciliation_status


class XenditFeeCheckoutTests(TestCase):
    def test_fee_quote_uses_selected_va_rate(self):
        response = self.client.get(
            reverse("xendit_fee_quote"),
            {
                "route": "saving",
                "channel": "BCA_VIRTUAL_ACCOUNT",
                "amount": "500000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["fee_total"], "2750")
        self.assertEqual(response.json()["total_amount"], "502750")

    @patch("_p2p.services.purchase_workflow.XenditService.create_invoice")
    def test_p2p_checkout_locks_one_va_and_sends_principal_plus_fee_items(self, create_invoice):
        project = make_project(service_fee=Decimal("999999"))
        create_invoice.side_effect = lambda **kwargs: {
            "payment_session_id": "ps-selected-va-123456789012345",
            "reference_id": kwargs["reference_id"],
            "status": "ACTIVE",
            "payment_link_url": "https://xen.to/selected-va",
            "expires_at": "2027-01-01T00:00:00Z",
        }

        purchase = create_p2p_purchase(
            project=project,
            full_name="Budi Santoso",
            phone="081234567890",
            email="budi@example.com",
            nik="1234567890123456",
            note="",
            slot_quantity=2,
            xendit_channel="BNI_VIRTUAL_ACCOUNT",
        )

        self.assertEqual(purchase.service_fee, Decimal("2750"))
        self.assertEqual(purchase.total_amount, Decimal("202750"))
        payload = create_invoice.call_args.kwargs
        self.assertEqual(payload["allowed_payment_channels"], ["BNI_VIRTUAL_ACCOUNT"])
        self.assertEqual([item["type"] for item in payload["items"]], ["DIGITAL_SERVICE", "FEE"])
        self.assertEqual(sum(item["net_unit_amount"] for item in payload["items"]), 202750)
        self.assertEqual(payload["metadata"]["selected_va_channel"], "BNI_VIRTUAL_ACCOUNT")

        snapshot = purchase.xendit_fee_snapshot
        self.assertEqual(snapshot.channel.code, "BNI_VIRTUAL_ACCOUNT")
        self.assertEqual(snapshot.charged_fee_total, Decimal("2750"))
        self.assertEqual(snapshot.session_request_snapshot["items"][1]["type"], "FEE")

    def test_p2p_financials_and_fee_snapshot_are_immutable(self):
        purchase = make_purchase()
        snapshot, _ = create_fee_snapshot(
            transaction=purchase,
            route="p2p",
            channel_code="BCA_VIRTUAL_ACCOUNT",
            principal_amount=purchase.subtotal,
        )
        snapshot.xendit_session_id = purchase.xendit_session_id
        snapshot.save()

        purchase.service_fee = Decimal("9999")
        with self.assertRaises(ValidationError):
            purchase.save()

        snapshot.charged_fee_total = Decimal("9999")
        with self.assertRaises(ValidationError):
            snapshot.save()


class XenditFeeReconciliationTests(TestCase):
    def _paid_fee(self, suffix, actual_fee):
        project = make_project(slug=f"fee-project-{suffix}")
        purchase = make_purchase(
            project=project,
            reference_id=f"FEE-REF-{suffix}",
            booking_number=f"FEE-BOOK-{suffix}",
            xendit_session_id=f"ps-fee-{suffix:0>25}",
            status=P2PPurchase.Status.PAID,
            paid_at=timezone.now(),
        )
        snapshot, _ = create_fee_snapshot(
            transaction=purchase,
            route="p2p",
            channel_code="BCA_VIRTUAL_ACCOUNT",
            principal_amount=purchase.subtotal,
        )
        snapshot.xendit_session_id = purchase.xendit_session_id
        snapshot.save()
        snapshot.actual_xendit_fee = Decimal(actual_fee)
        snapshot.actual_vat = Decimal("0")
        snapshot.actual_fee_status = "COMPLETED"
        snapshot.reconciled_at = timezone.now()
        snapshot.save()
        return refresh_reconciliation_status(snapshot)

    @patch("_payment.services.reconciliation.XenditService.list_transactions")
    def test_actual_fee_is_snapshotted_and_next_rate_is_auto_versioned(self, list_transactions):
        fee = self._paid_fee("sync", "2750")
        old_rate = fee.rate
        # Reset provider fields so this call represents the first Transactions API sync.
        fee.actual_xendit_fee = None
        fee.actual_vat = None
        fee.actual_fee_status = ""
        fee.reconciliation_status = XenditTransactionFee.ReconciliationStatus.PENDING
        fee.save()
        list_transactions.return_value = {
            "data": [
                {
                    "id": "txn_actual_fee_sync",
                    "product_id": "py_actual_fee_sync",
                    "type": "PAYMENT",
                    "status": "SUCCESS",
                    "channel_category": "VIRTUAL_ACCOUNT",
                    "channel_code": "BCA",
                    "reference_id": fee.p2p_purchase.reference_id,
                    "account_identifier": "1234567890",
                    "currency": "IDR",
                    "amount": 102750,
                    "net_amount": 98750,
                    "net_amount_currency": "IDR",
                    "cashflow": "MONEY_IN",
                    "settlement_status": "SETTLED",
                    "business_id": "business-test",
                    "created": "2026-08-02T00:00:00Z",
                    "updated": "2026-08-02T00:01:00Z",
                    "estimated_settlement_time": "2026-08-02T00:02:00Z",
                    "fee": {
                        "xendit_fee": 4000,
                        "value_added_tax": 0,
                        "xendit_withholding_tax": 100,
                        "third_party_withholding_tax": 50,
                        "status": "COMPLETED",
                    },
                    "product_data": {"payment_request_id": "pr_actual_fee_sync"},
                }
            ]
        }

        fee = reconcile_transaction_fee(fee)

        self.assertEqual(fee.actual_total_fee, Decimal("4000"))
        self.assertEqual(fee.raw_variance, Decimal("-1250"))
        self.assertEqual(fee.reconciliation_status, XenditTransactionFee.ReconciliationStatus.SHORT)
        self.assertEqual(fee.provider_transaction_id, "txn_actual_fee_sync")
        self.assertEqual(fee.actual_product_data["payment_request_id"], "pr_actual_fee_sync")
        self.assertEqual(fee.actual_payload["settlement_status"], "SETTLED")
        # Withholding tax is retained in audit fields, but not counted as gateway fee.
        self.assertEqual(fee.actual_xendit_withholding_tax, Decimal("100"))

        old_rate.refresh_from_db()
        self.assertEqual(old_rate.status, XenditFeeRate.Status.SUPERSEDED)
        current = XenditFeeRate.objects.get(
            channel__code="BCA_VIRTUAL_ACCOUNT",
            status=XenditFeeRate.Status.ACTIVE,
            effective_to__isnull=True,
        )
        self.assertEqual(current.fixed_fee, Decimal("4000"))
        self.assertEqual(current.source, XenditFeeRate.Source.OBSERVED)

    def test_one_adjustment_covers_many_variances_fifo_and_leaves_remainder(self):
        first = self._paid_fee("one", "3750")
        second = self._paid_fee("two", "3750")
        first_total = first.p2p_purchase.total_amount
        adjustment = XenditFeeAdjustment.objects.create(
            amount=Decimal("1500"),
            kind=XenditFeeAdjustment.Kind.PROVIDER_CREDIT,
            reason="Kredit gabungan perubahan fee VA",
        )

        post_adjustment_fifo(adjustment)

        first.refresh_from_db()
        second.refresh_from_db()
        adjustment.refresh_from_db()
        self.assertEqual(first.residual_variance, Decimal("0"))
        self.assertEqual(second.residual_variance, Decimal("-500"))
        self.assertEqual(first.reconciliation_status, XenditTransactionFee.ReconciliationStatus.ADJUSTED)
        self.assertEqual(second.reconciliation_status, XenditTransactionFee.ReconciliationStatus.SHORT)
        self.assertEqual(adjustment.allocated_amount, Decimal("1500"))
        self.assertEqual(adjustment.unallocated_amount, Decimal("0"))
        first.p2p_purchase.refresh_from_db()
        self.assertEqual(first.p2p_purchase.total_amount, first_total)

    def test_single_5000_adjustment_can_close_five_fee_changes(self):
        fees = [self._paid_fee(f"batch-{index}", "3750") for index in range(5)]
        adjustment = XenditFeeAdjustment.objects.create(
            amount=Decimal("5000"),
            kind=XenditFeeAdjustment.Kind.PROVIDER_CREDIT,
            reason="Satu kredit provider untuk lima selisih fee",
        )

        post_adjustment_fifo(adjustment)

        adjustment.refresh_from_db()
        self.assertEqual(adjustment.allocations.count(), 5)
        self.assertEqual(adjustment.allocated_amount, Decimal("5000"))
        self.assertEqual(adjustment.unallocated_amount, Decimal("0"))
        for fee in fees:
            fee.refresh_from_db()
            self.assertEqual(fee.residual_variance, Decimal("0"))
            self.assertEqual(
                fee.reconciliation_status,
                XenditTransactionFee.ReconciliationStatus.ADJUSTED,
            )

    def test_admin_reconciliation_report_is_available(self):
        user = get_user_model().objects.create_superuser(
            username="fee-admin", email="fee@example.com", password="secret"
        )
        self.client.force_login(user)
        response = self.client.get(reverse("xendit_fee_reconciliation_report"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rekonsiliasi Fee Xendit")
        self.assertContains(response, "Post adjustment")
