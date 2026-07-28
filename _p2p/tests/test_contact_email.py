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
        self.assertContains(response, "https://wa.me/6281234567890?text=")
        self.assertContains(response, "NIK%3A%201234567890123456")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_paid_email_has_ks3_branding_logo_and_contact(self):
        email_setting = EmailSetting.load()
        email_setting.email_host_user = "sender@example.com"
        email_setting.email_host_password = "app-password"
        email_setting.save()
        purchase = make_purchase(status=P2PPurchase.Status.PAID)

        self.assertTrue(send_paid_email_safely(purchase.pk))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.reply_to, ["cs@koperasiks3.id"])
        self.assertIn("KS3 Simpan Pinjam", message.from_email)
        self.assertIn("cid:ks3-logo", message.alternatives[0].content)
        self.assertTrue(
            any(attachment.get("Content-ID") == "<ks3-logo>" for attachment in message.attachments)
        )
