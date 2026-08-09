from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("_payment", "0002_seed_va_channels_and_backfill"),
        ("_setting", "0013_fixed_charge_per_payment_route"),
    ]

    operations = [
        migrations.AlterField(
            model_name="xendittransactionfee",
            name="rate",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transaction_fees",
                to="_payment.xenditfeerate",
            ),
        ),
        migrations.AddField(
            model_name="xendittransactionfee",
            name="charge_configuration_snapshot",
            field=models.JSONField(default=dict),
        ),
    ]
