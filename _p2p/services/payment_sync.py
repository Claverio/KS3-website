from backend.services.xendit import XenditService

from .payment_transition import apply_xendit_payment_update


def synchronize_xendit_purchase(purchase):
    if not purchase.xendit_session_id:
        raise ValueError("Purchase has no Xendit session ID.")
    payload = XenditService.get_session_status(purchase.xendit_session_id)
    return apply_xendit_payment_update(purchase, payload)
