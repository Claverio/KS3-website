from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def rupiah(value):
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError):
        return "Rp0"
    return f"Rp{number:,.0f}".replace(",", ".")


@register.filter
def percent(value):
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError):
        return "0%"
    rendered = f"{number:.2f}".rstrip("0").rstrip(".")
    return f"{rendered}%"


@register.filter
def payment_status_label(value):
    return {
        "creating": "Membuat pembayaran",
        "waiting_payment": "Menunggu pembayaran",
        "paid": "Lunas",
        "expired": "Kedaluwarsa",
        "canceled": "Dibatalkan",
        "failed": "Gagal",
    }.get(value, value)
