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

Domain production: [ks3.claverio.com](https://ks3.claverio.com)

