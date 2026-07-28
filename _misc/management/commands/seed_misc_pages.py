"""Seed useful demonstration pages below /halaman/ for each Wagtail Site."""

from io import BytesIO
from urllib.request import Request, urlopen
import uuid

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image as PillowImage
from wagtail.images import get_image_model
from wagtail.models import Collection, Site

from _misc.models import MiscellaneousIndexPage, MiscellaneousPage


IMAGE_SPECS = {
    "about": ("KS3 Page - Tentang Kami", "005DAA", "Tentang+Koperasi+KS3"),
    "guide": ("KS3 Page - Panduan Anggota", "147D64", "Panduan+Keanggotaan"),
    "policy": ("KS3 Page - Kebijakan", "5B6475", "Kebijakan+dan+Ketentuan"),
}


def block(block_type, value=None):
    return {"type": block_type, "value": value, "id": str(uuid.uuid4())}


def heading(title, level="h3"):
    return block("heading", {"level": level, "title": title})


def paragraph(html):
    return block("paragraph", {"content": html})


def callout():
    return block("callout", {"tone": "info", "title": "Konten demonstrasi", "content": "<p>Halaman ini berisi contoh struktur dan copy untuk kebutuhan presentasi. Redaksi final akan ditinjau dan disetujui bersama tim KS3 sebelum digunakan sebagai informasi resmi.</p>"})


def page_specs(images):
    return [
        {
            "title": "Tentang Kami", "slug": "tentang-kami", "intro": "Mengenal Koperasi KS3, tujuan, dan pendekatan layanan keuangan digital bagi anggota.", "menu": "Mengenal Koperasi KS3.", "main": True, "header": False, "footer": False, "order": 10,
            "content": [callout(), heading("Koperasi yang tumbuh bersama anggota", "h2"), paragraph("<p>KS3 hadir untuk membantu anggota mengelola simpanan sekaligus membuka akses pembiayaan yang lebih terstruktur bagi pelaku UMKM. Pendekatan digital digunakan untuk membuat informasi lebih mudah diakses dan dipantau.</p>"), block("image_text", {"image": images["about"].pk, "image_position": "right", "title": "Berorientasi pada kebutuhan nyata", "content": "<p>Layanan dikembangkan dengan fokus pada kemudahan anggota, tata kelola, dan dampak ekonomi bagi usaha produktif.</p>"}), heading("Prinsip layanan"), block("list", {"style": "unordered", "items": ["Transparan dalam menyampaikan informasi", "Praktis melalui dukungan layanan digital", "Bertanggung jawab dalam pengelolaan", "Berorientasi pada pertumbuhan anggota dan UMKM"]}), block("blockquote", {"quote": "<p>Membangun ekosistem koperasi yang relevan, mudah diakses, dan bertumbuh bersama anggotanya.</p>", "author": "Contoh visi KS3"})],
        },
        {
            "title": "FAQ", "slug": "faq", "intro": "Jawaban ringkas untuk pertanyaan umum mengenai keanggotaan, simpanan, dan layanan KS3.", "menu": "Pertanyaan umum KS3.", "main": True, "header": False, "footer": False, "order": 20,
            "content": [callout(), heading("Pertanyaan yang sering diajukan", "h2"), block("accordion", {"items": [{"title": "Siapa yang dapat menjadi anggota KS3?", "content": "<p>Persyaratan keanggotaan final mengikuti kebijakan dan proses verifikasi KS3.</p>"}, {"title": "Bagaimana cara melihat produk simpanan?", "content": "<p>Informasi produk tersedia melalui menu Produk. Setiap detail produk akan memuat manfaat dan ketentuan setelah disetujui.</p>"}, {"title": "Bagaimana cara menghubungi tim KS3?", "content": "<p>Gunakan email atau WhatsApp resmi yang tercantum pada header dan footer website.</p>"}, {"title": "Apakah informasi pada website sudah final?", "content": "<p>Konten yang diberi label demonstrasi masih akan melalui proses diskusi dan persetujuan.</p>"}]}), heading("Masih punya pertanyaan?"), paragraph("<p>Tim KS3 siap membantu melalui kanal kontak resmi pada jam operasional yang tercantum di website.</p>")],
        },
        {
            "title": "Panduan Keanggotaan", "slug": "panduan-keanggotaan", "intro": "Gambaran tahapan pendaftaran dan aktivasi anggota KS3.", "menu": "Cara menjadi anggota.", "main": False, "header": True, "footer": False, "order": 30,
            "content": [callout(), block("image", {"image": images["guide"].pk, "alt_text": "Ilustrasi panduan keanggotaan KS3", "caption": "Alur contoh pendaftaran anggota."}), heading("Tahapan menjadi anggota", "h2"), block("list", {"style": "ordered", "items": ["Mengisi data pendaftaran", "Melengkapi dokumen identitas", "Menjalani verifikasi", "Menyelesaikan Simpanan Pokok", "Menerima konfirmasi aktivasi"]}), block("two_column_text", {"left": "<p><strong>Siapkan data</strong><br/>Pastikan nama, nomor kontak, dan dokumen identitas dapat diverifikasi.</p>", "right": "<p><strong>Gunakan kanal resmi</strong><br/>Hindari membagikan informasi sensitif melalui kanal yang tidak tercantum di website KS3.</p>"}), block("accordion", {"items": [{"title": "Berapa lama proses verifikasi?", "content": "<p>Durasi final akan mengikuti kelengkapan data dan prosedur operasional KS3.</p>"}, {"title": "Apa yang dilakukan setelah aktif?", "content": "<p>Anggota dapat mengakses informasi produk dan layanan sesuai hak keanggotaan.</p>"}]})],
        },
        {
            "title": "Kebijakan Privasi", "slug": "kebijakan-privasi", "intro": "Contoh struktur kebijakan mengenai pengumpulan, penggunaan, dan perlindungan data.", "menu": "Perlindungan data pengguna.", "main": False, "header": False, "footer": True, "order": 40,
            "content": [callout(), block("image_text", {"image": images["policy"].pk, "image_position": "left", "title": "Perlindungan data anggota", "content": "<p>Data digunakan untuk mendukung proses layanan, verifikasi, komunikasi, dan pemenuhan kewajiban yang berlaku.</p>"}), heading("Data yang dapat diproses"), block("list", {"style": "unordered", "items": ["Data identitas dan kontak", "Data keanggotaan", "Riwayat interaksi dan transaksi", "Data teknis penggunaan layanan"]}), heading("Penggunaan dan keamanan"), paragraph("<p>KS3 menerapkan kontrol akses dan prosedur operasional untuk menjaga kerahasiaan data. Redaksi kebijakan final akan menjelaskan dasar pemrosesan, masa retensi, pihak penerima data, serta hak pengguna.</p>"), heading("Hak pengguna"), paragraph("<p>Pengguna dapat mengajukan pertanyaan atau permintaan terkait data melalui kanal kontak resmi, sesuai ketentuan yang berlaku.</p>")],
        },
        {
            "title": "Syarat dan Ketentuan", "slug": "syarat-dan-ketentuan", "intro": "Contoh kerangka ketentuan penggunaan website dan layanan digital KS3.", "menu": "Ketentuan layanan KS3.", "main": False, "header": False, "footer": True, "order": 50,
            "content": [callout(), heading("Penggunaan layanan", "h2"), paragraph("<p>Dengan menggunakan website, pengguna menyetujui untuk memberikan informasi yang benar, menjaga keamanan akses, dan menggunakan layanan sesuai tujuan yang sah.</p>"), heading("Informasi produk"), paragraph("<p>Informasi pada website tidak menggantikan perjanjian atau dokumen produk resmi. Apabila terdapat perbedaan, ketentuan pada dokumen yang telah disetujui para pihak akan berlaku.</p>"), heading("Tanggung jawab pengguna"), block("list", {"style": "unordered", "items": ["Menjaga kerahasiaan informasi akses", "Memastikan data yang diberikan akurat", "Membaca dokumen produk sebelum mengambil keputusan", "Menghubungi kanal resmi jika menemukan aktivitas mencurigakan"]}), block("separator"), paragraph("<p>Versi final halaman ini perlu ditinjau oleh tim legal dan operasional KS3.</p>")],
        },
    ]


class Command(BaseCommand):
    help = "Seed /halaman/ and useful demonstration MiscellaneousPages for each Wagtail Site."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Reset the seeded pages to canonical demo content.")

    def handle(self, *args, **options):
        images = self._ensure_images()
        specs = page_specs(images)
        for site in Site.objects.select_related("root_page"):
            index = MiscellaneousIndexPage.objects.child_of(site.root_page).filter(slug="halaman").first()
            if index is None:
                index = MiscellaneousIndexPage(title="Halaman", slug="halaman")
                site.root_page.add_child(instance=index)
            index.title = "Halaman"
            index.introduction = "Informasi penting mengenai layanan, keanggotaan, dan kebijakan KS3."
            index.save_revision().publish()
            for spec in specs:
                page = MiscellaneousPage.objects.child_of(index).filter(slug=spec["slug"]).first()
                if page is None:
                    page = MiscellaneousPage(
                        title=spec["title"],
                        slug=spec["slug"],
                        introduction=spec["intro"],
                        menu_description=spec["menu"],
                        content=spec["content"],
                        show_on_main_menu=spec["main"],
                        show_on_header=spec["header"],
                        show_on_footer=spec["footer"],
                        menu_order=spec["order"],
                    )
                    index.add_child(instance=page)
                elif not options["reset"]:
                    if page.menu_description != spec["menu"]:
                        page.menu_description = spec["menu"]
                        page.save_revision().publish()
                    self.stdout.write(f"  reused /halaman/{spec['slug']}/")
                    continue
                page.title = spec["title"]
                page.introduction = spec["intro"]
                page.menu_description = spec["menu"]
                page.content = spec["content"]
                page.show_on_main_menu = spec["main"]
                page.show_on_header = spec["header"]
                page.show_on_footer = spec["footer"]
                page.menu_order = spec["order"]
                page.save_revision().publish()
                self.stdout.write(f"  published /halaman/{spec['slug']}/")
        self.stdout.write(self.style.SUCCESS(f"Miscellaneous showcase ready for {Site.objects.count()} Site(s)."))

    def _ensure_images(self):
        collection = Collection.objects.filter(name="KS3 Pages").first()
        if collection is None:
            collection = Collection.get_first_root_node().add_child(name="KS3 Pages")
        Image = get_image_model()
        result = {}
        for key, (title, color, text) in IMAGE_SPECS.items():
            image = Image.objects.filter(title=title).first()
            if image is None:
                url = f"https://placehold.co/1400x800/{color}/FFFFFF/png?text={text}"
                try:
                    with urlopen(Request(url, headers={"User-Agent": "KS3-Misc-Seeder/1.0"}), timeout=30) as response:
                        payload = response.read()
                except Exception as exc:
                    raise CommandError(f"Could not download {url}: {exc}") from exc
                with PillowImage.open(BytesIO(payload)) as source:
                    width, height = source.size
                image = Image(title=title, collection=collection, file_size=len(payload))
                image.file.save(f"ks3-page-{key}.png", ContentFile(payload), save=False)
                image.width, image.height = width, height
                image.save()
                self.stdout.write(f"  uploaded {image.file.name}")
            else:
                self.stdout.write(f"  reused {image.file.name}")
            result[key] = image
        return result
