import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from _payment.models import (
    XenditReconciliationRun,
    XenditTransactionFee,
)
from backend.services.xendit import XenditService


logger = logging.getLogger(__name__)


def _normalized_va_code(code):
    value = str(code or "").upper()
    if value and not value.endswith("_VIRTUAL_ACCOUNT"):
        value = f"{value}_VIRTUAL_ACCOUNT"
    return value


def _decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _set_reconciliation_status(fee_record):
    if fee_record.actual_xendit_fee is None:
        fee_record.reconciliation_status = XenditTransactionFee.ReconciliationStatus.PENDING
        return
    if fee_record.actual_fee_status in {"PENDING", ""}:
        fee_record.reconciliation_status = XenditTransactionFee.ReconciliationStatus.PENDING
        return
    if fee_record.actual_fee_status in {"CANCELED", "REVERSED"}:
        fee_record.reconciliation_status = XenditTransactionFee.ReconciliationStatus.REVIEW
        return
    expected_total = (
        fee_record.saving_transaction.total_amount
        if fee_record.saving_transaction_id
        else fee_record.p2p_purchase.total_amount
    )
    if (
        (fee_record.actual_currency and fee_record.actual_currency != fee_record.currency)
        or (
            fee_record.actual_gross_amount is not None
            and fee_record.actual_gross_amount != expected_total
        )
    ):
        fee_record.reconciliation_status = XenditTransactionFee.ReconciliationStatus.REVIEW
        return
    if (
        fee_record.channel.code != "LEGACY_UNKNOWN_VIRTUAL_ACCOUNT"
        and fee_record.actual_channel_code
        and _normalized_va_code(fee_record.actual_channel_code) != fee_record.channel.code
    ):
        fee_record.reconciliation_status = XenditTransactionFee.ReconciliationStatus.REVIEW
        return
    residual = fee_record.residual_variance
    if residual == 0:
        fee_record.reconciliation_status = (
            XenditTransactionFee.ReconciliationStatus.ADJUSTED
            if fee_record.allocated_adjustment
            else XenditTransactionFee.ReconciliationStatus.MATCHED
        )
    elif residual < 0:
        fee_record.reconciliation_status = XenditTransactionFee.ReconciliationStatus.SHORT
    else:
        fee_record.reconciliation_status = XenditTransactionFee.ReconciliationStatus.OVER


def refresh_reconciliation_status(fee_record):
    _set_reconciliation_status(fee_record)
    fee_record.save(update_fields=("reconciliation_status", "updated_at"))
    return fee_record


@transaction.atomic
def _apply_actual_payload(fee_record, payload):
    fee_record = XenditTransactionFee.objects.select_for_update().get(pk=fee_record.pk)
    fee = payload.get("fee") or {}
    product_data = payload.get("product_data") or {}
    fee_record.provider_transaction_id = payload.get("id") or None
    fee_record.provider_product_id = payload.get("product_id") or ""
    fee_record.provider_payment_request_id = product_data.get("payment_request_id") or ""
    fee_record.provider_reference_id = payload.get("reference_id") or ""
    fee_record.provider_transaction_type = str(payload.get("type") or "").upper()
    fee_record.provider_transaction_status = str(payload.get("status") or "").upper()
    fee_record.provider_business_id = payload.get("business_id") or ""
    fee_record.actual_channel_category = payload.get("channel_category") or ""
    fee_record.actual_channel_code = payload.get("channel_code") or ""
    fee_record.actual_currency = payload.get("currency") or ""
    fee_record.account_identifier = payload.get("account_identifier") or ""
    fee_record.cashflow = str(payload.get("cashflow") or "").upper()
    fee_record.actual_net_amount_currency = payload.get("net_amount_currency") or ""
    fee_record.actual_gross_amount = _decimal(payload.get("amount"))
    fee_record.actual_net_amount = _decimal(payload.get("net_amount"))
    fee_record.actual_xendit_fee = _decimal(fee.get("xendit_fee"))
    fee_record.actual_vat = _decimal(fee.get("value_added_tax")) or Decimal("0")
    fee_record.actual_xendit_withholding_tax = (
        _decimal(fee.get("xendit_withholding_tax")) or Decimal("0")
    )
    fee_record.actual_third_party_withholding_tax = (
        _decimal(fee.get("third_party_withholding_tax")) or Decimal("0")
    )
    fee_record.actual_fee_status = str(fee.get("status") or "").upper()
    fee_record.settlement_status = str(payload.get("settlement_status") or "").upper()
    fee_record.provider_created_at = _datetime(payload.get("created"))
    fee_record.provider_updated_at = _datetime(payload.get("updated"))
    fee_record.estimated_settlement_at = _datetime(payload.get("estimated_settlement_time"))
    fee_record.actual_product_data = product_data
    fee_record.actual_payload = payload
    fee_record.reconciliation_attempts += 1
    fee_record.reconciliation_last_error = ""
    fee_record.reconciled_at = timezone.now()
    _set_reconciliation_status(fee_record)
    fee_record.save()
    return fee_record


def reconcile_transaction_fee(fee_record):
    reference_id = (
        fee_record.saving_transaction.reference_id
        if fee_record.saving_transaction_id
        else fee_record.p2p_purchase.reference_id
    )
    response = XenditService.list_transactions(
        reference_id=reference_id,
        transaction_type="PAYMENT",
        limit=10,
    )
    rows = response.get("data") or []
    candidates = [
        row
        for row in rows
        if row.get("reference_id") == reference_id
        and row.get("type") == "PAYMENT"
        and row.get("status") == "SUCCESS"
    ]
    if not candidates:
        XenditTransactionFee.objects.filter(pk=fee_record.pk).update(
            reconciliation_status=XenditTransactionFee.ReconciliationStatus.MISSING,
            reconciliation_attempts=fee_record.reconciliation_attempts + 1,
            reconciliation_last_error="Xendit transaction belum ditemukan.",
            updated_at=timezone.now(),
        )
        fee_record.refresh_from_db()
        return fee_record
    payload = sorted(candidates, key=lambda row: row.get("updated") or "", reverse=True)[0]
    fee_record = _apply_actual_payload(fee_record, payload)
    return fee_record


def reconcile_pending_fees(limit=50):
    run = XenditReconciliationRun.objects.create()
    qs = (
        XenditTransactionFee.objects.select_related(
            "saving_transaction", "p2p_purchase", "channel", "rate"
        )
        .filter(
            reconciliation_status__in=(
                XenditTransactionFee.ReconciliationStatus.PENDING,
                XenditTransactionFee.ReconciliationStatus.MISSING,
            )
        )
        .filter(
            Q(saving_transaction__status="paid") | Q(p2p_purchase__status="paid")
        )
        .order_by("created_at")[:limit]
    )
    processed = matched = variance = errors = 0
    for fee_record in qs:
        try:
            fee_record = reconcile_transaction_fee(fee_record)
            processed += 1
            if fee_record.reconciliation_status in {
                XenditTransactionFee.ReconciliationStatus.MATCHED,
                XenditTransactionFee.ReconciliationStatus.ADJUSTED,
            }:
                matched += 1
            elif fee_record.reconciliation_status in {
                XenditTransactionFee.ReconciliationStatus.SHORT,
                XenditTransactionFee.ReconciliationStatus.OVER,
            }:
                variance += 1
        except Exception as exc:
            errors += 1
            logger.exception("Xendit fee reconciliation failed for fee pk=%s", fee_record.pk)
            XenditTransactionFee.objects.filter(pk=fee_record.pk).update(
                reconciliation_attempts=fee_record.reconciliation_attempts + 1,
                reconciliation_last_error=str(exc)[:2000],
                updated_at=timezone.now(),
            )
    run.processed_count = processed
    run.matched_count = matched
    run.variance_count = variance
    run.error_count = errors
    run.finished_at = timezone.now()
    run.status = (
        XenditReconciliationRun.Status.COMPLETED_WITH_ERRORS
        if errors
        else XenditReconciliationRun.Status.COMPLETED
    )
    run.summary = {
        "processed": processed,
        "matched": matched,
        "variance": variance,
        "errors": errors,
    }
    run.save()
    return run
