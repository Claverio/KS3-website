import secrets
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface


nik_validator = RegexValidator(r"^\d{16}$", "NIK must contain exactly 16 digits.")
phone_validator = RegexValidator(r"^\+?[0-9][0-9\s-]{7,19}$", "Enter a valid phone number.")


class SavingTransaction(models.Model):
    IMMUTABLE_FIELDS = (
        "reference_id",
        "transaction_code",
        "product_id",
        "payment_channel",
        "manual_reference",
        "is_new_member",
        "nomor_anggota",
        "full_name",
        "phone",
        "email",
        "nik",
        "note",
        "amount",
        "service_fee",
        "total_amount",
        "currency",
    )
    class Status(models.TextChoices):
        CREATING = "creating", "Creating payment"
        WAITING_PAYMENT = "waiting_payment", "Waiting for payment"
        PAID = "paid", "Paid"
        EXPIRED = "expired", "Expired"
        CANCELED = "canceled", "Canceled"
        FAILED = "failed", "Failed"

    class PaymentChannel(models.TextChoices):
        XENDIT = "xendit", "Online via Xendit"
        MANUAL = "manual", "Setoran manual (langsung lunas)"

    # ── identifiers ──────────────────────────────────────────────
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    reference_id = models.CharField(max_length=80, unique=True, editable=False)
    transaction_code = models.CharField(max_length=80, unique=True, editable=False)

    # ── product FK (which savings product) ───────────────────────
    product = models.ForeignKey(
        "_product.Product",
        on_delete=models.PROTECT,
        related_name="saving_transactions",
        limit_choices_to={"category__slug": "simpanan"},
        help_text="The savings product this transaction belongs to.",
    )

    payment_channel = models.CharField(
        max_length=16,
        choices=PaymentChannel.choices,
        default=PaymentChannel.XENDIT,
        db_index=True,
    )
    manual_reference = models.CharField(
        max_length=120,
        blank=True,
        help_text="Nomor bukti setoran/transfer untuk transaksi manual (opsional).",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="recorded_saving_transactions",
    )

    # ── member info ──────────────────────────────────────────────
    is_new_member = models.BooleanField(
        default=False,
        help_text="Check if this person is a new member. New members do not need a nomor anggota.",
    )
    nomor_anggota = models.CharField(
        max_length=50,
        blank=True,
        help_text="Required for existing members. Leave blank for new members.",
    )

    # ── customer data (mirrors P2PPurchase) ──────────────────────
    full_name = models.CharField(max_length=255)
    phone = models.CharField(
        max_length=24,
        validators=[phone_validator],
        help_text="WhatsApp number (required).",
    )
    email = models.EmailField()
    nik = models.CharField(
        max_length=16,
        blank=True,
        validators=[nik_validator],
        help_text="Optional — 16-digit NIK.",
    )
    note = models.TextField(blank=True)

    # ── financials ───────────────────────────────────────────────
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    service_fee = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="IDR")

    # ── status ───────────────────────────────────────────────────
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.CREATING,
        db_index=True,
    )

    # ── Xendit payment ───────────────────────────────────────────
    xendit_session_id = models.CharField(max_length=80, unique=True, null=True, blank=True)
    xendit_session_status = models.CharField(max_length=32, blank=True)
    payment_link_url = models.URLField(max_length=500, blank=True)
    session_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    payment_id = models.CharField(max_length=100, blank=True)
    payment_request_id = models.CharField(max_length=100, blank=True)
    xendit_webhook_id = models.CharField(max_length=120, blank=True, db_index=True)
    xendit_create_response = models.JSONField(default=dict, blank=True)
    xendit_last_response = models.JSONField(default=dict, blank=True)
    xendit_webhook_payload = models.JSONField(default=dict, blank=True)
    provider_updated_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # ── email notifications ──────────────────────────────────────
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_attempt_count = models.PositiveSmallIntegerField(default=0)
    email_last_error = models.TextField(blank=True)

    # ── timestamps ───────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── wagtail admin ────────────────────────────────────────────
    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    FieldPanel("product"),
                    FieldPanel("payment_channel"),
                    FieldPanel("manual_reference"),
                    MultiFieldPanel(
                        [
                            FieldPanel("is_new_member"),
                            FieldPanel("nomor_anggota"),
                        ],
                        heading="Membership",
                    ),
                    FieldPanel("full_name"),
                    FieldPanel("phone"),
                    FieldPanel("email"),
                    FieldPanel("nik"),
                    FieldPanel("note"),
                    MultiFieldPanel(
                        [
                            FieldPanel("amount"),
                            FieldPanel("service_fee"),
                        ],
                        heading="Nominal",
                    ),
                ],
                heading="Customer",
            ),
            ObjectList(
                [
                    FieldPanel("reference_id", read_only=True),
                    FieldPanel("transaction_code", read_only=True),
                    FieldPanel("status", read_only=True),
                    MultiFieldPanel(
                        [
                            FieldPanel("total_amount", read_only=True),
                            FieldPanel("currency", read_only=True),
                        ],
                        heading="Snapshot",
                    ),
                ],
                heading="Order",
            ),
            ObjectList(
                [
                    FieldPanel("xendit_session_id", read_only=True),
                    FieldPanel("xendit_session_status", read_only=True),
                    FieldPanel("payment_link_url", read_only=True),
                    FieldPanel("session_expires_at", read_only=True),
                    FieldPanel("payment_id", read_only=True),
                    FieldPanel("payment_request_id", read_only=True),
                    FieldPanel("paid_at", read_only=True),
                    FieldPanel("email_sent_at", read_only=True),
                    FieldPanel("email_attempt_count", read_only=True),
                    FieldPanel("created_by", read_only=True),
                ],
                heading="Payment",
            ),
            ObjectList(
                [
                    FieldPanel("xendit_create_response", read_only=True),
                    FieldPanel("xendit_last_response", read_only=True),
                    FieldPanel("xendit_webhook_payload", read_only=True),
                    FieldPanel("email_last_error", read_only=True),
                ],
                heading="Audit",
            ),
        ]
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("product", "status"), name="saving_tx_product_status"),
            models.Index(fields=("reference_id", "status"), name="saving_tx_ref_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="saving_tx_amount_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name="saving_tx_total_gte_zero",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            if original:
                changed = [
                    field
                    for field in self.IMMUTABLE_FIELDS
                    if getattr(original, field) != getattr(self, field)
                ]
                if changed:
                    raise ValidationError(
                        "Transaksi simpanan immutable setelah dibuat: " + ", ".join(changed)
                    )
        if not self.reference_id:
            from django.utils import timezone

            token = secrets.token_hex(4).upper()
            stamp = timezone.localtime().strftime("%Y%m%d%H%M%S")
            self.reference_id = f"KS3-SAV-{stamp}-{token}"
        if not self.transaction_code:
            from django.utils import timezone

            token = secrets.token_hex(4).upper()
            self.transaction_code = f"KS3-STR-{timezone.localtime():%Y}-{token}"
        if not self.pk and self.amount is not None and self.service_fee is not None:
            self.total_amount = self.amount + self.service_fee
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        # Existing members must provide nomor_anggota
        if not self.is_new_member and not self.nomor_anggota:
            raise ValidationError(
                {"nomor_anggota": "Nomor anggota is required for existing members."}
            )
        # New members should not have a nomor_anggota
        if self.is_new_member and self.nomor_anggota:
            raise ValidationError(
                {"nomor_anggota": "New members should not provide a nomor anggota."}
            )
        # Total validation
        if (
            self.amount is not None
            and self.service_fee is not None
            and self.total_amount is not None
            and self.total_amount != self.amount + self.service_fee
        ):
            raise ValidationError(
                {"total_amount": "Total must equal amount + service fee."}
            )
        if self.status == self.Status.PAID and not self.paid_at:
            raise ValidationError({"paid_at": "Paid transactions require a paid timestamp."})
        if self.payment_channel == self.PaymentChannel.MANUAL and self.status != self.Status.PAID:
            raise ValidationError({"status": "Manual saving transactions must be marked paid."})

    @property
    def is_final(self):
        return self.status in {
            self.Status.PAID,
            self.Status.EXPIRED,
            self.Status.CANCELED,
            self.Status.FAILED,
        }

    @property
    def masked_nik(self):
        return f"************{self.nik[-4:]}" if self.nik else "-"

    def __str__(self):
        return self.transaction_code or str(self.public_id)
