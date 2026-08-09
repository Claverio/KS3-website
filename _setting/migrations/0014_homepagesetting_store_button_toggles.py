from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("_setting", "0013_fixed_charge_per_payment_route"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepagesetting",
            name="app_store_enabled",
            field=models.BooleanField(default=True, verbose_name="Tampilkan tombol App Store"),
        ),
        migrations.AddField(
            model_name="homepagesetting",
            name="play_store_enabled",
            field=models.BooleanField(default=True, verbose_name="Tampilkan tombol Google Play"),
        ),
    ]
