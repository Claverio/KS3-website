import csv

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from _p2p.models import P2P
from _p2p.reporting import project_purchases


def _csv_safe(value):
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@")) else text


@login_required
def export_project_purchases(request, project_id):
    if not (
        request.user.has_perm("_p2p.change_p2p")
        or request.user.has_perm("_p2p.view_p2ppurchase")
    ):
        raise PermissionDenied
    project = get_object_or_404(P2P, pk=project_id)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    timestamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    response["Content-Disposition"] = (
        f'attachment; filename="p2p-{project.slug}-purchases-{timestamp}.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Booking",
            "Nama",
            "WhatsApp",
            "Email",
            "Jumlah Slot",
            "Harga per Slot",
            "Subtotal",
            "Biaya Layanan",
            "Total",
            "Status",
            "Waktu Transaksi",
            "Waktu Dibayar",
        ]
    )
    for purchase in project_purchases(project):
        writer.writerow(
            [
                _csv_safe(purchase.booking_number),
                _csv_safe(purchase.full_name),
                _csv_safe(purchase.phone),
                _csv_safe(purchase.email),
                purchase.slot_quantity,
                purchase.unit_price,
                purchase.subtotal,
                purchase.service_fee,
                purchase.total_amount,
                purchase.get_status_display(),
                timezone.localtime(purchase.created_at).strftime("%Y-%m-%d %H:%M:%S %Z"),
                timezone.localtime(purchase.paid_at).strftime("%Y-%m-%d %H:%M:%S %Z")
                if purchase.paid_at
                else "",
            ]
        )
    return response
