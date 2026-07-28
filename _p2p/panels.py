from django.urls import reverse
from wagtail.admin.panels import Panel

from _p2p.reporting import build_project_report


class PurchaseReportPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "_p2p/admin/panels/purchase_report.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            if self.instance and self.instance.pk:
                report = build_project_report(self.instance)
                context.update(report)
                context["export_url"] = reverse(
                    "p2p_project_purchase_export", args=[self.instance.pk]
                )
            return context


class PurchaseGraphPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "_p2p/admin/panels/purchase_graph.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            if self.instance and self.instance.pk:
                context.update(build_project_report(self.instance))
            return context
