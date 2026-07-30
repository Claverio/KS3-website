from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from _product.models import Product, ProductSEOSettings
from _product.simulation import SimulationValidationError, public_config, simulate


def _published_products():
    return (
        Product.objects.select_related("category", "card_image", "simulation")
        .prefetch_related("simulation__rate_tiers", "simulation__fee_rules", "simulation__breakdown_bands")
        .filter(is_published=True, category__is_active=True)
        .order_by("category__sort_order", "category__name", "sort_order", "title")
    )


def _simulation_context(product):
    try:
        profile = product.simulation
    except Product.simulation.RelatedObjectDoesNotExist:
        return {}
    if not profile.is_enabled or not profile.is_ready:
        return {}
    return {"simulation_profile": profile, "simulation_config": public_config(profile)}


def product_list(request):
    seo = ProductSEOSettings.load()
    return render(request, "cms/pages/product.html", {
        "products": _published_products(),
        "page_title": "Produk",
        "page_description": "Temukan produk simpanan dan pinjaman yang sesuai dengan kebutuhan keuangan Anda.",
        "seo_title": seo.list_title,
        "seo_description": seo.list_description,
        "seo_keywords": seo.list_keywords,
        "seo_og_image": seo.og_image,
    })


def product_detail(request, slug):
    product = get_object_or_404(_published_products(), slug=slug)
    context = {
        "products": _published_products(),
        "selected_product": product,
        "streamfield": product.content,
        "page_title": product.title,
        "page_description": product.summary,
        "seo_title": product.seo_title or product.title,
        "seo_description": product.seo_description or product.summary,
        "seo_keywords": product.seo_keywords,
        "seo_og_image": product.seo_og_image or product.card_image,
    }
    context.update(_simulation_context(product))
    return render(request, "cms/pages/product.html", context)


@require_GET
def product_simulation(request, slug):
    product = get_object_or_404(_published_products(), slug=slug)
    try:
        profile = product.simulation
    except Product.simulation.RelatedObjectDoesNotExist:
        return JsonResponse({"error": "Simulator tidak tersedia."}, status=404)
    if not profile.is_enabled or not profile.is_ready:
        return JsonResponse({"error": "Simulator tidak tersedia."}, status=404)
    try:
        result = simulate(profile, request.GET)
    except SimulationValidationError as exc:
        return JsonResponse(
            {"error": "Data simulasi tidak valid.", "errors": exc.errors},
            status=400,
        )
    return JsonResponse(result)
