from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from backend.helper.singleton import SingletonSnippetViewSet
from _p2p.models import P2P, P2PCategory, P2PPurchase, P2PSEOSettings


class P2PSEOViewSet(SingletonSnippetViewSet):
    model = P2PSEOSettings
    menu_label = "Halaman & SEO"
    icon = "search"


class P2PCategoryViewSet(SnippetViewSet):
    model = P2PCategory
    menu_label = "Categories"
    icon = "tag"
    list_display = ("name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("sort_order", "name")


class P2PProjectViewSet(SnippetViewSet):
    model = P2P
    menu_label = "Projects"
    icon = "folder-open-inverse"
    list_display = (
        "title",
        "category",
        "status",
        "is_published",
        "available_slots",
        "progress_percentage",
        "funding_deadline",
    )
    list_filter = ("status", "is_published", "is_featured", "category")
    search_fields = ("title", "slug", "summary")
    ordering = ("sort_order", "-created_at")
    inspect_view_enabled = True


class P2PPurchaseViewSet(SnippetViewSet):
    model = P2PPurchase
    menu_label = "Pembelian Project"
    icon = "credit-card"
    list_display = (
        "booking_number",
        "project",
        "full_name",
        "masked_nik",
        "slot_quantity",
        "total_amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "project", "created_at")
    search_fields = ("booking_number", "reference_id", "full_name", "email", "phone")
    ordering = ("-created_at",)
    inspect_view_enabled = True


class P2PAdminGroup(SnippetViewSetGroup):
    menu_label = "Project"
    menu_icon = "hand-holding-dollar"
    menu_name = "p2p-lending"
    menu_order = 200
    items = (P2PSEOViewSet, P2PCategoryViewSet, P2PProjectViewSet, P2PPurchaseViewSet)


register_snippet(P2PAdminGroup)
