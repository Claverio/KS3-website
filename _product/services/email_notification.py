import logging
from email.mime.image import MIMEImage
from email.utils import formataddr

from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone

from _product.models import SavingTransaction
from _setting.models import ContactSetting, EmailSetting

logger = logging.getLogger(__name__)


def send_saving_paid_email_safely(saving_txn_id):
    saving_txn = SavingTransaction.objects.select_related("product").get(pk=saving_txn_id)
    if saving_txn.email_sent_at:
        return True
    SavingTransaction.objects.filter(pk=saving_txn_id).update(email_attempt_count=F("email_attempt_count") + 1)
    setting = EmailSetting.load()
    if not setting.email_host_user or not setting.email_host_password:
        error = "SMTP credentials are incomplete."
        SavingTransaction.objects.filter(pk=saving_txn_id).update(email_last_error=error)
        logger.warning("Paid email skipped for %s: %s", saving_txn.reference_id, error)
        return False
    try:
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=setting.email_host,
            port=setting.email_port,
            username=setting.email_host_user,
            password=setting.email_host_password,
            use_tls=setting.email_use_tls,
            timeout=15,
        )
        contact = ContactSetting.load()
        context = {"saving_txn": saving_txn, "contact_setting": contact}
        subject = render_to_string("cms/emails/saving/payment_success_subject.txt", context).strip()
        text = render_to_string("cms/emails/saving/payment_success.txt", context)
        html = render_to_string("cms/emails/saving/payment_success.html", context)
        message = EmailMultiAlternatives(
            subject,
            text,
            formataddr(("KS3 Simpan Pinjam", setting.email_host_user)),
            [saving_txn.email],
            reply_to=[contact.email] if contact.email else [],
            connection=connection,
        )
        message.attach_alternative(html, "text/html")
        logo_path = finders.find("cms/images/logo-koperasi-horizontal-email.png")
        if logo_path:
            with open(logo_path, "rb") as logo_file:
                logo = MIMEImage(logo_file.read(), _subtype="png")
            logo.add_header("Content-ID", "<ks3-logo>")
            logo.add_header("Content-Disposition", "inline", filename="ks3-logo.png")
            message.attach(logo)
        sent_count = message.send()
        if sent_count != 1:
            raise RuntimeError("SMTP backend did not accept the email.")
        SavingTransaction.objects.filter(pk=saving_txn_id).update(
            email_sent_at=timezone.now(),
            email_last_error="",
        )
        return True
    except Exception as exc:
        SavingTransaction.objects.filter(pk=saving_txn_id).update(email_last_error=str(exc)[:1000])
        logger.exception("Paid email failed for %s.", saving_txn.reference_id)
        return False
