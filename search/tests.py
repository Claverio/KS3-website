from django.test import TestCase
from django.urls import reverse
from wagtail.models import Site

from _misc.models import MiscellaneousIndexPage, MiscellaneousPage
from _p2p.tests.factories import make_project
from _product.tests.factories import make_product


class UnifiedSearchTests(TestCase):
    def setUp(self):
        self.site = Site.objects.get(is_default_site=True)
        self.index = MiscellaneousIndexPage(
            title="Halaman",
            slug="halaman",
            introduction="Informasi KS3.",
        )
        self.site.root_page.add_child(instance=self.index)
        self.index.save_revision().publish()

    def make_page(self, **overrides):
        values = {
            "title": "Panduan Kopi",
            "slug": "panduan-kopi",
            "introduction": "Informasi bagi pelaku usaha kopi.",
        }
        values.update(overrides)
        page = MiscellaneousPage(**values)
        self.index.add_child(instance=page)
        page.save_revision().publish()
        return page

    def test_search_combines_and_categorizes_published_content(self):
        project = make_project(title="Pendanaan Kopi Nusantara", summary="Ekspansi roastery.")
        product = make_product(title="Simpanan Kopi", summary="Simpanan untuk pengusaha kopi.")
        page = self.make_page()
        hidden = make_product(title="Kopi Rahasia", is_published=False)

        response = self.client.get(reverse("search"), {"q": "kopi"})

        self.assertContains(response, project.title)
        self.assertContains(response, product.title)
        self.assertContains(response, page.title)
        self.assertNotContains(response, hidden.title)
        self.assertEqual(response.context["total_count"], 3)
        self.assertContains(response, "P2P Lending")
        self.assertContains(response, "Produk KS3")
        self.assertContains(response, "Halaman Informasi")

    def test_category_filter_only_renders_selected_group(self):
        project = make_project(title="Pendanaan Kopi")
        product = make_product(title="Produk Kopi")

        response = self.client.get(reverse("search"), {"q": "kopi", "category": "product"})

        self.assertContains(response, product.title)
        self.assertNotContains(response, project.title)
        self.assertEqual(response.context["active_category"], "product")

    def test_header_search_posts_expected_query_parameter(self):
        response = self.client.get(reverse("landing"))

        self.assertContains(response, f'action="{reverse("search")}"')
        self.assertContains(response, 'name="q"')

    def test_empty_search_has_guidance(self):
        response = self.client.get(reverse("search"))

        self.assertContains(response, "Apa yang ingin Anda cari?")

    def test_empty_selected_category_offers_all_results(self):
        make_project(title="Pendanaan Kopi")

        response = self.client.get(reverse("search"), {"q": "kopi", "category": "product"})

        self.assertEqual(response.context["active_count"], 0)
        self.assertContains(response, "Belum menemukan hasil")
        self.assertContains(response, "Lihat semua 1 hasil")
