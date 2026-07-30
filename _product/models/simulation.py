from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.models import Orderable


MONEY_FIELD = {"max_digits": 20, "decimal_places": 2, "null": True, "blank": True}


class ProductSimulation(ClusterableModel):
    class ProductKind(models.TextChoices):
        SAVINGS = "savings", "Simpanan"
        LOAN = "loan", "Pinjaman"

    class Strategy(models.TextChoices):
        SAVINGS_SIMPLE = "savings_simple", "Simpanan bunga sederhana"
        SAVINGS_COMPOUND = "savings_compound", "Simpanan bunga majemuk"
        SAVINGS_RECURRING = "savings_recurring", "Simpanan rutin"
        LOAN_FLAT = "loan_flat", "Pinjaman bunga flat"
        LOAN_DECLINING = "loan_declining", "Pinjaman pokok tetap / bunga menurun"
        LOAN_ANNUITY = "loan_annuity", "Pinjaman anuitas"
        LOAN_BULLET = "loan_bullet", "Pinjaman pokok dibayar di akhir"

    class TenorMode(models.TextChoices):
        RANGE = "range", "Rentang tenor"
        OPTIONS = "options", "Pilihan tenor tertentu"

    class RateMode(models.TextChoices):
        FIXED = "fixed", "Bunga tetap"
        TIERED = "tiered", "Bunga berdasarkan tier"

    class RateApplication(models.TextChoices):
        LOCKED = "locked_at_start", "Dikunci dari nominal awal dan tenor"
        CURRENT_BALANCE = "current_balance", "Dievaluasi dari saldo setiap periode"
        PROGRESSIVE = "progressive", "Progresif per lapisan saldo"

    class ContributionTiming(models.TextChoices):
        BEGINNING = "beginning", "Awal periode"
        END = "end", "Akhir periode"

    class BreakdownMode(models.TextChoices):
        AUTO_COMPACT = "auto_compact", "Otomatis ringkas (maks. 12 baris)"
        AUTO_DETAILED = "auto_detailed", "Otomatis detail (maks. 20 baris)"
        FIXED = "fixed", "Interval tetap"
        CUSTOM = "custom", "Aturan tenor custom"

    SAVINGS_STRATEGIES = {
        Strategy.SAVINGS_SIMPLE,
        Strategy.SAVINGS_COMPOUND,
        Strategy.SAVINGS_RECURRING,
    }
    LOAN_STRATEGIES = {
        Strategy.LOAN_FLAT,
        Strategy.LOAN_DECLINING,
        Strategy.LOAN_ANNUITY,
        Strategy.LOAN_BULLET,
    }
    BREAKDOWN_INTERVAL_CHOICES = (
        (1, "Bulanan"),
        (3, "Triwulanan"),
        (6, "Semester"),
        (12, "Tahunan"),
        (24, "Dua tahunan"),
    )

    product = models.OneToOneField(
        "_product.Product",
        on_delete=models.CASCADE,
        related_name="simulation",
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="Simulator hanya tampil ketika aktif dan seluruh konfigurasi wajib lengkap.",
    )
    product_kind = models.CharField(max_length=20, choices=ProductKind.choices)
    strategy = models.CharField(max_length=40, choices=Strategy.choices)

    amount_min = models.DecimalField(**MONEY_FIELD)
    amount_max = models.DecimalField(**MONEY_FIELD)
    amount_default = models.DecimalField(**MONEY_FIELD)
    amount_step = models.DecimalField(**MONEY_FIELD)
    tenor_mode = models.CharField(max_length=20, choices=TenorMode.choices, default=TenorMode.RANGE)
    tenor_min_months = models.PositiveIntegerField(null=True, blank=True)
    tenor_max_months = models.PositiveIntegerField(null=True, blank=True)
    tenor_default_months = models.PositiveIntegerField(null=True, blank=True)
    tenor_step_months = models.PositiveIntegerField(default=1)
    tenor_options = models.JSONField(
        default=list,
        blank=True,
        help_text="Daftar angka bulan, misalnya [3, 6, 12]. Dipakai hanya untuk mode pilihan tenor.",
    )

    recurring_min = models.DecimalField(**MONEY_FIELD)
    recurring_max = models.DecimalField(**MONEY_FIELD)
    recurring_default = models.DecimalField(**MONEY_FIELD)
    recurring_step = models.DecimalField(**MONEY_FIELD)
    contribution_timing = models.CharField(
        max_length=20,
        choices=ContributionTiming.choices,
        default=ContributionTiming.BEGINNING,
    )

    rate_mode = models.CharField(max_length=20, choices=RateMode.choices, default=RateMode.FIXED)
    base_annual_rate = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Persentase per tahun. Contoh: 6.5 berarti 6,5% p.a.",
    )
    rate_application = models.CharField(
        max_length=30,
        choices=RateApplication.choices,
        default=RateApplication.LOCKED,
    )

    breakdown_mode = models.CharField(
        max_length=30,
        choices=BreakdownMode.choices,
        default=BreakdownMode.AUTO_COMPACT,
    )
    fixed_breakdown_months = models.PositiveIntegerField(
        choices=BREAKDOWN_INTERVAL_CHOICES,
        default=1,
    )
    show_chart = models.BooleanField(default=True)
    show_table = models.BooleanField(default=True)

    simulator_title = models.CharField(max_length=160, blank=True, default="Simulasikan produk ini")
    simulator_description = models.TextField(
        blank=True,
        default="Atur nominal dan tenor untuk melihat estimasi hasil beserta rinciannya.",
    )
    disclaimer = models.TextField(
        blank=True,
        default=(
            "Hasil simulasi merupakan estimasi dan bukan penawaran atau persetujuan final. "
            "Nilai aktual mengikuti verifikasi dan ketentuan koperasi."
        ),
    )
    advanced_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Cadangan konfigurasi tervalidasi untuk strategy khusus; bukan formula bebas.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    edit_handler = TabbedInterface(
        [
            ObjectList(
                [
                    FieldPanel("product"),
                    FieldPanel("is_enabled"),
                    MultiFieldPanel(
                        [FieldPanel("product_kind"), FieldPanel("strategy")],
                        heading="Preset kalkulasi",
                    ),
                ],
                heading="Setup",
            ),
            ObjectList(
                [
                    MultiFieldPanel(
                        [
                            FieldPanel("amount_min"),
                            FieldPanel("amount_max"),
                            FieldPanel("amount_default"),
                            FieldPanel("amount_step"),
                        ],
                        heading="Nominal utama",
                    ),
                    MultiFieldPanel(
                        [
                            FieldPanel("tenor_mode"),
                            FieldPanel("tenor_min_months"),
                            FieldPanel("tenor_max_months"),
                            FieldPanel("tenor_default_months"),
                            FieldPanel("tenor_step_months"),
                            FieldPanel("tenor_options"),
                        ],
                        heading="Tenor",
                    ),
                    MultiFieldPanel(
                        [
                            FieldPanel("recurring_min"),
                            FieldPanel("recurring_max"),
                            FieldPanel("recurring_default"),
                            FieldPanel("recurring_step"),
                            FieldPanel("contribution_timing"),
                        ],
                        heading="Setoran rutin (khusus preset simpanan rutin)",
                    ),
                ],
                heading="Input anggota",
            ),
            ObjectList(
                [
                    MultiFieldPanel(
                        [
                            FieldPanel("rate_mode"),
                            FieldPanel("base_annual_rate"),
                            FieldPanel("rate_application"),
                        ],
                        heading="Kebijakan bunga",
                    ),
                    InlinePanel("rate_tiers", label="Tier bunga"),
                ],
                heading="Bunga",
            ),
            ObjectList(
                [InlinePanel("fee_rules", label="Biaya, pajak, dan potongan")],
                heading="Biaya & pajak",
            ),
            ObjectList(
                [
                    MultiFieldPanel(
                        [
                            FieldPanel("breakdown_mode"),
                            FieldPanel("fixed_breakdown_months"),
                            FieldPanel("show_chart"),
                            FieldPanel("show_table"),
                        ],
                        heading="Penyajian hasil",
                    ),
                    InlinePanel("breakdown_bands", label="Aturan breakdown custom"),
                    FieldPanel("simulator_title"),
                    FieldPanel("simulator_description"),
                    FieldPanel("disclaimer"),
                ],
                heading="Display",
            ),
            ObjectList([FieldPanel("advanced_config")], heading="Advanced"),
        ]
    )

    class Meta:
        ordering = ("product__title",)
        verbose_name = "Product simulator"
        verbose_name_plural = "Product simulators"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(base_annual_rate__isnull=True) | models.Q(base_annual_rate__gte=0),
                name="product_sim_base_rate_gte_zero",
            ),
            models.CheckConstraint(condition=models.Q(tenor_step_months__gt=0), name="product_sim_tenor_step_gt_zero"),
        ]

    def __str__(self):
        return f"Simulator: {self.product}"

    def _related(self, name):
        try:
            return list(getattr(self, name).all())
        except (ValueError, AttributeError):
            return []

    @property
    def requires_recurring_amount(self):
        return self.strategy == self.Strategy.SAVINGS_RECURRING

    def allowed_tenors(self):
        if self.tenor_mode == self.TenorMode.OPTIONS:
            values = self.tenor_options or []
            if not isinstance(values, list) or any(
                isinstance(value, bool) or not isinstance(value, int) or value <= 0 or value > 600
                for value in values
            ):
                return []
            return sorted(set(values))
        if not self.tenor_min_months or not self.tenor_max_months or self.tenor_max_months > 600:
            return []
        step = self.tenor_step_months or 1
        return list(range(self.tenor_min_months, self.tenor_max_months + 1, step))

    def configuration_errors(self):
        errors = []
        strategy_kind = (
            self.ProductKind.SAVINGS
            if self.strategy in self.SAVINGS_STRATEGIES
            else self.ProductKind.LOAN if self.strategy in self.LOAN_STRATEGIES else None
        )
        if strategy_kind != self.product_kind:
            errors.append("Preset kalkulasi tidak sesuai dengan jenis produk.")
        if self.strategy == self.Strategy.LOAN_FLAT and self.rate_application != self.RateApplication.LOCKED:
            errors.append("Pinjaman bunga flat harus mengunci bunga dari nominal awal dan tenor.")

        amount_values = [self.amount_min, self.amount_max, self.amount_default, self.amount_step]
        if any(value is None for value in amount_values):
            errors.append("Batas, default, dan kelipatan nominal wajib diisi.")
        elif self.amount_min < 0 or (self.amount_min == 0 and not self.requires_recurring_amount) or self.amount_step <= 0:
            errors.append(
                "Nominal minimum harus positif (boleh nol untuk simpanan rutin) dan kelipatannya harus lebih besar dari nol."
            )
        elif not self.amount_min <= self.amount_default <= self.amount_max:
            errors.append("Nominal default harus berada di antara minimum dan maksimum.")

        tenors = self.allowed_tenors()
        if not tenors:
            errors.append("Konfigurasi tenor belum lengkap atau tidak menghasilkan pilihan valid.")
        elif self.tenor_default_months not in tenors:
            errors.append("Tenor default harus termasuk tenor yang diperbolehkan.")

        if self.requires_recurring_amount:
            recurring_values = [self.recurring_min, self.recurring_max, self.recurring_default, self.recurring_step]
            if any(value is None for value in recurring_values):
                errors.append("Batas, default, dan kelipatan setoran rutin wajib diisi.")
            elif self.recurring_min < 0 or self.recurring_step <= 0:
                errors.append("Setoran minimum tidak boleh negatif dan kelipatannya harus lebih besar dari nol.")
            elif not self.recurring_min <= self.recurring_default <= self.recurring_max:
                errors.append("Setoran rutin default harus berada di antara minimum dan maksimum.")

        tiers = [tier for tier in self._related("rate_tiers") if tier.is_active]
        if self.rate_mode == self.RateMode.FIXED and self.base_annual_rate is None:
            errors.append("Bunga tahunan wajib diisi untuk mode bunga tetap.")
        if self.rate_mode == self.RateMode.TIERED and not tiers and self.base_annual_rate is None:
            errors.append("Mode tiered membutuhkan minimal satu tier bunga atau bunga dasar sebagai fallback.")
        if self.base_annual_rate is not None and self.base_annual_rate < 0:
            errors.append("Bunga tahunan tidak boleh negatif.")

        for index, left in enumerate(tiers):
            for right in tiers[index + 1 :]:
                if left.overlaps(right) and self.rate_application == self.RateApplication.PROGRESSIVE:
                    errors.append(
                        f'Tier progresif "{left.label}" dan "{right.label}" tidak boleh tumpang tindih.'
                    )
                elif left.priority == right.priority and left.overlaps(right):
                    errors.append(
                        f'Tier bunga "{left.label}" dan "{right.label}" tumpang tindih dengan prioritas yang sama.'
                    )

        if (
            self.rate_mode == self.RateMode.TIERED
            and tiers
            and self.base_annual_rate is None
            and self.amount_min is not None
            and self.amount_max is not None
            and tenors
        ):
            coverage_lower = Decimal("0") if self.rate_application != self.RateApplication.LOCKED else self.amount_min
            coverage_upper = self.amount_max
            if self.requires_recurring_amount and self.recurring_max is not None:
                coverage_upper += self.recurring_max * max(tenors)
            for tenor in tenors:
                eligible = [
                    tier
                    for tier in tiers
                    if tenor >= tier.min_tenor_months
                    and (tier.max_tenor_months is None or tenor <= tier.max_tenor_months)
                ]
                if self.rate_application != self.RateApplication.LOCKED and not any(
                    tier.max_amount is None for tier in eligible
                ):
                    errors.append(
                        f"Tier bunga untuk tenor {tenor} bulan harus memiliki batas nominal atas terbuka karena bunga mengikuti saldo."
                    )
                    break
                boundaries = {coverage_lower, coverage_upper}
                for tier in eligible:
                    if coverage_lower <= tier.min_amount <= coverage_upper:
                        boundaries.add(tier.min_amount)
                    if tier.max_amount is not None and coverage_lower <= tier.max_amount <= coverage_upper:
                        boundaries.add(tier.max_amount)
                ordered = sorted(boundaries)
                samples = set(ordered)
                samples.update((left + right) / 2 for left, right in zip(ordered, ordered[1:]) if right > left)
                if any(not any(tier.matches(sample, tenor) for tier in eligible) for sample in samples):
                    errors.append(
                        f"Tier bunga belum mencakup seluruh nominal untuk tenor {tenor} bulan. Tambahkan tier atau bunga dasar fallback."
                    )
                    break

        if self.breakdown_mode == self.BreakdownMode.CUSTOM:
            bands = [band for band in self._related("breakdown_bands") if band.is_active]
            if not bands:
                errors.append("Breakdown custom membutuhkan minimal satu aturan aktif.")
            for tenor in tenors:
                matches = [band for band in bands if band.matches(tenor)]
                if not matches:
                    errors.append(f"Belum ada aturan breakdown untuk tenor {tenor} bulan.")
                    break
                top_priority = max(band.priority for band in matches)
                if sum(band.priority == top_priority for band in matches) > 1:
                    errors.append(f"Aturan breakdown ambigu untuk tenor {tenor} bulan.")
                    break

        if not self.show_chart and not self.show_table:
            errors.append("Aktifkan minimal grafik atau tabel breakdown.")
        if not isinstance(self.advanced_config, dict):
            errors.append("Advanced config harus berupa object JSON.")
        return errors

    @property
    def is_ready(self):
        return not self.configuration_errors()

    def readiness(self):
        return "Siap" if self.is_ready else "Belum lengkap"

    readiness.short_description = "Kelengkapan"

    def clean(self):
        super().clean()
        field_errors = {}
        if self.amount_min is not None and self.amount_max is not None and self.amount_max < self.amount_min:
            field_errors["amount_max"] = "Nominal maksimum tidak boleh lebih kecil dari minimum."
        if self.tenor_min_months and self.tenor_max_months and self.tenor_max_months < self.tenor_min_months:
            field_errors["tenor_max_months"] = "Tenor maksimum tidak boleh lebih kecil dari minimum."
        if self.tenor_mode == self.TenorMode.OPTIONS:
            if not isinstance(self.tenor_options, list) or any(
                isinstance(value, bool) or not isinstance(value, int) or value <= 0 or value > 600
                for value in self.tenor_options
            ):
                field_errors["tenor_options"] = "Tenor options harus berupa daftar bulan positif, maksimal 600 bulan."
        if self.is_enabled:
            errors = self.configuration_errors()
            if errors:
                field_errors["is_enabled"] = errors
        if field_errors:
            raise ValidationError(field_errors)


class SimulationRateTier(Orderable):
    simulation = ParentalKey(ProductSimulation, on_delete=models.CASCADE, related_name="rate_tiers")
    label = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Angka lebih besar dipilih lebih dahulu saat aturan overlap.")
    min_amount = models.DecimalField(max_digits=20, decimal_places=2, default=Decimal("0"))
    max_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    min_tenor_months = models.PositiveIntegerField(default=1)
    max_tenor_months = models.PositiveIntegerField(null=True, blank=True)
    annual_rate = models.DecimalField(max_digits=9, decimal_places=6)

    panels = [
        FieldPanel("label"),
        FieldPanel("is_active"),
        FieldPanel("priority"),
        FieldPanel("min_amount"),
        FieldPanel("max_amount"),
        FieldPanel("min_tenor_months"),
        FieldPanel("max_tenor_months"),
        FieldPanel("annual_rate"),
    ]

    class Meta(Orderable.Meta):
        constraints = [
            models.CheckConstraint(condition=models.Q(min_amount__gte=0), name="sim_rate_tier_min_amount_gte_zero"),
            models.CheckConstraint(condition=models.Q(annual_rate__gte=0), name="sim_rate_tier_rate_gte_zero"),
        ]

    def __str__(self):
        return self.label

    def clean(self):
        super().clean()
        errors = {}
        if self.max_amount is not None and self.max_amount <= self.min_amount:
            errors["max_amount"] = "Batas maksimum harus lebih besar dari batas minimum."
        if self.max_tenor_months is not None and self.max_tenor_months < self.min_tenor_months:
            errors["max_tenor_months"] = "Tenor maksimum tidak boleh lebih kecil dari minimum."
        if self.annual_rate < 0:
            errors["annual_rate"] = "Bunga tidak boleh negatif."
        if errors:
            raise ValidationError(errors)

    def matches(self, amount, tenor_months):
        return (
            amount >= self.min_amount
            and (self.max_amount is None or amount < self.max_amount)
            and tenor_months >= self.min_tenor_months
            and (self.max_tenor_months is None or tenor_months <= self.max_tenor_months)
        )

    def overlaps(self, other):
        amount_overlap = (
            self.max_amount is None or other.min_amount < self.max_amount
        ) and (other.max_amount is None or self.min_amount < other.max_amount)
        tenor_overlap = (
            self.max_tenor_months is None or other.min_tenor_months <= self.max_tenor_months
        ) and (other.max_tenor_months is None or self.min_tenor_months <= other.max_tenor_months)
        return amount_overlap and tenor_overlap


class SimulationFeeRule(Orderable):
    class Category(models.TextChoices):
        ADMIN = "admin", "Biaya administrasi"
        PROVISION = "provision", "Provisi"
        INSURANCE = "insurance", "Asuransi"
        TAX = "tax", "Pajak"
        OTHER = "other", "Biaya lainnya"

    class Calculation(models.TextChoices):
        FIXED = "fixed", "Nominal tetap"
        PERCENTAGE = "percentage", "Persentase"

    class Basis(models.TextChoices):
        INITIAL_AMOUNT = "initial_amount", "Nominal awal"
        OPENING_BALANCE = "opening_balance", "Saldo awal periode"
        INTEREST = "interest", "Bunga periode"
        PAYMENT = "payment", "Pembayaran periode"
        TOTAL_INTEREST = "total_interest", "Total bunga"

    class Timing(models.TextChoices):
        UPFRONT = "upfront", "Di awal"
        PER_PERIOD = "per_period", "Setiap periode"
        MATURITY = "maturity", "Saat jatuh tempo"

    simulation = ParentalKey(ProductSimulation, on_delete=models.CASCADE, related_name="fee_rules")
    label = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.ADMIN)
    calculation = models.CharField(max_length=20, choices=Calculation.choices, default=Calculation.FIXED)
    basis = models.CharField(max_length=30, choices=Basis.choices, default=Basis.INITIAL_AMOUNT)
    timing = models.CharField(max_length=20, choices=Timing.choices, default=Timing.UPFRONT)
    value = models.DecimalField(max_digits=20, decimal_places=6)
    minimum_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    maximum_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    panels = [
        FieldPanel("label"),
        FieldPanel("is_active"),
        FieldPanel("category"),
        FieldPanel("calculation"),
        FieldPanel("basis"),
        FieldPanel("timing"),
        FieldPanel("value"),
        FieldPanel("minimum_amount"),
        FieldPanel("maximum_amount"),
    ]

    class Meta(Orderable.Meta):
        constraints = [models.CheckConstraint(condition=models.Q(value__gte=0), name="sim_fee_rule_value_gte_zero")]

    def __str__(self):
        return self.label

    def clean(self):
        super().clean()
        errors = {}
        if self.value < 0:
            errors["value"] = "Nilai biaya tidak boleh negatif."
        if self.calculation == self.Calculation.PERCENTAGE and self.value > 100:
            errors["value"] = "Persentase tidak boleh lebih dari 100%."
        if self.minimum_amount is not None and self.maximum_amount is not None and self.maximum_amount < self.minimum_amount:
            errors["maximum_amount"] = "Batas maksimum tidak boleh lebih kecil dari minimum."
        if self.timing == self.Timing.UPFRONT and self.basis not in {
            self.Basis.INITIAL_AMOUNT,
            self.Basis.OPENING_BALANCE,
        }:
            errors["basis"] = "Biaya di awal hanya dapat memakai nominal awal atau saldo awal."
        if self.timing != self.Timing.MATURITY and self.basis == self.Basis.TOTAL_INTEREST:
            errors["basis"] = "Basis total bunga hanya tersedia saat jatuh tempo."
        if errors:
            raise ValidationError(errors)


class SimulationBreakdownBand(Orderable):
    simulation = ParentalKey(ProductSimulation, on_delete=models.CASCADE, related_name="breakdown_bands")
    label = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    min_tenor_months = models.PositiveIntegerField(default=1)
    max_tenor_months = models.PositiveIntegerField(null=True, blank=True)
    interval_months = models.PositiveIntegerField(choices=ProductSimulation.BREAKDOWN_INTERVAL_CHOICES)

    panels = [
        FieldPanel("label"),
        FieldPanel("is_active"),
        FieldPanel("priority"),
        FieldPanel("min_tenor_months"),
        FieldPanel("max_tenor_months"),
        FieldPanel("interval_months"),
    ]

    def __str__(self):
        return self.label

    def clean(self):
        super().clean()
        if self.max_tenor_months is not None and self.max_tenor_months < self.min_tenor_months:
            raise ValidationError({"max_tenor_months": "Tenor maksimum tidak boleh lebih kecil dari minimum."})

    def matches(self, tenor_months):
        return tenor_months >= self.min_tenor_months and (
            self.max_tenor_months is None or tenor_months <= self.max_tenor_months
        )
