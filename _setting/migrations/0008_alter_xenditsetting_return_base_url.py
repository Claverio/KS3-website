from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("_setting", "0007_xenditsetting_saving_payment_gateway_fee")]

    operations = [
        migrations.AlterField(
            model_name="xenditsetting",
            name="return_base_url",
            field=models.URLField(
                default="http://127.0.0.1:8000",
                help_text="Public HTTPS browser return URL after checkout (required by Xendit Payment Session).",
            ),
        ),
    ]
