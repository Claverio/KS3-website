from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface


MONEY_ZERO = Decimal("0")
IDR_QUANTUM = Decimal("1")


class XenditPaymentChannel(models.Model):
    class Category(models.TextChoices):
        VIRTUAL_ACCOUNT = "virtual_account", "Virtual Account"

    code = models.CharField(max_length=80, unique=True)
    display_name = models.CharField(max_length=120)
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        default=Category.VIRTUAL_ACCOUNT,
    )
    is_enabled = models.BooleanField(default=True)
    enabled_for_saving = models.BooleanField(default=True)
    enabled_for_p2p = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        MultiFieldPanel(
            [FieldPanel("code"), FieldPanel("display_name"), FieldPanel("category")],
            heading="Kanal Xendit",
        ),
        MultiFieldPanel(
            [
                FieldPanel("is_enabled"),
                FieldPanel("enabled_for_saving"),
                FieldPanel("enabled_for_p2p"),
                FieldPanel("sort_order"),
            ],
            heading="Ketersediaan",
        ),
    ]

    class Meta:
        db_table = "xendit_payment_channels"
        ordering = ("sort_order", "display_name")
        verbose_name = "Kanal pembayaran Xendit"
        verbose_name_plural = "Kanal pembayaran Xendit"

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if self.pk and self.transaction_fees.exists():
            original = type(self).objects.get(pk=self.pk)
            changed = [
                field
                for field in ("code", "category")
                if getattr(original, field) != getattr(self, field)
            ]
            if changed:
                raise ValidationError(
                    "Identitas kanal yang sudah dipakai transaksi tidak boleh diubah: "
                    + ", ".join(changed)
                )
        super().save(*args, **kwargs)


class XenditFeeRate(models.Model):
    class Source(models.TextChoices):
        MANUAL = "manual", "Manual/kontrak"
        OBSERVED = "observed", "Terdeteksi dari transaksi"
        LEGACY = "legacy", "Migrasi tarif lama"

    class Status(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        ACTIVE = "active", "Aktif"
        SUPERSEDED = "superseded", "Digantikan"

    channel = models.ForeignKey(
        XenditPaymentChannel,
        on_delete=models.PROTECT,
        related_name="fee_rates",
    )
    currency = models.CharField(max_length=3, default="IDR")
    fixed_fee = models.DecimalField(max_digits=18, decimal_places=2, default=MONEY_ZERO)
    percentage_fee = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=MONEY_ZERO,
        help_text="Persentase dari nominal pokok, misalnya 1.5000 untuk 1,5%.",
    )
    vat_percent = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=MONEY_ZERO,
        help_text="Persentase VAT/PPN atas fee provider.",
    )
    effective_from = models.DateTimeField(db_index=True)
    effective_to = models.DateTimeField(null=True, blank=True, db_index=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    source_reference = models.CharField(max_length=255, blank=True)
    observed_transaction_id = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    FieldPanel("channel"),
                    FieldPanel("currency"),
                    FieldPanel("fixed_fee"),
                    FieldPanel("percentage_fee"),
                    FieldPanel("vat_percent"),
                ],
                heading="Tarif",
            ),
            ObjectList(
                [
                    FieldPanel("effective_from"),
                    FieldPanel("effective_to"),
                    FieldPanel("status"),
                    FieldPanel("source"),
                    FieldPanel("source_reference"),
                    FieldPanel("observed_transaction_id", read_only=True),
                    FieldPanel("notes"),
                ],
                heading="Versi & audit",
            ),
        ]
    )

    class Meta:
        db_table = "xendit_fee_rates"
        ordering = ("channel", "-effective_from")
        constraints = [
            models.UniqueConstraint(
                fields=("channel", "currency", "effective_from"),
                name="payment_fee_rate_channel_currency_from_unique",
            ),
            models.CheckConstraint(
                condition=Q(fixed_fee__gte=0),
                name="payment_fee_rate_fixed_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(percentage_fee__gte=0),
                name="payment_fee_rate_percentage_gte_zero",
            ),
            models.CheckConstraint(
                condition=Q(vat_percent__gte=0),
                name="payment_fee_rate_vat_gte_zero",
            ),
        ]
        verbose_name = "Versi tarif Xendit"
        verbose_name_plural = "Versi tarif Xendit"

    def clean(self):
        super().clean()
        errors = {}
        if self.effective_to and self.effective_to <= self.effective_from:
            errors["effective_to"] = "Waktu selesai harus setelah waktu mulai."
        if self.status == self.Status.ACTIVE:
            overlap = XenditFeeRate.objects.filter(
                channel=self.channel,
                currency=self.currency,
                status=self.Status.ACTIVE,
            ).exclude(pk=self.pk)
            overlap = overlap.filter(
                Q(effective_to__isnull=True) | Q(effective_to__gt=self.effective_from)
            )
            if self.effective_to:
                overlap = overlap.filter(effective_from__lt=self.effective_to)
            if overlap.exists():
                errors["effective_from"] = "Periode tarif aktif tidak boleh overlap."
        if errors:
            raise ValidationError(errors)

    def calculate(self, principal_amount):
        principal = Decimal(principal_amount)
        fee_before_tax = self.fixed_fee + (
            principal * self.percentage_fee / Decimal("100")
        )
        vat = fee_before_tax * self.vat_percent / Decimal("100")
        quantum = IDR_QUANTUM if self.currency == "IDR" else Decimal("0.01")
        fee_before_tax = fee_before_tax.quantize(quantum, rounding=ROUND_HALF_UP)
        vat = vat.quantize(quantum, rounding=ROUND_HALF_UP)
        return fee_before_tax, vat, fee_before_tax + vat

    def save(self, *args, **kwargs):
        if self.pk and self.transaction_fees.exists():
            original = type(self).objects.get(pk=self.pk)
            definition_fields = (
                "channel_id", "currency", "fixed_fee", "percentage_fee",
                "vat_percent", "effective_from", "source",
            )
            changed = [
                field
                for field in definition_fields
                if getattr(original, field) != getattr(self, field)
            ]
            if changed:
                raise ValidationError(
                    "Definisi versi tarif yang sudah dipakai transaksi bersifat immutable: "
                    + ", ".join(changed)
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.channel.display_name} · {self.fixed_fee} · {self.effective_from:%Y-%m-%d}"


class XenditTransactionFee(models.Model):
    class ReconciliationStatus(models.TextChoices):
        PENDING = "pending", "Menunggu actual fee"
        MATCHED = "matched", "Sesuai"
        SHORT = "short", "Kurang"
        OVER = "over", "Lebih"
        ADJUSTED = "adjusted", "Sudah disesuaikan"
        MISSING = "missing", "Transaksi provider belum ditemukan"
        REVIEW = "review", "Perlu review"

    saving_transaction = models.OneToOneField(
        "_product.SavingTransaction",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="xendit_fee_snapshot",
    )
    p2p_purchase = models.OneToOneField(
        "_p2p.P2PPurchase",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="xendit_fee_snapshot",
    )
    channel = models.ForeignKey(
        XenditPaymentChannel,
        on_delete=models.PROTECT,
        related_name="transaction_fees",
    )
    rate = models.ForeignKey(
        XenditFeeRate,
        on_delete=models.PROTECT,
        related_name="transaction_fees",
    )
    currency = models.CharField(max_length=3, default="IDR")
    principal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    charged_fee_before_tax = models.DecimalField(max_digits=18, decimal_places=2)
    charged_fee_vat = models.DecimalField(max_digits=18, decimal_places=2, default=MONEY_ZERO)
    charged_fee_total = models.DecimalField(max_digits=18, decimal_places=2)
    rate_snapshot = models.JSONField(default=dict)
    allowed_payment_channels = models.JSONField(default=list)
    session_request_snapshot = models.JSONField(default=dict)
    session_response_snapshot = models.JSONField(default=dict)
    xendit_session_id = models.CharField(max_length=80, blank=True, db_index=True)

    provider_transaction_id = models.CharField(
        max_length=120,
        blank=True,
        unique=True,
        null=True,
    )
    provider_product_id = models.CharField(max_length=120, blank=True)
    provider_payment_request_id = models.CharField(max_length=120, blank=True)
    provider_reference_id = models.CharField(max_length=255, blank=True, db_index=True)
    provider_transaction_type = models.CharField(max_length=40, blank=True)
    provider_transaction_status = models.CharField(max_length=32, blank=True)
    provider_business_id = models.CharField(max_length=120, blank=True)
    actual_channel_category = models.CharField(max_length=40, blank=True)
    actual_channel_code = models.CharField(max_length=80, blank=True)
    actual_currency = models.CharField(max_length=3, blank=True)
    account_identifier = models.CharField(max_length=255, blank=True)
    cashflow = models.CharField(max_length=24, blank=True)
    actual_net_amount_currency = models.CharField(max_length=3, blank=True)
    actual_gross_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    actual_net_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    actual_xendit_fee = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    actual_vat = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    actual_xendit_withholding_tax = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    actual_third_party_withholding_tax = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    actual_fee_status = models.CharField(max_length=24, blank=True)
    settlement_status = models.CharField(max_length=24, blank=True)
    provider_created_at = models.DateTimeField(null=True, blank=True)
    provider_updated_at = models.DateTimeField(null=True, blank=True)
    estimated_settlement_at = models.DateTimeField(null=True, blank=True)
    actual_product_data = models.JSONField(default=dict)
    actual_payload = models.JSONField(default=dict)
    reconciliation_status = models.CharField(
        max_length=20,
        choices=ReconciliationStatus.choices,
        default=ReconciliationStatus.PENDING,
        db_index=True,
    )
    reconciliation_attempts = models.PositiveIntegerField(default=0)
    reconciliation_last_error = models.TextField(blank=True)
    reconciled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    FieldPanel("saving_transaction", read_only=True),
                    FieldPanel("p2p_purchase", read_only=True),
                    FieldPanel("channel", read_only=True),
                    FieldPanel("rate", read_only=True),
                    FieldPanel("principal_amount", read_only=True),
                    FieldPanel("charged_fee_before_tax", read_only=True),
                    FieldPanel("charged_fee_vat", read_only=True),
                    FieldPanel("charged_fee_total", read_only=True),
                    FieldPanel("rate_snapshot", read_only=True),
                ],
                heading="Snapshot tagihan",
            ),
            ObjectList(
                [
                    FieldPanel("xendit_session_id", read_only=True),
                    FieldPanel("provider_transaction_id", read_only=True),
                    FieldPanel("provider_transaction_status", read_only=True),
                    FieldPanel("actual_channel_code", read_only=True),
                    FieldPanel("actual_currency", read_only=True),
                    FieldPanel("actual_gross_amount", read_only=True),
                    FieldPanel("actual_net_amount", read_only=True),
                    FieldPanel("actual_xendit_fee", read_only=True),
                    FieldPanel("actual_vat", read_only=True),
                    FieldPanel("actual_fee_status", read_only=True),
                    FieldPanel("settlement_status", read_only=True),
                    FieldPanel("reconciliation_status", read_only=True),
                    FieldPanel("reconciled_at", read_only=True),
                ],
                heading="Actual Xendit",
            ),
            ObjectList(
                [
                    FieldPanel("allowed_payment_channels", read_only=True),
                    FieldPanel("session_request_snapshot", read_only=True),
                    FieldPanel("session_response_snapshot", read_only=True),
                    FieldPanel("actual_payload", read_only=True),
                    FieldPanel("actual_product_data", read_only=True),
                    FieldPanel("reconciliation_attempts", read_only=True),
                    FieldPanel("reconciliation_last_error", read_only=True),
                ],
                heading="Metadata & audit",
            ),
        ]
    )

    SNAPSHOT_FIELDS = (
        "saving_transaction_id",
        "p2p_purchase_id",
        "channel_id",
        "rate_id",
        "currency",
        "principal_amount",
        "charged_fee_before_tax",
        "charged_fee_vat",
        "charged_fee_total",
        "rate_snapshot",
        "allowed_payment_channels",
        "session_request_snapshot",
        "session_response_snapshot",
        "xendit_session_id",
    )

    class Meta:
        db_table = "xendit_fees"
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("reconciliation_status", "created_at"),
                name="payment_fee_recon_created",
            ),
            models.Index(
                fields=("actual_channel_code", "reconciled_at"),
                name="payment_fee_channel_recon",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(saving_transaction__isnull=False) & Q(p2p_purchase__isnull=True))
                    | (Q(saving_transaction__isnull=True) & Q(p2p_purchase__isnull=False))
                ),
                name="payment_fee_exactly_one_transaction",
            ),
            models.CheckConstraint(
                condition=Q(charged_fee_total__gte=0),
                name="payment_fee_charged_gte_zero",
            ),
        ]
        verbose_name = "Snapshot fee transaksi Xendit"
        verbose_name_plural = "Snapshot fee transaksi Xendit"

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            if original and original.xendit_session_id:
                changed = [
                    field
                    for field in self.SNAPSHOT_FIELDS
                    if getattr(original, field) != getattr(self, field)
                ]
                if changed:
                    raise ValidationError(
                        "Snapshot fee Xendit immutable setelah Payment Session dibuat: "
                        + ", ".join(changed)
                    )
        super().save(*args, **kwargs)

    @property
    def route_label(self):
        return "Nabung" if self.saving_transaction_id else "P2P"

    @property
    def transaction_reference(self):
        if self.saving_transaction_id:
            return self.saving_transaction.transaction_code
        return self.p2p_purchase.booking_number

    @property
    def actual_total_fee(self):
        if self.actual_xendit_fee is None:
            return None
        # Xendit's documented net amount is the gross amount less fee and VAT.
        # Withholding taxes remain separate audit fields and are not customer-facing
        # payment-gateway fees.
        return self.actual_xendit_fee + (self.actual_vat or MONEY_ZERO)

    @property
    def raw_variance(self):
        actual = self.actual_total_fee
        return None if actual is None else self.charged_fee_total - actual

    @property
    def allocated_adjustment(self):
        if hasattr(self, "adjustment_total"):
            return self.adjustment_total or MONEY_ZERO
        return self.adjustment_allocations.aggregate(total=Sum("amount"))["total"] or MONEY_ZERO

    @property
    def residual_variance(self):
        raw = self.raw_variance
        return None if raw is None else raw + self.allocated_adjustment

    def __str__(self):
        return f"{self.route_label} · {self.transaction_reference}"


class XenditReconciliationRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Berjalan"
        COMPLETED = "completed", "Selesai"
        COMPLETED_WITH_ERRORS = "completed_with_errors", "Selesai dengan error"
        FAILED = "failed", "Gagal"

    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.RUNNING)
    processed_count = models.PositiveIntegerField(default=0)
    matched_count = models.PositiveIntegerField(default=0)
    variance_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict)

    class Meta:
        db_table = "xendit_reconciliation_runs"
        ordering = ("-started_at",)

    def __str__(self):
        return f"Rekonsiliasi {self.started_at:%Y-%m-%d %H:%M}"


class XenditFeeAdjustment(models.Model):
    class Kind(models.TextChoices):
        PROVIDER_CREDIT = "provider_credit", "Kredit Xendit"
        PROVIDER_DEBIT = "provider_debit", "Debit Xendit"
        KS3_SUBSIDY = "ks3_subsidy", "Subsidi KS3"
        MANUAL_CORRECTION = "manual_correction", "Koreksi manual"
        REVERSAL = "reversal", "Reversal"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Disetujui"
        POSTED = "posted", "Posted"
        REVERSED = "reversed", "Dibatalkan"

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        help_text="Gunakan nilai positif untuk menutup kekurangan dan negatif untuk koreksi kelebihan.",
    )
    currency = models.CharField(max_length=3, default="IDR")
    kind = models.CharField(max_length=32, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    reason = models.TextField()
    external_reference = models.CharField(max_length=120, blank=True, db_index=True)
    evidence = models.ForeignKey(
        "wagtaildocs.Document",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="xendit_fee_adjustments",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_xendit_fee_adjustments",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_xendit_fee_adjustments",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    FieldPanel("amount"),
                    FieldPanel("currency"),
                    FieldPanel("kind"),
                    FieldPanel("reason"),
                    FieldPanel("external_reference"),
                    FieldPanel("evidence"),
                ],
                heading="Adjustment",
            ),
            ObjectList(
                [
                    FieldPanel("status", read_only=True),
                    FieldPanel("created_by", read_only=True),
                    FieldPanel("approved_by", read_only=True),
                    FieldPanel("approved_at", read_only=True),
                    FieldPanel("posted_at", read_only=True),
                ],
                heading="Approval & audit",
            ),
        ]
    )

    class Meta:
        db_table = "xendit_fee_adjustments"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=~Q(amount=0),
                name="payment_fee_adjustment_non_zero",
            )
        ]
        verbose_name = "Adjustment fee Xendit"
        verbose_name_plural = "Adjustment fee Xendit"

    @property
    def allocated_amount(self):
        return self.allocations.aggregate(total=Sum("amount"))["total"] or MONEY_ZERO

    @property
    def unallocated_amount(self):
        return self.amount - self.allocated_amount

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).first()
            if original and original.status in {self.Status.POSTED, self.Status.REVERSED}:
                mutable_audit_fields = {"status", "updated_at"}
                changed = {
                    field.name
                    for field in self._meta.concrete_fields
                    if field.name not in mutable_audit_fields
                    and getattr(original, field.attname) != getattr(self, field.attname)
                }
                if changed:
                    raise ValidationError("Adjustment posted bersifat immutable; gunakan reversal.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_kind_display()} · {self.amount}"


class XenditFeeAdjustmentAllocation(models.Model):
    adjustment = models.ForeignKey(
        XenditFeeAdjustment,
        on_delete=models.PROTECT,
        related_name="allocations",
    )
    transaction_fee = models.ForeignKey(
        XenditTransactionFee,
        on_delete=models.PROTECT,
        related_name="adjustment_allocations",
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "xendit_fee_adjustment_allocations"
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("adjustment", "transaction_fee"),
                name="payment_fee_adjustment_allocation_unique",
            ),
            models.CheckConstraint(
                condition=~Q(amount=0),
                name="payment_fee_allocation_non_zero",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.adjustment.currency != self.transaction_fee.currency:
            errors["amount"] = "Currency adjustment dan transaksi harus sama."
        if self.amount and self.adjustment.amount and (
            (self.amount > 0) != (self.adjustment.amount > 0)
        ):
            errors["amount"] = "Arah allocation harus sama dengan adjustment."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.adjustment_id} → {self.transaction_fee_id}: {self.amount}"

    def save(self, *args, **kwargs):
        if self.pk:
            original = type(self).objects.get(pk=self.pk)
            if (
                original.adjustment_id != self.adjustment_id
                or original.transaction_fee_id != self.transaction_fee_id
                or original.amount != self.amount
            ):
                raise ValidationError("Allocation adjustment bersifat immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.adjustment.status in {
            XenditFeeAdjustment.Status.POSTED,
            XenditFeeAdjustment.Status.REVERSED,
        }:
            raise ValidationError("Allocation adjustment posted tidak boleh dihapus.")
        return super().delete(*args, **kwargs)
