from .models import ContactSetting


def global_navigation(request):
    from _misc.models import MiscellaneousIndexPage, MiscellaneousPage
    from _product.models import Product
    from wagtail.models import Site

    site = Site.find_for_request(request)
    pages = MiscellaneousPage.objects.none()
    index_page = None
    if site:
        pages = MiscellaneousPage.objects.live().public().descendant_of(site.root_page)
        index_page = (
            MiscellaneousIndexPage.objects.live()
            .public()
            .descendant_of(site.root_page)
            .first()
        )
    return {
        "navigation_products": Product.objects.filter(
            is_published=True, category__is_active=True
        ).select_related("category")[:5],
        "misc_index_page": index_page,
        "header_misc_pages": pages.filter(show_on_header=True).order_by("menu_order", "title"),
        "main_menu_misc_pages": pages.filter(show_on_main_menu=True).order_by("menu_order", "title"),
        "footer_misc_pages": pages.filter(show_on_footer=True).order_by("menu_order", "title"),
    }


def global_contact_settings(request):
    return {"contact_setting": ContactSetting.load()}
