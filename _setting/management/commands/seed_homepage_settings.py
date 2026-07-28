"""Seed current homepage content and move editable imagery into Wagtail storage."""

from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image as PillowImage
from wagtail.images import get_image_model
from wagtail.models import Collection, Site

from _setting.models import HomePageSetting


IMAGE_SPECS = {
    "hero_background": {"title": "KS3 Homepage - Hero Background", "static": "cms/images/main-hero-bg.webp"},
    "products_background": {"title": "KS3 Homepage - Products Background", "static": "cms/images/service-bg.webp"},
    "hero_decorative": {"title": "KS3 Homepage - Hero Decoration", "url": "https://placehold.co/81x90/png", "filename": "hero-decoration.png"},
    "hero_main": {"title": "KS3 Homepage - Hero Main", "url": "https://placehold.co/975x725/png", "filename": "hero-main.png"},
    "about_primary": {"title": "KS3 Homepage - About Primary", "url": "https://placehold.co/470x566/png", "filename": "about-primary.png"},
    "about_secondary": {"title": "KS3 Homepage - About Secondary", "url": "https://placehold.co/350x419/png", "filename": "about-secondary.png"},
    "advantages": {"title": "KS3 Homepage - Advantages", "url": "https://placehold.co/542x606/png", "filename": "advantages.png"},
    "faq": {"title": "KS3 Homepage - FAQ Support", "url": "https://placehold.co/156x113/png", "filename": "faq-support.png"},
    "app": {"title": "KS3 Homepage - App Preview", "url": "https://placehold.co/600x1240/png", "filename": "app-preview.png"},
}


class Command(BaseCommand):
    help = "Create per-Site homepage settings using the current homepage as canonical content."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-content",
            action="store_true",
            help="Reset every Site homepage setting to the canonical current content.",
        )

    def handle(self, *args, **options):
        images = self._ensure_images()
        for site in Site.objects.all():
            if options["reset_content"]:
                HomePageSetting.objects.filter(site=site).delete()
            setting, created = HomePageSetting.objects.get_or_create(site=site)
            setting.hero_background_image = images["hero_background"]
            setting.products_background_image = images["products_background"]
            setting.hero_decorative_image = images["hero_decorative"]
            setting.hero_main_image = images["hero_main"]
            setting.about_primary_image = images["about_primary"]
            setting.about_secondary_image = images["about_secondary"]
            setting.advantages_image = images["advantages"]
            setting.faq_support_image = images["faq"]
            setting.app_first_image = images["app"]
            setting.app_second_image = images["app"]
            setting.save()
            action = "created" if created else "updated"
            self.stdout.write(f"  {action} homepage settings for {site.hostname}:{site.port}")
        self.stdout.write(self.style.SUCCESS(
            f"Homepage settings ready for {Site.objects.count()} Site(s) with {len(images)} storage-backed images."
        ))

    def _ensure_images(self):
        collection = Collection.objects.filter(name="KS3 Homepage").first()
        if collection is None:
            collection = Collection.get_first_root_node().add_child(name="KS3 Homepage")
        Image = get_image_model()
        result = {}
        for key, spec in IMAGE_SPECS.items():
            image = Image.objects.filter(title=spec["title"]).first()
            if image is None:
                payload, filename = self._load_payload(spec)
                with PillowImage.open(BytesIO(payload)) as source:
                    width, height = source.size
                image = Image(title=spec["title"], collection=collection, file_size=len(payload))
                image.file.save(f"ks3-homepage-{filename}", ContentFile(payload), save=False)
                image.width = width
                image.height = height
                image.save()
                self.stdout.write(f"  uploaded {image.file.name}")
            else:
                self.stdout.write(f"  reused {image.file.name}")
            result[key] = image
        return result

    def _load_payload(self, spec):
        if "static" in spec:
            source_path = finders.find(spec["static"])
            if not source_path:
                raise CommandError(f"Static homepage image not found: {spec['static']}")
            path = Path(source_path)
            return path.read_bytes(), path.name
        request = Request(spec["url"], headers={"User-Agent": "KS3-Homepage-Seeder/1.0"})
        try:
            with urlopen(request, timeout=30) as response:
                return response.read(), spec["filename"]
        except Exception as exc:
            raise CommandError(f"Could not download {spec['url']}: {exc}") from exc
