from wagtail import hooks
from django.urls import path

from _p2p.admin.views import export_project_purchases


@hooks.register("register_icons")
def register_font_awesome_icons(icons):
    return icons + [
        "wagtailfontawesomesvg/solid/chart-line.svg",
        "wagtailfontawesomesvg/solid/credit-card.svg",
        "wagtailfontawesomesvg/solid/envelope.svg",
        "wagtailfontawesomesvg/solid/gear.svg",
        "wagtailfontawesomesvg/solid/hand-holding-dollar.svg",
    ]


@hooks.register("register_admin_urls")
def register_p2p_report_urls():
    return [
        path(
            "p2p/projects/<int:project_id>/purchases.csv",
            export_project_purchases,
            name="p2p_project_purchase_export",
        )
    ]
