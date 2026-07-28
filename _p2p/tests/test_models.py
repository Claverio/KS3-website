from decimal import Decimal

from django.test import TestCase

from _p2p.models import P2PPurchase
from .factories import make_project, make_purchase


class P2PModelTests(TestCase):
    def test_availability_counts_only_reserving_statuses(self):
        project = make_project(total_slots=10)
        make_purchase(project, slot_quantity=2, subtotal=Decimal("200000"), total_amount=Decimal("202750"))
        make_purchase(
            project,
            reference_id="FAILED",
            booking_number="FAILED",
            xendit_session_id="ps-9999999999999999999999999",
            slot_quantity=3,
            subtotal=Decimal("300000"),
            total_amount=Decimal("302750"),
            status=P2PPurchase.Status.FAILED,
        )
        self.assertEqual(project.available_slots, 8)

    def test_masked_nik_does_not_expose_full_value(self):
        purchase = make_purchase()
        self.assertEqual(purchase.masked_nik, "************3456")
        self.assertNotIn(purchase.nik, purchase.masked_nik)

    def test_progress_uses_paid_slots_not_unpaid_reservations(self):
        project = make_project(total_slots=10)
        make_purchase(project, slot_quantity=2)
        make_purchase(
            project,
            reference_id="PAID",
            booking_number="PAID",
            xendit_session_id="ps-9999999999999999999999999",
            slot_quantity=3,
            subtotal=Decimal("300000"),
            total_amount=Decimal("302750"),
            status=P2PPurchase.Status.PAID,
        )
        self.assertEqual(project.available_slots, 5)
        self.assertEqual(project.progress_percentage, 30)

    def test_purchase_snapshot_validation(self):
        purchase = make_purchase()
        purchase.total_amount = Decimal("1")
        with self.assertRaisesMessage(Exception, "Total must equal"):
            purchase.full_clean()
