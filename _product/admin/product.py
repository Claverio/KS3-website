from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from backend.helper.singleton import SingletonSnippetViewSet
from _product.models import Product, ProductCategory, ProductSEOSettings


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


class ProductAdminGroup(SnippetViewSetGroup):
    menu_label = "Products"
    menu_icon = "folder-open-inverse"
    menu_name = "products"
    menu_order = 210
    items = (ProductSEOViewSet, ProductCategoryViewSet, ProductViewSet)


register_snippet(ProductAdminGroup)
