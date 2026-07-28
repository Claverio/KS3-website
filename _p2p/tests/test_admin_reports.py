from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from _p2p.models import P2PPurchase
from _p2p.tests.factories import make_project, make_purchase


class P2PAdminReportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="report-admin",
            email="admin@example.com",
            password="secret",
        )
        self.client.force_login(self.user)
        self.project = make_project(title="Project Laporan")
        self.other_project = make_project(title="Project Lain")
        self.paid_purchase = make_purchase(
            project=self.project,
            full_name="Pembeli Project Ini",
            email="project-ini@example.com",
            slot_quantity=2,
            subtotal=Decimal("200000"),
            total_amount=Decimal("202750"),
            status=P2PPurchase.Status.PAID,
            paid_at=timezone.now(),
        )
        make_purchase(
            project=self.other_project,
            full_name="Pembeli Project Lain",
            email="project-lain@example.com",
        )

    def test_project_edit_has_purchase_and_graph_tabs_with_scoped_data(self):
        response = self.client.get(
            reverse("wagtailsnippets__p2p_p2p:edit", args=[self.project.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pembelian")
        self.assertContains(response, "Grafik")
        self.assertContains(response, "Pembeli Project Ini")
        self.assertNotContains(response, "Pembeli Project Lain")
        self.assertContains(response, "Progres terhadap target")
        self.assertContains(response, "Aktivitas transaksi")
        self.assertContains(response, "Top pembeli")
        self.assertContains(
            response,
            reverse("p2p_project_purchase_export", args=[self.project.pk]),
        )

    def test_project_purchase_export_is_scoped_and_complete(self):
        response = self.client.get(
            reverse("p2p_project_purchase_export", args=[self.project.pk])
        )
        csv_text = response.content.decode("utf-8-sig")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("Pembeli Project Ini", csv_text)
        self.assertIn("202750.00", csv_text)
        self.assertNotIn("Pembeli Project Lain", csv_text)

    def test_export_requires_report_permission(self):
        user = get_user_model().objects.create_user(
            username="without-report-access",
            password="secret",
            is_staff=True,
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("p2p_project_purchase_export", args=[self.project.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
