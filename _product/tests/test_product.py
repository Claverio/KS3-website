from io import BytesIO
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse
from PIL import Image as PillowImage
from wagtail.images import get_image_model
from wagtail.models import Collection

from _p2p.tests.factories import make_project
from _product.management.commands.seed_product_showcase import Command as SeedCommand
from _product.models import Product
from _product.tests.factories import make_product
from _setting.models import ContactSetting


def make_test_image(title="Test image"):
    buffer = BytesIO()
    PillowImage.new("RGB", (10, 10), "#005daa").save(buffer, format="PNG")
    Image = get_image_model()
    image = Image(
        title=title,
        collection=Collection.get_first_root_node(),
    )
    image.file.save(
        f"{title.lower().replace(' ', '-')}.png",
        ContentFile(buffer.getvalue()),
        save=False,
    )
    image.width = 10
    image.height = 10
    image.file_size = len(buffer.getvalue())
    image.save()
    return image


class ProductPageTests(TestCase):
    def test_list_and_detail_are_model_driven(self):
        published = make_product(title="Published Product", slug="published-product")
        hidden = make_product(title="Hidden Product", slug="hidden-product", is_published=False)

        listing = self.client.get(reverse("product"))
        detail = self.client.get(published.get_absolute_url())

        self.assertContains(listing, published.title)
        self.assertNotContains(listing, hidden.title)
        self.assertContains(detail, published.title)
        self.assertEqual(self.client.get(hidden.get_absolute_url()).status_code, 404)

    def test_legacy_product_url_redirects_permanently(self):
        response = self.client.get("/product")
        self.assertRedirects(response, reverse("product"), status_code=301)

    def test_product_help_card_links_to_whatsapp(self):
        product = make_product()
        contact = ContactSetting.load()
        contact.whatsapp_display = "+62 812-3456-7890"
        contact.whatsapp_link = "https://wa.me/6281234567890"
        contact.save()

        response = self.client.get(product.get_absolute_url())

        self.assertContains(response, contact.whatsapp_display)
        self.assertContains(response, contact.whatsapp_link)

    def test_homepage_uses_only_featured_published_products(self):
        featured = make_product(
            title="Homepage Product",
            is_featured=True,
            menu_description="Short product menu copy.",
        )
        regular = make_product(title="Listing Only Product", is_featured=False)
        hidden = make_product(title="Hidden Homepage Product", is_featured=True, is_published=False)

        response = self.client.get(reverse("landing"))

        homepage_products = list(response.context["featured_products"])
        self.assertIn(featured, homepage_products)
        self.assertNotIn(regular, homepage_products)
        self.assertNotIn(hidden, homepage_products)
        self.assertContains(response, featured.menu_description)

    def test_product_and_p2p_preview_render_streamfield_drafts(self):
        product = make_product(is_published=False, content=[{"type": "heading", "value": {"level": "h2", "title": "Draft Product Content"}}])
        project = make_project(is_published=False, content=[{"type": "heading", "value": {"level": "h2", "title": "Draft P2P Content"}}])
        request = RequestFactory().get("/admin/preview/")

        product_response = product.serve_preview(request, product.default_preview_mode)
        project_response = project.serve_preview(request, project.default_preview_mode)
        product_response.render()
        project_response.render()

        self.assertContains(product_response, "Draft Product Content")
        self.assertContains(project_response, "Draft P2P Content")


class ProductSeedTests(TestCase):
    def test_seed_is_idempotent(self):
        image = make_test_image("Product seed image")
        images = {key: image for key in ("wajib", "sukarela", "berjangka", "pokok", "lain")}
        with patch.object(SeedCommand, "_ensure_images", return_value=images):
            call_command("seed_product_showcase")
            call_command("seed_product_showcase")

        self.assertEqual(Product.objects.filter(slug__in=["simpanan-wajib", "simpanan-sukarela", "simpanan-berjangka", "simpanan-pokok", "simpanan-lain"]).count(), 5)
