from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from _product.models import SavingTransaction


class SavingPaymentTransitionError(Exception):
    pass


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


@transaction.atomic
def apply_saving_payment_update(saving_txn, payload, *, webhook_id="", webhook_payload=None):
    saving_txn = SavingTransaction.objects.select_for_update().get(pk=saving_txn.pk)
    data = payload.get("data", payload)
    reference_id = data.get("reference_id")
    session_id = data.get("payment_session_id")
    if reference_id != saving_txn.reference_id:
        raise SavingPaymentTransitionError("Xendit reference ID does not match the saving transaction.")
    if session_id and saving_txn.xendit_session_id and session_id != saving_txn.xendit_session_id:
        raise SavingPaymentTransitionError("Xendit session ID does not match the saving transaction.")
    try:
        amount = Decimal(str(data.get("amount")))
    except (InvalidOperation, TypeError):
        raise SavingPaymentTransitionError("Xendit amount is missing or invalid.")
    if amount != saving_txn.total_amount:
        raise SavingPaymentTransitionError("Xendit amount does not match the saving transaction total.")
    if data.get("currency") and data.get("currency") != saving_txn.currency:
        raise SavingPaymentTransitionError("Xendit currency does not match the saving transaction.")

    provider_status = str(data.get("status", "")).upper()
    mapping = {
        "COMPLETED": SavingTransaction.Status.PAID,
        "EXPIRED": SavingTransaction.Status.EXPIRED,
        "CANCELED": SavingTransaction.Status.CANCELED,
        "ACTIVE": SavingTransaction.Status.WAITING_PAYMENT,
    }
    target_status = mapping.get(provider_status)
    if not target_status:
        raise SavingPaymentTransitionError(f"Unsupported Xendit status: {provider_status or '-'}.")
    if saving_txn.status == SavingTransaction.Status.PAID and target_status != SavingTransaction.Status.PAID:
        raise SavingPaymentTransitionError("A paid saving transaction cannot move to another status.")

    became_paid = saving_txn.status != SavingTransaction.Status.PAID and target_status == SavingTransaction.Status.PAID
    saving_txn.status = target_status
    saving_txn.xendit_session_status = provider_status
    saving_txn.payment_id = data.get("payment_id") or saving_txn.payment_id
    saving_txn.payment_request_id = data.get("payment_request_id") or saving_txn.payment_request_id
    saving_txn.provider_updated_at = _parse_datetime(data.get("updated")) or timezone.now()
    saving_txn.xendit_last_response = payload
    if webhook_payload is not None:
        saving_txn.xendit_webhook_payload = webhook_payload
    if webhook_id:
        saving_txn.xendit_webhook_id = webhook_id
    if became_paid:
        saving_txn.paid_at = saving_txn.provider_updated_at
    saving_txn.save()

    if became_paid:
        from .email_notification import send_saving_paid_email_safely

        transaction.on_commit(lambda: send_saving_paid_email_safely(saving_txn.pk))
    return saving_txn
