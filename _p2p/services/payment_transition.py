from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from _p2p.models import P2PPurchase


class PaymentTransitionError(Exception):
    pass


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


@transaction.atomic
def apply_xendit_payment_update(purchase, payload, *, webhook_id="", webhook_payload=None):
    purchase = P2PPurchase.objects.select_for_update().get(pk=purchase.pk)
    data = payload.get("data", payload)
    reference_id = data.get("reference_id")
    session_id = data.get("payment_session_id")
    if reference_id != purchase.reference_id:
        raise PaymentTransitionError("Xendit reference ID does not match the purchase.")
    if purchase.xendit_session_id and session_id != purchase.xendit_session_id:
        raise PaymentTransitionError("Xendit session ID does not match the purchase.")
    try:
        amount = Decimal(str(data.get("amount")))
    except (InvalidOperation, TypeError):
        raise PaymentTransitionError("Xendit amount is missing or invalid.")
    if amount != purchase.total_amount:
        raise PaymentTransitionError("Xendit amount does not match the purchase total.")
    if data.get("currency") != purchase.currency:
        raise PaymentTransitionError("Xendit currency does not match the purchase.")

    provider_status = str(data.get("status", "")).upper()
    mapping = {
        "COMPLETED": P2PPurchase.Status.PAID,
        "EXPIRED": P2PPurchase.Status.EXPIRED,
        "CANCELED": P2PPurchase.Status.CANCELED,
        "ACTIVE": P2PPurchase.Status.WAITING_PAYMENT,
    }
    target_status = mapping.get(provider_status)
    if not target_status:
        raise PaymentTransitionError(f"Unsupported Xendit status: {provider_status or '-'}.")
    if purchase.status == P2PPurchase.Status.PAID and target_status != P2PPurchase.Status.PAID:
        raise PaymentTransitionError("A paid purchase cannot move to another status.")

    became_paid = purchase.status != P2PPurchase.Status.PAID and target_status == P2PPurchase.Status.PAID
    purchase.status = target_status
    purchase.xendit_session_status = provider_status
    purchase.payment_id = data.get("payment_id") or purchase.payment_id
    purchase.payment_request_id = data.get("payment_request_id") or purchase.payment_request_id
    purchase.provider_updated_at = _parse_datetime(data.get("updated")) or timezone.now()
    purchase.xendit_last_response = payload
    if webhook_payload is not None:
        purchase.xendit_webhook_payload = webhook_payload
    if webhook_id:
        purchase.xendit_webhook_id = webhook_id
    if became_paid:
        purchase.paid_at = purchase.provider_updated_at
    purchase.save()

    if became_paid:
        from .email_notification import send_paid_email_safely

        transaction.on_commit(lambda: send_paid_email_safely(purchase.pk))
    return purchase
