from unittest.mock import patch

from django.test import TestCase

from _p2p.models import P2PPurchase
from _p2p.services.purchase_workflow import PurchaseWorkflowError, create_p2p_purchase
from .factories import make_project


class PurchaseWorkflowTests(TestCase):
    @patch("_p2p.services.purchase_workflow.XenditService.create_invoice")
    def test_creates_snapshot_and_xendit_session(self, create_invoice):
        project = make_project()
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
        purchase = create_p2p_purchase(
            project=project,
            full_name="Budi Santoso",
            phone="081234567890",
            email="budi@example.com",
            nik="1234567890123456",
            note="",
            slot_quantity=2,
        )
        self.assertEqual(purchase.status, P2PPurchase.Status.WAITING_PAYMENT)
        self.assertEqual(purchase.subtotal, project.slot_price * 2)
        self.assertEqual(project.available_slots, 8)
        request_kwargs = create_invoice.call_args.kwargs
        self.assertNotIn("success_return_url", request_kwargs)
        self.assertNotIn("cancel_return_url", request_kwargs)

    def test_rejects_unavailable_quantity_before_provider_call(self):
        project = make_project(total_slots=1)
        with self.assertRaises(PurchaseWorkflowError):
            create_p2p_purchase(
                project=project,
                full_name="Budi",
                phone="081234567890",
                email="budi@example.com",
                nik="",
                note="",
                slot_quantity=2,
            )
