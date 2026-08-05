from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from _payment.models import XenditFeeRate, XenditPaymentChannel, XenditTransactionFee


class FeeConfigurationError(Exception):
    pass


@dataclass(frozen=True)
class ResolvedXenditFee:
    channel: XenditPaymentChannel
    rate: XenditFeeRate
    principal_amount: Decimal
    fee_before_tax: Decimal
    vat: Decimal
    total_fee: Decimal


def active_channels(route):
    field = {
        "saving": "enabled_for_saving",
        "p2p": "enabled_for_p2p",
    }.get(route)
    if field is None:
        raise ValueError("Unsupported payment route.")
    return XenditPaymentChannel.objects.filter(
        is_enabled=True,
        category=XenditPaymentChannel.Category.VIRTUAL_ACCOUNT,
        **{field: True},
    ).order_by("sort_order", "display_name")


def _resolve_channel(channel_code, route):
    channels = active_channels(route)
    if channel_code:
        channel = channels.filter(code=channel_code).first()
        if not channel:
            raise FeeConfigurationError("Kanal Virtual Account tidak aktif untuk transaksi ini.")
        return channel
    channel = channels.first()
    if not channel:
        raise FeeConfigurationError("Belum ada kanal Virtual Account yang aktif.")
    return channel


def resolve_fee(*, channel_code, route, principal_amount, at=None, currency="IDR"):
    principal = Decimal(principal_amount)
    if principal <= 0:
        raise FeeConfigurationError("Nominal pokok harus lebih besar dari nol.")
    moment = at or timezone.now()
    channel = _resolve_channel(channel_code, route)
    rate = (
        XenditFeeRate.objects.filter(
            channel=channel,
            currency=currency,
            status=XenditFeeRate.Status.ACTIVE,
            effective_from__lte=moment,
        )
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gt=moment))
        .order_by("-effective_from")
        .first()
    )
    if not rate:
        raise FeeConfigurationError(
            f"Tarif aktif untuk {channel.display_name} belum dikonfigurasi."
        )
    fee_before_tax, vat, total_fee = rate.calculate(principal)
    return ResolvedXenditFee(
        channel=channel,
        rate=rate,
        principal_amount=principal,
        fee_before_tax=fee_before_tax,
        vat=vat,
        total_fee=total_fee,
    )


def _rate_snapshot(resolved):
    rate = resolved.rate
    return {
        "rate_id": rate.pk,
        "channel_code": resolved.channel.code,
        "channel_name": resolved.channel.display_name,
        "currency": rate.currency,
        "fixed_fee": str(rate.fixed_fee),
        "percentage_fee": str(rate.percentage_fee),
        "vat_percent": str(rate.vat_percent),
        "effective_from": rate.effective_from.isoformat(),
        "effective_to": rate.effective_to.isoformat() if rate.effective_to else None,
        "source": rate.source,
        "source_reference": rate.source_reference,
    }


def create_fee_snapshot(
    *, transaction, route, channel_code, principal_amount, resolved=None
):
    if route not in {"saving", "p2p"}:
        raise ValueError("Unsupported payment route.")
    resolved = resolved or resolve_fee(
        channel_code=channel_code,
        route=route,
        principal_amount=principal_amount,
        currency=transaction.currency,
    )
    link = (
        {"saving_transaction": transaction}
        if route == "saving"
        else {"p2p_purchase": transaction}
    )
    snapshot = XenditTransactionFee.objects.create(
        **link,
        channel=resolved.channel,
        rate=resolved.rate,
        currency=transaction.currency,
        principal_amount=resolved.principal_amount,
        charged_fee_before_tax=resolved.fee_before_tax,
        charged_fee_vat=resolved.vat,
        charged_fee_total=resolved.total_fee,
        rate_snapshot=_rate_snapshot(resolved),
        allowed_payment_channels=[resolved.channel.code],
    )
    return snapshot, resolved
