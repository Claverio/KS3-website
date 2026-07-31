from django.db import models
from django.utils import timezone
from wagtail.admin.panels import FieldPanel

class PublicDocument(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(max_length=500, blank=True, help_text="Small description of the document.")
    document = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
        related_name="+"
    )
    upload_date = models.DateField(default=timezone.now, help_text="Date of upload/publication")
    is_published = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("description"),
        FieldPanel("document"),
        FieldPanel("upload_date"),
        FieldPanel("is_published"),
        FieldPanel("sort_order"),
    ]

    class Meta:
        ordering = ("sort_order", "-upload_date")
        verbose_name = "Public Document"
        verbose_name_plural = "Public Documents"

    def __str__(self):
        return self.title