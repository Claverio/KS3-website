from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase


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
