from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse
from wagtail.models import Site
from unittest.mock import patch

from _misc.management.commands.seed_misc_pages import Command as SeedCommand
from _misc.models import MiscellaneousIndexPage, MiscellaneousPage
from _product.tests.test_product import make_test_image


class MiscellaneousPageTests(TestCase):
    def setUp(self):
        self.site = Site.objects.get(is_default_site=True)
        self.index = MiscellaneousIndexPage(title="Halaman", slug="halaman", introduction="Informasi penting.")
        self.site.root_page.add_child(instance=self.index)
        self.index.save_revision().publish()

    def make_page(self, **overrides):
        values = {
            "title": "Test Information",
            "slug": "test-information",
            "introduction": "Short introduction.",
            "content": [{"type": "heading", "value": {"level": "h2", "title": "Full StreamField Content"}}],
        }
        values.update(overrides)
        page = MiscellaneousPage(**values)
        self.index.add_child(instance=page)
        page.save_revision().publish()
        return page

    def test_index_detail_and_native_preview_render(self):
        page = self.make_page()
        request = RequestFactory().get("/admin/preview/")

        self.assertContains(self.client.get(self.index.url), page.title)
        self.assertContains(self.client.get(page.url), "Full StreamField Content")
        preview = page.serve_preview(request, page.default_preview_mode)
        preview.render()
        self.assertContains(preview, "Full StreamField Content")

    def test_header_and_main_menu_are_mutually_exclusive(self):
        page = MiscellaneousPage(
            title="Invalid Navigation",
            slug="invalid-navigation",
            introduction="Invalid.",
            show_on_header=True,
            show_on_main_menu=True,
        )
        with self.assertRaises(ValidationError):
            self.index.add_child(instance=page)

    def test_navigation_flags_place_live_pages_in_correct_regions(self):
        dropdown = self.make_page(
            title="Dropdown Page",
            slug="dropdown-page",
            menu_description="Short misc menu copy.",
            show_on_header=True,
        )
        main = self.make_page(title="Main Menu Page", slug="main-menu-page", show_on_main_menu=True)
        footer = self.make_page(title="Footer Page", slug="footer-page", show_on_footer=True)

        response = self.client.get(reverse("landing"))

        self.assertContains(response, dropdown.title)
        self.assertContains(response, main.title)
        self.assertContains(response, footer.title)
        self.assertContains(response, f'href="{self.index.url}" class="nav-link">Halaman</a>')
        self.assertContains(response, dropdown.url)
        self.assertContains(response, dropdown.menu_description)
        self.assertContains(response, main.url)
        self.assertContains(response, footer.url)

    def test_unpublished_page_is_not_exposed_in_navigation(self):
        page = MiscellaneousPage(
            title="Private Draft",
            slug="private-draft",
            introduction="Draft content.",
            show_on_main_menu=True,
            live=False,
        )
        self.index.add_child(instance=page)
        page.save_revision()

        response = self.client.get(reverse("landing"))

        self.assertNotContains(response, page.title)


class MiscellaneousSeedTests(TestCase):
    def test_seed_is_idempotent(self):
        image = make_test_image("Misc seed image")
        images = {key: image for key in ("about", "guide", "policy")}
        with patch.object(SeedCommand, "_ensure_images", return_value=images):
            call_command("seed_misc_pages")
            call_command("seed_misc_pages")

        self.assertEqual(MiscellaneousIndexPage.objects.filter(slug="halaman").count(), 1)
        self.assertEqual(MiscellaneousPage.objects.count(), 5)
