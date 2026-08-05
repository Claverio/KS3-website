from django.test import TestCase
from django.urls import reverse

from _p2p.models import P2PSEOSettings


class P2PListPageSettingsTests(TestCase):
    def test_list_heading_and_intro_are_managed_by_wagtail_settings(self):
        settings = P2PSEOSettings.load()
        settings.list_heading = "Proyek Anggota Pilihan"
        settings.list_intro = "Pendanaan pilihan khusus anggota KS3."
        settings.save()

        response = self.client.get(reverse("p2p_list"))

        self.assertContains(response, "Proyek Anggota Pilihan")
        self.assertContains(response, "Pendanaan pilihan khusus anggota KS3.")
        self.assertNotContains(
            response,
            "Danai proyek pilihan dan dapatkan imbal hasil yang kompetitif.",
        )
