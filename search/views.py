from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import render
from wagtail.models import Site

from _misc.models import MiscellaneousPage
from _p2p.models import P2P
from _product.models import Product


SEARCH_CATEGORIES = {"all", "p2p", "product", "page"}


def _ranked(queryset, query):
    return queryset.annotate(
        search_rank=Case(
            When(title__iexact=query, then=Value(3)),
            When(title__istartswith=query, then=Value(2)),
            When(title__icontains=query, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by("-search_rank", "title")


def search(request):
    query = request.GET.get("q", "").strip()[:100]
    active_category = request.GET.get("category", "all").lower()
    if active_category not in SEARCH_CATEGORIES:
        active_category = "all"

    p2p_results = P2P.objects.none()
    product_results = Product.objects.none()
    page_results = MiscellaneousPage.objects.none()

    if query:
        p2p_results = _ranked(
            P2P.objects.select_related("category").filter(
                Q(title__icontains=query)
                | Q(summary__icontains=query)
                | Q(category__name__icontains=query),
                is_published=True,
                category__is_active=True,
            ).distinct(),
            query,
        )
        product_results = _ranked(
            Product.objects.select_related("category", "card_image").filter(
                Q(title__icontains=query)
                | Q(summary__icontains=query)
                | Q(menu_description__icontains=query)
                | Q(category__name__icontains=query),
                is_published=True,
                category__is_active=True,
            ).distinct(),
            query,
        )
        site = Site.find_for_request(request)
        if site:
            page_results = _ranked(
                MiscellaneousPage.objects.live()
                .public()
                .descendant_of(site.root_page)
                .filter(
                    Q(title__icontains=query)
                    | Q(introduction__icontains=query)
                    | Q(menu_description__icontains=query)
                ),
                query,
            )

    p2p_count = p2p_results.count()
    product_count = product_results.count()
    page_count = page_results.count()
    total_count = p2p_count + product_count + page_count
    category_counts = {
        "all": total_count,
        "p2p": p2p_count,
        "product": product_count,
        "page": page_count,
    }

    return render(
        request,
        "cms/pages/search.html",
        {
            "query": query,
            "active_category": active_category,
            "p2p_results": p2p_results,
            "product_results": product_results,
            "page_results": page_results,
            "p2p_count": p2p_count,
            "product_count": product_count,
            "page_count": page_count,
            "total_count": total_count,
            "active_count": category_counts[active_category],
            "page_title": "Pencarian",
            "page_description": "Temukan peluang pendanaan, produk simpanan, dan informasi KS3.",
            "seo_title": f'Hasil pencarian “{query}” | KS3' if query else "Pencarian | KS3",
            "seo_description": "Cari P2P Lending, produk simpanan, dan halaman informasi Koperasi KS3.",
        },
    )
