from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from backend.helper.streamfield import page_content_blocks
from _p2p.services.payment_transition import apply_xendit_payment_update
from _setting.models import XenditSetting
from .factories import make_project


class StreamFieldDefinitionTests(SimpleTestCase):
    def test_global_blocks_have_templates_and_no_raw_html(self):
        blocks = dict(page_content_blocks())
        self.assertNotIn("raw_html", blocks)
        self.assertNotIn("table", blocks)
        for block in blocks.values():
            self.assertTrue(block.meta.template)


class SimulatePurchaseCommandTests(TestCase):
    @patch("_p2p.management.commands.simulate_p2p_purchase.synchronize_xendit_purchase")
    @patch("_p2p.services.purchase_workflow.XenditService.create_invoice")
    @patch("builtins.input")
    def test_real_workflow_wiring_in_poll_mode(self, user_input, create_invoice, synchronize):
        project = make_project()
        setting = XenditSetting.load()
        setting.api_key = "test-key"
        setting.public_base_url = "https://example.test"
        setting.return_base_url = "http://127.0.0.1:8000"
        setting.save()
        user_input.side_effect = [
            "1",
            "Budi Santoso",
            "081234567890",
            "budi@example.com",
            "1234567890123456",
            "",
            "CREATE",
        ]

        def create_response(**kwargs):
            return {
                "payment_session_id": "ps-1234567890123456789012345",
                "reference_id": kwargs["reference_id"],
                "status": "ACTIVE",
                "payment_link_url": "https://xen.to/test",
                "expires_at": "2027-01-01T00:00:00Z",
            }

        def complete(purchase):
            return apply_xendit_payment_update(
                purchase,
                {
                    "payment_session_id": purchase.xendit_session_id,
                    "reference_id": purchase.reference_id,
                    "amount": str(purchase.total_amount),
                    "currency": "IDR",
                    "status": "COMPLETED",
                },
            )

        create_invoice.side_effect = create_response
        synchronize.side_effect = complete
        output = StringIO()
        call_command(
            "simulate_p2p_purchase",
            xendit_mode="poll",
            project_id=project.pk,
            payment_wait=2,
            interval=1,
            stdout=output,
        )
        self.assertIn("Payment completed safely", output.getvalue())
