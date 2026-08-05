from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.fields import StreamField
from wagtail.models import PreviewableMixin

from backend.helper.streamfield import page_content_blocks
from _p2p.panels import PurchaseGraphPanel, PurchaseReportPanel


class P2P(PreviewableMixin, models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        CANCELED = "canceled", "Canceled"

    class InstallmentFrequency(models.TextChoices):
        MONTHLY = "monthly", "Bulanan"
        QUARTERLY = "quarterly", "Triwulanan"
        END_OF_TERM = "end_of_term", "Di akhir tenor"

    category = models.ForeignKey(
        "_p2p.P2PCategory", on_delete=models.PROTECT, related_name="projects"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    summary = models.TextField()
    content = StreamField(page_content_blocks(), use_json_field=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    target_amount = models.DecimalField(max_digits=18, decimal_places=2)
    slot_price = models.DecimalField(max_digits=18, decimal_places=2)
    service_fee = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("2750"))
    total_slots = models.PositiveIntegerField()
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2)
    tenor_months = models.PositiveIntegerField()
    installment_frequency = models.CharField(
        max_length=20,
        choices=InstallmentFrequency.choices,
        default=InstallmentFrequency.MONTHLY,
    )
    funding_deadline = models.DateTimeField()
    project_start_date = models.DateField()
    project_end_date = models.DateField()
    collateral = models.CharField(max_length=255, blank=True, default="Tidak ada")
    prospectus = models.ForeignKey(
        "wagtaildocs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    FieldPanel("category"),
                    FieldPanel("title"),
                    FieldPanel("slug"),
                    FieldPanel("summary"),
                    FieldPanel("content"),
                ],
                heading="Content",
            ),
            ObjectList(
                [
                    MultiFieldPanel(
                        [FieldPanel("target_amount"), FieldPanel("slot_price"), FieldPanel("total_slots")],
                        heading="Funding",
                    ),
                    MultiFieldPanel(
                        [FieldPanel("interest_rate"), FieldPanel("tenor_months"), FieldPanel("installment_frequency")],
                        heading="Return",
                    ),
                    FieldPanel("collateral"),
                    FieldPanel("prospectus"),
                ],
                heading="Investment",
            ),
            ObjectList(
                [FieldPanel("funding_deadline"), FieldPanel("project_start_date"), FieldPanel("project_end_date")],
                heading="Schedule",
            ),
            ObjectList(
                [FieldPanel("status"), FieldPanel("is_published"), FieldPanel("is_featured"), FieldPanel("sort_order")],
                heading="Publishing",
            ),
            ObjectList([PurchaseReportPanel()], heading="Pembelian"),
            ObjectList([PurchaseGraphPanel()], heading="Grafik"),
        ]
    )

    class Meta:
        ordering = ("sort_order", "-created_at")
        constraints = [
            models.CheckConstraint(condition=models.Q(slot_price__gt=0), name="p2p_slot_price_gt_zero"),
            models.CheckConstraint(condition=models.Q(total_slots__gt=0), name="p2p_total_slots_gt_zero"),
            models.CheckConstraint(condition=models.Q(target_amount__gt=0), name="p2p_target_amount_gt_zero"),
            models.CheckConstraint(condition=models.Q(interest_rate__gte=0), name="p2p_interest_rate_gte_zero"),
        ]
        verbose_name_plural = "Proyek"
        verbose_name = "Proyek"

    def clean(self):
        super().clean()
        errors = {}
        if self.project_start_date and self.project_end_date and self.project_end_date <= self.project_start_date:
            errors["project_end_date"] = "Project end date must be after the start date."
        if errors:
            raise ValidationError(errors)

    @cached_property
    def slot_totals(self):
        from .purchase import P2PPurchase

        totals = self.purchases.filter(
            status__in=P2PPurchase.reserving_statuses()
        ).aggregate(total=Coalesce(Sum("slot_quantity"), 0))
        paid = self.purchases.filter(status=P2PPurchase.Status.PAID).aggregate(
            total=Coalesce(Sum("slot_quantity"), 0)
        )
        return int(totals["total"]), int(paid["total"])

    @property
    def reserved_and_paid_slots(self):
        return self.slot_totals[0]

    @property
    def paid_slots(self):
        return self.slot_totals[1]

    @property
    def available_slots(self):
        return max(self.total_slots - self.reserved_and_paid_slots, 0)

    @property
    def funded_amount(self):
        return self.slot_price * self.paid_slots

    @property
    def lender_count(self):
        return self.purchases.filter(status="paid").values("email").distinct().count()

    @property
    def progress_percentage(self):
        return min(round((self.paid_slots / self.total_slots) * 100), 100)

    @property
    def can_purchase(self):
        return (
            self.is_published
            and self.status == self.Status.OPEN
            and self.funding_deadline > timezone.now()
            and self.available_slots > 0
        )

    @property
    def display_status(self):
        if self.available_slots == 0:
            return "Terkumpul"
        if self.available_slots <= max(round(self.total_slots * 0.1), 1):
            return "Hampir penuh"
        if self.can_purchase:
            return "Open"
        return self.get_status_display()

    def get_absolute_url(self):
        return reverse("p2p_details", kwargs={"slug": self.slug})

    def get_preview_template(self, request, mode_name):
        return "cms/pages/p2p_details.html"

    def get_preview_context(self, request, mode_name):
        return {"project": self, "streamfield": self.content}

    def __str__(self):
        return self.title
