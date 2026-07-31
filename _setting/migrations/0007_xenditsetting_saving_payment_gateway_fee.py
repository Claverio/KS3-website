from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("_setting", "0006_alter_homepagesetting_products_description_and_more")]

    operations = [
        migrations.AddField(
            model_name="xenditsetting",
            name="saving_payment_gateway_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("2750"),
                help_text="Biaya tambahan payment gateway untuk setiap setoran simpanan.",
                max_digits=18,
            ),
        ),
    ]
