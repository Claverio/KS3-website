# KS3 Website

Website dan CMS Koperasi KS3 berbasis Django 6 dan Wagtail 7, termasuk katalog produk, P2P lending, Xendit payment session, polling status pembayaran, email notification, dan report admin.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp backend/settings/.env.example backend/settings/.env
python manage.py migrate
python manage.py runserver
```

## Production

Production dijalankan menggunakan Docker Compose dan Gunicorn. Environment production disimpan di `backend/settings/.env` pada server dan tidak pernah dimasukkan ke repository.

```bash
docker compose up -d --build
docker compose logs -f web
```

Container `payment-sync` menjalankan `python manage.py sync_unpaid_payments`
setiap 60 detik untuk merekonsiliasi transaksi P2P dan tabungan Xendit yang
masih menunggu pembayaran, lalu menarik actual fee dari Transactions API untuk
ledger `xendit_fees`. API key Xendit harus memiliki permission `Transaction Read`.
Pantau worker dengan:

```bash
docker compose logs -f payment-sync
```

Kanal Virtual Account, status aktif per rute, dan versi tarif efektif dikelola
dari menu **Xendit Fee** di Wagtail. Selisih charged fee vs actual fee serta
adjustment FIFO tersedia di menu **Rekonsiliasi Xendit**. Adjustment tidak pernah
mengubah nominal transaksi asli.

Domain production: [ks3.claverio.com](https://ks3.claverio.com)
