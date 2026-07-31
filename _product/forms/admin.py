from decimal import Decimal

from django.utils import timezone
from wagtail.admin.forms.models import WagtailAdminModelForm

from _product.models import SavingTransaction
from _setting.models import XenditSetting


class SavingTransactionAdminForm(WagtailAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.instance.pk and "service_fee" in self.fields:
            fee = XenditSetting.load().saving_payment_gateway_fee
            self.initial["service_fee"] = fee
            self.fields["service_fee"].initial = fee
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
        return cleaned_data
