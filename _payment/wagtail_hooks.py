from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .admin_views import export_fee_reconciliation_csv, fee_reconciliation_report
from .models import XenditFeeRate, XenditPaymentChannel


class XenditPaymentChannelViewSet(SnippetViewSet):
    model = XenditPaymentChannel
    menu_label = "Kanal VA"
    icon = "credit-card"
    list_display = (
        "display_name", "code", "is_enabled", "enabled_for_saving", "enabled_for_p2p",
    )
    list_filter = ("is_enabled", "enabled_for_saving", "enabled_for_p2p")
    search_fields = ("display_name", "code")
    ordering = ("sort_order", "display_name")
    inspect_view_enabled = True


class XenditFeeRateViewSet(SnippetViewSet):
    model = XenditFeeRate
    menu_label = "Versi Tarif VA"
    icon = "date"
    list_display = (
        "channel", "fixed_fee", "percentage_fee", "vat_percent", "effective_from",
        "effective_to", "source", "status",
    )
    list_filter = ("channel", "source", "status", "currency")
    search_fields = ("channel__display_name", "channel__code", "source_reference", "notes")
    ordering = ("channel", "-effective_from")
    inspect_view_enabled = True


class XenditFeeConfigurationGroup(SnippetViewSetGroup):
    menu_label = "Xendit Fee"
    menu_icon = "credit-card"
    menu_name = "xendit-fee-configuration"
    menu_order = 790
    items = (XenditPaymentChannelViewSet, XenditFeeRateViewSet)


register_snippet(XenditFeeConfigurationGroup)


@hooks.register("register_admin_urls")
def register_xendit_fee_report_urls():
    return [
        path(
            "xendit-fees/reconciliation/",
            fee_reconciliation_report,
            name="xendit_fee_reconciliation_report",
        ),
        path(
            "xendit-fees/reconciliation/export.csv",
            export_fee_reconciliation_csv,
            name="xendit_fee_reconciliation_export",
        ),
    ]


@hooks.register("register_admin_menu_item")
def register_xendit_fee_report_menu_item():
    return MenuItem(
        "Rekonsiliasi Xendit",
        reverse("xendit_fee_reconciliation_report"),
        icon_name="table",
        order=225,
    )
