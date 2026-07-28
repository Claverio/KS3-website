from datetime import date, datetime, timezone
from decimal import Decimal
import uuid

from django.db import migrations


PROJECTS = [
    ("Modal Usaha Toko Kelontong", "modal-usaha-toko-kelontong", "Pembiayaan modal kerja untuk perluasan jaringan toko kelontong di wilayah Bandung.", "1350000000", "2700000", 500, "12", 12, "monthly"),
    ("Pinjaman Karyawan PT Sinar Abadi", "pinjaman-karyawan-pt-sinar-abadi", "Pendanaan pinjaman karyawan dengan potongan gaji bulanan sebagai sumber pengembalian.", "850500000", "4252500", 200, "9.5", 6, "monthly"),
    ("Pembiayaan Alat Produksi CV Karya", "pembiayaan-alat-produksi-cv-karya", "Pengadaan mesin produksi baru untuk meningkatkan kapasitas produksi furnitur.", "2100000000", "26250000", 80, "13", 24, "monthly"),
    ("Modal Tani Kelompok Makmur", "modal-tani-kelompok-makmur", "Pendanaan musim tanam untuk 45 petani anggota kelompok tani di Subang.", "120000000", "300000", 400, "11", 6, "end_of_term"),
    ("Pinjaman Pendidikan Angkatan XII", "pinjaman-pendidikan-angkatan-xii", "Pembiayaan biaya pendidikan anggota dengan skema cicilan ringan per bulan.", "96750000", "387000", 250, "8", 12, "monthly"),
    ("Pembiayaan Invoice PT Logam Jaya", "pembiayaan-invoice-pt-logam-jaya", "Pendanaan invoice dengan underlying kontrak pengadaan komponen otomotif.", "3000000000", "10000000", 300, "12.5", 12, "monthly"),
]


def seed(apps, schema_editor):
    Category = apps.get_model("_p2p", "P2PCategory")
    Project = apps.get_model("_p2p", "P2P")
    SEO = apps.get_model("_p2p", "P2PSEOSettings")
    category, _ = Category.objects.get_or_create(
        slug="modal-usaha", defaults={"name": "Modal Usaha", "is_active": True}
    )
    for order, item in enumerate(PROJECTS, start=1):
        title, slug, summary, target, price, slots, interest, tenor, frequency = item
        Project.objects.get_or_create(
            slug=slug,
            defaults={
                "category": category,
                "title": title,
                "summary": summary,
                "content": [
                    {
                        "type": "paragraph",
                        "value": {"content": f"<p>{summary}</p>"},
                        "id": str(uuid.uuid4()),
                    }
                ],
                "status": "open",
                "target_amount": Decimal(target),
                "slot_price": Decimal(price),
                "service_fee": Decimal("2750"),
                "total_slots": slots,
                "interest_rate": Decimal(interest),
                "tenor_months": tenor,
                "installment_frequency": frequency,
                "funding_deadline": datetime(2027, 12, 31, 23, 59, tzinfo=timezone.utc),
                "project_start_date": date(2028, 1, 1),
                "project_end_date": date(2028 + max(tenor // 12, 1), 1, 1),
                "collateral": "Tidak ada",
                "is_featured": order <= 3,
                "is_published": True,
                "sort_order": order,
            },
        )
    SEO.objects.get_or_create(
        pk=1,
        defaults={
            "list_title": "Peer to Peer Lending | KS3",
            "list_description": "Danai project pilihan dan dapatkan imbal hasil yang kompetitif.",
            "detail_title": "Detail Project P2P | KS3",
            "purchase_title": "Form Pendanaan | KS3",
            "complete_title": "Pembayaran Berhasil | KS3",
        },
    )


def unseed(apps, schema_editor):
    Project = apps.get_model("_p2p", "P2P")
    Project.objects.filter(slug__in=[row[1] for row in PROJECTS]).delete()


class Migration(migrations.Migration):
    dependencies = [("_p2p", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
