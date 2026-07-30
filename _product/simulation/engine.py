from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from math import ceil

from _product.models import ProductSimulation, SimulationFeeRule


ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
TWELVE = Decimal("12")
MONEY_QUANTUM = Decimal("0.01")
MAX_TENOR_MONTHS = 600


def money(value):
    return Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def decimal_string(value):
    return format(money(value), "f")


class SimulationValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Data simulasi tidak valid.")


@dataclass(frozen=True)
class SimulationInputs:
    amount: Decimal
    tenor_months: int
    recurring_amount: Decimal = ZERO


class RateResolver:
    def __init__(self, profile, inputs):
        self.profile = profile
        self.inputs = inputs
        self.tiers = sorted(
            [tier for tier in profile.rate_tiers.all() if tier.is_active],
            key=lambda tier: (-tier.priority, tier.sort_order or 0, tier.pk or 0),
        )
        self.used_rules = {}
        if profile.rate_application == profile.RateApplication.LOCKED:
            self.locked_rate = self._whole_balance_rate(inputs.amount)
        else:
            self.locked_rate = None

    def _record(self, tier):
        if tier is not None:
            self.used_rules[tier.pk or tier.label] = {
                "label": tier.label,
                "annual_rate": format(tier.annual_rate, "f"),
            }

    def _record_base(self, label):
        self.used_rules[f"base:{label}"] = {
            "label": label,
            "annual_rate": format(self.profile.base_annual_rate, "f"),
        }

    def _whole_balance_rate(self, amount):
        if self.profile.rate_mode == self.profile.RateMode.FIXED:
            if self.profile.base_annual_rate is None:
                raise SimulationValidationError({"configuration": ["Bunga dasar belum dikonfigurasi."]})
            self._record_base("Bunga tetap")
            return self.profile.base_annual_rate
        for tier in self.tiers:
            if tier.matches(amount, self.inputs.tenor_months):
                self._record(tier)
                return tier.annual_rate
        if self.profile.base_annual_rate is not None:
            self._record_base("Bunga dasar fallback")
            return self.profile.base_annual_rate
        raise SimulationValidationError(
            {"amount": ["Tidak ada tier bunga yang mencakup nominal dan tenor tersebut."]}
        )

    def _progressive_rate(self, amount):
        if amount <= 0:
            return ZERO
        eligible = [
            tier
            for tier in self.tiers
            if self.inputs.tenor_months >= tier.min_tenor_months
            and (tier.max_tenor_months is None or self.inputs.tenor_months <= tier.max_tenor_months)
        ]
        weighted = ZERO
        covered = ZERO
        for tier in sorted(eligible, key=lambda item: (item.min_amount, -(item.priority or 0))):
            upper = amount if tier.max_amount is None else min(amount, tier.max_amount)
            portion = max(upper - tier.min_amount, ZERO)
            if portion > 0:
                weighted += portion * tier.annual_rate
                covered += portion
                self._record(tier)
        if covered < amount:
            if self.profile.base_annual_rate is None:
                raise SimulationValidationError(
                    {"amount": ["Tier bunga progresif tidak mencakup seluruh nominal."]}
                )
            weighted += (amount - covered) * self.profile.base_annual_rate
            self._record_base("Bunga dasar fallback")
        return weighted / amount

    def annual_rate(self, balance):
        if self.locked_rate is not None:
            return self.locked_rate
        if self.profile.rate_application == self.profile.RateApplication.PROGRESSIVE:
            return self._progressive_rate(balance)
        return self._whole_balance_rate(balance)

    def monthly_rate(self, balance):
        return self.annual_rate(balance) / ONE_HUNDRED / TWELVE


class FeeEvaluator:
    def __init__(self, profile):
        self.rules = [rule for rule in profile.fee_rules.all() if rule.is_active]
        self.used_rules = {}

    def evaluate(self, timing, bases):
        result = {"fees": ZERO, "tax": ZERO, "upfront": ZERO}
        for rule in self.rules:
            if rule.timing != timing:
                continue
            base = bases.get(rule.basis, ZERO)
            if rule.calculation == rule.Calculation.FIXED:
                amount = rule.value
            else:
                amount = base * rule.value / ONE_HUNDRED
            if rule.minimum_amount is not None:
                amount = max(amount, rule.minimum_amount)
            if rule.maximum_amount is not None:
                amount = min(amount, rule.maximum_amount)
            amount = money(amount)
            bucket = "tax" if rule.category == rule.Category.TAX else "fees"
            result[bucket] += amount
            if timing == rule.Timing.UPFRONT:
                result["upfront"] += amount
            self.used_rules[rule.pk or rule.label] = {
                "label": rule.label,
                "category": rule.get_category_display(),
            }
        return {key: money(value) for key, value in result.items()}


def _row(period, opening, inflow=ZERO, principal=ZERO, interest=ZERO, fees=ZERO, tax=ZERO, payment=ZERO, closing=ZERO, annual_rate=ZERO):
    return {
        "period": period,
        "opening_balance": money(opening),
        "inflow": money(inflow),
        "principal": money(principal),
        "interest": money(interest),
        "fees": money(fees),
        "tax": money(tax),
        "payment": money(payment),
        "closing_balance": money(closing),
        "annual_rate": Decimal(annual_rate),
    }


def _fee_bases(inputs, opening, interest, payment, total_interest):
    return {
        SimulationFeeRule.Basis.INITIAL_AMOUNT: inputs.amount,
        SimulationFeeRule.Basis.OPENING_BALANCE: opening,
        SimulationFeeRule.Basis.INTEREST: interest,
        SimulationFeeRule.Basis.PAYMENT: payment,
        SimulationFeeRule.Basis.TOTAL_INTEREST: total_interest,
    }


def _savings_schedule(profile, inputs, rates, fees):
    balance = inputs.amount
    accrued_simple_interest = ZERO
    rows = []
    total_interest = ZERO
    is_simple = profile.strategy == profile.Strategy.SAVINGS_SIMPLE
    is_recurring = profile.strategy == profile.Strategy.SAVINGS_RECURRING

    upfront = fees.evaluate(
        SimulationFeeRule.Timing.UPFRONT,
        _fee_bases(inputs, balance, ZERO, ZERO, ZERO),
    )
    balance = money(balance - upfront["fees"] - upfront["tax"])
    if balance < 0:
        raise SimulationValidationError(
            {"configuration": ["Biaya di awal melebihi nominal simpanan."]}
        )

    for period in range(1, inputs.tenor_months + 1):
        opening = balance + accrued_simple_interest
        contribution = inputs.recurring_amount if is_recurring else ZERO
        if contribution and profile.contribution_timing == profile.ContributionTiming.BEGINNING:
            balance += contribution

        annual_rate = rates.annual_rate(inputs.amount if is_simple else balance)
        interest_base = inputs.amount if is_simple else balance
        interest = money(interest_base * annual_rate / ONE_HUNDRED / TWELVE)
        total_interest += interest
        provisional_payment = contribution + interest
        charges = fees.evaluate(
            SimulationFeeRule.Timing.PER_PERIOD,
            _fee_bases(inputs, balance, interest, provisional_payment, total_interest),
        )
        periodic_fees = charges["fees"]
        periodic_tax = charges["tax"]
        if period == 1:
            charges["fees"] += upfront["fees"]
            charges["tax"] += upfront["tax"]

        if is_simple:
            accrued_simple_interest += interest - periodic_tax
            balance -= periodic_fees
        else:
            balance += interest - periodic_fees - periodic_tax

        if contribution and profile.contribution_timing == profile.ContributionTiming.END:
            balance += contribution

        if period == inputs.tenor_months:
            maturity = fees.evaluate(
                SimulationFeeRule.Timing.MATURITY,
                _fee_bases(inputs, balance, interest, provisional_payment, total_interest),
            )
            charges["fees"] += maturity["fees"]
            charges["tax"] += maturity["tax"]
            if is_simple:
                balance -= maturity["fees"]
                accrued_simple_interest -= maturity["tax"]
            else:
                balance -= maturity["fees"] + maturity["tax"]

        closing = balance + accrued_simple_interest
        if closing < 0:
            raise SimulationValidationError(
                {"configuration": [f"Saldo menjadi negatif pada periode {period} akibat biaya atau pajak."]}
            )
        rows.append(
            _row(
                period,
                opening,
                inflow=contribution,
                principal=contribution,
                interest=interest,
                fees=charges["fees"],
                tax=charges["tax"],
                closing=closing,
                annual_rate=annual_rate,
            )
        )
    return rows


def _annuity_payment(outstanding, monthly_rate, remaining_periods):
    if monthly_rate == 0:
        return money(outstanding / remaining_periods)
    factor = (Decimal("1") + monthly_rate) ** remaining_periods
    return money(outstanding * monthly_rate * factor / (factor - Decimal("1")))


def _loan_schedule(profile, inputs, rates, fees):
    outstanding = inputs.amount
    rows = []
    total_interest = ZERO
    upfront = fees.evaluate(
        SimulationFeeRule.Timing.UPFRONT,
        _fee_bases(inputs, outstanding, ZERO, ZERO, ZERO),
    )
    if upfront["fees"] + upfront["tax"] > inputs.amount:
        raise SimulationValidationError(
            {"configuration": ["Biaya di awal melebihi nominal pinjaman."]}
        )

    fixed_flat_interest = None
    if profile.strategy == profile.Strategy.LOAN_FLAT:
        fixed_flat_interest = money(inputs.amount * rates.monthly_rate(inputs.amount))

    for period in range(1, inputs.tenor_months + 1):
        opening = outstanding
        remaining = inputs.tenor_months - period + 1
        annual_rate = rates.annual_rate(opening)
        monthly_rate = annual_rate / ONE_HUNDRED / TWELVE

        if profile.strategy == profile.Strategy.LOAN_FLAT:
            interest = fixed_flat_interest
            principal = outstanding if period == inputs.tenor_months else money(inputs.amount / inputs.tenor_months)
        elif profile.strategy == profile.Strategy.LOAN_DECLINING:
            interest = money(opening * monthly_rate)
            principal = outstanding if period == inputs.tenor_months else money(inputs.amount / inputs.tenor_months)
        elif profile.strategy == profile.Strategy.LOAN_ANNUITY:
            interest = money(opening * monthly_rate)
            installment = _annuity_payment(opening, monthly_rate, remaining)
            principal = outstanding if period == inputs.tenor_months else money(installment - interest)
        elif profile.strategy == profile.Strategy.LOAN_BULLET:
            interest = money(opening * monthly_rate)
            principal = outstanding if period == inputs.tenor_months else ZERO
        else:
            raise SimulationValidationError({"configuration": ["Strategy pinjaman tidak didukung."]})

        principal = min(principal, outstanding)
        core_payment = money(principal + interest)
        total_interest += interest
        charges = fees.evaluate(
            SimulationFeeRule.Timing.PER_PERIOD,
            _fee_bases(inputs, opening, interest, core_payment, total_interest),
        )
        if period == 1:
            charges["fees"] += upfront["fees"]
            charges["tax"] += upfront["tax"]
        scheduled_charges = money(charges["fees"] + charges["tax"] - (upfront["fees"] + upfront["tax"] if period == 1 else ZERO))

        if period == inputs.tenor_months:
            maturity = fees.evaluate(
                SimulationFeeRule.Timing.MATURITY,
                _fee_bases(inputs, opening, interest, core_payment, total_interest),
            )
            charges["fees"] += maturity["fees"]
            charges["tax"] += maturity["tax"]
            scheduled_charges += maturity["fees"] + maturity["tax"]

        outstanding = money(outstanding - principal)
        if period == inputs.tenor_months and outstanding != ZERO:
            principal += outstanding
            core_payment += outstanding
            outstanding = ZERO
        payment = money(core_payment + scheduled_charges)
        rows.append(
            _row(
                period,
                opening,
                principal=principal,
                interest=interest,
                fees=charges["fees"],
                tax=charges["tax"],
                payment=payment,
                closing=outstanding,
                annual_rate=annual_rate,
            )
        )
    return rows


def _add_cumulative(rows, profile, inputs):
    cumulative_principal = inputs.amount if profile.product_kind == profile.ProductKind.SAVINGS else ZERO
    cumulative_interest = ZERO
    cumulative_fees = ZERO
    cumulative_tax = ZERO
    cumulative_total = cumulative_principal if profile.product_kind == profile.ProductKind.SAVINGS else ZERO
    for row in rows:
        if profile.product_kind == profile.ProductKind.SAVINGS:
            cumulative_principal += row["principal"]
        else:
            cumulative_principal += row["principal"]
        cumulative_interest += row["interest"]
        cumulative_fees += row["fees"]
        cumulative_tax += row["tax"]
        if profile.product_kind == profile.ProductKind.SAVINGS:
            cumulative_total = row["closing_balance"]
        else:
            cumulative_total += row["payment"]
        row["cumulative_principal"] = money(cumulative_principal)
        row["cumulative_interest"] = money(cumulative_interest)
        row["cumulative_fees"] = money(cumulative_fees)
        row["cumulative_tax"] = money(cumulative_tax)
        row["cumulative_total"] = money(cumulative_total)
    return rows


def _breakdown_interval(profile, tenor_months):
    if profile.breakdown_mode == profile.BreakdownMode.FIXED:
        return profile.fixed_breakdown_months
    if profile.breakdown_mode == profile.BreakdownMode.CUSTOM:
        matches = [band for band in profile.breakdown_bands.all() if band.is_active and band.matches(tenor_months)]
        if not matches:
            raise SimulationValidationError({"configuration": ["Aturan breakdown untuk tenor ini tidak ditemukan."]})
        matches.sort(key=lambda band: (-band.priority, band.sort_order or 0, band.pk or 0))
        return matches[0].interval_months
    maximum_rows = 20 if profile.breakdown_mode == profile.BreakdownMode.AUTO_DETAILED else 12
    for interval in (1, 3, 6, 12, 24, 60):
        if ceil(tenor_months / interval) <= maximum_rows:
            return interval
    return max(60, ceil(tenor_months / maximum_rows))


def _aggregate_rows(rows, interval):
    aggregated = []
    for start in range(0, len(rows), interval):
        group = rows[start : start + interval]
        first, last = group[0], group[-1]
        rates = [row["annual_rate"] for row in group]
        aggregated.append(
            {
                "period_start": first["period"],
                "period_end": last["period"],
                "label": (
                    f"Bulan {first['period']}" if first["period"] == last["period"]
                    else f"Bulan {first['period']}–{last['period']}"
                ),
                "opening_balance": first["opening_balance"],
                "inflow": money(sum((row["inflow"] for row in group), ZERO)),
                "principal": money(sum((row["principal"] for row in group), ZERO)),
                "interest": money(sum((row["interest"] for row in group), ZERO)),
                "fees": money(sum((row["fees"] for row in group), ZERO)),
                "tax": money(sum((row["tax"] for row in group), ZERO)),
                "payment": money(sum((row["payment"] for row in group), ZERO)),
                "closing_balance": last["closing_balance"],
                "cumulative_principal": last["cumulative_principal"],
                "cumulative_interest": last["cumulative_interest"],
                "cumulative_fees": last["cumulative_fees"],
                "cumulative_tax": last["cumulative_tax"],
                "cumulative_total": last["cumulative_total"],
                "annual_rate_min": min(rates),
                "annual_rate_max": max(rates),
            }
        )
    return aggregated


def _serialize_row(row):
    result = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            result[key] = format(value, ".6f" if key.startswith("annual_rate") else ".2f")
        else:
            result[key] = value
    return result


def _parse_decimal(raw, field, required=True):
    if raw in (None, ""):
        if required:
            raise SimulationValidationError({field: ["Field ini wajib diisi."]})
        return ZERO
    try:
        value = Decimal(str(raw))
        if not value.is_finite():
            raise InvalidOperation
        return money(value)
    except (InvalidOperation, ValueError, TypeError):
        raise SimulationValidationError({field: ["Masukkan angka yang valid."]}) from None


def _parse_inputs(profile, data):
    errors = {}
    try:
        amount = _parse_decimal(data.get("amount"), "amount")
    except SimulationValidationError as exc:
        errors.update(exc.errors)
        amount = ZERO
    raw_tenor = data.get("tenor_months")
    try:
        if isinstance(raw_tenor, bool) or str(raw_tenor).strip() == "":
            raise ValueError
        tenor = int(raw_tenor)
        if str(tenor) != str(raw_tenor).strip() and not isinstance(raw_tenor, int):
            raise ValueError
    except (ValueError, TypeError):
        errors["tenor_months"] = ["Masukkan tenor dalam bulan berupa bilangan bulat."]
        tenor = 0
    try:
        recurring = _parse_decimal(
            data.get("recurring_amount"),
            "recurring_amount",
            required=profile.requires_recurring_amount,
        )
    except SimulationValidationError as exc:
        errors.update(exc.errors)
        recurring = ZERO

    if "amount" not in errors and profile.amount_min is not None and amount < profile.amount_min:
        errors.setdefault("amount", []).append(f"Nominal minimum adalah Rp {profile.amount_min:,.0f}.")
    if "amount" not in errors and profile.amount_max is not None and amount > profile.amount_max:
        errors.setdefault("amount", []).append(f"Nominal maksimum adalah Rp {profile.amount_max:,.0f}.")
    if "amount" not in errors and profile.amount_step and profile.amount_min is not None and (amount - profile.amount_min) % profile.amount_step != 0:
        errors.setdefault("amount", []).append(f"Nominal harus mengikuti kelipatan Rp {profile.amount_step:,.0f}.")

    allowed_tenors = profile.allowed_tenors()
    if tenor not in allowed_tenors:
        errors.setdefault("tenor_months", []).append("Tenor tidak tersedia untuk produk ini.")
    if tenor > MAX_TENOR_MONTHS:
        errors.setdefault("tenor_months", []).append("Tenor maksimum sistem adalah 600 bulan.")

    if profile.requires_recurring_amount:
        if profile.recurring_min is not None and recurring < profile.recurring_min:
            errors.setdefault("recurring_amount", []).append(f"Setoran minimum adalah Rp {profile.recurring_min:,.0f}.")
        if profile.recurring_max is not None and recurring > profile.recurring_max:
            errors.setdefault("recurring_amount", []).append(f"Setoran maksimum adalah Rp {profile.recurring_max:,.0f}.")
        if profile.recurring_step and profile.recurring_min is not None and (recurring - profile.recurring_min) % profile.recurring_step != 0:
            errors.setdefault("recurring_amount", []).append(
                f"Setoran harus mengikuti kelipatan Rp {profile.recurring_step:,.0f}."
            )
    if errors:
        raise SimulationValidationError(errors)
    return SimulationInputs(amount=amount, tenor_months=tenor, recurring_amount=recurring)


def _summary(profile, inputs, rows):
    total_interest = money(sum((row["interest"] for row in rows), ZERO))
    total_fees = money(sum((row["fees"] for row in rows), ZERO))
    total_tax = money(sum((row["tax"] for row in rows), ZERO))
    if profile.product_kind == profile.ProductKind.SAVINGS:
        total_contributions = money(inputs.amount + sum((row["inflow"] for row in rows), ZERO))
        return {
            "initial_amount": decimal_string(inputs.amount),
            "total_contributions": decimal_string(total_contributions),
            "gross_interest": decimal_string(total_interest),
            "total_fees": decimal_string(total_fees),
            "total_tax": decimal_string(total_tax),
            "net_interest": decimal_string(total_interest - total_tax),
            "maturity_balance": decimal_string(rows[-1]["closing_balance"]),
        }

    upfront_charges = ZERO
    if rows:
        for rule in profile.fee_rules.all():
            if rule.is_active and rule.timing == rule.Timing.UPFRONT:
                bases = _fee_bases(inputs, inputs.amount, ZERO, ZERO, total_interest)
                if rule.calculation == rule.Calculation.FIXED:
                    charge = rule.value
                else:
                    charge = bases.get(rule.basis, ZERO) * rule.value / ONE_HUNDRED
                if rule.minimum_amount is not None:
                    charge = max(charge, rule.minimum_amount)
                if rule.maximum_amount is not None:
                    charge = min(charge, rule.maximum_amount)
                upfront_charges += money(charge)
    total_scheduled_payment = money(sum((row["payment"] for row in rows), ZERO))
    scheduled_payments = [row["payment"] for row in rows if row["payment"] > 0]
    return {
        "loan_amount": decimal_string(inputs.amount),
        "net_disbursed": decimal_string(inputs.amount - upfront_charges),
        "total_principal": decimal_string(sum((row["principal"] for row in rows), ZERO)),
        "total_interest": decimal_string(total_interest),
        "total_fees": decimal_string(total_fees),
        "total_tax": decimal_string(total_tax),
        "total_scheduled_payment": decimal_string(total_scheduled_payment),
        "total_cost": decimal_string(total_interest + total_fees + total_tax),
        "installment_min": decimal_string(min(scheduled_payments) if scheduled_payments else ZERO),
        "installment_max": decimal_string(max(scheduled_payments) if scheduled_payments else ZERO),
    }


def simulate(profile, data):
    if not profile.is_enabled or not profile.is_ready:
        raise SimulationValidationError({"configuration": ["Simulator belum aktif atau konfigurasinya belum lengkap."]})
    inputs = _parse_inputs(profile, data)
    rates = RateResolver(profile, inputs)
    fee_evaluator = FeeEvaluator(profile)
    if profile.product_kind == profile.ProductKind.SAVINGS:
        rows = _savings_schedule(profile, inputs, rates, fee_evaluator)
    else:
        rows = _loan_schedule(profile, inputs, rates, fee_evaluator)
    rows = _add_cumulative(rows, profile, inputs)
    interval = _breakdown_interval(profile, inputs.tenor_months)
    breakdown = _aggregate_rows(rows, interval)
    chart_interval = max(1, ceil(len(rows) / 60))
    chart_rows = _aggregate_rows(rows, chart_interval)

    return {
        "metadata": {
            "product_kind": profile.product_kind,
            "strategy": profile.strategy,
            "strategy_label": profile.get_strategy_display(),
            "breakdown_interval_months": interval,
            "breakdown_rows": len(breakdown),
            "configuration_version": profile.updated_at.isoformat() if profile.updated_at else None,
        },
        "inputs": {
            "amount": decimal_string(inputs.amount),
            "tenor_months": inputs.tenor_months,
            "recurring_amount": decimal_string(inputs.recurring_amount),
        },
        "applied_rules": {
            "rates": list(rates.used_rules.values()),
            "charges": list(fee_evaluator.used_rules.values()),
        },
        "summary": _summary(profile, inputs, rows),
        "breakdown": [_serialize_row(row) for row in breakdown],
        "chart": [_serialize_row(row) for row in chart_rows],
    }


def public_config(profile):
    config = {
        "product_kind": profile.product_kind,
        "strategy": profile.strategy,
        "strategy_label": profile.get_strategy_display(),
        "title": profile.simulator_title,
        "description": profile.simulator_description,
        "disclaimer": profile.disclaimer,
        "show_chart": profile.show_chart,
        "show_table": profile.show_table,
        "amount": {
            "min": decimal_string(profile.amount_min),
            "max": decimal_string(profile.amount_max),
            "default": decimal_string(profile.amount_default),
            "step": decimal_string(profile.amount_step),
            "label": "Dana awal" if profile.product_kind == profile.ProductKind.SAVINGS else "Nominal pinjaman",
        },
        "tenor": {
            "mode": profile.tenor_mode,
            "min": profile.tenor_min_months,
            "max": profile.tenor_max_months,
            "default": profile.tenor_default_months,
            "step": profile.tenor_step_months,
            "options": profile.allowed_tenors() if profile.tenor_mode == profile.TenorMode.OPTIONS else [],
        },
        "requires_recurring_amount": profile.requires_recurring_amount,
    }
    if profile.requires_recurring_amount:
        config["recurring"] = {
            "min": decimal_string(profile.recurring_min),
            "max": decimal_string(profile.recurring_max),
            "default": decimal_string(profile.recurring_default),
            "step": decimal_string(profile.recurring_step),
            "label": "Setoran rutin per bulan",
        }
    return config
