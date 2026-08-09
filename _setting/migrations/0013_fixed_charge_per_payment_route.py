from decimal import Decimal

from django.db import migrations, models


def disable_legacy_auto_learning(apps, schema_editor):
    XenditSetting = apps.get_model("_setting", "XenditSetting")
    XenditSetting.objects.update(auto_learn_va_fees=False)


class Migration(migrations.Migration):
    dependencies = [
        ("_setting", "0012_alter_xenditsetting_saving_payment_gateway_fee"),
    ]

    operations = [
        migrations.AddField(
            model_name="xenditsetting",
            name="p2p_payment_gateway_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("2750"),
                help_text=(
                    "Biaya tetap yang dibebankan ke customer untuk setiap "
                    "pembayaran proyek/P2P."
                ),
                max_digits=18,
            ),
        ),
        migrations.AlterField(
            model_name="xenditsetting",
            name="saving_payment_gateway_fee",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("2750"),
                help_text=(
                    "Biaya tetap yang dibebankan ke customer untuk setiap transaksi nabung."
                ),
                max_digits=18,
            ),
        ),
        migrations.AlterField(
            model_name="xenditsetting",
            name="auto_learn_va_fees",
            field=models.BooleanField(
                default=False,
                help_text="Legacy/nonaktif: actual fee tidak lagi mengubah biaya checkout.",
            ),
        ),
        migrations.RunPython(disable_legacy_auto_learning, migrations.RunPython.noop),
    ]
