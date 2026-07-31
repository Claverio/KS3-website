import logging
from urllib.parse import quote

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_exempt

from _product.forms import SavingTransactionForm
from _product.models import SavingTransaction
from _product.services import create_online_saving_transaction, synchronize_saving_transaction
from _product.services.saving_workflow import SavingWorkflowError
from _setting.models import ContactSetting, XenditSetting
from backend.services.xendit import XenditError

logger = logging.getLogger(__name__)


def saving_create(request):
    payment_gateway_fee = XenditSetting.load().saving_payment_gateway_fee
    form = SavingTransactionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            saving_txn = create_online_saving_transaction(**form.cleaned_data)
        except SavingWorkflowError as exc:
            form.add_error(None, str(exc))
        except XenditError as exc:
            logger.warning("Xendit unavailable while creating a saving transaction: %s", exc)
            form.add_error(
                None,
                "Koneksi ke Xendit sedang lambat atau tidak tersedia. Belum ada tagihan yang dibuat; silakan coba kembali.",
            )
        except Exception:
            logger.exception("Public saving transaction creation failed.")
            form.add_error(None, "Payment Session gagal dibuat. Silakan coba lagi atau hubungi admin.")
        else:
            return redirect("saving_waiting", public_id=saving_txn.public_id)
    return render(
        request,
        "cms/pages/saving_form.html",
        {"form": form, "payment_gateway_fee": payment_gateway_fee},
    )


def saving_waiting(request, public_id):
    saving_txn = get_object_or_404(
        SavingTransaction.objects.select_related("product"), public_id=public_id
    )
    if saving_txn.status == SavingTransaction.Status.PAID:
        return redirect("saving_complete", public_id=saving_txn.public_id)
    return render(request, "cms/pages/saving_waiting.html", {"saving_txn": saving_txn})


def saving_status(request, public_id):
    saving_txn = get_object_or_404(SavingTransaction, public_id=public_id)
    if (
        saving_txn.status == SavingTransaction.Status.WAITING_PAYMENT
        and saving_txn.xendit_session_id
        and cache.add(f"saving:status-sync:{saving_txn.pk}", True, timeout=10)
    ):
        try:
            saving_txn = synchronize_saving_transaction(saving_txn)
        except Exception as exc:
            logger.warning("Saving status reconciliation failed for %s: %s", saving_txn.reference_id, exc)
            saving_txn.refresh_from_db()
    redirect_url = None
    if saving_txn.status == SavingTransaction.Status.PAID:
        redirect_url = reverse("saving_complete", kwargs={"public_id": saving_txn.public_id})
    return JsonResponse(
        {
            "reference_id": saving_txn.reference_id,
            "status": saving_txn.status,
            "provider_status": saving_txn.xendit_session_status,
            "is_final": saving_txn.is_final,
            "redirect_url": redirect_url,
        }
    )


@xframe_options_exempt
def saving_xendit_return(request, public_id):
    saving_txn = SavingTransaction.objects.filter(public_id=public_id).first()
    if saving_txn is None:
        target_url = request.build_absolute_uri(reverse("saving_create"))
        return render(
            request,
            "cms/pages/p2p_xendit_return.html",
            {
                "public_id": public_id,
                "target_url": target_url,
                "transaction_missing": True,
                "return_event_type": "saving-payment-return",
            },
        )

    if (
        saving_txn.status == SavingTransaction.Status.WAITING_PAYMENT
        and saving_txn.xendit_session_id
    ):
        try:
            saving_txn = synchronize_saving_transaction(saving_txn)
        except Exception as exc:
            logger.warning(
                "Xendit return reconciliation failed for %s: %s",
                saving_txn.reference_id,
                exc,
            )
            saving_txn.refresh_from_db()

    route_name = (
        "saving_complete"
        if saving_txn.status == SavingTransaction.Status.PAID
        else "saving_waiting"
    )
    target_url = request.build_absolute_uri(
        reverse(route_name, kwargs={"public_id": saving_txn.public_id})
    )
    return render(
        request,
        "cms/pages/p2p_xendit_return.html",
        {
            "saving_txn": saving_txn,
            "public_id": public_id,
            "target_url": target_url,
            "return_event_type": "saving-payment-return",
        },
    )


def _whatsapp_confirmation_url(saving_txn):
    contact = ContactSetting.load()
    if not contact.whatsapp_link:
        return ""
    lines = [
        "Halo Koperasi KS3,",
        "",
        "Saya ingin mengonfirmasi setoran simpanan yang telah saya lakukan.",
        f"Nama: {saving_txn.full_name}",
        f"Produk: {saving_txn.product.title}",
        f"Nominal: Rp{saving_txn.total_amount:,.0f}".replace(",", "."),
        f"Kode setoran: {saving_txn.transaction_code}",
        "Status: Lunas",
    ]
    separator = "&" if "?" in contact.whatsapp_link else "?"
    return f"{contact.whatsapp_link}{separator}text={quote(chr(10).join(lines), safe='')}"


def saving_complete(request, public_id):
    saving_txn = get_object_or_404(
        SavingTransaction.objects.select_related("product"), public_id=public_id
    )
    if saving_txn.status != SavingTransaction.Status.PAID:
        return redirect("saving_waiting", public_id=saving_txn.public_id)
    if not saving_txn.email_sent_at and saving_txn.email_attempt_count < 3:
        from _product.services.email_notification import send_saving_paid_email_safely

        send_saving_paid_email_safely(saving_txn.pk)
        saving_txn.refresh_from_db()
    return render(
        request,
        "cms/pages/saving_complete.html",
        {
            "saving_txn": saving_txn,
            "whatsapp_confirmation_url": _whatsapp_confirmation_url(saving_txn),
        },
    )
