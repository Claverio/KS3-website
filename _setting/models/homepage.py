import uuid

from django.db import models
from wagtail.admin.panels import FieldPanel, ObjectList, TabbedInterface
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import StreamField

from backend.helper.homepage_streamfield import (
    faq_item_blocks,
    icon_text_item_blocks,
    marquee_item_blocks,
    text_item_blocks,
)


def _item(value):
    return {"type": "item", "value": value, "id": str(uuid.uuid4())}


def default_hero_points():
    return [_item({"text": text}) for text in (
        "Akses digital", "Dikelola profesional", "Berorientasi pada UMKM"
    )]


def default_marquee_items():
    return [
        _item({"text": "Koperasi Terdaftar", "tone": "dark"}),
        _item({"text": "P2P Lending", "tone": "muted"}),
        _item({"text": "Imbal Hasil Kompetitif", "tone": "dark"}),
        _item({"text": "Pembiayaan UMKM", "tone": "muted"}),
        _item({"text": "Koperasi Terdaftar", "tone": "dark"}),
        _item({"text": "Imbal Hasil Kompetitif", "tone": "muted"}),
    ]


def default_about_audiences():
    return [
        _item({"icon": "bi-wallet2", "title": "Untuk Anggota", "description": "Produk simpanan yang fleksibel dan mudah dipantau."}),
        _item({"icon": "bi-shop", "title": "Untuk UMKM", "description": "Pembiayaan yang lebih ringkas dan terverifikasi."}),
    ]


def default_about_highlights():
    return default_hero_points()


def default_advantages():
    return [
        _item({"icon": "bi-phone", "title": "Digitalisasi", "description": "Akses pembiayaan dan pantau simpanan secara digital, kapan pun dibutuhkan."}),
        _item({"icon": "bi-graph-up-arrow", "title": "Kompetitif", "description": "Proses pinjaman yang ringkas dengan jasa simpanan yang kompetitif bagi anggota."}),
        _item({"icon": "bi-shield-check", "title": "Terverifikasi", "description": "Didukung sistem pengendalian internal dan tim yang kompeten dalam melayani anggota serta UMKM."}),
    ]


FAQ_ANSWER = (
    "<p>KS3 (Koperasi Simpan Pinjam Sentra Solusi Sejahtera) adalah koperasi "
    "berbasis digital yang mengoperasikan model peer-to-peer (P2P) lending. "
    "Berbeda dengan koperasi konvensional, KS3 memungkinkan anggota untuk "
    "langsung mendanai pelaku UMKM terverifikasi melalui platform digital dan "
    "mendapatkan imbal hasil dari pembiayaan yang tersalurkan.</p>"
)


def default_faq_items():
    return [_item({"question": question, "answer": FAQ_ANSWER}) for question in (
        "Apa itu KS3 dan apa bedanya dengan koperasi biasa?",
        "Berapa imbal hasil yang bisa saya dapatkan sebagai pendana?",
        "Berapa minimum dana untuk mulai mendanai?",
        "Apakah dana saya aman di KS3?",
    )]


@register_setting(icon="home", order=100)
class HomePageSetting(BaseSiteSetting):
    hero_enabled = models.BooleanField(default=True)
    hero_background_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    hero_decorative_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    hero_badge = models.CharField(max_length=160, default="Koperasi Simpan Pinjam Berbasis Digital")
    hero_title = models.CharField(max_length=255, default="Simpanan dan Pendanaan UMKM dalam Satu Ekosistem")
    hero_description = models.TextField(default="KS3 menyediakan produk simpanan bagi anggota serta akses P2P Investment untuk mendukung pembiayaan UMKM terverifikasi.")
    hero_primary_label = models.CharField(max_length=80, default="Lihat Produk")
    hero_primary_url = models.CharField(max_length=500, default="/product")
    hero_secondary_label = models.CharField(max_length=80, default="Lihat Investasi P2P")
    hero_secondary_url = models.CharField(max_length=500, default="/peer-to-peer/")
    hero_points = StreamField(text_item_blocks(), use_json_field=True, default=default_hero_points)
    hero_floating_title = models.CharField(max_length=120, default="Produk KSP & P2P")
    hero_floating_description = models.CharField(max_length=160, default="Untuk anggota dan UMKM")
    hero_main_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    hero_main_image_alt = models.CharField(max_length=160, default="Layanan digital Koperasi KS3")

    marquee_enabled = models.BooleanField(default=True)
    marquee_items = StreamField(marquee_item_blocks(), use_json_field=True, default=default_marquee_items)

    about_enabled = models.BooleanField(default=True)
    about_primary_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    about_secondary_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    about_badge = models.CharField(max_length=120, default="Tentang KSP KS3")
    about_title = models.CharField(max_length=255, default="Layanan Keuangan Digital bagi Anggota dan UMKM")
    about_description = models.TextField(default="KS3 adalah koperasi simpan pinjam berbasis digital yang membantu anggota mengelola dana sekaligus membuka akses pembiayaan bagi UMKM.")
    about_audiences = StreamField(icon_text_item_blocks(), use_json_field=True, default=default_about_audiences)
    about_highlights = StreamField(text_item_blocks(), use_json_field=True, default=default_about_highlights)

    p2p_enabled = models.BooleanField(default=True)
    p2p_small_title = models.CharField(max_length=120, default="P2P Investment")
    p2p_title = models.CharField(max_length=255, default="P2P Investment Pilihan")
    p2p_description = models.TextField(default="Pilih peluang pendanaan UMKM yang sesuai dengan tujuan investasi Anda.")

    products_enabled = models.BooleanField(default=True)
    products_background_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    products_small_title = models.CharField(max_length=120, default="Produk KSP KS3")
    products_title = models.CharField(max_length=255, default="Produk Simpanan untuk Setiap Kebutuhan")
    products_description = models.TextField(default="Mulai dari simpanan keanggotaan, dana fleksibel, hingga simpanan berjangka untuk rencana keuangan Anda.")

    advantages_enabled = models.BooleanField(default=True)
    advantages_badge = models.CharField(max_length=120, default="Keunggulan KS3")
    advantages_title = models.CharField(max_length=255, default="Mengapa Memilih Koperasi KS3?")
    advantages_description = models.TextField(default="KS3 menggabungkan layanan koperasi dengan akses digital untuk membantu anggota mengelola simpanan dan memperoleh pembiayaan secara lebih praktis.")
    advantages_items = StreamField(icon_text_item_blocks(), use_json_field=True, default=default_advantages)
    advantages_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    advantages_image_alt = models.CharField(max_length=160, default="Layanan digital Koperasi KS3")
    advantages_floating_title = models.CharField(max_length=120, default="Koperasi Digital")
    advantages_floating_description = models.CharField(max_length=160, default="Untuk anggota dan UMKM")

    faq_enabled = models.BooleanField(default=True)
    faq_badge = models.CharField(max_length=120, default="Pertanyaan Umum")
    faq_title = models.CharField(max_length=255, default="Punya Pertanyaan?")
    faq_description = models.TextField(default="Kami memahami bahwa memilih layanan keuangan adalah keputusan penting. Berikut jawaban atas pertanyaan yang paling sering diajukan oleh calon anggota dan pendana KS3.")
    faq_contact_prefix = models.CharField(max_length=160, default="Untuk pertanyaan lainnya hubungi :")
    faq_items = StreamField(faq_item_blocks(), use_json_field=True, default=default_faq_items)

    app_enabled = models.BooleanField(default=True)
    app_first_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    app_second_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    app_image_alt = models.CharField(max_length=160, default="Tampilan aplikasi KS3")
    app_badge = models.CharField(max_length=120, default="Aplikasi KS3")
    app_title = models.CharField(max_length=255, default="KS3, Kini dalam Genggaman Anda")
    app_description = models.TextField(default="Akses informasi pendanaan, pantau peluang P2P, dan dapatkan update KS3 langsung dari aplikasi.")
    app_store_url = models.CharField(max_length=500, default="#")
    play_store_url = models.CharField(max_length=500, default="#")

    edit_handler = TabbedInterface([
        ObjectList([FieldPanel("hero_enabled"), FieldPanel("hero_background_image"), FieldPanel("hero_decorative_image"), FieldPanel("hero_badge"), FieldPanel("hero_title"), FieldPanel("hero_description"), FieldPanel("hero_primary_label"), FieldPanel("hero_primary_url"), FieldPanel("hero_secondary_label"), FieldPanel("hero_secondary_url"), FieldPanel("hero_points"), FieldPanel("hero_floating_title"), FieldPanel("hero_floating_description"), FieldPanel("hero_main_image"), FieldPanel("hero_main_image_alt")], heading="Hero"),
        ObjectList([FieldPanel("marquee_enabled"), FieldPanel("marquee_items")], heading="Marquee"),
        ObjectList([FieldPanel("about_enabled"), FieldPanel("about_primary_image"), FieldPanel("about_secondary_image"), FieldPanel("about_badge"), FieldPanel("about_title"), FieldPanel("about_description"), FieldPanel("about_audiences"), FieldPanel("about_highlights")], heading="About"),
        ObjectList([FieldPanel("p2p_enabled"), FieldPanel("p2p_small_title"), FieldPanel("p2p_title"), FieldPanel("p2p_description")], heading="P2P"),
        ObjectList([FieldPanel("products_enabled"), FieldPanel("products_background_image"), FieldPanel("products_small_title"), FieldPanel("products_title"), FieldPanel("products_description")], heading="Products"),
        ObjectList([FieldPanel("advantages_enabled"), FieldPanel("advantages_badge"), FieldPanel("advantages_title"), FieldPanel("advantages_description"), FieldPanel("advantages_items"), FieldPanel("advantages_image"), FieldPanel("advantages_image_alt"), FieldPanel("advantages_floating_title"), FieldPanel("advantages_floating_description")], heading="Advantages"),
        ObjectList([FieldPanel("faq_enabled"), FieldPanel("faq_badge"), FieldPanel("faq_title"), FieldPanel("faq_description"), FieldPanel("faq_contact_prefix"), FieldPanel("faq_items")], heading="FAQ"),
        ObjectList([FieldPanel("app_enabled"), FieldPanel("app_first_image"), FieldPanel("app_second_image"), FieldPanel("app_image_alt"), FieldPanel("app_badge"), FieldPanel("app_title"), FieldPanel("app_description"), FieldPanel("app_store_url"), FieldPanel("play_store_url")], heading="App CTA"),
    ])

    class Meta:
        verbose_name = "Homepage setting"

    def __str__(self):
        return f"Homepage Settings — {self.site}"
