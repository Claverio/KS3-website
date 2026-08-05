import secrets
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from backend.services.xendit import XenditService
from _payment.services import create_fee_snapshot, resolve_fee
from _p2p.models import P2P, P2PPurchase

from .availability import available_slot_count
from .pricing import calculate_purchase_price


class PurchaseWorkflowError(Exception):
    pass


def _identifiers():
    token = secrets.token_hex(4).upper()
    stamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
    return f"KS3-P2P-{stamp}-{token}", f"KS3-{timezone.localtime():%Y}-{token}"


def create_p2p_purchase(
    *, project, full_name, phone, email, nik, note, slot_quantity, xendit_channel=None
):
    with transaction.atomic():
        project = P2P.objects.select_for_update().get(pk=project.pk)
        if not project.can_purchase:
            raise PurchaseWorkflowError("This project is not available for purchase.")
        if slot_quantity > available_slot_count(project):
            raise PurchaseWorkflowError("Not enough slots are available.")
        principal_amount = project.slot_price * slot_quantity
        resolved = resolve_fee(
            channel_code=xendit_channel,
            route="p2p",
            principal_amount=principal_amount,
        )
        price = calculate_purchase_price(
            project,
            slot_quantity,
            service_fee=resolved.total_fee,
        )
        reference_id, booking_number = _identifiers()
        purchase = P2PPurchase(
            reference_id=reference_id,
            booking_number=booking_number,
            project=project,
            full_name=full_name,
            phone=phone,
            email=email,
            nik=nik,
            note=note,
            slot_quantity=slot_quantity,
            unit_price=price.unit_price,
            subtotal=price.subtotal,
            service_fee=price.service_fee,
            total_amount=price.total,
            status=P2PPurchase.Status.CREATING,
        )
        purchase.full_clean()
        purchase.save()
        fee_snapshot, _ = create_fee_snapshot(
            transaction=purchase,
            route="p2p",
            channel_code=resolved.channel.code,
            principal_amount=price.subtotal,
            resolved=resolved,
        )

    try:
        items = [
            {
                "reference_id": f"{purchase.reference_id}-principal",
                "type": "DIGITAL_SERVICE",
                "name": f"Pendanaan {project.title}"[:255],
                "net_unit_amount": int(purchase.subtotal),
                "quantity": 1,
            }
        ]
        if purchase.service_fee:
            items.append(
                {
                    "reference_id": f"{purchase.reference_id}-fee",
                    "type": "FEE",
                    "name": "Biaya administrasi pembayaran",
                    "net_unit_amount": int(purchase.service_fee),
                    "quantity": 1,
                }
            )
        session_kwargs = {
            "reference_id": purchase.reference_id,
            "amount": purchase.total_amount,
            "description": f"Pendanaan {project.title} ({purchase.booking_number})",
            "currency": purchase.currency,
            "allowed_payment_channels": fee_snapshot.allowed_payment_channels,
            "items": items,
            "metadata": {
                "route": "p2p",
                "transaction_reference": purchase.reference_id,
                "booking_number": purchase.booking_number,
                "fee_snapshot_id": str(fee_snapshot.pk),
                "fee_rate_version": str(fee_snapshot.rate_id),
                "selected_va_channel": fee_snapshot.channel.code,
                "principal_amount": str(purchase.subtotal),
                "charged_fee_total": str(purchase.service_fee),
                "charged_total_amount": str(purchase.total_amount),
            },
        }
        fee_snapshot.session_request_snapshot = {
            **session_kwargs,
            "amount": str(purchase.total_amount),
            "items": [
                {**item, "net_unit_amount": str(item["net_unit_amount"])} for item in items
            ],
        }
        fee_snapshot.save(update_fields=("session_request_snapshot", "updated_at"))
        response = XenditService.create_invoice(
            **session_kwargs,
        )
        required = ("payment_session_id", "reference_id", "status", "payment_link_url", "expires_at")
        missing = [field for field in required if not response.get(field)]
        if missing:
            raise PurchaseWorkflowError(f"Xendit response is missing: {', '.join(missing)}.")
        if response["reference_id"] != purchase.reference_id:
            raise PurchaseWorkflowError("Xendit returned a different reference ID.")
        purchase.xendit_session_id = response["payment_session_id"]
        purchase.xendit_session_status = response["status"]
        purchase.payment_link_url = response["payment_link_url"]
        purchase.session_expires_at = datetime.fromisoformat(
            response["expires_at"].replace("Z", "+00:00")
        )
        purchase.xendit_create_response = response
        purchase.xendit_last_response = response
        purchase.status = P2PPurchase.Status.WAITING_PAYMENT
        purchase.save()
        fee_snapshot.xendit_session_id = response["payment_session_id"]
        fee_snapshot.session_response_snapshot = response
        fee_snapshot.save(
            update_fields=(
                "xendit_session_id",
                "session_response_snapshot",
                "updated_at",
            )
        )
        return purchase
    except Exception:
        purchase.status = P2PPurchase.Status.FAILED
        purchase.save(update_fields=("status", "updated_at"))
        raise
