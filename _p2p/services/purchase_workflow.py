import secrets
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from backend.services.xendit import XenditService
from _p2p.models import P2P, P2PPurchase

from .availability import available_slot_count
from .pricing import calculate_purchase_price


class PurchaseWorkflowError(Exception):
    pass


def _identifiers():
    token = secrets.token_hex(4).upper()
    stamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
    return f"KS3-P2P-{stamp}-{token}", f"KS3-{timezone.localtime():%Y}-{token}"


def create_p2p_purchase(*, project, full_name, phone, email, nik, note, slot_quantity):
    with transaction.atomic():
        project = P2P.objects.select_for_update().get(pk=project.pk)
        if not project.can_purchase:
            raise PurchaseWorkflowError("This project is not available for purchase.")
        if slot_quantity > available_slot_count(project):
            raise PurchaseWorkflowError("Not enough slots are available.")
        price = calculate_purchase_price(project, slot_quantity)
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

    try:
        response = XenditService.create_invoice(
            reference_id=purchase.reference_id,
            amount=purchase.total_amount,
            description=f"Pendanaan {project.title} ({purchase.booking_number})",
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
        return purchase
    except Exception:
        purchase.status = P2PPurchase.Status.FAILED
        purchase.save(update_fields=("status", "updated_at"))
        raise
