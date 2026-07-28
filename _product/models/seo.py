from django.db import models
from wagtail.admin.panels import FieldPanel

from backend.helper.singleton_model import SingletonModel


class ProductSEOSettings(SingletonModel):
    list_title = models.CharField(max_length=255, default="Produk | KS3")
    list_description = models.TextField(default="Temukan produk simpanan yang sesuai dengan rencana keuangan Anda.")
    list_keywords = models.CharField(max_length=255, blank=True)
    og_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    panels = [FieldPanel("list_title"), FieldPanel("list_description"), FieldPanel("list_keywords"), FieldPanel("og_image")]

    class Meta:
        verbose_name = "Product SEO setting"

    def __str__(self):
        return "Product SEO Settings"
