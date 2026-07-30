from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from _product.models import ProductSimulation, SimulationBreakdownBand, SimulationFeeRule, SimulationRateTier
from _product.tests.factories import make_product, make_simulation


class ProductSimulationValidationTests(TestCase):
    def test_disabled_incomplete_configuration_is_allowed_but_not_ready(self):
        profile = ProductSimulation(
            product=make_product(),
            is_enabled=False,
            product_kind=ProductSimulation.ProductKind.SAVINGS,
            strategy=ProductSimulation.Strategy.SAVINGS_SIMPLE,
        )

        profile.full_clean()

        self.assertFalse(profile.is_ready)
        self.assertIn("Batas, default, dan kelipatan nominal wajib diisi.", profile.configuration_errors())

    def test_enabled_incomplete_configuration_is_rejected(self):
        profile = ProductSimulation(
            product=make_product(),
            is_enabled=True,
            product_kind=ProductSimulation.ProductKind.SAVINGS,
            strategy=ProductSimulation.Strategy.SAVINGS_SIMPLE,
        )

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("is_enabled", context.exception.message_dict)

    def test_complete_fixed_profile_is_ready(self):
        profile = make_simulation()

        profile.full_clean()

        self.assertTrue(profile.is_ready)

    def test_strategy_must_match_product_kind(self):
        profile = make_simulation(
            product_kind=ProductSimulation.ProductKind.LOAN,
            strategy=ProductSimulation.Strategy.SAVINGS_COMPOUND,
        )

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("Preset kalkulasi tidak sesuai", " ".join(context.exception.message_dict["is_enabled"]))

    def test_flat_loan_requires_locked_rate(self):
        profile = make_simulation(
            product_kind=ProductSimulation.ProductKind.LOAN,
            strategy=ProductSimulation.Strategy.LOAN_FLAT,
            rate_application=ProductSimulation.RateApplication.CURRENT_BALANCE,
        )

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("harus mengunci bunga", " ".join(context.exception.message_dict["is_enabled"]))

    def test_default_amount_must_be_inside_range(self):
        profile = make_simulation(amount_default=Decimal("500000"))

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_tenor_option_must_be_positive_integer_list(self):
        profile = make_simulation(
            tenor_mode=ProductSimulation.TenorMode.OPTIONS,
            tenor_options=[3, "6", -12],
            tenor_default_months=3,
        )

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("tenor_options", context.exception.message_dict)

    def test_tenor_option_cannot_exceed_fifty_years(self):
        profile = make_simulation(
            tenor_mode=ProductSimulation.TenorMode.OPTIONS,
            tenor_options=[12, 601],
            tenor_default_months=12,
        )

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("tenor_options", context.exception.message_dict)

    def test_tenor_is_limited_to_fifty_years(self):
        profile = make_simulation(tenor_max_months=601)

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("Konfigurasi tenor", " ".join(context.exception.message_dict["is_enabled"]))

    def test_recurring_strategy_requires_complete_recurring_inputs(self):
        profile = make_simulation(strategy=ProductSimulation.Strategy.SAVINGS_RECURRING)

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("setoran rutin wajib diisi", " ".join(context.exception.message_dict["is_enabled"]))

    def test_recurring_savings_can_start_from_zero_balance(self):
        profile = make_simulation(
            strategy=ProductSimulation.Strategy.SAVINGS_RECURRING,
            amount_min=Decimal("0"),
            amount_default=Decimal("0"),
            recurring_min=Decimal("100000"),
            recurring_max=Decimal("1000000"),
            recurring_default=Decimal("100000"),
            recurring_step=Decimal("100000"),
        )

        profile.full_clean()

        self.assertTrue(profile.is_ready)

    def test_disabled_profile_cannot_hide_invalid_range(self):
        profile = make_simulation(is_enabled=False, amount_min=Decimal("2000000"), amount_max=Decimal("1000000"))

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("amount_max", context.exception.message_dict)

    def test_at_least_chart_or_table_must_be_visible(self):
        profile = make_simulation(show_chart=False, show_table=False)

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("minimal grafik atau tabel", " ".join(context.exception.message_dict["is_enabled"]))

    def test_advanced_config_must_be_json_object(self):
        profile = make_simulation(advanced_config=["not", "an", "object"])

        with self.assertRaises(ValidationError):
            profile.full_clean()


class RateTierValidationTests(TestCase):
    def test_tier_bounds_are_lower_inclusive_upper_exclusive(self):
        tier = SimulationRateTier(
            simulation=make_simulation(),
            label="A sampai B",
            min_amount=Decimal("10000000"),
            max_amount=Decimal("20000000"),
            min_tenor_months=6,
            max_tenor_months=12,
            annual_rate=Decimal("6"),
        )

        self.assertTrue(tier.matches(Decimal("10000000"), 6))
        self.assertFalse(tier.matches(Decimal("20000000"), 6))
        self.assertTrue(tier.matches(Decimal("19999999.99"), 12))
        self.assertFalse(tier.matches(Decimal("10000000"), 13))

    def test_invalid_tier_range_is_rejected(self):
        tier = SimulationRateTier(
            simulation=make_simulation(),
            label="Invalid",
            min_amount=Decimal("10000000"),
            max_amount=Decimal("10000000"),
            annual_rate=Decimal("6"),
        )

        with self.assertRaises(ValidationError):
            tier.full_clean()

    def test_same_priority_overlapping_tiers_block_activation(self):
        profile = make_simulation(is_enabled=False, rate_mode=ProductSimulation.RateMode.TIERED, base_annual_rate=None)
        profile.rate_tiers.create(
            label="Tier satu",
            priority=0,
            min_amount=Decimal("0"),
            max_amount=Decimal("20000000"),
            annual_rate=Decimal("5"),
        )
        profile.rate_tiers.create(
            label="Tier dua",
            priority=0,
            min_amount=Decimal("10000000"),
            max_amount=None,
            annual_rate=Decimal("6"),
        )
        profile.is_enabled = True

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("tumpang tindih", " ".join(context.exception.message_dict["is_enabled"]))

    def test_different_priority_overlap_is_allowed_for_exception_rules(self):
        profile = make_simulation(is_enabled=False, rate_mode=ProductSimulation.RateMode.TIERED, base_annual_rate=Decimal("4"))
        profile.rate_tiers.create(
            label="General",
            priority=0,
            min_amount=Decimal("0"),
            annual_rate=Decimal("5"),
        )
        profile.rate_tiers.create(
            label="Promo",
            priority=10,
            min_amount=Decimal("10000000"),
            max_amount=Decimal("20000000"),
            annual_rate=Decimal("6"),
        )
        profile.is_enabled = True

        profile.full_clean()

        self.assertTrue(profile.is_ready)

    def test_progressive_tiers_may_not_overlap_even_with_different_priority(self):
        profile = make_simulation(
            is_enabled=False,
            rate_mode=ProductSimulation.RateMode.TIERED,
            rate_application=ProductSimulation.RateApplication.PROGRESSIVE,
            base_annual_rate=Decimal("4"),
        )
        profile.rate_tiers.create(label="One", priority=0, min_amount=0, max_amount=20000000, annual_rate=5)
        profile.rate_tiers.create(label="Two", priority=10, min_amount=10000000, annual_rate=6)
        profile.is_enabled = True

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_tiered_profile_without_fallback_must_cover_full_input_domain(self):
        profile = make_simulation(is_enabled=False, rate_mode=ProductSimulation.RateMode.TIERED, base_annual_rate=None)
        profile.rate_tiers.create(label="Only small", min_amount=0, max_amount=5000000, annual_rate=4)
        profile.is_enabled = True

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("belum mencakup seluruh nominal", " ".join(context.exception.message_dict["is_enabled"]))

    def test_current_balance_tiers_require_open_ended_top_band_without_fallback(self):
        profile = make_simulation(
            is_enabled=False,
            rate_mode=ProductSimulation.RateMode.TIERED,
            rate_application=ProductSimulation.RateApplication.CURRENT_BALANCE,
            base_annual_rate=None,
        )
        profile.rate_tiers.create(label="Bounded", min_amount=0, max_amount=200000000, annual_rate=4)
        profile.is_enabled = True

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("batas nominal atas terbuka", " ".join(context.exception.message_dict["is_enabled"]))


class FeeAndBreakdownValidationTests(TestCase):
    def test_percentage_fee_cannot_exceed_one_hundred_percent(self):
        rule = SimulationFeeRule(
            simulation=make_simulation(),
            label="Invalid tax",
            calculation=SimulationFeeRule.Calculation.PERCENTAGE,
            basis=SimulationFeeRule.Basis.INTEREST,
            timing=SimulationFeeRule.Timing.PER_PERIOD,
            value=Decimal("100.01"),
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_upfront_fee_cannot_use_future_interest(self):
        rule = SimulationFeeRule(
            simulation=make_simulation(),
            label="Invalid upfront",
            calculation=SimulationFeeRule.Calculation.PERCENTAGE,
            basis=SimulationFeeRule.Basis.TOTAL_INTEREST,
            timing=SimulationFeeRule.Timing.UPFRONT,
            value=Decimal("2"),
        )

        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_custom_breakdown_must_cover_every_available_tenor(self):
        profile = make_simulation(
            is_enabled=False,
            tenor_min_months=1,
            tenor_max_months=24,
            breakdown_mode=ProductSimulation.BreakdownMode.CUSTOM,
        )
        profile.breakdown_bands.create(
            label="Hanya satu tahun",
            min_tenor_months=1,
            max_tenor_months=12,
            interval_months=1,
        )
        profile.is_enabled = True

        with self.assertRaises(ValidationError) as context:
            profile.full_clean()

        self.assertIn("tenor 13 bulan", " ".join(context.exception.message_dict["is_enabled"]))

    def test_custom_breakdown_rejects_ambiguous_top_priority(self):
        profile = make_simulation(
            is_enabled=False,
            tenor_min_months=1,
            tenor_max_months=12,
            breakdown_mode=ProductSimulation.BreakdownMode.CUSTOM,
        )
        profile.breakdown_bands.create(label="One", priority=1, min_tenor_months=1, max_tenor_months=12, interval_months=1)
        profile.breakdown_bands.create(label="Two", priority=1, min_tenor_months=1, max_tenor_months=12, interval_months=3)
        profile.is_enabled = True

        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_breakdown_band_rejects_inverted_range(self):
        band = SimulationBreakdownBand(
            simulation=make_simulation(),
            label="Invalid",
            min_tenor_months=12,
            max_tenor_months=6,
            interval_months=1,
        )

        with self.assertRaises(ValidationError):
            band.full_clean()
