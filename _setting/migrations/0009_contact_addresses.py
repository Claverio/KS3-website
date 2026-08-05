from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields


INITIAL_ADDRESSES = (
    (
        "Kantor Jakarta",
        "Equity Tower, Lantai 49, Jl. Jenderal Sudirman Kav. 52–53, "
        "Senayan, Kebayoran Baru, Jakarta 12190.",
    ),
    (
        "Kantor Tangerang",
        "Rukan Shibuya Blok B No. 26, PIK 2, Lemo, Teluknaga, "
        "Kabupaten Tangerang, Banten 15510.",
    ),
)


def create_initial_addresses(apps, schema_editor):
    ContactSetting = apps.get_model("_setting", "ContactSetting")
    ContactAddress = apps.get_model("_setting", "ContactAddress")
    contact_setting, _ = ContactSetting.objects.get_or_create(pk=1)
    if ContactAddress.objects.filter(contact_setting=contact_setting).exists():
        return
    ContactAddress.objects.bulk_create(
        [
            ContactAddress(
                contact_setting=contact_setting,
                name=name,
                address=address,
                sort_order=index,
            )
            for index, (name, address) in enumerate(INITIAL_ADDRESSES)
        ]
    )


def restore_legacy_address(apps, schema_editor):
    ContactSetting = apps.get_model("_setting", "ContactSetting")
    ContactAddress = apps.get_model("_setting", "ContactAddress")
    contact_setting = ContactSetting.objects.filter(pk=1).first()
    if not contact_setting:
        return
    first_address = ContactAddress.objects.filter(
        contact_setting=contact_setting
    ).order_by("sort_order", "pk").first()
    if first_address:
        contact_setting.address = first_address.address
        contact_setting.save(update_fields=["address"])


class Migration(migrations.Migration):
    dependencies = [("_setting", "0008_alter_xenditsetting_return_base_url")]

    operations = [
        migrations.CreateModel(
            name="ContactAddress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("sort_order", models.IntegerField(blank=True, editable=False, null=True)),
                (
                    "name",
                    models.CharField(
                        help_text="Contoh: Kantor Jakarta atau Kantor Tangerang.",
                        max_length=120,
                    ),
                ),
                ("address", models.TextField()),
                (
                    "contact_setting",
                    modelcluster.fields.ParentalKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="addresses",
                        to="_setting.contactsetting",
                    ),
                ),
            ],
            options={
                "verbose_name": "Alamat kantor",
                "verbose_name_plural": "Alamat kantor",
                "ordering": ["sort_order"],
                "abstract": False,
            },
        ),
        migrations.RunPython(create_initial_addresses, restore_legacy_address),
        migrations.RemoveField(model_name="contactsetting", name="address"),
    ]
