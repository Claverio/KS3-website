from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel

from backend.helper.singleton_model import SingletonModel


DEFAULT_EMAIL_CONFIRMATION_SUBJECT = "Confirm your email address"
DEFAULT_EMAIL_CONFIRMATION_HTML = "<p>Please confirm your email address.</p>"
DEFAULT_PASSWORD_RESET_SUBJECT = "Reset your password"
DEFAULT_PASSWORD_RESET_HTML = "<p>Use the password reset link provided in this email.</p>"


class EmailSetting(SingletonModel):
    email_host = models.CharField(max_length=255, default="smtp.gmail.com")
    email_port = models.PositiveIntegerField(default=587)
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.EmailField(max_length=255, blank=True, null=True)
    email_host_password = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Use an App Password when using Gmail.",
    )
    reverify_cooldown_minutes = models.PositiveIntegerField(
        default=2,
        help_text="Cooldown in minutes before a verification link can be resent.",
    )
    email_confirmation_subject = models.CharField(
        max_length=255, default=DEFAULT_EMAIL_CONFIRMATION_SUBJECT
    )
    email_confirmation_html = models.TextField(default=DEFAULT_EMAIL_CONFIRMATION_HTML)
    password_reset_subject = models.CharField(
        max_length=255, default=DEFAULT_PASSWORD_RESET_SUBJECT
    )
    password_reset_html = models.TextField(default=DEFAULT_PASSWORD_RESET_HTML)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("email_host"),
                FieldPanel("email_port"),
                FieldPanel("email_use_tls"),
                FieldPanel("email_host_user"),
                FieldPanel("email_host_password"),
            ],
            heading="SMTP connection",
        ),
        FieldPanel("reverify_cooldown_minutes"),
    ]

    class Meta:
        verbose_name = "Email setting"

    def __str__(self):
        return "Email Settings"
