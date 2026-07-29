from django.templatetags.static import static
from django.urls import path, reverse
from django.utils.html import format_html
from wagtail import hooks
from wagtail.admin.search import SearchArea

from cms.admin_dashboard import KS3DashboardPanel
from cms.admin_views import global_admin_search


@hooks.register("insert_global_admin_css")
def ks3_admin_css():
    return format_html(
        '<link rel="stylesheet" href="{}">',
        static("cms/css/ks3-wagtail-admin.css"),
    )


@hooks.register("register_admin_urls")
def register_ks3_admin_urls():
    return [
        path("global-search/", global_admin_search, name="ks3_admin_search"),
    ]


@hooks.register("register_admin_search_area")
def register_ks3_global_search():
    return SearchArea(
        "Semua data KS3",
        reverse("ks3_admin_search"),
        name="ks3-global",
        icon_name="search",
        order=1,
    )


@hooks.register("construct_search")
def make_admin_search_global(request, search_areas):
    search_areas[:] = [area for area in search_areas if area.name == "ks3-global"]


@hooks.register("construct_homepage_panels")
def build_ks3_dashboard(request, panels):
    panels[:] = [KS3DashboardPanel()]


@hooks.register("construct_main_menu")
def simplify_main_menu(request, menu_items):
    hidden = {"images", "documents"}
    menu_items[:] = [item for item in menu_items if item.name not in hidden]


@hooks.register("construct_settings_menu")
def simplify_settings_menu(request, menu_items):
    hidden = {
        "homepage-setting",
        "redirects",
        "collections",
        "workflows",
        "workflow-tasks",
    }
    menu_items[:] = [item for item in menu_items if item.name not in hidden]
