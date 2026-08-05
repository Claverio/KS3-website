from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import RequestFactory, TestCase
from django.utils import timezone
from wagtail.admin.menu import admin_menu, settings_menu

from _p2p.models import P2PPurchase
from _p2p.tests.factories import make_project, make_purchase
from _product.tests.factories import make_product


class WagtailAdminBrandingTests(TestCase):
    def test_login_uses_ks3_branding(self):
        response = self.client.get("/admin/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Masuk ke KS3 Admin")
        self.assertContains(response, "logo-koperasi-horizontal.svg")
        self.assertContains(response, "logo-koperasi-mark.svg")
        self.assertContains(response, "ks3-wagtail-admin.css")

    def test_authenticated_admin_uses_ks3_sidebar_branding(self):
        user = get_user_model().objects.create_superuser(
            username="branding-admin",
            email="branding@example.com",
            password="secret",
        )
        self.client.force_login(user)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "KS3 Admin")
        self.assertContains(response, "logo-koperasi-vertical.svg")
        self.assertContains(response, "logo-koperasi-mark.svg")
        self.assertContains(response, "ks3-wagtail-admin.css")

    def test_admin_stylesheet_is_collectable(self):
        self.assertIsNotNone(finders.find("cms/css/ks3-wagtail-admin.css"))

    def test_public_home_uses_ks3_mark_favicon(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "logo-koperasi-mark.svg")


class KS3AdminDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="operations-admin",
            email="operations@example.com",
            password="secret",
        )
        self.client.force_login(self.user)
        self.project = make_project(title="Pendanaan Kopi Dashboard")
        self.purchase = make_purchase(
            project=self.project,
            full_name="Pembeli Dashboard",
            status=P2PPurchase.Status.PAID,
            paid_at=timezone.now(),
        )

    def test_home_is_operational_dashboard(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Proyek sedang berjalan")
        self.assertContains(response, "Pendanaan Kopi Dashboard")
        self.assertContains(response, "Pembeli Dashboard")
        self.assertContains(response, "20 TERBARU")
        self.assertContains(response, "/admin/global-search/")

    def test_global_search_combines_operational_and_content_models(self):
        make_product(title="Produk Kopi Anggota", summary="Tabungan usaha kopi")

        project_response = self.client.get(
            "/admin/global-search/", {"q": "Kopi"}
        )
        buyer_response = self.client.get(
            "/admin/global-search/", {"q": "Pembeli Dashboard"}
        )

        self.assertEqual(project_response.status_code, 200)
        self.assertContains(project_response, "Pendanaan Kopi Dashboard")
        self.assertContains(project_response, "Produk Kopi Anggota")
        self.assertContains(buyer_response, self.purchase.booking_number)
        self.assertContains(buyer_response, "Transaksi Proyek")

    def test_sidebar_hides_unused_items_and_groups_homepage_settings(self):
        request = RequestFactory().get("/admin/")
        request.user = self.user
        main_items = admin_menu.menu_items_for_request(request)
        settings_items = settings_menu.menu_items_for_request(request)

        self.assertFalse(
            {"images", "documents", "help"} & {item.name for item in main_items}
        )
        self.assertFalse(
            {"homepage-setting", "redirects", "collections", "workflows", "workflow-tasks"}
            & {item.name for item in settings_items}
        )
        general = next(item for item in main_items if item.name == "general-settings")
        self.assertIn(
            "homepage",
            {item.name for item in general.menu.menu_items_for_request(request)},
        )
        custom_page = next(item for item in main_items if item.name == "custom-page")
        self.assertEqual(custom_page.label, "Custom Page")
        self.assertEqual(custom_page.url, "/admin/pages/4/")
