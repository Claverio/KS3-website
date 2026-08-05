from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import (
    FieldPanel,
    InlinePanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
)
from wagtail.models import Orderable

from backend.helper.singleton_model import SingletonModel


class ContactSetting(SingletonModel):
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
    whatsapp_floating_enabled = models.BooleanField(
        "Tampilkan tombol WhatsApp melayang",
        default=True,
        help_text=(
            "Tampilkan tombol chat WhatsApp di semua halaman. "
            "Tombol hanya muncul jika tautan WhatsApp sudah diisi."
        ),
    )
    email = models.EmailField(default="cs@koperasiks3.id")
    financing_email = models.EmailField(default="pembiayaan@koperasiks3.id")
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    behance_url = models.URLField(blank=True)

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    InlinePanel(
                        "addresses",
                        label="Alamat kantor",
                        heading="Daftar kantor dan cabang",
                        help_text=(
                            "Klik Tambah alamat kantor untuk menambah cabang. "
                            "Urutan pertama digunakan sebagai kantor utama pada email."
                        ),
                    )
                ],
                heading="Alamat Kantor",
            ),
            ObjectList(
                [
                    MultiFieldPanel(
                        [
                            FieldPanel("email"),
                            FieldPanel("financing_email"),
                        ],
                        heading="Alamat email",
                    ),
                    FieldPanel("operational_hours"),
                ],
                heading="Email & Operasional",
            ),
            ObjectList(
                [
                    FieldPanel("whatsapp_floating_enabled"),
                    FieldPanel("whatsapp_display"),
                    FieldPanel("whatsapp_link"),
                ],
                heading="WhatsApp",
            ),
            ObjectList(
                [
                    FieldPanel("facebook_url"),
                    FieldPanel("instagram_url"),
                    FieldPanel("twitter_url"),
                    FieldPanel("behance_url"),
                ],
                heading="Media Sosial",
            ),
        ]
    )

    class Meta:
        verbose_name = "Contact setting"

    def __str__(self):
        return "Contact Settings"

    @property
    def primary_address(self):
        return self.addresses.first()

    @property
    def primary_address_text(self):
        address = self.primary_address
        return address.address if address else ""


class ContactAddress(Orderable):
    contact_setting = ParentalKey(
        ContactSetting,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    name = models.CharField(
        max_length=120,
        help_text="Contoh: Kantor Jakarta atau Kantor Tangerang.",
    )
    address = models.TextField()

    panels = [FieldPanel("name"), FieldPanel("address")]

    class Meta(Orderable.Meta):
        verbose_name = "Alamat kantor"
        verbose_name_plural = "Alamat kantor"

    def __str__(self):
        return self.name
