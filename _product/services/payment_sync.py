from backend.services.xendit import XenditService

from .payment_transition import apply_saving_payment_update


def synchronize_saving_transaction(saving_txn):
    if not saving_txn.xendit_session_id:
        raise ValueError("Saving transaction has no Xendit session ID.")
    payload = XenditService.get_session_status(saving_txn.xendit_session_id)
    return apply_saving_payment_update(saving_txn, payload)
