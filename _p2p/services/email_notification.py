import logging
from email.mime.image import MIMEImage
from email.utils import formataddr

from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

from _p2p.models import P2PPurchase
from _setting.models import ContactSetting, EmailSetting

logger = logging.getLogger(__name__)


def send_paid_email_safely(purchase_id):
    purchase = P2PPurchase.objects.select_related("project").get(pk=purchase_id)
    setting = EmailSetting.load()
    if not setting.email_host_user or not setting.email_host_password:
        logger.warning("Paid email skipped for %s: SMTP credentials are incomplete.", purchase.reference_id)
        return False
    try:
        connection = get_connection(
            host=setting.email_host,
            port=setting.email_port,
            username=setting.email_host_user,
            password=setting.email_host_password,
            use_tls=setting.email_use_tls,
        )
        contact = ContactSetting.load()
        context = {"purchase": purchase, "contact_setting": contact}
        subject = render_to_string("cms/emails/p2p/payment_success_subject.txt", context).strip()
        text = render_to_string("cms/emails/p2p/payment_success.txt", context)
        html = render_to_string("cms/emails/p2p/payment_success.html", context)
        message = EmailMultiAlternatives(
            subject,
            text,
            formataddr(("KS3 Simpan Pinjam", setting.email_host_user)),
            [purchase.email],
            reply_to=[contact.email],
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
        message.send()
        return True
    except Exception:
        logger.exception("Paid email failed for %s.", purchase.reference_id)
        return False
