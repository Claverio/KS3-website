from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from wagtail.models import Site

from _p2p.tests.factories import make_project
from _product.tests.factories import make_product
from _setting.models import ContactAddress, ContactSetting, HomePageSetting


class HomePageSettingTests(TestCase):
    section_fields = (
        ("hero_enabled", "home-hero"),
        ("marquee_enabled", "home-marquee"),
        ("about_enabled", "home-about"),
        ("products_enabled", "home-products"),
        ("p2p_enabled", "home-p2p"),
        ("advantages_enabled", "home-advantages"),
        ("faq_enabled", "home-faq"),
        ("app_enabled", "home-app"),
    )

    def setUp(self):
        self.site = Site.objects.get(is_default_site=True)
        self.setting, _ = HomePageSetting.objects.get_or_create(site=self.site)

    def test_canonical_content_matches_existing_homepage(self):
        self.assertEqual(
            self.setting.hero_title,
            "Simpanan dan Pendanaan UMKM dalam Satu Ekosistem",
        )
        self.assertEqual(self.setting.p2p_title, "P2P Investment Pilihan")
        self.assertEqual(
            self.setting.products_title,
            "Simpanan dan Pinjaman untuk Setiap Kebutuhan",
        )
        self.assertEqual(len(self.setting.marquee_items), 6)
        self.assertEqual(len(self.setting.about_audiences), 2)
        self.assertEqual(len(self.setting.advantages_items), 3)
        self.assertEqual(len(self.setting.faq_items), 4)

    def test_wagtail_admin_home_renders_with_registered_settings(self):
        user = get_user_model().objects.create_superuser(
            username="admin-settings-test",
            email="admin@example.test",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)

    def test_footer_has_no_newsletter_form(self):
        response = self.client.get(reverse("landing"))

        self.assertNotContains(response, "Berlangganan Newsletter KS3")
        self.assertNotContains(response, "Masukkan email Anda")
        self.assertContains(response, "© 2026 KSP Sentra Solusi Sejahtera.")

    def test_footer_renders_multiple_contact_addresses_in_order(self):
        contact = ContactSetting.load()
        contact.addresses.all().delete()
        ContactAddress.objects.create(
            contact_setting=contact,
            name="Kantor Jakarta",
            address="Equity Tower, Jakarta",
            sort_order=0,
        )
        ContactAddress.objects.create(
            contact_setting=contact,
            name="Kantor Tangerang",
            address="Rukan Shibuya, Tangerang",
            sort_order=1,
        )

        response = self.client.get(reverse("landing"))
        body = response.content.decode()

        self.assertContains(response, "Kantor Jakarta")
        self.assertContains(response, "Equity Tower, Jakarta")
        self.assertContains(response, "Kantor Tangerang")
        self.assertContains(response, "Rukan Shibuya, Tangerang")
        self.assertLess(body.index("Kantor Jakarta"), body.index("Kantor Tangerang"))

    def test_contact_admin_separates_addresses_and_contact_channels_into_tabs(self):
        user = get_user_model().objects.create_superuser(
            username="admin-contact-settings-test",
            email="contact-admin@example.test",
            password="test-password",
        )
        self.client.force_login(user)
        contact = ContactSetting.load()

        response = self.client.get(
            reverse(
                "wagtailsnippets__setting_contactsetting:edit",
                args=[contact.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alamat Kantor")
        self.assertContains(response, "Email &amp; Operasional")
        self.assertContains(response, "WhatsApp")
        self.assertContains(response, "Tampilkan tombol WhatsApp melayang")
        self.assertContains(response, "Media Sosial")
        self.assertContains(response, "Tambah alamat kantor")

    def test_homepage_renders_all_sections_in_fixed_order(self):
        response = self.client.get(reverse("landing"))
        body = response.content.decode()

        positions = [body.index(f'id="{marker}"') for _, marker in self.section_fields]
        self.assertEqual(positions, sorted(positions))

    def test_each_section_can_be_disabled_independently(self):
        for field, marker in self.section_fields:
            with self.subTest(field=field):
                setattr(self.setting, field, False)
                self.setting.save(update_fields=[field])
                self.assertNotContains(self.client.get(reverse("landing")), f'id="{marker}"')
                setattr(self.setting, field, True)
                self.setting.save(update_fields=[field])

    def test_p2p_section_copy_is_editable_but_cards_stay_model_driven(self):
        project = make_project(is_featured=True, title="Live P2P Domain Card")
        self.setting.p2p_small_title = "Small P2P Copy"
        self.setting.p2p_title = "Custom P2P Heading"
        self.setting.p2p_description = "Custom P2P description."
        self.setting.save()

        response = self.client.get(reverse("landing"))

        self.assertContains(response, "Small P2P Copy")
        self.assertContains(response, "Custom P2P Heading")
        self.assertContains(response, "Custom P2P description.")
        self.assertContains(response, project.title)
        self.assertContains(response, project.get_absolute_url())

    def test_product_section_only_exposes_heading_copy_not_card_content(self):
        from _product.models import ProductCategory

        category = ProductCategory.objects.create(name="Simpanan", slug="simpanan")
        product = make_product(title="Simpanan Wajib", category=category, is_featured=True)
        self.setting.products_small_title = "Small Product Copy"
        self.setting.products_title = "Custom Product Heading"
        self.setting.products_description = "Custom Product description."
        self.setting.save()

        response = self.client.get(reverse("landing"))

        self.assertContains(response, "Small Product Copy")
        self.assertContains(response, "Custom Product Heading")
        self.assertContains(response, "Custom Product description.")
        self.assertContains(response, product.title)
        self.assertContains(response, product.get_absolute_url())

    def test_faq_uses_whatsapp_contact_without_legacy_support_block(self):
        contact = ContactSetting.load()
        contact.whatsapp_display = "+62 812-3456-7890"
        contact.whatsapp_link = "https://wa.me/6281234567890"
        contact.save()

        response = self.client.get(reverse("landing"))

        self.assertContains(response, contact.whatsapp_display)
        self.assertContains(response, contact.whatsapp_link)
        self.assertNotContains(response, "Tim kami siap membantu Anda")

    def test_whatsapp_floating_button_uses_contact_setting_link(self):
        contact = ContactSetting.load()
        contact.whatsapp_floating_enabled = True
        contact.whatsapp_link = "https://wa.me/6281234567890"
        contact.save()

        response = self.client.get(reverse("landing"))

        self.assertContains(response, 'class="ks3-whatsapp-float"')
        self.assertContains(response, f'href="{contact.whatsapp_link}"')
        self.assertContains(response, "Chat dengan KS3")

    def test_whatsapp_floating_button_can_be_disabled(self):
        contact = ContactSetting.load()
        contact.whatsapp_floating_enabled = False
        contact.whatsapp_link = "https://wa.me/6281234567890"
        contact.save()

        response = self.client.get(reverse("landing"))

        self.assertNotContains(response, 'class="ks3-whatsapp-float"')

    def test_whatsapp_floating_button_requires_a_link(self):
        contact = ContactSetting.load()
        contact.whatsapp_floating_enabled = True
        contact.whatsapp_link = ""
        contact.save()

        response = self.client.get(reverse("landing"))

        self.assertNotContains(response, 'class="ks3-whatsapp-float"')

    def test_settings_are_isolated_per_wagtail_site(self):
        other_site = Site.objects.create(
            hostname="client.example.test",
            port=80,
            root_page=self.site.root_page,
            site_name="Client Site",
        )
        HomePageSetting.objects.create(
            site=other_site,
            hero_title="Homepage khusus client",
        )

        default_response = self.client.get(reverse("landing"), HTTP_HOST=self.site.hostname)
        client_response = self.client.get(reverse("landing"), HTTP_HOST=other_site.hostname)

        self.assertNotContains(default_response, "Homepage khusus client")
        self.assertContains(client_response, "Homepage khusus client")
