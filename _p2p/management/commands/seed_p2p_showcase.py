"""Build a presentation-ready P2P catalogue with representative StreamField content."""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from urllib.request import Request, urlopen
import uuid

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from wagtail.images import get_image_model
from wagtail.models import Collection
from PIL import Image as PillowImage

from _p2p.models import P2P, P2PCategory, P2PPurchase


IMAGE_SPECS = {
    "marathon": ("KS3 Showcase - Danamon Run", "005DAA", "Danamon+Run+2026"),
    "marathon_prep": ("KS3 Showcase - Persiapan Marathon", "FFAC0A", "Persiapan+Event+Marathon"),
    "coffee": ("KS3 Showcase - Roastery Kopi", "6F4E37", "Roastery+Kopi+Nusantara"),
    "coffee_pack": ("KS3 Showcase - Produk Kopi", "B88746", "Produk+Kopi+Siap+Kirim"),
    "solar": ("KS3 Showcase - Solar Warehouse", "147D64", "Solar+Panel+Gudang+Logistik"),
    "festival": ("KS3 Showcase - Festival Kuliner", "C84B31", "Festival+Kuliner+Bandung"),
    "cold_chain": ("KS3 Showcase - Armada Pendingin", "247BA0", "Armada+Pendingin+Ikan"),
}


def _block(block_type, value=None):
    return {"type": block_type, "value": value, "id": str(uuid.uuid4())}


def _heading(title, level="h3"):
    return _block("heading", {"level": level, "title": title})


def _paragraph(html):
    return _block("paragraph", {"content": html})


def _image(image, alt_text, caption=""):
    return _block(
        "image",
        {"image": image.pk, "alt_text": alt_text, "caption": caption},
    )


def _image_text(image, position, title, html):
    return _block(
        "image_text",
        {
            "image": image.pk,
            "image_position": position,
            "title": title,
            "content": html,
        },
    )


def _list(items, style="unordered"):
    return _block("list", {"style": style, "items": items})


def _table(title, columns, rows, note=""):
    return _block(
        "manual_table",
        {
            "title": title,
            "columns": columns,
            "rows": [{"cells": row} for row in rows],
            "footer_note": note,
        },
    )


def _accordion(items):
    return _block(
        "accordion",
        {"items": [{"title": title, "content": content} for title, content in items]},
    )


def _project_specs(images):
    disclaimer = (
        "<p><em>Konten dan angka pada project ini merupakan data simulasi untuk "
        "demonstrasi CMS KS3.</em></p>"
    )
    return [
        {
            "category": "event",
            "title": "Pembiayaan Vendor Danamon Run 2026",
            "slug": "pembiayaan-vendor-danamon-run-2026",
            "summary": "Modal kerja vendor produksi untuk kebutuhan operasional, race pack, dan infrastruktur event marathon nasional.",
            "target": "750000000",
            "slot_price": "1500000",
            "slots": 500,
            "interest": "11.50",
            "tenor": 6,
            "frequency": P2P.InstallmentFrequency.QUARTERLY,
            "collateral": "Assignment piutang berdasarkan SPK penyelenggaraan event",
            "featured": True,
            "paid_slots": 185,
            "content": [
                _image(images["marathon"], "Ilustrasi event Danamon Run 2026", "Pendanaan kebutuhan vendor dari fase persiapan hingga hari pelaksanaan."),
                _heading("Tentang project", "h2"),
                _paragraph("<p>Vendor terpilih membutuhkan modal kerja untuk produksi <strong>race pack</strong>, penyewaan perangkat waktu, barikade, dan kebutuhan water station. Pencairan dilakukan bertahap mengikuti milestone pekerjaan.</p>"),
                _block("two_column_text", {"left": "<p><strong>Sumber pembayaran</strong><br/>Termin invoice berdasarkan berita acara penyelesaian pekerjaan.</p>", "right": "<p><strong>Mitigasi utama</strong><br/>Verifikasi SPK, kontrol penggunaan dana, dan monitoring milestone mingguan.</p>"}),
                _image_text(images["marathon_prep"], "right", "Penggunaan dana terukur", "<p>Dana dialokasikan ke kebutuhan yang langsung mendukung pelaksanaan event dan dicairkan sesuai jadwal produksi.</p>"),
                _table("Rencana penggunaan dana", ["Kebutuhan", "Porsi", "Nilai"], [["Produksi race pack", "35%", "Rp262.500.000"], ["Infrastruktur rute", "30%", "Rp225.000.000"], ["Operasional & kru", "20%", "Rp150.000.000"], ["Dana cadangan", "15%", "Rp112.500.000"]], "Realisasi akan dilaporkan melalui pembaruan project."),
                _heading("Mengapa project ini menarik?"),
                _list(["Underlying pekerjaan dan jadwal pembayaran terdokumentasi", "Tenor pendek selama 6 bulan", "Pencairan berbasis milestone", "Monitoring penggunaan dana oleh tim KS3"]),
                _block("blockquote", {"quote": "<p>Event besar membutuhkan disiplin eksekusi. Karena itu, pencairan dan monitoring dibuat berbasis milestone yang dapat diverifikasi.</p>", "author": "Tim Analisis KS3"}),
                _accordion([("Kapan imbal hasil dibayarkan?", "<p>Pembayaran mengikuti frekuensi triwulanan sesuai jadwal pada perjanjian pendanaan.</p>"), ("Apa risiko utamanya?", "<p>Keterlambatan milestone dan pembayaran invoice. Risiko dimitigasi melalui verifikasi dokumen dan kontrol pencairan.</p>"), ("Apakah nama brand menandakan kerja sama langsung?", "<p>Tidak. Project ini adalah simulasi tampilan CMS dan bukan penawaran atau pernyataan kerja sama resmi.</p>")]),
                _block("separator"),
                _paragraph(disclaimer),
            ],
        },
        {
            "category": "umkm",
            "title": "Ekspansi Roastery Kopi Nusantara",
            "slug": "ekspansi-roastery-kopi-nusantara",
            "summary": "Pembelian mesin roasting dan modal bahan baku untuk memenuhi kontrak pasokan hotel serta jaringan kafe.",
            "target": "480000000",
            "slot_price": "1200000",
            "slots": 400,
            "interest": "12.00",
            "tenor": 12,
            "frequency": P2P.InstallmentFrequency.MONTHLY,
            "collateral": "Mesin roasting dan personal guarantee pengelola",
            "featured": True,
            "paid_slots": 252,
            "content": [
                _heading("Dari biji lokal ke pasar hospitality", "h2"),
                _paragraph("<p>Roastery telah beroperasi selama empat tahun dan memasok kopi ke 18 mitra usaha. Pendanaan digunakan untuk meningkatkan kapasitas produksi tanpa mengorbankan konsistensi profil rasa.</p>"),
                _block("two_column_image", {"left_image": images["coffee"].pk, "left_alt_text": "Area produksi roastery", "right_image": images["coffee_pack"].pk, "right_alt_text": "Produk kopi siap distribusi"}),
                _image_text(images["coffee"], "left", "Kapasitas naik 2,5 kali", "<p>Mesin baru meningkatkan kapasitas dari 80 kg menjadi 200 kg per hari sekaligus menekan waktu henti produksi.</p>"),
                _heading("Kekuatan usaha"),
                _list(["Kontrak pasokan aktif dengan hotel dan kafe", "Riwayat penjualan berulang selama 24 bulan", "Bahan baku dari koperasi petani mitra", "Margin kotor historis yang stabil"]),
                _table("Proyeksi setelah ekspansi", ["Indikator", "Saat ini", "Setelah pendanaan"], [["Kapasitas/hari", "80 kg", "200 kg"], ["Mitra aktif", "18", "32"], ["Estimasi omzet/bulan", "Rp210 juta", "Rp465 juta"]], "Proyeksi bukan jaminan hasil aktual."),
                _accordion([("Bagaimana skema angsurannya?", "<p>Pokok dan imbal hasil dibayarkan setiap bulan selama 12 bulan.</p>"), ("Apa agunannya?", "<p>Mesin roasting yang dibiayai serta personal guarantee dari pengelola usaha.</p>")]),
                _paragraph(disclaimer),
            ],
        },
        {
            "category": "green",
            "title": "Solar Panel Gudang Logistik Cikarang",
            "slug": "solar-panel-gudang-logistik-cikarang",
            "summary": "Instalasi pembangkit surya atap untuk menekan biaya energi gudang dan mendukung target operasional hijau.",
            "target": "1200000000",
            "slot_price": "3000000",
            "slots": 400,
            "interest": "10.75",
            "tenor": 18,
            "frequency": P2P.InstallmentFrequency.MONTHLY,
            "collateral": "Peralatan solar panel dan corporate guarantee",
            "featured": True,
            "paid_slots": 164,
            "content": [
                _image(images["solar"], "Ilustrasi solar panel pada atap gudang", "Sistem surya atap untuk fasilitas logistik di Cikarang."),
                _heading("Efisiensi energi yang dapat diukur", "h2"),
                _block("two_column_text", {"left": "<p><strong>Kapasitas sistem</strong><br/>250 kWp dengan estimasi produksi 360 MWh per tahun.</p>", "right": "<p><strong>Potensi penghematan</strong><br/>Sekitar 22% dari biaya listrik tahunan fasilitas.</p>"}),
                _heading("Tahapan implementasi"),
                _list(["Audit struktur dan finalisasi desain", "Pengadaan panel, inverter, serta mounting", "Instalasi dan pengujian sistem", "Commissioning dan monitoring produksi energi"], "ordered"),
                _table("Indikator dampak", ["Indikator", "Estimasi tahunan"], [["Produksi energi", "360 MWh"], ["Pengurangan emisi", "±300 ton CO₂e"], ["Penghematan biaya", "Rp410 juta"]], "Estimasi berdasarkan studi teknis awal dan dapat berubah setelah commissioning."),
                _block("blockquote", {"quote": "<p>Penghematan energi menjadi sumber kemampuan bayar sekaligus menghasilkan dampak lingkungan yang terukur.</p>", "author": "Tim Green Financing KS3"}),
                _paragraph(disclaimer),
            ],
        },
        {
            "category": "event",
            "title": "Festival Kuliner Bandung 2026",
            "slug": "festival-kuliner-bandung-2026",
            "summary": "Pembiayaan produksi festival bagi 80 tenant kuliner lokal dan rangkaian pertunjukan komunitas kreatif.",
            "target": "300000000",
            "slot_price": "1000000",
            "slots": 300,
            "interest": "13.00",
            "tenor": 4,
            "frequency": P2P.InstallmentFrequency.END_OF_TERM,
            "collateral": "Escrow penjualan tiket dan piutang sponsor",
            "featured": False,
            "paid_slots": 246,
            "content": [
                _image_text(images["festival"], "left", "Menggerakkan ekosistem kuliner lokal", "<p>Festival mempertemukan UMKM kuliner, komunitas kreatif, dan pengunjung dalam program tiga hari dengan transaksi nontunai terintegrasi.</p>"),
                _heading("Sumber pendapatan"),
                _list(["Penjualan tiket masuk", "Biaya partisipasi tenant", "Sponsorship dan media partner", "Revenue sharing area aktivitas"]),
                _table("Milestone event", ["Periode", "Aktivitas"], [["H-90", "Konfirmasi venue dan sponsor utama"], ["H-60", "Kurasi tenant dan penjualan tiket"], ["H-14", "Produksi venue dan pelatihan tenant"], ["H+14", "Rekonsiliasi dan pelunasan"]]),
                _accordion([("Bagaimana pembayaran dilakukan?", "<p>Pokok dan imbal hasil dibayarkan pada akhir tenor setelah rekonsiliasi penerimaan event.</p>"), ("Bagaimana penjualan dipantau?", "<p>Penjualan tiket dan transaksi utama menggunakan kanal nontunai yang direkonsiliasi berkala.</p>")]),
                _paragraph(disclaimer),
            ],
        },
        {
            "category": "supply-chain",
            "title": "Armada Pendingin Ikan Muara Baru",
            "slug": "armada-pendingin-ikan-muara-baru",
            "summary": "Pengadaan kendaraan berpendingin untuk menjaga kualitas hasil laut dari pelabuhan hingga pelanggan horeca.",
            "target": "900000000",
            "slot_price": "2250000",
            "slots": 400,
            "interest": "12.25",
            "tenor": 15,
            "frequency": P2P.InstallmentFrequency.MONTHLY,
            "collateral": "BPKB kendaraan yang dibiayai dan fidusia",
            "featured": False,
            "paid_slots": 72,
            "content": [
                _image(images["cold_chain"], "Ilustrasi armada berpendingin hasil laut"),
                _heading("Menjaga mutu sepanjang perjalanan", "h2"),
                _paragraph("<p>Dua unit kendaraan berpendingin akan melayani rute harian Muara Baru–Jabodetabek. Sensor suhu dan GPS membantu memastikan kualitas produk serta ketepatan pengiriman.</p>"),
                _block("two_column_text", {"left": "<p><strong>Pasar utama</strong><br/>Hotel, restoran, katering, dan distributor pangan segar.</p>", "right": "<p><strong>Sumber pembayaran</strong><br/>Arus kas kontrak distribusi dan pendapatan pengiriman reguler.</p>"}),
                _heading("Kontrol operasional"),
                _list(["Pelacakan GPS secara real time", "Pencatatan suhu selama perjalanan", "Asuransi kendaraan dan muatan", "Jadwal preventive maintenance"]),
                _accordion([("Apa yang menjadi jaminan?", "<p>Kendaraan yang dibiayai diikat secara fidusia sesuai dokumen pembiayaan.</p>"), ("Bagaimana bila armada tidak beroperasi?", "<p>Terdapat proteksi asuransi dan jadwal perawatan untuk menekan risiko downtime.</p>")]),
                _paragraph(disclaimer),
            ],
        },
    ]


class Command(BaseCommand):
    help = "Seed presentation-ready P2P projects, StreamField content, images, and demo progress."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete every existing P2P purchase, project, and category before seeding.",
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Do not ask for confirmation when --reset is used.",
        )

    def handle(self, *args, **options):
        if options["reset"] and not options["no_input"]:
            answer = input(
                "This deletes ALL P2P purchases, projects, and categories. Type 'reset' to continue: "
            )
            if answer.strip().lower() != "reset":
                raise CommandError("P2P showcase reset canceled.")

        self.stdout.write("Downloading showcase images through Wagtail storage...")
        images = self._ensure_images()

        with transaction.atomic():
            if options["reset"]:
                purchase_count = P2PPurchase.objects.count()
                project_count = P2P.objects.count()
                P2PPurchase.objects.all().delete()
                P2P.objects.all().delete()
                P2PCategory.objects.all().delete()
                self.stdout.write(
                    f"Deleted {purchase_count} purchase(s) and {project_count} project(s)."
                )

            categories = self._ensure_categories()
            specs = _project_specs(images)
            showcase_slugs = [spec["slug"] for spec in specs]
            P2PPurchase.objects.filter(reference_id__startswith="KS3-DEMO-").delete()
            P2P.objects.filter(slug__in=showcase_slugs).delete()

            for order, spec in enumerate(specs, start=1):
                project = self._create_project(spec, categories, order)
                self._create_paid_progress(project, spec["paid_slots"])
                self.stdout.write(
                    f"  [{order}/{len(specs)}] {project.title} ({project.progress_percentage}%)"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"P2P showcase ready: {len(specs)} projects and {len(images)} S3-backed images."
            )
        )

    def _ensure_images(self):
        collection = Collection.objects.filter(name="KS3 P2P Showcase").first()
        if collection is None:
            collection = Collection.get_first_root_node().add_child(name="KS3 P2P Showcase")

        Image = get_image_model()
        images = {}
        for key, (title, color, text) in IMAGE_SPECS.items():
            image = Image.objects.filter(title=title).first()
            if image is None:
                url = f"https://placehold.co/1600x900/{color}/FFFFFF/png?text={text}"
                request = Request(url, headers={"User-Agent": "KS3-P2P-Showcase-Seeder/1.0"})
                try:
                    with urlopen(request, timeout=30) as response:
                        payload = response.read()
                except Exception as exc:
                    raise CommandError(f"Could not download {url}: {exc}") from exc
                filename = f"ks3-p2p-showcase-{key}.png"
                with PillowImage.open(BytesIO(payload)) as source_image:
                    width, height = source_image.size
                image = Image(
                    title=title,
                    collection=collection,
                    file_size=len(payload),
                )
                image.file.save(filename, ContentFile(payload), save=False)
                # ImageField.save() updates its dimension fields before the model
                # exists and may reset them to NULL on remote storage backends.
                image.width = width
                image.height = height
                image.save()
                self.stdout.write(f"  uploaded {filename} -> {image.file.name}")
            else:
                self.stdout.write(f"  reused {image.file.name}")
            images[key] = image
        return images

    def _ensure_categories(self):
        specs = [
            ("event", "Event & Creative", 10),
            ("umkm", "UMKM & Retail", 20),
            ("green", "Green Financing", 30),
            ("supply-chain", "Supply Chain", 40),
        ]
        categories = {}
        for slug, name, order in specs:
            category, _ = P2PCategory.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "is_active": True, "sort_order": order},
            )
            categories[slug] = category
        return categories

    def _create_project(self, spec, categories, order):
        now = timezone.now()
        start_date = timezone.localdate() + timedelta(days=60 + order * 7)
        return P2P.objects.create(
            category=categories[spec["category"]],
            title=spec["title"],
            slug=spec["slug"],
            summary=spec["summary"],
            content=spec["content"],
            status=P2P.Status.OPEN,
            target_amount=Decimal(spec["target"]),
            slot_price=Decimal(spec["slot_price"]),
            service_fee=Decimal("2750"),
            total_slots=spec["slots"],
            interest_rate=Decimal(spec["interest"]),
            tenor_months=spec["tenor"],
            installment_frequency=spec["frequency"],
            funding_deadline=now + timedelta(days=45 + order * 5),
            project_start_date=start_date,
            project_end_date=start_date + timedelta(days=spec["tenor"] * 31),
            collateral=spec["collateral"],
            is_featured=spec["featured"],
            is_published=True,
            sort_order=order,
        )

    def _create_paid_progress(self, project, paid_slots):
        lender_count = min(5, paid_slots)
        base, remainder = divmod(paid_slots, lender_count)
        now = timezone.now()
        for index in range(lender_count):
            quantity = base + (1 if index < remainder else 0)
            subtotal = project.slot_price * quantity
            P2PPurchase.objects.create(
                reference_id=f"KS3-DEMO-{project.pk}-{index + 1}",
                booking_number=f"DEMO-{project.pk:03d}-{index + 1:02d}",
                project=project,
                full_name=f"Demo Lender {index + 1}",
                phone=f"08120000{project.pk:03d}{index + 1:02d}",
                email=f"lender{index + 1}.{project.slug}@example.test",
                nik="",
                note="Data simulasi untuk progress showcase.",
                slot_quantity=quantity,
                unit_price=project.slot_price,
                subtotal=subtotal,
                service_fee=project.service_fee,
                total_amount=subtotal + project.service_fee,
                status=P2PPurchase.Status.PAID,
                xendit_session_status="DEMO_PAID",
                paid_at=now - timedelta(days=index + 1),
            )
