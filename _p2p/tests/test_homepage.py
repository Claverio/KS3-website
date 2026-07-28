from django.test import TestCase
from django.urls import reverse

from _p2p.tests.factories import make_project


class HomepageP2PCardTests(TestCase):
    def test_featured_project_uses_live_project_card_and_detail_link(self):
        project = make_project(is_featured=True, title="Project Pilihan Dinamis")

        response = self.client.get(reverse("landing"))

        self.assertContains(response, project.title)
        self.assertContains(response, project.get_absolute_url(), count=2)
        self.assertTemplateUsed(response, "cms/components/p2p_card.html")

    def test_unfeatured_project_is_not_rendered_on_homepage(self):
        project = make_project(is_featured=False, title="Bukan Project Pilihan")

        response = self.client.get(reverse("landing"))

        self.assertNotContains(response, project.title)
