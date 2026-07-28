from django.db import models
from wagtail.admin.panels import FieldPanel


class P2PCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("is_active"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ("sort_order", "name")
        verbose_name_plural = "P2P categories"

    def __str__(self):
        return self.name
