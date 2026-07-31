from decimal import Decimal

from django.db.models import Count, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from wagtail.admin.ui.components import Component

from _p2p.models import P2P, P2PPurchase


class KS3DashboardPanel(Component):
    """Operational overview shown as the entire Wagtail admin homepage."""

    template_name = "wagtailadmin/home/ks3_dashboard.html"
    order = 10

    def get_context_data(self, parent_context):
        paid = P2PPurchase.objects.filter(status=P2PPurchase.Status.PAID)
        waiting = P2PPurchase.objects.filter(
            status__in=(
                P2PPurchase.Status.CREATING,
                P2PPurchase.Status.WAITING_PAYMENT,
            )
        )
        paid_totals = paid.aggregate(
            count=Count("pk"),
            slots=Coalesce(Sum("slot_quantity"), 0),
            amount=Coalesce(Sum("total_amount"), Value(Decimal("0"))),
        )

        projects = list(
            P2P.objects.filter(is_published=True, status=P2P.Status.OPEN)
            .select_related("category")
            .order_by("funding_deadline", "sort_order", "title")
        )
        project_rows = []
        for project in projects:
            project_rows.append(
                {
                    "project": project,
                    "edit_url": reverse(
                        "wagtailsnippets__p2p_p2p:edit", args=[project.pk]
                    ),
                }
            )

        context = super().get_context_data(parent_context)
        context.update(
            {
                "project_rows": project_rows,
                "latest_paid": paid.select_related("project").order_by("-paid_at")[:20],
                "paid_count": paid_totals["count"],
                "paid_slots": paid_totals["slots"],
                "paid_amount": paid_totals["amount"],
                "waiting_count": waiting.count(),
                "failed_count": P2PPurchase.objects.filter(
                    status__in=(P2PPurchase.Status.FAILED, P2PPurchase.Status.EXPIRED)
                ).count(),
                "project_list_url": reverse("wagtailsnippets__p2p_p2p:list"),
                "purchase_list_url": reverse(
                    "wagtailsnippets__p2p_p2ppurchase:list"
                ),
                "product_list_url": reverse("wagtailsnippets__product_product:list"),
                "saving_report_url": reverse("saving_report"),
            }
        )
        return context
