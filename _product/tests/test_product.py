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
from _product.models import Product, ProductCategory, ProductSimulation, SimulationFeeRule
from _product.simulation import simulate
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

    def test_product_listing_body_is_grouped_by_category_order(self):
        loan_category = ProductCategory.objects.create(
            name="Pinjaman",
            slug="pinjaman",
            sort_order=20,
        )
        savings_category = ProductCategory.objects.create(
            name="Simpanan",
            slug="simpanan",
            sort_order=10,
        )
        savings = make_product(title="Simpanan Menu", category=savings_category, sort_order=20)
        loan = make_product(title="Pinjaman Menu", category=loan_category, sort_order=10)

        response = self.client.get(reverse("product"))

        self.assertContains(response, 'data-product-section-group="simpanan"')
        self.assertContains(response, 'data-product-section-group="pinjaman"')
        content = response.content.decode()
        self.assertLess(content.index(savings.title), content.index(loan.title))

    def test_homepage_uses_only_featured_published_products(self):
        savings_category = ProductCategory.objects.create(
            name="Simpanan",
            slug="simpanan",
            sort_order=10,
        )
        loan_category = ProductCategory.objects.create(
            name="Pinjaman",
            slug="pinjaman",
            sort_order=20,
        )
        featured = make_product(
            title="Homepage Product",
            category=savings_category,
            is_featured=True,
            menu_description="Short product menu copy.",
        )
        loan = make_product(
            title="Homepage Loan",
            category=loan_category,
            is_featured=True,
            menu_description="Short loan menu copy.",
        )
        regular = make_product(title="Listing Only Product", is_featured=False)
        hidden = make_product(title="Hidden Homepage Product", is_featured=True, is_published=False)

        response = self.client.get(reverse("landing"))

        homepage_products = list(response.context["featured_products"])
        self.assertIn(featured, homepage_products)
        self.assertIn(loan, homepage_products)
        self.assertNotIn(regular, homepage_products)
        self.assertNotIn(hidden, homepage_products)
        self.assertEqual(list(response.context["featured_savings"]), [featured])
        self.assertEqual(list(response.context["featured_loans"]), [loan])
        self.assertContains(response, featured.menu_description)
        self.assertContains(response, loan.menu_description)
        self.assertContains(response, "data-home-products-carousel")
        self.assertContains(response, "1 Simpanan")
        self.assertContains(response, "1 Pinjaman")
        self.assertContains(response, 'data-nav-products="savings"')
        self.assertContains(response, 'data-nav-products="loans"')

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
        images = {
            key: image
            for key in (
                "wajib",
                "sukarela",
                "berjangka",
                "pokok",
                "lain",
                "pinjaman-reguler",
                "pinjaman-usaha",
            )
        }
        with patch.object(SeedCommand, "_ensure_images", return_value=images):
            call_command("seed_product_showcase")
            call_command("seed_product_showcase")

        expected_slugs = [
            "simpanan-wajib",
            "simpanan-sukarela",
            "simpanan-berjangka",
            "simpanan-pokok",
            "simpanan-lain",
            "pinjaman-reguler",
            "pinjaman-usaha-produktif",
        ]
        self.assertEqual(Product.objects.filter(slug__in=expected_slugs).count(), 7)
        self.assertEqual(ProductSimulation.objects.count(), 7)

        wajib = ProductSimulation.objects.get(product__slug="simpanan-wajib")
        self.assertTrue(wajib.is_enabled)
        self.assertEqual(wajib.strategy, ProductSimulation.Strategy.SAVINGS_RECURRING)
        self.assertEqual(wajib.amount_default, 0)
        self.assertEqual(wajib.recurring_default, 100000)
        wajib_result = simulate(
            wajib,
            {"amount": "0", "tenor_months": "12", "recurring_amount": "100000"},
        )
        self.assertEqual(wajib_result["summary"]["total_contributions"], "1200000.00")
        self.assertEqual(wajib_result["summary"]["gross_interest"], "0.00")

        berjangka = ProductSimulation.objects.get(product__slug="simpanan-berjangka")
        self.assertTrue(berjangka.is_enabled)
        self.assertEqual(berjangka.rate_mode, ProductSimulation.RateMode.TIERED)
        self.assertEqual(berjangka.rate_tiers.count(), 6)
        self.assertEqual(
            berjangka.fee_rules.filter(category=SimulationFeeRule.Category.TAX).count(),
            1,
        )
        berjangka_result = simulate(
            berjangka,
            {"amount": "10000000", "tenor_months": "12"},
        )
        self.assertEqual(berjangka_result["summary"]["gross_interest"], "525000.00")
        self.assertEqual(berjangka_result["summary"]["total_tax"], "105000.00")
        self.assertEqual(berjangka_result["summary"]["maturity_balance"], "10420000.00")

        pokok = ProductSimulation.objects.get(product__slug="simpanan-pokok")
        self.assertFalse(pokok.is_enabled)
        self.assertFalse(pokok.show_chart)
        self.assertTrue(pokok.is_ready)

        regular = ProductSimulation.objects.get(product__slug="pinjaman-reguler")
        self.assertEqual(regular.strategy, ProductSimulation.Strategy.LOAN_FLAT)
        self.assertEqual(regular.fee_rules.count(), 0)
        regular_result = simulate(regular, {"amount": "12000000", "tenor_months": "12"})
        self.assertEqual(regular_result["summary"]["total_interest"], "1440000.00")
        self.assertEqual(regular_result["summary"]["installment_min"], "1120000.00")
        self.assertEqual(regular_result["summary"]["installment_max"], "1120000.00")
        self.assertEqual(regular_result["summary"]["total_scheduled_payment"], "13440000.00")

        productive = ProductSimulation.objects.get(product__slug="pinjaman-usaha-produktif")
        self.assertEqual(productive.strategy, ProductSimulation.Strategy.LOAN_ANNUITY)
        self.assertEqual(productive.rate_application, ProductSimulation.RateApplication.PROGRESSIVE)
        self.assertEqual(productive.rate_tiers.count(), 3)
        self.assertEqual(productive.fee_rules.count(), 4)
        self.assertEqual(productive.breakdown_bands.count(), 3)
        productive_result = simulate(productive, {"amount": "250000000", "tenor_months": "36"})
        self.assertEqual(productive_result["summary"]["net_disbursed"], "246650000.00")
        self.assertEqual(productive_result["summary"]["total_principal"], "250000000.00")
        self.assertEqual(productive_result["summary"]["total_fees"], "3890000.00")
        self.assertEqual(len(productive_result["applied_rules"]["rates"]), 3)
        self.assertEqual(productive_result["breakdown"][-1]["closing_balance"], "0.00")
        self.assertEqual(productive_result["metadata"]["breakdown_interval_months"], 3)

    def test_dedicated_simulator_seed_updates_existing_products_without_images(self):
        products = [
            make_product(title=title, slug=slug)
            for title, slug in (
                ("Simpanan Wajib", "simpanan-wajib"),
                ("Simpanan Sukarela", "simpanan-sukarela"),
                ("Simpanan Berjangka", "simpanan-berjangka"),
                ("Simpanan Pokok", "simpanan-pokok"),
                ("Simpanan Lain", "simpanan-lain"),
                ("Pinjaman Reguler", "pinjaman-reguler"),
                ("Pinjaman Usaha Produktif", "pinjaman-usaha-produktif"),
            )
        ]

        call_command("seed_product_simulators", "--strict")
        call_command("seed_product_simulators", "--strict")

        self.assertEqual(ProductSimulation.objects.filter(product__in=products).count(), 7)
        self.assertEqual(
            ProductSimulation.objects.get(product__slug="simpanan-lain").tenor_options,
            [12, 24, 36, 60, 120],
        )
