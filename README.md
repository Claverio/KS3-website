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

Kanal Virtual Account dan status aktif per rute dikelola dari menu **Xendit Fee**
di Wagtail. Nominal biaya yang dibebankan ke customer diatur terpisah untuk
**Nabung** dan **P2P/Proyek** pada **General Settings → Xendit**. Menu
**Rekonsiliasi Xendit** tetap menarik actual fee untuk observasi, tetapi
auto-update tarif dan posting adjustment sedang dinonaktifkan.

Domain production: [ks3.claverio.com](https://ks3.claverio.com)
