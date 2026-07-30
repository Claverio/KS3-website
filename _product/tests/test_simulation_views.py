from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from _product.models import ProductSimulation
from _product.tests.factories import make_product, make_simulation


class SimulationPageIntegrationTests(TestCase):
    def test_product_without_simulator_does_not_render_component_or_assets(self):
        product = make_product()

        response = self.client.get(product.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-simulator")
        self.assertNotContains(response, "product-simulator.js")
        self.assertNotContains(response, "product-simulator.css")

    def test_disabled_simulator_is_not_rendered_and_endpoint_is_not_public(self):
        product = make_product()
        make_simulation(product=product, is_enabled=False)

        page = self.client.get(product.get_absolute_url())
        endpoint = self.client.get(reverse("product_simulation", args=[product.slug]), {"amount": 12000000, "tenor_months": 12})

        self.assertNotContains(page, "data-simulator")
        self.assertEqual(endpoint.status_code, 404)

    def test_enabled_but_incomplete_configuration_fails_closed(self):
        product = make_product()
        ProductSimulation.objects.create(
            product=product,
            is_enabled=True,
            product_kind=ProductSimulation.ProductKind.SAVINGS,
            strategy=ProductSimulation.Strategy.SAVINGS_SIMPLE,
        )

        page = self.client.get(product.get_absolute_url())
        endpoint = self.client.get(reverse("product_simulation", args=[product.slug]), {"amount": 12000000, "tenor_months": 12})

        self.assertNotContains(page, "data-simulator")
        self.assertEqual(endpoint.status_code, 404)

    def test_incomplete_tier_coverage_is_not_rendered(self):
        product = make_product()
        profile = make_simulation(
            product=product,
            rate_mode=ProductSimulation.RateMode.TIERED,
            base_annual_rate=None,
        )
        profile.rate_tiers.create(label="Partial", min_amount=0, max_amount=5000000, annual_rate=4)

        page = self.client.get(product.get_absolute_url())
        endpoint = self.client.get(reverse("product_simulation", args=[product.slug]), {"amount": 12000000, "tenor_months": 12})

        self.assertNotContains(page, "data-simulator")
        self.assertEqual(endpoint.status_code, 404)

    def test_ready_simulator_renders_fully_wired_component(self):
        product = make_product(title="Simpanan Berjangka")
        make_simulation(product=product)

        response = self.client.get(product.get_absolute_url())

        self.assertContains(response, "data-simulator")
        self.assertContains(response, reverse("product_simulation", args=[product.slug]))
        self.assertContains(response, "product-simulator.js")
        self.assertContains(response, "product-simulator.css")
        self.assertContains(response, 'name="amount"')
        self.assertContains(response, 'name="tenor_months"')
        self.assertContains(response, "product-simulation-config")
        self.assertContains(response, "Grafik pertumbuhan")
        self.assertContains(response, "ks3-simulator__chart-scroll")
        self.assertContains(response, "Rincian periode")
        self.assertNotContains(response, "bi-stars")

    def test_recurring_input_only_renders_for_recurring_strategy(self):
        normal_product = make_product(title="Normal")
        recurring_product = make_product(title="Recurring")
        make_simulation(product=normal_product)
        make_simulation(
            product=recurring_product,
            strategy=ProductSimulation.Strategy.SAVINGS_RECURRING,
            recurring_min=Decimal("100000"),
            recurring_max=Decimal("1000000"),
            recurring_default=Decimal("100000"),
            recurring_step=Decimal("100000"),
        )

        normal = self.client.get(normal_product.get_absolute_url())
        recurring = self.client.get(recurring_product.get_absolute_url())

        self.assertNotContains(normal, 'name="recurring_amount"')
        self.assertContains(recurring, 'name="recurring_amount"')

    def test_optional_chart_and_table_render_independently(self):
        product = make_product()
        profile = make_simulation(product=product, show_chart=False, show_table=True)

        table_only = self.client.get(product.get_absolute_url())
        self.assertNotContains(table_only, "data-simulator-chart")
        self.assertContains(table_only, "data-breakdown-body")

        profile.show_chart = True
        profile.show_table = False
        profile.save()
        chart_only = self.client.get(product.get_absolute_url())
        self.assertContains(chart_only, "data-simulator-chart")
        self.assertNotContains(chart_only, "data-breakdown-body")

    def test_unpublished_product_simulator_is_not_accessible(self):
        product = make_product(is_published=False)
        make_simulation(product=product)

        response = self.client.get(reverse("product_simulation", args=[product.slug]), {"amount": 12000000, "tenor_months": 12})

        self.assertEqual(response.status_code, 404)

    def test_product_preview_includes_ready_simulator(self):
        product = make_product(is_published=False)
        make_simulation(product=product)
        request = RequestFactory().get("/admin/preview/")

        response = product.serve_preview(request, product.default_preview_mode)
        response.render()

        self.assertContains(response, "data-simulator")


class SimulationEndpointTests(TestCase):
    def setUp(self):
        self.product = make_product(title="Pinjaman Usaha")
        self.profile = make_simulation(
            product=self.product,
            product_kind=ProductSimulation.ProductKind.LOAN,
            strategy=ProductSimulation.Strategy.LOAN_ANNUITY,
        )
        self.url = reverse("product_simulation", args=[self.product.slug])

    def test_valid_request_returns_complete_contract(self):
        response = self.client.get(self.url, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"metadata", "inputs", "applied_rules", "summary", "breakdown", "chart"})
        self.assertEqual(body["metadata"]["product_kind"], "loan")
        self.assertEqual(body["metadata"]["strategy"], "loan_annuity")
        self.assertEqual(body["summary"]["total_principal"], "12000000.00")
        self.assertEqual(body["breakdown"][-1]["closing_balance"], "0.00")
        self.assertTrue(body["chart"])

    def test_invalid_request_returns_field_errors(self):
        response = self.client.get(self.url, {"amount": "not-money", "tenor_months": "999"})

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["error"], "Data simulasi tidak valid.")
        self.assertIn("amount", body["errors"])
        self.assertIn("tenor_months", body["errors"])

    def test_endpoint_is_read_only(self):
        response = self.client.post(self.url, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(response.status_code, 405)

    def test_configuration_version_is_returned_for_auditability(self):
        response = self.client.get(self.url, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(response.json()["metadata"]["configuration_version"], self.profile.updated_at.isoformat())


class SimulationAdminIntegrationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="simulation-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_simulator_listing_loads_and_shows_readiness(self):
        profile = make_simulation()
        url = reverse("wagtailsnippets__product_productsimulation:list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, profile.product.title)
        self.assertContains(response, "Siap")

    def test_simulator_editor_exposes_all_assistive_sections(self):
        profile = make_simulation()
        url = reverse("wagtailsnippets__product_productsimulation:edit", args=[profile.pk])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        for label in ("Setup", "Input anggota", "Bunga", "Biaya &amp; pajak", "Display", "Advanced"):
            self.assertContains(response, label)
        self.assertContains(response, "Tier bunga")
        self.assertContains(response, "Biaya, pajak, dan potongan")
