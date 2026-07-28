from django.db import models
from wagtail.admin.panels import FieldPanel


class ProductCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    panels = [FieldPanel("name"), FieldPanel("slug"), FieldPanel("is_active"), FieldPanel("sort_order")]

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name_plural = "Product categories"

    def __str__(self):
        return self.name
