from django.test import TestCase

from _p2p.forms import P2PPurchaseForm

from .factories import make_project


class PurchaseFormValidationTests(TestCase):
    def setUp(self):
        self.project = make_project(total_slots=10)

    def form(self, **overrides):
        data = {
            "full_name": "Budi Santoso",
            "phone": "0812 3456 7890",
            "email": "BUDI@EXAMPLE.COM",
            "nik": "1234567890123456",
            "slot_quantity": "1",
            "note": "Konfirmasi via WhatsApp",
        }
        data.update(overrides)
        return P2PPurchaseForm(data=data, project=self.project)

    def test_rejects_invalid_identity_and_quantity_fields(self):
        form = self.form(
            full_name="Budi123",
            phone="081234abcd",
            email="bukan-email",
            nik="123abc",
            slot_quantity="10aaaa",
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            set(("full_name", "phone", "email", "nik", "slot_quantity")) - set(form.errors),
            set(),
        )

    def test_normalizes_valid_name_phone_email_and_note(self):
        form = self.form(
            full_name="  Budi   Santoso  ",
            phone="0812-3456 7890",
            email="BUDI@EXAMPLE.COM",
            note="  Hubungi sore hari  ",
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["full_name"], "Budi Santoso")
        self.assertEqual(form.cleaned_data["phone"], "081234567890")
        self.assertEqual(form.cleaned_data["email"], "budi@example.com")
        self.assertEqual(form.cleaned_data["note"], "Hubungi sore hari")

    def test_rejects_quantity_above_current_availability(self):
        form = self.form(slot_quantity="11")
        self.assertFalse(form.is_valid())
        self.assertIn("Slot tersedia tidak mencukupi.", form.errors["slot_quantity"])
