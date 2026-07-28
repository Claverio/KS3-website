import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from _p2p.models import P2PPurchase
from _p2p.services import synchronize_xendit_purchase

logger = logging.getLogger(__name__)


def purchase_status(request, public_id):
    purchase = get_object_or_404(P2PPurchase, public_id=public_id)
    if (
        purchase.status == P2PPurchase.Status.WAITING_PAYMENT
        and purchase.xendit_session_id
        and cache.add(f"p2p:status-sync:{purchase.pk}", True, timeout=10)
    ):
        try:
            purchase = synchronize_xendit_purchase(purchase)
        except Exception as exc:
            logger.warning("Xendit status reconciliation failed for %s: %s", purchase.reference_id, exc)
            purchase.refresh_from_db()
    redirect_url = None
    if purchase.status == P2PPurchase.Status.PAID:
        redirect_url = reverse("p2p_booking_complete", kwargs={"public_id": purchase.public_id})
    return JsonResponse(
        {
            "reference_id": purchase.reference_id,
            "status": purchase.status,
            "provider_status": purchase.xendit_session_status,
            "is_final": purchase.is_final,
            "redirect_url": redirect_url,
        }
    )
