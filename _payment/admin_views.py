import csv
from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from wagtail.admin.auth import user_passes_test

from .forms import XenditFeeAdjustmentPostForm
from .models import (
    XenditFeeAdjustment,
    XenditPaymentChannel,
    XenditReconciliationRun,
    XenditTransactionFee,
)
from .services import post_adjustment_fifo


def _admin_access(user):
    return user.has_perm("wagtailadmin.access_admin")


def _ensure_report_permission(request):
    if not request.user.has_perm("_payment.view_xendittransactionfee"):
        raise PermissionDenied


def _filtered_fees(request):
    today = timezone.localdate()
    date_from = parse_date(request.GET.get("date_from", "")) or today - timedelta(days=30)
    date_to = parse_date(request.GET.get("date_to", "")) or today
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    status = request.GET.get("status", "")
    route = request.GET.get("route", "")
    channel = request.GET.get("channel", "")
    qs = XenditTransactionFee.objects.select_related(
        "channel", "rate", "saving_transaction", "p2p_purchase"
    ).filter(created_at__date__range=(date_from, date_to))
    if status in dict(XenditTransactionFee.ReconciliationStatus.choices):
        qs = qs.filter(reconciliation_status=status)
    else:
        status = ""
    if route == "saving":
        qs = qs.filter(saving_transaction__isnull=False)
    elif route == "p2p":
        qs = qs.filter(p2p_purchase__isnull=False)
    else:
        route = ""
    if channel.isdigit() and XenditPaymentChannel.objects.filter(pk=channel).exists():
        qs = qs.filter(channel_id=channel)
    else:
        channel = ""
    money = DecimalField(max_digits=18, decimal_places=2)
    qs = qs.annotate(
        adjustment_total=Coalesce(
            Sum("adjustment_allocations__amount"), Value(0), output_field=money
        )
    ).order_by("-created_at")
    return qs, {
        "date_from": date_from,
        "date_to": date_to,
        "status": status,
        "route": route,
        "channel": channel,
    }


def _totals(qs):
    total_count = qs.count()
    charged = actual = residual = 0
    matched = variances = pending = 0
    for fee in qs.iterator(chunk_size=500):
        charged += fee.charged_fee_total
        if fee.actual_total_fee is not None:
            actual += fee.actual_total_fee
        if fee.residual_variance is not None:
            residual += fee.residual_variance
        if fee.reconciliation_status in {"matched", "adjusted"}:
            matched += 1
        elif fee.reconciliation_status in {"short", "over"}:
            variances += 1
        else:
            pending += 1
    return {
        "transaction_count": total_count,
        "charged_total": charged,
        "actual_total": actual,
        "residual_total": residual,
        "matched_count": matched,
        "variance_count": variances,
        "pending_count": pending,
    }


@user_passes_test(_admin_access)
def fee_reconciliation_report(request):
    _ensure_report_permission(request)
    if request.method == "POST":
        if not request.user.has_perm("_payment.add_xenditfeeadjustment"):
            raise PermissionDenied
        adjustment_form = XenditFeeAdjustmentPostForm(request.POST)
        if adjustment_form.is_valid():
            adjustment = adjustment_form.save(commit=False)
            adjustment.created_by = request.user
            adjustment.save()
            post_adjustment_fifo(adjustment, approved_by=request.user)
            messages.success(
                request,
                f"Adjustment {adjustment.amount:,.0f} diposting; "
                f"{adjustment.allocated_amount:,.0f} berhasil dialokasikan.",
            )
            return redirect("xendit_fee_reconciliation_report")
    else:
        adjustment_form = XenditFeeAdjustmentPostForm()

    fees, filters = _filtered_fees(request)
    query = request.GET.copy()
    query.pop("page", None)
    context = {
        "rows": Paginator(fees, 50).get_page(request.GET.get("page")),
        "filters": filters,
        "statuses": XenditTransactionFee.ReconciliationStatus.choices,
        "channels": XenditPaymentChannel.objects.order_by("sort_order", "display_name"),
        "adjustment_form": adjustment_form,
        "recent_adjustments": XenditFeeAdjustment.objects.select_related("created_by")[:10],
        "last_run": XenditReconciliationRun.objects.first(),
        "export_query": query.urlencode(),
        "channel_list_url": reverse("wagtailsnippets__payment_xenditpaymentchannel:list"),
        "rate_list_url": reverse("wagtailsnippets__payment_xenditfeerate:list"),
        **_totals(fees),
    }
    return render(request, "_payment/admin/fee_reconciliation_report.html", context)


@user_passes_test(_admin_access)
def export_fee_reconciliation_csv(request):
    _ensure_report_permission(request)
    fees, filters = _filtered_fees(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="xendit-fee-{filters["date_from"]}-{filters["date_to"]}.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Waktu", "Rute", "Referensi", "VA", "Pokok", "Fee Dibebankan",
            "Fee Actual Xendit", "Adjustment", "Selisih Tersisa", "Status",
            "Xendit Transaction ID", "Xendit Session ID", "Settlement",
        ]
    )
    for fee in fees.iterator(chunk_size=500):
        writer.writerow(
            [
                timezone.localtime(fee.created_at).isoformat(), fee.route_label,
                fee.transaction_reference, fee.channel.code, fee.principal_amount,
                fee.charged_fee_total, fee.actual_total_fee, fee.allocated_adjustment,
                fee.residual_variance, fee.reconciliation_status,
                fee.provider_transaction_id or "", fee.xendit_session_id,
                fee.settlement_status,
            ]
        )
    return response
