from django.db import models
from wagtail.admin.panels import FieldPanel

class ImageGallery(models.Model):
    title = models.CharField(max_length=255)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        related_name="+"
    )
    is_published = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("image"),
        FieldPanel("is_published"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ("sort_order", "-created_at")
        verbose_name = "Image Gallery"
        verbose_name_plural = "Image Galleries"

    def __str__(self):
        return self.title
