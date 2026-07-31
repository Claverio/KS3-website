from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from _product.admin.views import export_saving_report, saving_report


@hooks.register("register_admin_urls")
def register_saving_report_urls():
    return [
        path("savings/report/", saving_report, name="saving_report"),
        path("savings/report/export/<str:file_format>/", export_saving_report, name="saving_report_export"),
    ]


@hooks.register("register_admin_menu_item")
def register_saving_report_menu_item():
    return MenuItem("Laporan Tabungan", reverse("saving_report"), icon_name="table", order=220)
