from urllib.parse import quote

from django.contrib import messages
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_exempt

from _p2p.forms import P2PPurchaseForm
from _p2p.models import P2P, P2PSEOSettings, P2PPurchase
from _p2p.services.purchase_workflow import PurchaseWorkflowError, create_p2p_purchase
from _payment.services import FeeConfigurationError
from _setting.models import ContactSetting, XenditSetting


def _seo_context(section):
    seo = P2PSEOSettings.load()
    context = {
        "seo_title": getattr(seo, f"{section}_title"),
        "seo_description": getattr(seo, f"{section}_description"),
        "seo_keywords": getattr(seo, f"{section}_keywords"),
        "seo_og_image": seo.og_image,
    }
    if section == "list":
        context.update(
            {
                "page_heading": seo.list_heading,
                "page_intro": seo.list_intro,
            }
        )
    return context


def p2p_list(request):
    projects = P2P.objects.select_related("category").filter(
        is_published=True, category__is_active=True
    )
    return render(
        request,
        "cms/pages/p2p_list.html",
        {"projects": projects, **_seo_context("list")},
    )


def p2p_detail(request, slug):
    project = get_object_or_404(
        P2P.objects.select_related("category", "prospectus"), slug=slug, is_published=True
    )
    context = {"project": project, "streamfield": project.content, **_seo_context("detail")}
    if not context["seo_title"]:
        context["seo_title"] = project.title
    if not context["seo_description"]:
        context["seo_description"] = project.summary
    return render(request, "cms/pages/p2p_details.html", context)


def p2p_purchase(request, slug):
    project = get_object_or_404(P2P.objects.select_related("category"), slug=slug, is_published=True)
    if not project.can_purchase:
        raise Http404("Project is not available for purchase.")
    form = P2PPurchaseForm(request.POST or None, project=project)
    if request.method == "POST" and form.is_valid():
        try:
            purchase = create_p2p_purchase(
                project=project,
                **form.cleaned_data,
            )
        except (PurchaseWorkflowError, FeeConfigurationError) as exc:
            form.add_error(None, str(exc))
        except Exception:
            form.add_error(None, "Payment Session gagal dibuat. Silakan coba lagi atau hubungi admin.")
        else:
            return redirect("p2p_purchase_waiting", public_id=purchase.public_id)
    return render(
        request,
        "cms/pages/p2p_purchase.html",
        {"project": project, "form": form, **_seo_context("purchase")},
    )


def p2p_waiting(request, public_id):
    purchase = get_object_or_404(P2PPurchase.objects.select_related("project"), public_id=public_id)
    if purchase.status == P2PPurchase.Status.PAID:
        return redirect("p2p_booking_complete", public_id=purchase.public_id)
    return render(
        request,
        "cms/pages/p2p_waiting.html",
        {"purchase": purchase, **_seo_context("purchase")},
    )


@xframe_options_exempt
def p2p_xendit_return(request, public_id):
    """Iframe-safe landing page for Xendit's required public HTTPS return URL."""
    purchase = get_object_or_404(P2PPurchase, public_id=public_id)
    setting = XenditSetting.load()
    base_url = setting.return_base_url or request.build_absolute_uri("/").rstrip("/")
    return render(
        request,
        "cms/pages/p2p_xendit_return.html",
        {"purchase": purchase, "target_url": _absolute_return_url(base_url, purchase.public_id)},
    )


def _absolute_return_url(base_url, public_id):
    path = reverse("p2p_purchase_waiting", kwargs={"public_id": public_id})
    return f"{base_url.rstrip('/')}{path}"


def _whatsapp_confirmation_url(purchase):
    contact = ContactSetting.load()
    if not contact.whatsapp_link:
        return ""
    lines = [
        "Halo Koperasi KS3,",
        "",
        "Saya ingin mengonfirmasi pendanaan yang telah saya lakukan.",
        "",
        "Data pendana:",
        f"Nama: {purchase.full_name}",
        f"No. WhatsApp: {purchase.phone}",
        f"Email: {purchase.email}",
        "",
        "Detail pendanaan:",
        f"Produk P2P: {purchase.project.title}",
        f"Jumlah slot: {purchase.slot_quantity} slot",
        f"Total pembayaran: Rp{purchase.total_amount:,.0f}".replace(",", "."),
        f"Nomor booking: {purchase.booking_number}",
        "Status pembayaran: Lunas",
    ]
    if purchase.note:
        lines.append(f"Catatan: {purchase.note}")
    lines.extend(["", "Mohon bantu konfirmasi data pendanaan saya. Terima kasih."])
    separator = "&" if "?" in contact.whatsapp_link else "?"
    return f"{contact.whatsapp_link}{separator}text={quote(chr(10).join(lines), safe='')}"


def p2p_complete(request, public_id):
    purchase = get_object_or_404(P2PPurchase.objects.select_related("project"), public_id=public_id)
    if purchase.status != P2PPurchase.Status.PAID:
        return redirect("p2p_purchase_waiting", public_id=purchase.public_id)
    if not purchase.email_sent_at and purchase.email_attempt_count < 3:
        from _p2p.services.email_notification import send_paid_email_safely

        send_paid_email_safely(purchase.pk)
        purchase.refresh_from_db()
    return render(
        request,
        "cms/pages/p2p_booking_complete.html",
        {
            "purchase": purchase,
            "project": purchase.project,
            "whatsapp_confirmation_url": _whatsapp_confirmation_url(purchase),
            **_seo_context("complete"),
        },
    )
