from decimal import Decimal

from django import forms
from django.utils import timezone
from wagtail.admin.forms.models import WagtailAdminModelForm

from _payment.services import FeeConfigurationError, resolve_fee
from _product.models import SavingTransaction


class SavingTransactionAdminForm(WagtailAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "service_fee" in self.fields:
            self.fields["service_fee"].help_text = (
                "Untuk transaksi Xendit, nilai ini dihitung ulang dari tarif VA aktif."
            )
        if self.instance.pk and "payment_channel" in self.fields:
            self.fields["payment_channel"].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("payment_channel") == SavingTransaction.PaymentChannel.MANUAL:
            paid_at = timezone.now()
            cleaned_data["service_fee"] = Decimal("0")
            self.instance.status = SavingTransaction.Status.PAID
            self.instance.paid_at = paid_at
            self.instance.provider_updated_at = paid_at
            self.instance.xendit_session_status = "MANUAL"
        elif cleaned_data.get("amount"):
            try:
                resolved = resolve_fee(
                    channel_code=None,
                    route="saving",
                    principal_amount=cleaned_data["amount"],
                )
            except FeeConfigurationError as exc:
                raise forms.ValidationError(str(exc)) from exc
            cleaned_data["service_fee"] = resolved.total_fee
        return cleaned_data
