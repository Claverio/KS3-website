"""Seed the current KS3 product catalogue with contextual demonstration content."""

from io import BytesIO
from urllib.request import Request, urlopen
import uuid

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image as PillowImage
from wagtail.images import get_image_model
from wagtail.models import Collection

from _product.models import Product, ProductCategory, ProductSEOSettings


IMAGE_SPECS = {
    "wajib": ("KS3 Product - Simpanan Wajib", "005DAA", "Simpanan+Wajib"),
    "sukarela": ("KS3 Product - Simpanan Sukarela", "147D64", "Simpanan+Sukarela"),
    "berjangka": ("KS3 Product - Simpanan Berjangka", "6C63FF", "Simpanan+Berjangka"),
    "pokok": ("KS3 Product - Simpanan Pokok", "FFAC0A", "Simpanan+Pokok"),
    "lain": ("KS3 Product - Simpanan Lain", "C84B31", "Simpanan+Lain"),
}


def block(block_type, value=None):
    return {"type": block_type, "value": value, "id": str(uuid.uuid4())}


def callout():
    return block("callout", {
        "tone": "warning",
        "title": "Konten contoh untuk diskusi",
        "content": "<p>Informasi pada halaman ini masih berupa contoh untuk demonstrasi CMS. Ketentuan, manfaat, biaya, dan mekanisme final akan disesuaikan setelah diskusi bersama tim KS3.</p>",
    })


def heading(title, level="h3"):
    return block("heading", {"level": level, "title": title})


def paragraph(html):
    return block("paragraph", {"content": html})


def item_list(items, style="unordered"):
    return block("list", {"style": style, "items": items})


def image_text(image, position, title, html):
    return block("image_text", {"image": image.pk, "image_position": position, "title": title, "content": html})


def table(title, columns, rows, note=""):
    return block("manual_table", {"title": title, "columns": columns, "rows": [{"cells": row} for row in rows], "footer_note": note})


def accordion(items):
    return block("accordion", {"items": [{"title": title, "content": content} for title, content in items]})


def product_specs(images):
    return [
        {
            "title": "Simpanan Wajib", "slug": "simpanan-wajib", "icon": "bi-wallet2", "image": images["wajib"],
            "summary": "Simpanan rutin yang dibayarkan setiap bulan selama menjadi anggota koperasi.", "menu": "Simpanan rutin bulanan.",
            "content": [callout(), heading("Komitmen rutin sebagai anggota", "h2"), paragraph("<p>Simpanan Wajib merupakan setoran berkala anggota yang mendukung permodalan dan keberlanjutan layanan koperasi. Besaran serta jadwal setoran mengikuti ketentuan keanggotaan yang berlaku.</p>"), image_text(images["wajib"], "right", "Mudah dipantau secara digital", "<p>Riwayat setoran dapat dipantau sehingga anggota memiliki catatan yang jelas dan teratur.</p>"), heading("Manfaat utama"), item_list(["Membantu membangun kebiasaan menyimpan secara rutin", "Mendukung kekuatan modal koperasi", "Tercatat sebagai bagian dari simpanan anggota", "Informasi transaksi dapat dipantau"]), table("Ilustrasi jadwal setoran", ["Periode", "Status", "Keterangan"], [["Bulan berjalan", "Terjadwal", "Mengikuti tanggal penagihan anggota"], ["Setelah pembayaran", "Tercatat", "Masuk ke riwayat simpanan"]], "Nominal dan tanggal pada implementasi final mengikuti kebijakan KS3."), accordion([("Apakah nominalnya sama untuk semua anggota?", "<p>Ketentuan nominal akan mengikuti kebijakan keanggotaan KS3 yang berlaku.</p>"), ("Di mana setoran dapat dipantau?", "<p>Mekanisme pemantauan akan disesuaikan dengan kanal layanan digital KS3.</p>")])],
        },
        {
            "title": "Simpanan Sukarela", "slug": "simpanan-sukarela", "icon": "bi-piggy-bank", "image": images["sukarela"],
            "summary": "Simpanan fleksibel yang dapat dilakukan anggota sesuai kemampuan dan kebutuhan.", "menu": "Fleksibel sesuai kebutuhan.",
            "content": [callout(), heading("Fleksibel mengikuti kebutuhan anggota", "h2"), paragraph("<p>Simpanan Sukarela dirancang sebagai pilihan penyimpanan dana tambahan di luar kewajiban rutin anggota. Anggota dapat menyesuaikan frekuensi dan nominal berdasarkan rencana keuangan masing-masing.</p>"), block("two_column_text", {"left": "<p><strong>Setoran fleksibel</strong><br/>Penambahan dana dapat dilakukan sesuai kemampuan anggota.</p>", "right": "<p><strong>Catatan transparan</strong><br/>Setiap transaksi tercatat dalam riwayat simpanan.</p>"}), image_text(images["sukarela"], "left", "Untuk kebutuhan jangka pendek maupun bertahap", "<p>Dapat digunakan untuk membangun dana cadangan atau target keuangan personal secara bertahap.</p>"), heading("Alur umum"), item_list(["Anggota menentukan nominal simpanan", "Dana disetorkan melalui kanal yang tersedia", "Transaksi diverifikasi dan tercatat", "Saldo dapat dipantau oleh anggota"], "ordered"), accordion([("Apakah ada minimum setoran?", "<p>Minimum setoran merupakan bagian dari ketentuan final yang akan dikonfirmasi oleh KS3.</p>"), ("Apakah dana dapat ditarik kapan saja?", "<p>Mekanisme penarikan mengikuti syarat produk dan proses verifikasi yang berlaku.</p>")])],
        },
        {
            "title": "Simpanan Berjangka", "slug": "simpanan-berjangka", "icon": "bi-calendar-check", "image": images["berjangka"],
            "summary": "Simpanan dengan pilihan tenor 3, 6, dan 12 bulan serta hasil yang kompetitif.", "menu": "Pilihan tenor terukur.",
            "content": [callout(), heading("Rencana simpanan dengan periode terukur", "h2"), paragraph("<p>Simpanan Berjangka membantu anggota menempatkan dana untuk jangka waktu tertentu. Pilihan tenor awal yang ditampilkan adalah <strong>3, 6, dan 12 bulan</strong>.</p>"), image_text(images["berjangka"], "right", "Pilih tenor sesuai rencana", "<p>Tenor yang berbeda dapat digunakan untuk menyesuaikan kebutuhan likuiditas dan tujuan keuangan anggota.</p>"), table("Pilihan tenor contoh", ["Tenor", "Karakteristik", "Cocok untuk"], [["3 bulan", "Jangka pendek", "Dana yang akan digunakan dalam waktu dekat"], ["6 bulan", "Jangka menengah", "Target keuangan bertahap"], ["12 bulan", "Jangka lebih panjang", "Perencanaan dana tahunan"]], "Imbal hasil dan ketentuan pencairan belum merupakan penawaran final."), heading("Sebelum memilih tenor"), item_list(["Pastikan dana tidak dibutuhkan selama periode simpanan", "Pelajari ketentuan pencairan sebelum jatuh tempo", "Konfirmasi perhitungan hasil dan biaya", "Simpan bukti transaksi dan dokumen produk"]), accordion([("Kapan hasil dibayarkan?", "<p>Jadwal pembayaran hasil akan mengikuti ketentuan produk final untuk setiap tenor.</p>"), ("Bisakah dicairkan lebih awal?", "<p>Pencairan lebih awal dapat memiliki ketentuan khusus yang akan dijelaskan dalam dokumen produk resmi.</p>")])],
        },
        {
            "title": "Simpanan Pokok", "slug": "simpanan-pokok", "icon": "bi-award", "image": images["pokok"],
            "summary": "Simpanan yang dibayarkan satu kali saat pertama kali menjadi anggota koperasi.", "menu": "Setoran awal keanggotaan.",
            "content": [callout(), heading("Bagian dari proses keanggotaan", "h2"), paragraph("<p>Simpanan Pokok merupakan setoran awal yang dibayarkan satu kali ketika seseorang resmi menjadi anggota koperasi. Pencatatannya melekat pada status keanggotaan sesuai ketentuan koperasi.</p>"), image_text(images["pokok"], "left", "Satu kali saat bergabung", "<p>Setoran dilakukan dalam proses aktivasi anggota dan diverifikasi bersama dokumen keanggotaan.</p>"), heading("Tahapan umum"), item_list(["Mengisi formulir pendaftaran anggota", "Melengkapi proses verifikasi identitas", "Membayar Simpanan Pokok", "Menerima konfirmasi keanggotaan"], "ordered"), block("blockquote", {"quote": "<p>Simpanan Pokok menandai partisipasi anggota dalam kepemilikan dan keberlanjutan koperasi.</p>", "author": "Contoh narasi keanggotaan KS3"}), accordion([("Apakah dibayar setiap bulan?", "<p>Tidak. Simpanan Pokok pada konsep ini dibayarkan satu kali ketika menjadi anggota.</p>"), ("Apakah nominalnya dapat berubah?", "<p>Nominal resmi mengikuti keputusan dan ketentuan koperasi yang berlaku.</p>")])],
        },
        {
            "title": "Simpanan Lain", "slug": "simpanan-lain", "icon": "bi-folder-plus", "image": images["lain"],
            "summary": "Alokasi dana mandiri untuk kebutuhan pendidikan, hari tua, rekreasi, dan tujuan lainnya.", "menu": "Untuk beragam tujuan.",
            "content": [callout(), heading("Satu tempat untuk berbagai tujuan", "h2"), paragraph("<p>Simpanan Lain menggambarkan pilihan alokasi dana berdasarkan tujuan personal anggota, seperti pendidikan, hari tua, rekreasi, atau kebutuhan terencana lainnya.</p>"), image_text(images["lain"], "right", "Buat tujuan yang lebih spesifik", "<p>Pemisahan tujuan membantu anggota melihat progres dan menjaga disiplin alokasi dana.</p>"), block("two_column_text", {"left": "<p><strong>Tujuan jangka menengah</strong><br/>Pendidikan, renovasi, atau pembelian terencana.</p>", "right": "<p><strong>Tujuan jangka panjang</strong><br/>Persiapan hari tua dan rencana keluarga.</p>"}), heading("Contoh kategori tujuan"), item_list(["Dana pendidikan", "Dana hari tua", "Dana rekreasi", "Dana pembelian terencana", "Tujuan personal lainnya"]), accordion([("Apakah setiap tujuan memiliki rekening terpisah?", "<p>Struktur pencatatan final akan disesuaikan dengan kapabilitas sistem dan kebijakan produk KS3.</p>"), ("Bisakah tujuan diubah?", "<p>Fleksibilitas perubahan tujuan akan dijelaskan pada ketentuan produk final.</p>")])],
        },
    ]


class Command(BaseCommand):
    help = "Seed five current KS3 products with contextual StreamField showcase content."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete all product data before seeding.")

    def handle(self, *args, **options):
        images = self._ensure_images()
        with transaction.atomic():
            if options["reset"]:
                Product.objects.all().delete()
                ProductCategory.objects.all().delete()
            category, _ = ProductCategory.objects.update_or_create(slug="simpanan", defaults={"name": "Simpanan", "is_active": True, "sort_order": 10})
            specs = product_specs(images)
            for order, spec in enumerate(specs, start=1):
                product, _ = Product.objects.update_or_create(
                    slug=spec["slug"],
                    defaults={
                        "category": category,
                        "title": spec["title"],
                        "summary": spec["summary"],
                        "menu_description": spec["menu"],
                        "icon": spec["icon"],
                        "card_image": spec["image"],
                        "content": spec["content"],
                        "is_featured": True,
                        "is_published": True,
                        "sort_order": order,
                    },
                )
                self.stdout.write(f"  [{order}/{len(specs)}] {product.title}")
            ProductSEOSettings.load()
        self.stdout.write(self.style.SUCCESS(f"Product showcase ready: {len(specs)} products and {len(images)} S3-backed images."))

    def _ensure_images(self):
        collection = Collection.objects.filter(name="KS3 Products").first()
        if collection is None:
            collection = Collection.get_first_root_node().add_child(name="KS3 Products")
        Image = get_image_model()
        result = {}
        for key, (title, color, text) in IMAGE_SPECS.items():
            image = Image.objects.filter(title=title).first()
            if image is None:
                url = f"https://placehold.co/800x600/{color}/FFFFFF/png?text={text}"
                try:
                    with urlopen(Request(url, headers={"User-Agent": "KS3-Product-Seeder/1.0"}), timeout=30) as response:
                        payload = response.read()
                except Exception as exc:
                    raise CommandError(f"Could not download {url}: {exc}") from exc
                with PillowImage.open(BytesIO(payload)) as source:
                    width, height = source.size
                image = Image(title=title, collection=collection, file_size=len(payload))
                image.file.save(f"ks3-product-{key}.png", ContentFile(payload), save=False)
                image.width, image.height = width, height
                image.save()
                self.stdout.write(f"  uploaded {image.file.name}")
            else:
                self.stdout.write(f"  reused {image.file.name}")
            result[key] = image
        return result
