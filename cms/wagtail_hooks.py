from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks


@hooks.register("insert_global_admin_css")
def ks3_admin_css():
    return format_html(
        '<link rel="stylesheet" href="{}">',
        static("cms/css/ks3-wagtail-admin.css"),
    )
