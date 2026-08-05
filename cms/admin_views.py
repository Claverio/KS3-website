from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from wagtail.admin.auth import user_passes_test
from wagtail.models import Page

from _p2p.models import P2P, P2PPurchase
from _product.models import Product


@user_passes_test(lambda user: user.has_perm("wagtailadmin.access_admin"))
def global_admin_search(request):
    query = request.GET.get("q", "").strip()[:100]
    groups = []

    if query:
        projects = P2P.objects.filter(
            Q(title__icontains=query)
            | Q(slug__icontains=query)
            | Q(summary__icontains=query)
            | Q(category__name__icontains=query)
        ).select_related("category")[:20]
        groups.append(
            {
                "key": "p2p",
                "title": "P2P Lending",
                "icon": "hand-holding-dollar",
                "items": [
                    {
                        "title": item.title,
                        "description": f"{item.category.name} · {item.get_status_display()}",
                        "meta": f"{item.available_slots} slot tersedia",
                        "url": reverse(
                            "wagtailsnippets__p2p_p2p:edit", args=[item.pk]
                        ),
                    }
                    for item in projects
                ],
            }
        )

        purchases = P2PPurchase.objects.filter(
            Q(booking_number__icontains=query)
            | Q(reference_id__icontains=query)
            | Q(full_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(project__title__icontains=query)
        ).select_related("project")[:20]
        groups.append(
            {
                "key": "purchase",
                "title": "Transaksi Proyek",
                "icon": "credit-card",
                "items": [
                    {
                        "title": item.booking_number,
                        "description": f"{item.full_name} · {item.project.title}",
                        "meta": f"{item.get_status_display()} · {item.slot_quantity} slot",
                        "url": reverse(
                            "wagtailsnippets__p2p_p2ppurchase:edit", args=[item.pk]
                        ),
                    }
                    for item in purchases
                ],
            }
        )

        products = Product.objects.filter(
            Q(title__icontains=query)
            | Q(slug__icontains=query)
            | Q(summary__icontains=query)
            | Q(category__name__icontains=query)
        ).select_related("category")[:20]
        groups.append(
            {
                "key": "product",
                "title": "Produk",
                "icon": "folder-open-inverse",
                "items": [
                    {
                        "title": item.title,
                        "description": item.category.name,
                        "meta": "Published" if item.is_published else "Draft",
                        "url": reverse(
                            "wagtailsnippets__product_product:edit", args=[item.pk]
                        ),
                    }
                    for item in products
                ],
            }
        )

        pages = Page.objects.filter(
            Q(title__icontains=query)
            | Q(slug__icontains=query)
            | Q(search_description__icontains=query)
        ).order_by("title")[:20]
        groups.append(
            {
                "key": "page",
                "title": "Halaman",
                "icon": "doc-full-inverse",
                "items": [
                    {
                        "title": item.get_admin_display_title(),
                        "description": item.specific._meta.verbose_name.title(),
                        "meta": "Live" if item.live else "Draft",
                        "url": reverse("wagtailadmin_pages:edit", args=[item.pk]),
                    }
                    for item in pages
                ],
            }
        )

    total_results = sum(len(group["items"]) for group in groups)
    return render(
        request,
        "wagtailadmin/ks3_search.html",
        {
            "query": query,
            "groups": groups,
            "total_results": total_results,
        },
    )
