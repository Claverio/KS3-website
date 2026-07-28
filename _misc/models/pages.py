from django.core.exceptions import ValidationError
from django.db import models
from wagtail.admin.panels import FieldPanel, ObjectList, TabbedInterface
from wagtail.fields import StreamField
from wagtail.models import Page

from backend.helper.streamfield import page_content_blocks


class MiscellaneousIndexPage(Page):
    template = "cms/pages/miscellaneous_index.html"
    introduction = models.TextField(
        default="Informasi penting mengenai layanan, keanggotaan, dan kebijakan KS3."
    )

    parent_page_types = ["home.HomePage"]
    subpage_types = ["_misc.MiscellaneousPage"]
    max_count_per_parent = 1
    content_panels = Page.content_panels + [FieldPanel("introduction")]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update({
            "pages": MiscellaneousPage.objects.live().public().child_of(self).order_by("menu_order", "title"),
            "page_title": self.title,
            "page_description": self.introduction,
            "seo_title": self.seo_title or self.title,
            "seo_description": self.search_description or self.introduction,
        })
        return context


class MiscellaneousPage(Page):
    template = "cms/pages/miscellaneous_detail.html"
    introduction = models.TextField(max_length=500)
    menu_description = models.CharField(
        max_length=60,
        blank=True,
        help_text="Very short description for the header dropdown (3–5 words).",
    )
    content = StreamField(page_content_blocks(), use_json_field=True, blank=True)
    menu_order = models.PositiveIntegerField(default=0, db_index=True)
    show_on_header = models.BooleanField(
        default=False,
        help_text="Show inside the Halaman dropdown in the header.",
    )
    show_on_main_menu = models.BooleanField(
        default=False,
        help_text="Show directly as a top-level header menu item.",
    )
    show_on_footer = models.BooleanField(default=False)

    parent_page_types = ["_misc.MiscellaneousIndexPage"]
    subpage_types = []

    edit_handler = TabbedInterface([
        ObjectList(Page.content_panels + [FieldPanel("introduction"), FieldPanel("menu_description"), FieldPanel("content")], heading="Content"),
        ObjectList([FieldPanel("show_on_header"), FieldPanel("show_on_main_menu"), FieldPanel("show_on_footer"), FieldPanel("menu_order")], heading="Navigation"),
        ObjectList([FieldPanel("seo_title"), FieldPanel("search_description")], heading="SEO"),
        ObjectList(Page.settings_panels, heading="Settings"),
    ])

    def clean(self):
        super().clean()
        if self.show_on_header and self.show_on_main_menu:
            raise ValidationError(
                {"show_on_main_menu": "Choose either the Halaman dropdown or the main menu, not both."}
            )

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update({
            "streamfield": self.content,
            "page_title": self.title,
            "page_description": self.introduction,
            "seo_title": self.seo_title or self.title,
            "seo_description": self.search_description or self.introduction,
        })
        return context

    class Meta:
        ordering = ("menu_order", "title")
