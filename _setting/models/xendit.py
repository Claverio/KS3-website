from django.core.exceptions import ValidationError
from django.db import models
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
        help_text="Browser return URL after checkout. Localhost is valid for local testing.",
    )
    session_duration = models.PositiveIntegerField(
        default=86400,
        help_text="Payment Session lifetime in seconds; minimum 600.",
    )

    panels = [
        FieldPanel("is_active"),
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

    def __str__(self):
        return "Xendit Settings"
