from decimal import Decimal, ROUND_HALF_UP

from django.test import TestCase

from _product.models import ProductSimulation, SimulationFeeRule
from _product.simulation import SimulationValidationError, public_config, simulate
from _product.tests.factories import make_simulation


Q = Decimal("0.01")


def q(value):
    return Decimal(value).quantize(Q, rounding=ROUND_HALF_UP)


class SavingsStrategyTests(TestCase):
    def test_simple_savings_one_year(self):
        profile = make_simulation(strategy=ProductSimulation.Strategy.SAVINGS_SIMPLE)

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["gross_interest"], "1440000.00")
        self.assertEqual(result["summary"]["net_interest"], "1440000.00")
        self.assertEqual(result["summary"]["maturity_balance"], "13440000.00")
        self.assertEqual(len(result["breakdown"]), 12)
        self.assertEqual(result["breakdown"][0]["interest"], "120000.00")

    def test_compound_savings_rounds_every_month(self):
        profile = make_simulation(strategy=ProductSimulation.Strategy.SAVINGS_COMPOUND)
        expected = Decimal("12000000")
        expected_interest = Decimal("0")
        for _ in range(12):
            interest = q(expected * Decimal("0.01"))
            expected += interest
            expected_interest += interest

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["maturity_balance"], f"{q(expected):f}")
        self.assertEqual(result["summary"]["gross_interest"], f"{q(expected_interest):f}")
        self.assertGreater(Decimal(result["summary"]["gross_interest"]), Decimal("1440000"))

    def test_recurring_savings_supports_beginning_contributions(self):
        profile = make_simulation(
            strategy=ProductSimulation.Strategy.SAVINGS_RECURRING,
            amount_min=Decimal("1000000"),
            amount_default=Decimal("1000000"),
            recurring_min=Decimal("100000"),
            recurring_max=Decimal("5000000"),
            recurring_default=Decimal("100000"),
            recurring_step=Decimal("100000"),
        )

        result = simulate(
            profile,
            {"amount": "1000000", "tenor_months": "12", "recurring_amount": "100000"},
        )

        self.assertEqual(result["summary"]["total_contributions"], "2200000.00")
        self.assertGreater(Decimal(result["summary"]["maturity_balance"]), Decimal("2200000"))
        self.assertEqual(result["breakdown"][0]["inflow"], "100000.00")

    def test_recurring_end_of_period_earns_less_than_beginning(self):
        common = {
            "strategy": ProductSimulation.Strategy.SAVINGS_RECURRING,
            "amount_min": Decimal("1000000"),
            "amount_default": Decimal("1000000"),
            "recurring_min": Decimal("100000"),
            "recurring_max": Decimal("5000000"),
            "recurring_default": Decimal("100000"),
            "recurring_step": Decimal("100000"),
        }
        beginning = make_simulation(**common)
        ending = make_simulation(
            **common,
            product=None,
            contribution_timing=ProductSimulation.ContributionTiming.END,
        )
        data = {"amount": "1000000", "tenor_months": "12", "recurring_amount": "100000"}

        beginning_result = simulate(beginning, data)
        ending_result = simulate(ending, data)

        self.assertGreater(
            Decimal(beginning_result["summary"]["gross_interest"]),
            Decimal(ending_result["summary"]["gross_interest"]),
        )

    def test_interest_tax_is_visible_and_reduces_maturity_balance(self):
        profile = make_simulation(strategy=ProductSimulation.Strategy.SAVINGS_SIMPLE)
        profile.fee_rules.create(
            label="Pajak bunga 20%",
            category=SimulationFeeRule.Category.TAX,
            calculation=SimulationFeeRule.Calculation.PERCENTAGE,
            basis=SimulationFeeRule.Basis.INTEREST,
            timing=SimulationFeeRule.Timing.PER_PERIOD,
            value=Decimal("20"),
        )

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["gross_interest"], "1440000.00")
        self.assertEqual(result["summary"]["total_tax"], "288000.00")
        self.assertEqual(result["summary"]["net_interest"], "1152000.00")
        self.assertEqual(result["summary"]["maturity_balance"], "13152000.00")

    def test_compound_savings_period_fee_affects_next_interest_base(self):
        profile = make_simulation(strategy=ProductSimulation.Strategy.SAVINGS_COMPOUND)
        profile.fee_rules.create(
            label="Admin bulanan",
            category=SimulationFeeRule.Category.ADMIN,
            calculation=SimulationFeeRule.Calculation.FIXED,
            basis=SimulationFeeRule.Basis.OPENING_BALANCE,
            timing=SimulationFeeRule.Timing.PER_PERIOD,
            value=Decimal("10000"),
        )

        charged = simulate(profile, {"amount": "12000000", "tenor_months": "12"})
        uncharged = simulate(make_simulation(strategy=ProductSimulation.Strategy.SAVINGS_COMPOUND), {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(charged["summary"]["total_fees"], "120000.00")
        self.assertLess(Decimal(charged["summary"]["gross_interest"]), Decimal(uncharged["summary"]["gross_interest"]))

    def test_upfront_savings_fee_is_reported_once_and_not_deducted_twice(self):
        profile = make_simulation(strategy=ProductSimulation.Strategy.SAVINGS_COMPOUND)
        profile.fee_rules.create(
            label="Biaya pembukaan",
            category=SimulationFeeRule.Category.ADMIN,
            calculation=SimulationFeeRule.Calculation.FIXED,
            basis=SimulationFeeRule.Basis.INITIAL_AMOUNT,
            timing=SimulationFeeRule.Timing.UPFRONT,
            value=Decimal("100000"),
        )

        result = simulate(profile, {"amount": "12000000", "tenor_months": "1"})

        self.assertEqual(result["summary"]["total_fees"], "100000.00")
        self.assertEqual(result["summary"]["gross_interest"], "119000.00")
        self.assertEqual(result["summary"]["maturity_balance"], "12019000.00")
        self.assertEqual(result["breakdown"][0]["fees"], "100000.00")


class LoanStrategyTests(TestCase):
    def loan_profile(self, strategy, **overrides):
        return make_simulation(
            product_kind=ProductSimulation.ProductKind.LOAN,
            strategy=strategy,
            **overrides,
        )

    def test_flat_loan_has_constant_interest_and_payment(self):
        profile = self.loan_profile(ProductSimulation.Strategy.LOAN_FLAT)

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["total_principal"], "12000000.00")
        self.assertEqual(result["summary"]["total_interest"], "1440000.00")
        self.assertEqual(result["summary"]["total_scheduled_payment"], "13440000.00")
        self.assertEqual(result["summary"]["installment_min"], "1120000.00")
        self.assertEqual(result["summary"]["installment_max"], "1120000.00")
        self.assertEqual(result["breakdown"][-1]["closing_balance"], "0.00")

    def test_declining_loan_interest_falls_with_outstanding_balance(self):
        profile = self.loan_profile(ProductSimulation.Strategy.LOAN_DECLINING)

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["total_interest"], "780000.00")
        self.assertEqual(result["breakdown"][0]["interest"], "120000.00")
        self.assertEqual(result["breakdown"][-1]["interest"], "10000.00")
        self.assertEqual(result["breakdown"][-1]["closing_balance"], "0.00")

    def test_annuity_reconciles_principal_and_closes_at_zero(self):
        profile = self.loan_profile(ProductSimulation.Strategy.LOAN_ANNUITY)

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["total_principal"], "12000000.00")
        self.assertEqual(result["breakdown"][-1]["closing_balance"], "0.00")
        self.assertLessEqual(
            Decimal(result["summary"]["installment_max"]) - Decimal(result["summary"]["installment_min"]),
            Decimal("0.10"),
        )

    def test_zero_rate_annuity_divides_principal_evenly(self):
        profile = self.loan_profile(ProductSimulation.Strategy.LOAN_ANNUITY, base_annual_rate=Decimal("0"))

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["total_interest"], "0.00")
        self.assertEqual(result["summary"]["installment_min"], "1000000.00")
        self.assertEqual(result["summary"]["installment_max"], "1000000.00")

    def test_bullet_loan_pays_principal_only_at_maturity(self):
        profile = self.loan_profile(ProductSimulation.Strategy.LOAN_BULLET)

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["breakdown"][0]["principal"], "0.00")
        self.assertEqual(result["breakdown"][-1]["principal"], "12000000.00")
        self.assertEqual(result["breakdown"][-1]["payment"], "12120000.00")
        self.assertEqual(result["breakdown"][-1]["closing_balance"], "0.00")

    def test_upfront_provision_reduces_net_disbursement_not_installment(self):
        profile = self.loan_profile(ProductSimulation.Strategy.LOAN_FLAT)
        profile.fee_rules.create(
            label="Provisi 2%",
            category=SimulationFeeRule.Category.PROVISION,
            calculation=SimulationFeeRule.Calculation.PERCENTAGE,
            basis=SimulationFeeRule.Basis.INITIAL_AMOUNT,
            timing=SimulationFeeRule.Timing.UPFRONT,
            value=Decimal("2"),
        )

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["net_disbursed"], "11760000.00")
        self.assertEqual(result["summary"]["total_fees"], "240000.00")
        self.assertEqual(result["summary"]["total_scheduled_payment"], "13440000.00")
        self.assertEqual(result["summary"]["total_cost"], "1680000.00")
        self.assertEqual(result["chart"][-1]["cumulative_total"], "13440000.00")

    def test_upfront_loan_charges_cannot_exceed_disbursement(self):
        profile = self.loan_profile(ProductSimulation.Strategy.LOAN_FLAT)
        profile.fee_rules.create(
            label="Biaya tidak valid",
            category=SimulationFeeRule.Category.ADMIN,
            calculation=SimulationFeeRule.Calculation.FIXED,
            basis=SimulationFeeRule.Basis.INITIAL_AMOUNT,
            timing=SimulationFeeRule.Timing.UPFRONT,
            value=Decimal("13000000"),
        )

        with self.assertRaises(SimulationValidationError) as context:
            simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertIn("configuration", context.exception.errors)

    def test_periodic_admin_fee_is_added_to_each_payment(self):
        profile = self.loan_profile(ProductSimulation.Strategy.LOAN_FLAT)
        profile.fee_rules.create(
            label="Admin bulanan",
            category=SimulationFeeRule.Category.ADMIN,
            calculation=SimulationFeeRule.Calculation.FIXED,
            basis=SimulationFeeRule.Basis.PAYMENT,
            timing=SimulationFeeRule.Timing.PER_PERIOD,
            value=Decimal("10000"),
        )

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["total_fees"], "120000.00")
        self.assertEqual(result["summary"]["total_scheduled_payment"], "13560000.00")
        self.assertEqual(result["breakdown"][0]["payment"], "1130000.00")

    def test_maturity_fee_can_use_total_interest(self):
        profile = self.loan_profile(ProductSimulation.Strategy.LOAN_FLAT)
        profile.fee_rules.create(
            label="Biaya akhir",
            category=SimulationFeeRule.Category.OTHER,
            calculation=SimulationFeeRule.Calculation.PERCENTAGE,
            basis=SimulationFeeRule.Basis.TOTAL_INTEREST,
            timing=SimulationFeeRule.Timing.MATURITY,
            value=Decimal("10"),
        )

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["summary"]["total_fees"], "144000.00")
        self.assertEqual(result["breakdown"][-1]["payment"], "1264000.00")


class TieredRateTests(TestCase):
    def test_locked_tier_uses_upper_bound_exclusively(self):
        profile = make_simulation(
            rate_mode=ProductSimulation.RateMode.TIERED,
            base_annual_rate=None,
            amount_min=Decimal("1000000"),
            amount_max=Decimal("50000000"),
        )
        profile.rate_tiers.create(label="Di bawah A", min_amount=0, max_amount=10000000, annual_rate=4)
        profile.rate_tiers.create(label="A ke atas", min_amount=10000000, max_amount=None, annual_rate=8)

        below = simulate(profile, {"amount": "9900000", "tenor_months": "12"})
        boundary = simulate(profile, {"amount": "10000000", "tenor_months": "12"})

        self.assertEqual(below["breakdown"][0]["annual_rate_min"], "4.000000")
        self.assertEqual(boundary["breakdown"][0]["annual_rate_min"], "8.000000")
        self.assertEqual(boundary["applied_rules"]["rates"][0]["label"], "A ke atas")

    def test_tier_can_depend_on_selected_tenor(self):
        profile = make_simulation(
            rate_mode=ProductSimulation.RateMode.TIERED,
            base_annual_rate=None,
        )
        profile.rate_tiers.create(label="Pendek", min_amount=0, min_tenor_months=1, max_tenor_months=11, annual_rate=4)
        profile.rate_tiers.create(label="Panjang", min_amount=0, min_tenor_months=12, max_tenor_months=None, annual_rate=7)

        short = simulate(profile, {"amount": "12000000", "tenor_months": "6"})
        long = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(short["breakdown"][0]["annual_rate_min"], "4.000000")
        self.assertEqual(long["breakdown"][0]["annual_rate_min"], "7.000000")

    def test_current_balance_rate_changes_after_recurring_deposit_crosses_tier(self):
        profile = make_simulation(
            strategy=ProductSimulation.Strategy.SAVINGS_RECURRING,
            rate_mode=ProductSimulation.RateMode.TIERED,
            rate_application=ProductSimulation.RateApplication.CURRENT_BALANCE,
            base_annual_rate=None,
            amount_min=Decimal("1000000"),
            amount_default=Decimal("1000000"),
            recurring_min=Decimal("1000000"),
            recurring_max=Decimal("5000000"),
            recurring_default=Decimal("1000000"),
            recurring_step=Decimal("1000000"),
        )
        profile.rate_tiers.create(label="Saldo kecil", min_amount=0, max_amount=2000000, annual_rate=0)
        profile.rate_tiers.create(label="Saldo besar", min_amount=2000000, max_amount=None, annual_rate=12)

        result = simulate(
            profile,
            {"amount": "1000000", "tenor_months": "2", "recurring_amount": "1000000"},
        )

        self.assertEqual(result["breakdown"][0]["interest"], "20000.00")
        self.assertEqual(result["breakdown"][1]["annual_rate_min"], "12.000000")

    def test_progressive_rate_applies_each_balance_layer(self):
        profile = make_simulation(
            rate_mode=ProductSimulation.RateMode.TIERED,
            rate_application=ProductSimulation.RateApplication.PROGRESSIVE,
            base_annual_rate=None,
            amount_min=Decimal("1000000"),
            amount_max=Decimal("50000000"),
        )
        profile.rate_tiers.create(label="Lapisan pertama", min_amount=0, max_amount=10000000, annual_rate=6)
        profile.rate_tiers.create(label="Lapisan kedua", min_amount=10000000, max_amount=None, annual_rate=12)

        result = simulate(profile, {"amount": "20000000", "tenor_months": "1"})

        self.assertEqual(result["breakdown"][0]["annual_rate_min"], "9.000000")
        self.assertEqual(result["breakdown"][0]["interest"], "150000.00")

    def test_missing_tier_coverage_makes_simulator_unready(self):
        profile = make_simulation(rate_mode=ProductSimulation.RateMode.TIERED, base_annual_rate=None)
        profile.rate_tiers.create(label="Only small", min_amount=0, max_amount=5000000, annual_rate=4)

        with self.assertRaises(SimulationValidationError) as context:
            simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertIn("configuration", context.exception.errors)


class BreakdownAndInputTests(TestCase):
    def test_auto_compact_selects_expected_intervals(self):
        cases = [(12, 1, 12), (24, 3, 8), (36, 3, 12), (60, 6, 10), (120, 12, 10)]
        for tenor, interval, rows in cases:
            with self.subTest(tenor=tenor):
                profile = make_simulation()
                result = simulate(profile, {"amount": "12000000", "tenor_months": str(tenor)})
                self.assertEqual(result["metadata"]["breakdown_interval_months"], interval)
                self.assertEqual(len(result["breakdown"]), rows)

    def test_auto_detailed_five_year_term_uses_quarters(self):
        profile = make_simulation(breakdown_mode=ProductSimulation.BreakdownMode.AUTO_DETAILED)

        result = simulate(profile, {"amount": "12000000", "tenor_months": "60"})

        self.assertEqual(result["metadata"]["breakdown_interval_months"], 3)
        self.assertEqual(len(result["breakdown"]), 20)

    def test_fixed_breakdown_honors_admin_override(self):
        profile = make_simulation(
            breakdown_mode=ProductSimulation.BreakdownMode.FIXED,
            fixed_breakdown_months=12,
        )

        result = simulate(profile, {"amount": "12000000", "tenor_months": "60"})

        self.assertEqual(len(result["breakdown"]), 5)
        self.assertEqual(result["breakdown"][0]["label"], "Bulan 1–12")

    def test_custom_breakdown_chooses_highest_priority_matching_band(self):
        profile = make_simulation(
            is_enabled=False,
            breakdown_mode=ProductSimulation.BreakdownMode.CUSTOM,
        )
        profile.breakdown_bands.create(label="Default", priority=0, min_tenor_months=1, max_tenor_months=120, interval_months=12)
        profile.breakdown_bands.create(label="Detail 1 tahun", priority=10, min_tenor_months=1, max_tenor_months=12, interval_months=1)
        profile.is_enabled = True

        result = simulate(profile, {"amount": "12000000", "tenor_months": "12"})

        self.assertEqual(result["metadata"]["breakdown_interval_months"], 1)

    def test_aggregation_preserves_financial_totals(self):
        profile = make_simulation(
            product_kind=ProductSimulation.ProductKind.LOAN,
            strategy=ProductSimulation.Strategy.LOAN_DECLINING,
            breakdown_mode=ProductSimulation.BreakdownMode.FIXED,
            fixed_breakdown_months=6,
        )

        result = simulate(profile, {"amount": "12000000", "tenor_months": "60"})

        self.assertEqual(
            sum((Decimal(row["interest"]) for row in result["breakdown"]), Decimal("0")),
            Decimal(result["summary"]["total_interest"]),
        )
        self.assertEqual(
            sum((Decimal(row["principal"]) for row in result["breakdown"]), Decimal("0")),
            Decimal("12000000.00"),
        )
        self.assertEqual(result["breakdown"][-1]["closing_balance"], "0.00")

    def test_chart_is_capped_at_sixty_points_without_changing_breakdown(self):
        profile = make_simulation(tenor_max_months=600)

        result = simulate(profile, {"amount": "12000000", "tenor_months": "600"})

        self.assertLessEqual(len(result["chart"]), 60)
        self.assertEqual(result["breakdown"][-1]["period_end"], 600)

    def assert_invalid(self, profile, data, field):
        with self.assertRaises(SimulationValidationError) as context:
            simulate(profile, data)
        self.assertIn(field, context.exception.errors)

    def test_invalid_inputs_are_rejected(self):
        profile = make_simulation()
        cases = [
            ({"tenor_months": "12"}, "amount"),
            ({"amount": "abc", "tenor_months": "12"}, "amount"),
            ({"amount": "NaN", "tenor_months": "12"}, "amount"),
            ({"amount": "0", "tenor_months": "12"}, "amount"),
            ({"amount": "1e999999", "tenor_months": "12"}, "amount"),
            ({"amount": "500000", "tenor_months": "12"}, "amount"),
            ({"amount": "100000001", "tenor_months": "12"}, "amount"),
            ({"amount": "1050000", "tenor_months": "12"}, "amount"),
            ({"amount": "12000000", "tenor_months": "12.5"}, "tenor_months"),
            ({"amount": "12000000", "tenor_months": "121"}, "tenor_months"),
        ]
        for data, field in cases:
            with self.subTest(data=data):
                self.assert_invalid(profile, data, field)

    def test_recurring_amount_is_required_and_bounded(self):
        profile = make_simulation(
            strategy=ProductSimulation.Strategy.SAVINGS_RECURRING,
            recurring_min=Decimal("100000"),
            recurring_max=Decimal("1000000"),
            recurring_default=Decimal("100000"),
            recurring_step=Decimal("100000"),
        )

        self.assert_invalid(profile, {"amount": "12000000", "tenor_months": "12"}, "recurring_amount")
        self.assert_invalid(
            profile,
            {"amount": "12000000", "tenor_months": "12", "recurring_amount": "1050000"},
            "recurring_amount",
        )

    def test_public_config_only_exposes_relevant_recurring_input(self):
        normal = public_config(make_simulation())
        recurring = public_config(
            make_simulation(
                strategy=ProductSimulation.Strategy.SAVINGS_RECURRING,
                recurring_min=Decimal("100000"),
                recurring_max=Decimal("1000000"),
                recurring_default=Decimal("100000"),
                recurring_step=Decimal("100000"),
            )
        )

        self.assertNotIn("recurring", normal)
        self.assertIn("recurring", recurring)
        self.assertFalse(normal["requires_recurring_amount"])
        self.assertTrue(recurring["requires_recurring_amount"])
