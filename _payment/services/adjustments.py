from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from _payment.models import (
    XenditFeeAdjustment,
    XenditFeeAdjustmentAllocation,
    XenditTransactionFee,
)
from .reconciliation import refresh_reconciliation_status


@transaction.atomic
def post_adjustment_fifo(adjustment, *, approved_by=None):
    adjustment = XenditFeeAdjustment.objects.select_for_update().get(pk=adjustment.pk)
    if adjustment.status not in {
        XenditFeeAdjustment.Status.DRAFT,
        XenditFeeAdjustment.Status.APPROVED,
    }:
        raise ValidationError("Adjustment sudah diposting atau dibatalkan.")
    if adjustment.amount == 0:
        raise ValidationError("Nominal adjustment tidak boleh nol.")

    remaining = adjustment.amount
    candidates = list(
        XenditTransactionFee.objects.select_for_update()
        .filter(
            currency=adjustment.currency,
            reconciliation_status__in=(
                XenditTransactionFee.ReconciliationStatus.SHORT,
                XenditTransactionFee.ReconciliationStatus.OVER,
            ),
        )
        .order_by("reconciled_at", "created_at")
    )
    touched = []
    for fee_record in candidates:
        residual = fee_record.residual_variance
        if residual is None or residual == 0:
            continue
        if remaining > 0 and residual >= 0:
            continue
        if remaining < 0 and residual <= 0:
            continue
        amount = (
            min(remaining, -residual)
            if remaining > 0
            else -min(abs(remaining), residual)
        )
        XenditFeeAdjustmentAllocation.objects.create(
            adjustment=adjustment,
            transaction_fee=fee_record,
            amount=amount,
        )
        remaining -= amount
        touched.append(fee_record)
        if remaining == 0:
            break

    now = timezone.now()
    adjustment.status = XenditFeeAdjustment.Status.POSTED
    adjustment.approved_by = approved_by
    adjustment.approved_at = now
    adjustment.posted_at = now
    adjustment.save(
        update_fields=(
            "status",
            "approved_by",
            "approved_at",
            "posted_at",
            "updated_at",
        )
    )
    for fee_record in touched:
        fee_record.refresh_from_db()
        refresh_reconciliation_status(fee_record)
    return adjustment
