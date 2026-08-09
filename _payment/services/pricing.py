from dataclasses import dataclass
from decimal import Decimal

from _payment.models import XenditFeeRate, XenditPaymentChannel, XenditTransactionFee
from _setting.models import XenditSetting


class FeeConfigurationError(Exception):
    pass


@dataclass(frozen=True)
class ResolvedXenditFee:
    channel: XenditPaymentChannel
    rate: XenditFeeRate | None
    principal_amount: Decimal
    fee_before_tax: Decimal
    vat: Decimal
    total_fee: Decimal
    charge_setting_field: str


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
    channel = _resolve_channel(channel_code, route)
    setting = XenditSetting.load()
    setting_field = {
        "saving": "saving_payment_gateway_fee",
        "p2p": "p2p_payment_gateway_fee",
    }[route]
    total_fee = Decimal(getattr(setting, setting_field))
    if total_fee < 0:
        raise FeeConfigurationError("Biaya payment gateway tidak boleh negatif.")
    return ResolvedXenditFee(
        channel=channel,
        rate=None,
        principal_amount=principal,
        fee_before_tax=total_fee,
        vat=Decimal("0"),
        total_fee=total_fee,
        charge_setting_field=setting_field,
    )


def _rate_snapshot(resolved):
    rate = resolved.rate
    if rate is None:
        return {}
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
        charge_configuration_snapshot={
            "source": "xendit_setting",
            "route": route,
            "setting_field": resolved.charge_setting_field,
            "configured_amount": str(resolved.total_fee),
            "currency": transaction.currency,
            "selected_channel": resolved.channel.code,
            "channel_independent": True,
        },
        allowed_payment_channels=[resolved.channel.code],
    )
    return snapshot, resolved
