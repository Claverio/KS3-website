import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface


nik_validator = RegexValidator(r"^\d{16}$", "NIK must contain exactly 16 digits.")
phone_validator = RegexValidator(r"^\+?[0-9][0-9\s-]{7,19}$", "Enter a valid phone number.")


class P2PPurchase(models.Model):
    class Status(models.TextChoices):
        CREATING = "creating", "Creating payment"
        WAITING_PAYMENT = "waiting_payment", "Waiting for payment"
        PAID = "paid", "Paid"
        EXPIRED = "expired", "Expired"
        CANCELED = "canceled", "Canceled"
        FAILED = "failed", "Failed"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    reference_id = models.CharField(max_length=80, unique=True, editable=False)
    booking_number = models.CharField(max_length=80, unique=True, editable=False)
    project = models.ForeignKey("_p2p.P2P", on_delete=models.PROTECT, related_name="purchases")
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=24, validators=[phone_validator])
    email = models.EmailField()
    nik = models.CharField(max_length=16, blank=True, validators=[nik_validator])
    note = models.TextField(blank=True)
    slot_quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=18, decimal_places=2)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2)
    service_fee = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="IDR")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.CREATING, db_index=True)
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
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    FieldPanel("project", read_only=True),
                    FieldPanel("full_name"),
                    FieldPanel("phone"),
                    FieldPanel("email"),
                    FieldPanel("nik"),
                    FieldPanel("note"),
                ],
                heading="Customer",
            ),
            ObjectList(
                [
                    FieldPanel("reference_id", read_only=True),
                    FieldPanel("booking_number", read_only=True),
                    FieldPanel("status", read_only=True),
                    MultiFieldPanel(
                        [
                            FieldPanel("slot_quantity", read_only=True),
                            FieldPanel("unit_price", read_only=True),
                            FieldPanel("subtotal", read_only=True),
                            FieldPanel("service_fee", read_only=True),
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
                ],
                heading="Payment",
            ),
            ObjectList(
                [
                    FieldPanel("xendit_create_response", read_only=True),
                    FieldPanel("xendit_last_response", read_only=True),
                    FieldPanel("xendit_webhook_payload", read_only=True),
                ],
                heading="Audit",
            ),
        ]
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("project", "status"), name="p2p_purchase_project_status"),
            models.Index(fields=("reference_id", "status"), name="p2p_purchase_ref_status"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(slot_quantity__gt=0), name="p2p_purchase_slots_gt_zero"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="p2p_purchase_unit_price_gte_zero"),
            models.CheckConstraint(condition=models.Q(total_amount__gte=0), name="p2p_purchase_total_gte_zero"),
        ]

    @classmethod
    def reserving_statuses(cls):
        return (cls.Status.CREATING, cls.Status.WAITING_PAYMENT, cls.Status.PAID)

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

    def clean(self):
        super().clean()
        has_subtotal_parts = self.unit_price is not None and self.slot_quantity is not None
        if has_subtotal_parts and self.subtotal is not None and self.subtotal != self.unit_price * self.slot_quantity:
            raise ValidationError({"subtotal": "Subtotal does not match unit price × quantity."})
        has_total_parts = self.subtotal is not None and self.service_fee is not None
        if has_total_parts and self.total_amount is not None and self.total_amount != self.subtotal + self.service_fee:
            raise ValidationError({"total_amount": "Total must equal subtotal + service fee."})
        if self.status == self.Status.PAID and not self.paid_at:
            raise ValidationError({"paid_at": "Paid orders require a paid timestamp."})

    def __str__(self):
        return self.booking_number or str(self.public_id)
