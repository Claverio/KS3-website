from django.shortcuts import get_object_or_404, render

from _product.models import Product, ProductSEOSettings


def _published_products():
    return Product.objects.select_related("category", "card_image").filter(
        is_published=True, category__is_active=True
    )


def product_list(request):
    seo = ProductSEOSettings.load()
    return render(request, "cms/pages/product.html", {
        "products": _published_products(),
        "page_title": "Produk",
        "page_description": "Temukan produk simpanan yang sesuai dengan rencana keuangan Anda.",
        "seo_title": seo.list_title,
        "seo_description": seo.list_description,
        "seo_keywords": seo.list_keywords,
        "seo_og_image": seo.og_image,
    })


def product_detail(request, slug):
    product = get_object_or_404(_published_products(), slug=slug)
    return render(request, "cms/pages/product.html", {
        "products": _published_products(),
        "selected_product": product,
        "streamfield": product.content,
        "page_title": product.title,
        "page_description": product.summary,
        "seo_title": product.seo_title or product.title,
        "seo_description": product.seo_description or product.summary,
        "seo_keywords": product.seo_keywords,
        "seo_og_image": product.seo_og_image or product.card_image,
    })
