from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel

from backend.helper.singleton_model import SingletonModel


class ContactSetting(SingletonModel):
    address = models.TextField(
        default="Werkspace Pluit, Jl. Pluit Indah No.168B, Jakarta Utara"
    )
    operational_hours = models.CharField(
        max_length=255, default="Dukungan Pelanggan (09:00 - 17:00 WIB)"
    )
    whatsapp_display = models.CharField(
        max_length=50,
        blank=True,
        help_text="Nomor yang ditampilkan, contoh: +62 812-3456-7890.",
    )
    whatsapp_link = models.URLField(
        blank=True,
        help_text="Tautan WhatsApp lengkap, contoh: https://wa.me/6281234567890.",
    )
    email = models.EmailField(default="cs@koperasiks3.id")
    financing_email = models.EmailField(default="pembiayaan@koperasiks3.id")
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    behance_url = models.URLField(blank=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("address"),
                FieldPanel("operational_hours"),
                FieldPanel("email"),
                FieldPanel("financing_email"),
            ],
            heading="Contact information",
        ),
        MultiFieldPanel(
            [FieldPanel("whatsapp_display"), FieldPanel("whatsapp_link")],
            heading="WhatsApp",
        ),
        MultiFieldPanel(
            [
                FieldPanel("facebook_url"),
                FieldPanel("instagram_url"),
                FieldPanel("twitter_url"),
                FieldPanel("behance_url"),
            ],
            heading="Social media",
        ),
    ]

    class Meta:
        verbose_name = "Contact setting"

    def __str__(self):
        return "Contact Settings"
