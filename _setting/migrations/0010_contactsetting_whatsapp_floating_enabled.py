from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("_setting", "0009_contact_addresses")]

    operations = [
        migrations.AddField(
            model_name="contactsetting",
            name="whatsapp_floating_enabled",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Tampilkan tombol chat WhatsApp di semua halaman. "
                    "Tombol hanya muncul jika tautan WhatsApp sudah diisi."
                ),
                verbose_name="Tampilkan tombol WhatsApp melayang",
            ),
        ),
    ]
