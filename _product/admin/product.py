from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from backend.helper.singleton import SingletonSnippetViewSet
from _product.models import Product, ProductCategory, ProductSEOSettings, ProductSimulation, SavingTransaction
from _product.admin.views import SavingTransactionCreateView
from _product.forms.admin import SavingTransactionAdminForm


SavingTransaction.base_form_class = SavingTransactionAdminForm


class ProductSEOViewSet(SingletonSnippetViewSet):
    model = ProductSEOSettings
    menu_label = "SEO"
    icon = "search"


class ProductCategoryViewSet(SnippetViewSet):
    model = ProductCategory
    menu_label = "Categories"
    icon = "tag"
    list_display = ("name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("sort_order", "name")


class ProductViewSet(SnippetViewSet):
    model = Product
    menu_label = "Products"
    icon = "folder-open-inverse"
    list_display = ("title", "category", "is_published", "is_featured", "sort_order")
    list_filter = ("is_published", "is_featured", "category")
    search_fields = ("title", "slug", "summary")
    ordering = ("sort_order", "title")
    inspect_view_enabled = True


class ProductSimulationViewSet(SnippetViewSet):
    model = ProductSimulation
    menu_label = "Simulators"
    icon = "calculator"
    list_display = ("product", "product_kind", "strategy", "is_enabled", "readiness", "updated_at")
    list_filter = ("is_enabled", "product_kind", "strategy")
    search_fields = ("product__title", "product__slug", "simulator_title")
    ordering = ("product__title",)
    inspect_view_enabled = True


class SavingTransactionViewSet(SnippetViewSet):
    model = SavingTransaction
    menu_label = "Setoran Simpanan"
    icon = "credit-card"
    add_view_class = SavingTransactionCreateView
    list_display = (
        "transaction_code",
        "product",
        "full_name",
        "nomor_anggota",
        "amount",
        "payment_channel",
        "status",
        "created_at",
    )
    list_filter = ("status", "payment_channel", "product", "is_new_member", "created_at")
    search_fields = ("transaction_code", "reference_id", "full_name", "email", "phone", "nomor_anggota")
    ordering = ("-created_at",)
    inspect_view_enabled = True


class ProductAdminGroup(SnippetViewSetGroup):
    menu_label = "Products"
    menu_icon = "folder-open-inverse"
    menu_name = "products"
    menu_order = 210
    items = (ProductSEOViewSet, ProductCategoryViewSet, ProductViewSet, ProductSimulationViewSet, SavingTransactionViewSet)


register_snippet(ProductAdminGroup)
