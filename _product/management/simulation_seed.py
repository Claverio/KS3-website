"""Deterministic simulator presets for the current KS3 product catalogue."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from _product.models import (
    Product,
    ProductSimulation,
    SimulationBreakdownBand,
    SimulationFeeRule,
    SimulationRateTier,
)


D = Decimal
SEED_VERSION = "ks3-current-products-v2"


def _common(**overrides):
    values = {
        "is_enabled": True,
        "product_kind": ProductSimulation.ProductKind.SAVINGS,
        "strategy": ProductSimulation.Strategy.SAVINGS_SIMPLE,
        "amount_min": D("100000"),
        "amount_max": D("100000000"),
        "amount_default": D("1000000"),
        "amount_step": D("100000"),
        "tenor_mode": ProductSimulation.TenorMode.RANGE,
        "tenor_min_months": 1,
        "tenor_max_months": 120,
        "tenor_default_months": 12,
        "tenor_step_months": 1,
        "tenor_options": [],
        "recurring_min": None,
        "recurring_max": None,
        "recurring_default": None,
        "recurring_step": None,
        "contribution_timing": ProductSimulation.ContributionTiming.BEGINNING,
        "rate_mode": ProductSimulation.RateMode.FIXED,
        "base_annual_rate": D("0"),
        "rate_application": ProductSimulation.RateApplication.LOCKED,
        "breakdown_mode": ProductSimulation.BreakdownMode.AUTO_COMPACT,
        "fixed_breakdown_months": 1,
        "show_chart": True,
        "show_table": True,
        "advanced_config": {
            "seed_profile": SEED_VERSION,
            "assumption_status": "illustrative",
        },
    }
    values.update(overrides)
    return values


SIMULATION_SEEDS = {
    "simpanan-wajib": {
        "profile": _common(
            strategy=ProductSimulation.Strategy.SAVINGS_RECURRING,
            amount_min=D("0"),
            amount_max=D("0"),
            amount_default=D("0"),
            amount_step=D("100000"),
            tenor_mode=ProductSimulation.TenorMode.OPTIONS,
            tenor_min_months=None,
            tenor_max_months=None,
            tenor_default_months=12,
            tenor_options=[12, 24, 36, 60],
            recurring_min=D("100000"),
            recurring_max=D("100000"),
            recurring_default=D("100000"),
            recurring_step=D("100000"),
            base_annual_rate=D("0"),
            simulator_title="Proyeksi Simpanan Wajib",
            simulator_description=(
                "Ilustrasi akumulasi setoran wajib Rp100.000 per bulan, dimulai dari saldo Rp0."
            ),
            disclaimer=(
                "Nominal Rp100.000 merupakan data seed ilustratif, bukan ketentuan resmi KS3. "
                "Proyeksi tidak memasukkan SHU karena SHU bukan bunga yang dijamin dan nilainya "
                "bergantung pada keputusan serta kinerja koperasi."
            ),
        ),
    },
    "simpanan-sukarela": {
        "profile": _common(
            strategy=ProductSimulation.Strategy.SAVINGS_RECURRING,
            amount_min=D("0"),
            amount_max=D("100000000"),
            amount_default=D("5000000"),
            amount_step=D("100000"),
            recurring_min=D("0"),
            recurring_max=D("5000000"),
            recurring_default=D("500000"),
            recurring_step=D("100000"),
            rate_application=ProductSimulation.RateApplication.CURRENT_BALANCE,
            base_annual_rate=D("3"),
            simulator_title="Simulasi Simpanan Sukarela",
            simulator_description=(
                "Proyeksikan saldo awal dan setoran bulanan fleksibel dengan asumsi jasa 3% per tahun."
            ),
            disclaimer=(
                "Jasa 3% p.a. adalah asumsi demonstrasi untuk menguji simulator, bukan penawaran "
                "atau ketentuan resmi KS3. Penarikan selama periode simulasi belum diperhitungkan."
            ),
        ),
    },
    "simpanan-berjangka": {
        "profile": _common(
            strategy=ProductSimulation.Strategy.SAVINGS_SIMPLE,
            amount_min=D("1000000"),
            amount_max=D("500000000"),
            amount_default=D("10000000"),
            amount_step=D("100000"),
            tenor_mode=ProductSimulation.TenorMode.OPTIONS,
            tenor_min_months=None,
            tenor_max_months=None,
            tenor_default_months=12,
            tenor_options=[3, 6, 12],
            rate_mode=ProductSimulation.RateMode.TIERED,
            base_annual_rate=None,
            rate_application=ProductSimulation.RateApplication.LOCKED,
            simulator_title="Simulasi Simpanan Berjangka",
            simulator_description=(
                "Bandingkan tenor 3, 6, atau 12 bulan dengan tier jasa berdasarkan nominal penempatan."
            ),
            disclaimer=(
                "Seluruh rate dan pajak pada simulator ini adalah data seed ilustratif, bukan "
                "penawaran resmi KS3. Nilai final wajib mengikuti lembar ketentuan produk dan "
                "peraturan perpajakan yang berlaku saat transaksi."
            ),
        ),
        "rate_tiers": [
            {"label": "3 bulan < Rp10 juta", "min_amount": D("0"), "max_amount": D("10000000"), "min_tenor_months": 3, "max_tenor_months": 3, "annual_rate": D("3.5")},
            {"label": "3 bulan ≥ Rp10 juta", "min_amount": D("10000000"), "max_amount": None, "min_tenor_months": 3, "max_tenor_months": 3, "annual_rate": D("4")},
            {"label": "6 bulan < Rp10 juta", "min_amount": D("0"), "max_amount": D("10000000"), "min_tenor_months": 6, "max_tenor_months": 6, "annual_rate": D("4")},
            {"label": "6 bulan ≥ Rp10 juta", "min_amount": D("10000000"), "max_amount": None, "min_tenor_months": 6, "max_tenor_months": 6, "annual_rate": D("4.5")},
            {"label": "12 bulan < Rp10 juta", "min_amount": D("0"), "max_amount": D("10000000"), "min_tenor_months": 12, "max_tenor_months": 12, "annual_rate": D("4.5")},
            {"label": "12 bulan ≥ Rp10 juta", "min_amount": D("10000000"), "max_amount": None, "min_tenor_months": 12, "max_tenor_months": 12, "annual_rate": D("5.25")},
        ],
        "fee_rules": [
            {
                "label": "Pajak hasil ilustratif 20%",
                "category": SimulationFeeRule.Category.TAX,
                "calculation": SimulationFeeRule.Calculation.PERCENTAGE,
                "basis": SimulationFeeRule.Basis.TOTAL_INTEREST,
                "timing": SimulationFeeRule.Timing.MATURITY,
                "value": D("20"),
            }
        ],
    },
    "simpanan-pokok": {
        "profile": _common(
            is_enabled=False,
            strategy=ProductSimulation.Strategy.SAVINGS_SIMPLE,
            amount_min=D("100000"),
            amount_max=D("100000"),
            amount_default=D("100000"),
            amount_step=D("100000"),
            tenor_mode=ProductSimulation.TenorMode.OPTIONS,
            tenor_min_months=None,
            tenor_max_months=None,
            tenor_default_months=1,
            tenor_options=[1],
            base_annual_rate=D("0"),
            show_chart=False,
            show_table=True,
            simulator_title="Ilustrasi Simpanan Pokok",
            simulator_description="Setoran satu kali pada awal keanggotaan.",
            disclaimer=(
                "Simulator publik dinonaktifkan karena Simpanan Pokok merupakan setoran satu kali, "
                "bukan produk pertumbuhan berkala. Nominal Rp100.000 hanya data seed ilustratif."
            ),
        ),
    },
    "simpanan-lain": {
        "profile": _common(
            strategy=ProductSimulation.Strategy.SAVINGS_RECURRING,
            amount_min=D("0"),
            amount_max=D("200000000"),
            amount_default=D("1000000"),
            amount_step=D("100000"),
            tenor_mode=ProductSimulation.TenorMode.OPTIONS,
            tenor_min_months=None,
            tenor_max_months=None,
            tenor_default_months=36,
            tenor_options=[12, 24, 36, 60, 120],
            recurring_min=D("100000"),
            recurring_max=D("10000000"),
            recurring_default=D("500000"),
            recurring_step=D("100000"),
            rate_application=ProductSimulation.RateApplication.CURRENT_BALANCE,
            base_annual_rate=D("3.25"),
            simulator_title="Simulasi Tabungan Tujuan",
            simulator_description=(
                "Proyeksikan dana pendidikan, hari tua, rekreasi, atau tujuan lain dengan setoran rutin."
            ),
            disclaimer=(
                "Jasa 3,25% p.a. adalah asumsi demonstrasi dan bukan ketentuan resmi KS3. "
                "Hasil aktual mengikuti produk tujuan yang dipilih, biaya, pajak, dan kebijakan pencairan."
            ),
        ),
    },
    "pinjaman-reguler": {
        "profile": _common(
            product_kind=ProductSimulation.ProductKind.LOAN,
            strategy=ProductSimulation.Strategy.LOAN_FLAT,
            amount_min=D("1000000"),
            amount_max=D("50000000"),
            amount_default=D("12000000"),
            amount_step=D("500000"),
            tenor_mode=ProductSimulation.TenorMode.OPTIONS,
            tenor_min_months=None,
            tenor_max_months=None,
            tenor_default_months=12,
            tenor_options=[6, 12, 18, 24],
            rate_mode=ProductSimulation.RateMode.FIXED,
            base_annual_rate=D("12"),
            rate_application=ProductSimulation.RateApplication.LOCKED,
            breakdown_mode=ProductSimulation.BreakdownMode.AUTO_COMPACT,
            simulator_title="Simulasi Pinjaman Reguler",
            simulator_description=(
                "Hitung angsuran flat dengan pemisahan pokok, bunga, total pembayaran, dan sisa pinjaman."
            ),
            disclaimer=(
                "Bunga flat 12% p.a. dan seluruh batas nominal pada simulator ini adalah data "
                "demonstrasi, bukan penawaran atau persetujuan pembiayaan resmi KS3. Hasil final "
                "mengikuti analisis kelayakan, dokumen produk, dan keputusan koperasi."
            ),
        ),
    },
    "pinjaman-usaha-produktif": {
        "profile": _common(
            product_kind=ProductSimulation.ProductKind.LOAN,
            strategy=ProductSimulation.Strategy.LOAN_ANNUITY,
            amount_min=D("10000000"),
            amount_max=D("500000000"),
            amount_default=D("250000000"),
            amount_step=D("1000000"),
            tenor_mode=ProductSimulation.TenorMode.OPTIONS,
            tenor_min_months=None,
            tenor_max_months=None,
            tenor_default_months=36,
            tenor_options=[12, 24, 36, 48, 60],
            rate_mode=ProductSimulation.RateMode.TIERED,
            base_annual_rate=None,
            rate_application=ProductSimulation.RateApplication.PROGRESSIVE,
            breakdown_mode=ProductSimulation.BreakdownMode.CUSTOM,
            simulator_title="Simulasi Pinjaman Usaha Produktif",
            simulator_description=(
                "Uji anuitas dengan rate progresif, potongan biaya awal, biaya bulanan, dan breakdown adaptif."
            ),
            disclaimer=(
                "Tier bunga 10%–13% p.a., provisi, administrasi, asuransi, dan biaya layanan pada "
                "simulator ini seluruhnya merupakan asumsi demonstrasi. Nilai tersebut bukan "
                "penawaran atau persetujuan resmi KS3 dan wajib diganti sesuai hasil analisis serta dokumen produk."
            ),
        ),
        "rate_tiers": [
            {
                "label": "Lapisan sisa pokok Rp0–<Rp50 juta",
                "min_amount": D("0"),
                "max_amount": D("50000000"),
                "min_tenor_months": 1,
                "max_tenor_months": 60,
                "annual_rate": D("10"),
            },
            {
                "label": "Lapisan sisa pokok Rp50–<Rp150 juta",
                "min_amount": D("50000000"),
                "max_amount": D("150000000"),
                "min_tenor_months": 1,
                "max_tenor_months": 60,
                "annual_rate": D("11.5"),
            },
            {
                "label": "Lapisan sisa pokok mulai Rp150 juta",
                "min_amount": D("150000000"),
                "max_amount": None,
                "min_tenor_months": 1,
                "max_tenor_months": 60,
                "annual_rate": D("13"),
            },
        ],
        "fee_rules": [
            {
                "label": "Provisi ilustratif 1%",
                "category": SimulationFeeRule.Category.PROVISION,
                "calculation": SimulationFeeRule.Calculation.PERCENTAGE,
                "basis": SimulationFeeRule.Basis.INITIAL_AMOUNT,
                "timing": SimulationFeeRule.Timing.UPFRONT,
                "value": D("1"),
                "minimum_amount": D("250000"),
                "maximum_amount": D("2000000"),
            },
            {
                "label": "Administrasi ilustratif",
                "category": SimulationFeeRule.Category.ADMIN,
                "calculation": SimulationFeeRule.Calculation.FIXED,
                "basis": SimulationFeeRule.Basis.INITIAL_AMOUNT,
                "timing": SimulationFeeRule.Timing.UPFRONT,
                "value": D("100000"),
            },
            {
                "label": "Asuransi ilustratif 0,5%",
                "category": SimulationFeeRule.Category.INSURANCE,
                "calculation": SimulationFeeRule.Calculation.PERCENTAGE,
                "basis": SimulationFeeRule.Basis.INITIAL_AMOUNT,
                "timing": SimulationFeeRule.Timing.UPFRONT,
                "value": D("0.5"),
                "minimum_amount": D("100000"),
                "maximum_amount": D("1500000"),
            },
            {
                "label": "Biaya layanan bulanan ilustratif",
                "category": SimulationFeeRule.Category.ADMIN,
                "calculation": SimulationFeeRule.Calculation.FIXED,
                "basis": SimulationFeeRule.Basis.PAYMENT,
                "timing": SimulationFeeRule.Timing.PER_PERIOD,
                "value": D("15000"),
            },
        ],
        "breakdown_bands": [
            {
                "label": "Sampai 12 bulan: detail bulanan",
                "priority": 10,
                "min_tenor_months": 1,
                "max_tenor_months": 12,
                "interval_months": 1,
            },
            {
                "label": "13–36 bulan: ringkas per triwulan",
                "priority": 10,
                "min_tenor_months": 13,
                "max_tenor_months": 36,
                "interval_months": 3,
            },
            {
                "label": "37–60 bulan: ringkas per semester",
                "priority": 10,
                "min_tenor_months": 37,
                "max_tenor_months": 60,
                "interval_months": 6,
            },
        ],
    },
}


def _replace_children(simulation, model, definitions):
    model.objects.filter(simulation=simulation).delete()
    for sort_order, definition in enumerate(definitions or []):
        child = model(simulation=simulation, sort_order=sort_order, **definition)
        child.full_clean()
        child.save()


@transaction.atomic
def seed_product_simulations(*, strict=False):
    """Create or replace deterministic simulator profiles for known product slugs."""

    products = Product.objects.in_bulk(SIMULATION_SEEDS, field_name="slug")
    missing = sorted(set(SIMULATION_SEEDS) - set(products))
    if strict and missing:
        raise ValidationError(f"Produk seed tidak ditemukan: {', '.join(missing)}")

    seeded = []
    for slug, seed in SIMULATION_SEEDS.items():
        product = products.get(slug)
        if product is None:
            continue
        simulation, _ = ProductSimulation.objects.update_or_create(
            product=product,
            defaults=seed["profile"],
        )
        _replace_children(simulation, SimulationRateTier, seed.get("rate_tiers"))
        _replace_children(simulation, SimulationFeeRule, seed.get("fee_rules"))
        _replace_children(
            simulation,
            SimulationBreakdownBand,
            seed.get("breakdown_bands"),
        )
        errors = simulation.configuration_errors()
        if errors:
            raise ValidationError({"is_enabled": errors})
        simulation.full_clean()
        simulation.save()
        seeded.append(simulation)
    return seeded, missing
