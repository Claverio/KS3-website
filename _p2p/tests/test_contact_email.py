from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from _p2p.models import P2PPurchase
from _p2p.services.email_notification import send_paid_email_safely
from _setting.models import ContactSetting, EmailSetting

from .factories import make_purchase


class ContactAndEmailTests(TestCase):
    def setUp(self):
        contact = ContactSetting.load()
        contact.whatsapp_display = "+62 812-3456-7890"
        contact.whatsapp_link = "https://wa.me/6281234567890"
        contact.save()

    def test_complete_page_builds_prefilled_whatsapp_confirmation(self):
        purchase = make_purchase(
            status=P2PPurchase.Status.PAID,
            nik="1234567890123456",
            note="Hubungi sore hari",
        )
        response = self.client.get(
            reverse("p2p_booking_complete", kwargs={"public_id": purchase.public_id})
        )
        self.assertContains(response, "Konfirmasi via WhatsApp")
        self.assertContains(response, purchase.booking_number)
        self.assertContains(response, 'class="ks3-copy-booking"')
        self.assertContains(response, f'data-booking-number="{purchase.booking_number}"')
        self.assertContains(response, "https://wa.me/6281234567890?text=")
        self.assertContains(response, "Halo%20Koperasi%20KS3")
        self.assertContains(response, "Data%20pendana%3A")
        self.assertContains(response, "Status%20pembayaran%3A%20Lunas")
        self.assertNotContains(response, "NIK%3A")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_paid_email_has_ks3_branding_logo_and_contact(self):
        email_setting = EmailSetting.load()
        email_setting.email_host_user = "sender@example.com"
        email_setting.email_host_password = "app-password"
        email_setting.save()
        purchase = make_purchase(status=P2PPurchase.Status.PAID)

        self.assertTrue(send_paid_email_safely(purchase.pk))
        purchase.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIsNotNone(purchase.email_sent_at)
        self.assertEqual(purchase.email_attempt_count, 1)
        self.assertEqual(purchase.email_last_error, "")
        message = mail.outbox[0]
        self.assertEqual(message.reply_to, ["cs@koperasiks3.id"])
        self.assertIn("KS3 Simpan Pinjam", message.from_email)
        self.assertIn("cid:ks3-logo", message.alternatives[0].content)
        self.assertTrue(
            any(attachment.get("Content-ID") == "<ks3-logo>" for attachment in message.attachments)
        )

    def test_missing_smtp_credentials_are_recorded_for_retry(self):
        email_setting = EmailSetting.load()
        email_setting.email_host_user = None
        email_setting.email_host_password = None
        email_setting.save()
        purchase = make_purchase(status=P2PPurchase.Status.PAID)

        self.assertFalse(send_paid_email_safely(purchase.pk))
        purchase.refresh_from_db()
        self.assertEqual(purchase.email_attempt_count, 1)
        self.assertIn("SMTP credentials", purchase.email_last_error)
