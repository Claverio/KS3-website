from decimal import Decimal

from django.db import migrations
from django.utils import timezone


VA_CHANNELS = (
    ("BCA_VIRTUAL_ACCOUNT", "BCA Virtual Account"),
    ("BNI_VIRTUAL_ACCOUNT", "BNI Virtual Account"),
    ("BRI_VIRTUAL_ACCOUNT", "BRI Virtual Account"),
    ("MANDIRI_VIRTUAL_ACCOUNT", "Mandiri Virtual Account"),
    ("PERMATA_VIRTUAL_ACCOUNT", "Permata Virtual Account"),
    ("BSI_VIRTUAL_ACCOUNT", "BSI Virtual Account"),
    ("CIMB_VIRTUAL_ACCOUNT", "CIMB Niaga Virtual Account"),
)


def seed_and_backfill(apps, schema_editor):
    Channel = apps.get_model("_payment", "XenditPaymentChannel")
    Rate = apps.get_model("_payment", "XenditFeeRate")
    Fee = apps.get_model("_payment", "XenditTransactionFee")
    Saving = apps.get_model("_product", "SavingTransaction")
    Purchase = apps.get_model("_p2p", "P2PPurchase")
    XenditSetting = apps.get_model("_setting", "XenditSetting")

    setting = XenditSetting.objects.order_by("pk").first()
    legacy_fee = (
        setting.saving_payment_gateway_fee if setting else Decimal("2750")
    )
    effective_from = timezone.now()
    rates = {}
    for sort_order, (code, name) in enumerate(VA_CHANNELS, start=10):
        channel, _ = Channel.objects.get_or_create(
            code=code,
            defaults={
                "display_name": name,
                "category": "virtual_account",
                "is_enabled": True,
                "enabled_for_saving": True,
                "enabled_for_p2p": True,
                "sort_order": sort_order,
            },
        )
        rate, _ = Rate.objects.get_or_create(
            channel=channel,
            currency="IDR",
            effective_from=effective_from,
            defaults={
                "fixed_fee": legacy_fee,
                "percentage_fee": Decimal("0"),
                "vat_percent": Decimal("0"),
                "source": "legacy",
                "status": "active",
                "source_reference": "Migrated from saving_payment_gateway_fee",
                "notes": "Tarif awal; akan diversi otomatis dari actual Xendit fee.",
            },
        )
        rates[code] = rate

    unknown_channel, _ = Channel.objects.get_or_create(
        code="LEGACY_UNKNOWN_VIRTUAL_ACCOUNT",
        defaults={
            "display_name": "Legacy - kanal tidak tersimpan",
            "category": "virtual_account",
            "is_enabled": False,
            "enabled_for_saving": False,
            "enabled_for_p2p": False,
            "sort_order": 999,
        },
    )
    unknown_rate, _ = Rate.objects.get_or_create(
        channel=unknown_channel,
        currency="IDR",
        effective_from=effective_from,
        defaults={
            "fixed_fee": legacy_fee,
            "percentage_fee": Decimal("0"),
            "vat_percent": Decimal("0"),
            "source": "legacy",
            "status": "superseded",
            "source_reference": "Historical backfill",
            "notes": "Placeholder only; historical checkout did not persist its selected channel.",
        },
    )

    common_rate_snapshot = {
        "rate_id": unknown_rate.pk,
        "channel_code": unknown_channel.code,
        "channel_name": unknown_channel.display_name,
        "currency": "IDR",
        "fixed_fee": str(legacy_fee),
        "percentage_fee": "0",
        "vat_percent": "0",
        "effective_from": effective_from.isoformat(),
        "effective_to": None,
        "source": "legacy",
        "source_reference": "Historical backfill",
        "channel_unknown": True,
    }

    for saving in Saving.objects.filter(payment_channel="xendit").iterator():
        Fee.objects.get_or_create(
            saving_transaction_id=saving.pk,
            defaults={
                "channel": unknown_channel,
                "rate": unknown_rate,
                "currency": saving.currency,
                "principal_amount": saving.amount,
                "charged_fee_before_tax": saving.service_fee,
                "charged_fee_vat": Decimal("0"),
                "charged_fee_total": saving.service_fee,
                "rate_snapshot": common_rate_snapshot,
                "allowed_payment_channels": [],
                "session_request_snapshot": {
                    "source": "legacy_backfill",
                    "reference_id": saving.reference_id,
                    "amount": str(saving.total_amount),
                },
                "session_response_snapshot": saving.xendit_create_response or {},
                "xendit_session_id": saving.xendit_session_id or "",
                "provider_payment_request_id": saving.payment_request_id or "",
                "reconciliation_status": "pending" if saving.status == "paid" else "review",
            },
        )

    for purchase in Purchase.objects.all().iterator():
        Fee.objects.get_or_create(
            p2p_purchase_id=purchase.pk,
            defaults={
                "channel": unknown_channel,
                "rate": unknown_rate,
                "currency": purchase.currency,
                "principal_amount": purchase.subtotal,
                "charged_fee_before_tax": purchase.service_fee,
                "charged_fee_vat": Decimal("0"),
                "charged_fee_total": purchase.service_fee,
                "rate_snapshot": common_rate_snapshot,
                "allowed_payment_channels": [],
                "session_request_snapshot": {
                    "source": "legacy_backfill",
                    "reference_id": purchase.reference_id,
                    "amount": str(purchase.total_amount),
                },
                "session_response_snapshot": purchase.xendit_create_response or {},
                "xendit_session_id": purchase.xendit_session_id or "",
                "provider_payment_request_id": purchase.payment_request_id or "",
                "reconciliation_status": "pending" if purchase.status == "paid" else "review",
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("_payment", "0001_initial"),
        ("_setting", "0011_xenditsetting_auto_learn_va_fees_and_more"),
    ]

    operations = [migrations.RunPython(seed_and_backfill, migrations.RunPython.noop)]
