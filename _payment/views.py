from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .services import FeeConfigurationError, resolve_fee


@require_GET
def fee_quote(request):
    route = request.GET.get("route", "")
    channel_code = request.GET.get("channel", "")
    try:
        principal_amount = Decimal(request.GET.get("amount", ""))
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse({"error": "Nominal transaksi tidak valid."}, status=400)
    if route not in {"saving", "p2p"}:
        return JsonResponse({"error": "Rute pembayaran tidak valid."}, status=400)
    if (
        principal_amount <= 0
        or principal_amount != principal_amount.to_integral_value()
        or principal_amount > Decimal("9999999999999999")
    ):
        return JsonResponse({"error": "Nominal transaksi tidak valid."}, status=400)
    try:
        resolved = resolve_fee(
            channel_code=channel_code,
            route=route,
            principal_amount=principal_amount,
        )
    except FeeConfigurationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(
        {
            "route": route,
            "channel": resolved.channel.code,
            "channel_name": resolved.channel.display_name,
            "principal_amount": str(resolved.principal_amount),
            "fee_before_tax": str(resolved.fee_before_tax),
            "fee_vat": str(resolved.vat),
            "fee_total": str(resolved.total_fee),
            "total_amount": str(resolved.principal_amount + resolved.total_fee),
            "rate_version": resolved.rate.pk,
        }
    )
