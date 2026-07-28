from django.db import models
from wagtail.admin.panels import FieldPanel, ObjectList, TabbedInterface

from backend.helper.singleton_model import SingletonModel


class P2PSEOSettings(SingletonModel):
    list_title = models.CharField(max_length=255, blank=True)
    list_description = models.TextField(blank=True)
    list_keywords = models.CharField(max_length=255, blank=True)
    detail_title = models.CharField(max_length=255, blank=True)
    detail_description = models.TextField(blank=True)
    detail_keywords = models.CharField(max_length=255, blank=True)
    purchase_title = models.CharField(max_length=255, blank=True)
    purchase_description = models.TextField(blank=True)
    purchase_keywords = models.CharField(max_length=255, blank=True)
    complete_title = models.CharField(max_length=255, blank=True)
    complete_description = models.TextField(blank=True)
    complete_keywords = models.CharField(max_length=255, blank=True)
    og_image = models.ForeignKey(
        "wagtailimages.Image",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [FieldPanel("list_title"), FieldPanel("list_description"), FieldPanel("list_keywords")],
                heading="List",
            ),
            ObjectList(
                [FieldPanel("detail_title"), FieldPanel("detail_description"), FieldPanel("detail_keywords")],
                heading="Detail",
            ),
            ObjectList(
                [FieldPanel("purchase_title"), FieldPanel("purchase_description"), FieldPanel("purchase_keywords")],
                heading="Purchase",
            ),
            ObjectList(
                [FieldPanel("complete_title"), FieldPanel("complete_description"), FieldPanel("complete_keywords")],
                heading="Complete",
            ),
            ObjectList([FieldPanel("og_image")], heading="Social image"),
        ]
    )

    class Meta:
        verbose_name = "P2P SEO setting"

    def __str__(self):
        return "P2P SEO Settings"
