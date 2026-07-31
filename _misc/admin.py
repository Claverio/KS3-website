from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from _misc.models import PublicDocument, ImageGallery


class PublicDocumentViewSet(SnippetViewSet):
    model = PublicDocument
    menu_label = "Public Documents"
    icon = "doc-full"
    list_display = ("title", "upload_date", "is_published", "sort_order")
    list_filter = ("is_published",)
    search_fields = ("title", "description")
    ordering = ("sort_order", "-upload_date")
    inspect_view_enabled = True


class ImageGalleryViewSet(SnippetViewSet):
    model = ImageGallery
    menu_label = "Image Galleries"
    icon = "image"
    list_display = ("title", "is_published", "sort_order", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title",)
    ordering = ("sort_order", "-created_at")
    inspect_view_enabled = True


class MiscAdminGroup(SnippetViewSetGroup):
    menu_label = "Miscellaneous"
    menu_icon = "folder-open-inverse"
    menu_name = "misc"
    menu_order = 300
    items = (PublicDocumentViewSet, ImageGalleryViewSet)


register_snippet(MiscAdminGroup)