from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone


def format_rupiah(value):
    return f"Rp{int(value or 0):,}".replace(",", ".")


def project_purchases(project):
    return project.purchases.order_by("-created_at")


def build_project_report(project):
    from _p2p.models.purchase import P2PPurchase

    purchases = project_purchases(project)
    paid = purchases.filter(status=P2PPurchase.Status.PAID)
    purchase_count = purchases.count()
    paid_count = paid.count()
    totals = paid.aggregate(
        amount=Sum("total_amount"),
        principal=Sum("subtotal"),
        slots=Sum("slot_quantity"),
    )
    paid_amount = totals["amount"] or 0
    paid_principal = totals["principal"] or 0
    paid_slots = totals["slots"] or 0
    funding_percentage = min(
        round((paid_principal / project.target_amount) * 100),
        100,
    ) if project.target_amount else 0
    payment_rate = round((paid_count / purchase_count) * 100) if purchase_count else 0
    average_paid = paid_amount / paid_count if paid_count else 0
    trend_rows = list(
        purchases.annotate(
            day=TruncDate(
                "created_at",
                tzinfo=timezone.get_current_timezone(),
            )
        )
        .values("day")
        .annotate(
            order_count=Count("pk"),
            amount=Sum("total_amount"),
            slots=Sum("slot_quantity"),
        )
        .order_by("day")
    )
    max_trend_amount = max(
        (row["amount"] or 0 for row in trend_rows),
        default=0,
    )
    trend = [
        {
            "label": row["day"].strftime("%d %b %Y"),
            "order_count": row["order_count"],
            "slots": row["slots"] or 0,
            "amount_display": format_rupiah(row["amount"]),
            "percentage": round(
                ((row["amount"] or 0) / max_trend_amount) * 100
            )
            if max_trend_amount
            else 0,
        }
        for row in trend_rows
    ]
    status_rows = list(
        purchases.values("status")
        .annotate(count=Count("pk"))
        .order_by("status")
    )
    max_status_count = max((row["count"] for row in status_rows), default=0)
    status_labels = dict(P2PPurchase.Status.choices)
    status_labels.update(
        {
            P2PPurchase.Status.CREATING: "Membuat pembayaran",
            P2PPurchase.Status.WAITING_PAYMENT: "Menunggu pembayaran",
            P2PPurchase.Status.PAID: "Lunas",
            P2PPurchase.Status.EXPIRED: "Kedaluwarsa",
            P2PPurchase.Status.CANCELED: "Dibatalkan",
            P2PPurchase.Status.FAILED: "Gagal",
        }
    )
    statuses = [
        {
            "label": status_labels.get(row["status"], row["status"]),
            "key": row["status"],
            "count": row["count"],
            "percentage": round((row["count"] / max_status_count) * 100)
            if max_status_count
            else 0,
        }
        for row in status_rows
    ]
    top_buyer_rows = list(
        paid.values("email", "full_name")
        .annotate(
            amount=Sum("total_amount"),
            slots=Sum("slot_quantity"),
            order_count=Count("pk"),
        )
        .order_by("-amount", "full_name")[:8]
    )
    max_buyer_amount = max(
        (row["amount"] or 0 for row in top_buyer_rows),
        default=0,
    )
    top_buyers = [
        {
            **row,
            "amount_display": format_rupiah(row["amount"]),
            "percentage": round(((row["amount"] or 0) / max_buyer_amount) * 100)
            if max_buyer_amount
            else 0,
        }
        for row in top_buyer_rows
    ]
    return {
        "purchase_rows": purchases[:250],
        "purchase_count": purchase_count,
        "paid_count": paid_count,
        "buyer_count": paid.values("email").distinct().count(),
        "paid_slots": paid_slots,
        "available_slots": project.available_slots,
        "paid_amount_display": format_rupiah(paid_amount),
        "paid_principal_display": format_rupiah(paid_principal),
        "remaining_funding_display": format_rupiah(
            max(project.target_amount - paid_principal, 0)
        ),
        "target_amount_display": format_rupiah(project.target_amount),
        "funding_percentage": funding_percentage,
        "payment_rate": payment_rate,
        "average_paid_display": format_rupiah(average_paid),
        "trend": trend,
        "statuses": statuses,
        "top_buyers": top_buyers,
    }
