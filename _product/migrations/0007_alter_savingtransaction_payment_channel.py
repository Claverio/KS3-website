from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("_product", "0006_savingtransaction_manual_channel")]

    operations = [
        migrations.AlterField(
            model_name="savingtransaction",
            name="payment_channel",
            field=models.CharField(
                choices=[
                    ("xendit", "Online via Xendit"),
                    ("manual", "Setoran manual (langsung lunas)"),
                ],
                db_index=True,
                default="xendit",
                max_length=16,
            ),
        ),
    ]
