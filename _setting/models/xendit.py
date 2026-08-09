from django.core.exceptions import ValidationError
from django.db import models
from decimal import Decimal
from wagtail.admin.panels import FieldPanel, MultiFieldPanel

from backend.helper.singleton_model import SingletonModel


class XenditSetting(SingletonModel):
    is_active = models.BooleanField(default=True)
    api_key = models.CharField(max_length=255, blank=True)
    api_url = models.URLField(max_length=255, default="https://api.xendit.co")
    webhook_verification_token = models.CharField(max_length=255, blank=True)
    public_base_url = models.URLField(
        blank=True,
        help_text="Public HTTPS base URL used by Xendit webhooks (for example the ngrok URL).",
    )
    return_base_url = models.URLField(
        default="http://127.0.0.1:8000",
        help_text="Public HTTPS browser return URL after checkout (required by Xendit Payment Session).",
    )
    session_duration = models.PositiveIntegerField(
        default=86400,
        help_text="Payment Session lifetime in seconds; minimum 600.",
    )
    saving_payment_gateway_fee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("2750"),
        help_text="Biaya tetap yang dibebankan ke customer untuk setiap transaksi nabung.",
    )
    p2p_payment_gateway_fee = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("2750"),
        help_text="Biaya tetap yang dibebankan ke customer untuk setiap pembayaran proyek/P2P.",
    )
    auto_learn_va_fees = models.BooleanField(
        default=False,
        help_text="Legacy/nonaktif: actual fee tidak lagi mengubah biaya checkout.",
    )
    fee_auto_update_max_delta = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("5000"),
        help_text="Perubahan di atas nominal ini ditahan sebagai candidate untuk review admin.",
    )

    panels = [
        FieldPanel("is_active"),
        MultiFieldPanel(
            [
                FieldPanel("saving_payment_gateway_fee"),
                FieldPanel("p2p_payment_gateway_fee"),
            ],
            heading="Biaya yang dibebankan ke customer",
        ),
        MultiFieldPanel(
            [
                FieldPanel("api_url"),
                FieldPanel("api_key"),
                FieldPanel("webhook_verification_token"),
                FieldPanel("public_base_url"),
                FieldPanel("return_base_url"),
                FieldPanel("session_duration"),
            ],
            heading="Xendit API",
        ),
    ]

    class Meta:
        verbose_name = "Xendit setting"

    def clean(self):
        super().clean()
        if self.session_duration < 600:
            raise ValidationError({"session_duration": "Minimum session duration is 600 seconds."})
        if self.fee_auto_update_max_delta < 0:
            raise ValidationError(
                {"fee_auto_update_max_delta": "Batas perubahan fee tidak boleh negatif."}
            )
        fee_errors = {}
        if self.saving_payment_gateway_fee < 0:
            fee_errors["saving_payment_gateway_fee"] = "Biaya nabung tidak boleh negatif."
        if self.p2p_payment_gateway_fee < 0:
            fee_errors["p2p_payment_gateway_fee"] = "Biaya proyek/P2P tidak boleh negatif."
        if fee_errors:
            raise ValidationError(fee_errors)

    def __str__(self):
        return "Xendit Settings"
