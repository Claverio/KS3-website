from django.db import models
from django.urls import reverse
from wagtail.admin.panels import FieldPanel, ObjectList, TabbedInterface
from wagtail.fields import StreamField
from wagtail.models import PreviewableMixin

from backend.helper.streamfield import page_content_blocks


class Product(PreviewableMixin, models.Model):
    ICON_CHOICES = (
        ("bi-wallet2", "Wallet"),
        ("bi-piggy-bank", "Piggy bank"),
        ("bi-calendar-check", "Calendar check"),
        ("bi-award", "Award"),
        ("bi-folder-plus", "Folder plus"),
        ("bi-cash-stack", "Cash stack"),
        ("bi-building", "Building"),
    )

    category = models.ForeignKey("_product.ProductCategory", on_delete=models.PROTECT, related_name="products")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    summary = models.TextField(max_length=500)
    menu_description = models.CharField(
        max_length=60,
        blank=True,
        help_text="Very short description for the header dropdown (3–5 words).",
    )
    icon = models.CharField(max_length=40, choices=ICON_CHOICES, default="bi-wallet2")
    card_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    content = StreamField(page_content_blocks(), use_json_field=True, blank=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)
    seo_keywords = models.CharField(max_length=255, blank=True)
    seo_og_image = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    edit_handler = TabbedInterface([
        ObjectList([FieldPanel("category"), FieldPanel("title"), FieldPanel("slug"), FieldPanel("summary"), FieldPanel("menu_description"), FieldPanel("icon"), FieldPanel("card_image"), FieldPanel("content")], heading="Content"),
        ObjectList([FieldPanel("is_featured"), FieldPanel("is_published"), FieldPanel("sort_order")], heading="Publishing"),
        ObjectList([FieldPanel("seo_title"), FieldPanel("seo_description"), FieldPanel("seo_keywords"), FieldPanel("seo_og_image")], heading="SEO"),
    ])

    class Meta:
        ordering = ("sort_order", "title")

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})

    def get_preview_template(self, request, mode_name):
        return "cms/pages/product.html"

    def get_preview_context(self, request, mode_name):
        products = list(Product.objects.select_related("category").filter(is_published=True, category__is_active=True))
        if not any(product.pk == self.pk for product in products):
            products.append(self)
            products.sort(key=lambda product: (product.sort_order, product.title))
        return {
            "products": products,
            "selected_product": self,
            "streamfield": self.content,
            "page_title": self.title,
            "page_description": self.summary,
            "seo_title": self.seo_title or self.title,
            "seo_description": self.seo_description or self.summary,
            "seo_keywords": self.seo_keywords,
            "seo_og_image": self.seo_og_image,
        }

    def __str__(self):
        return self.title
