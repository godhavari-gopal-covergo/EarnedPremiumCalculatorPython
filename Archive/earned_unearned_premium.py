"""
Earned / Unearned Premium Calculator
Replicates the logic from "Earned and Unearned Sample - Phil.xlsx"

Supports:
  1. Monthly billing  – multiple installments, only collected ones count
  2. Annual billing   – single installment covering the full term
  3. Mid-term endorsements (MTA) – additional premium layers with retro handling

Core idea: daily pro-rata earning per premium layer, constrained by paid amounts.
Waterfall allocation: original layer claims paid first, endorsements get the rest.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from models import (
    Endorsement,
    Installment,
    InstallmentInfo,
    InstallmentStatus,
    ReportingPeriodResult,
    Policy,
    PolicyPeriod,
    PolicyResult,
    SummaryLayerInfo,
    ZERO,
    TWO_PLACES,
)


def _build_layers(policy: Policy) -> list:
    """Build premium layers: original + endorsements."""
    layers = []
    end_excl = policy._end_exclusive(policy.end_date)
    days = max((end_excl - policy.start_date).days, 1)
    layers.append({
        "label": "Original",
        "start": policy.start_date,
        "end_exclusive": end_excl,
        "premium": policy.total_premium,
        "daily": (policy.total_premium / days).quantize(TWO_PLACES),
    })
    for idx, e in enumerate(policy.endorsements):
        e_end_excl = e.end_date + timedelta(days=1) if e.end_date_inclusive else e.end_date
        e_days = max((e_end_excl - e.effective_date).days, 1)
        layers.append({
            "label": f"Endorsement {idx+1}",
            "start": e.effective_date,
            "end_exclusive": e_end_excl,
            "premium": e.additional_premium,
            "daily": (e.additional_premium / e_days).quantize(TWO_PLACES),
        })
    return layers


def _is_collected_by(inst: Installment, as_of: date) -> bool:
    """An installment counts as paid if status is COLLECTED and
    collected_date (when present) is on or before as_of."""
    if inst.status != InstallmentStatus.COLLECTED:
        return False
    if inst.collected_date is not None:
        return inst.collected_date <= as_of
    return True


def calculate_for_period(
    policy: Policy,
    reportingperiod_start: date,
    reportingperiod_end: date,
    accumulated_earned: Decimal = ZERO,
    last_earned_end: Optional[date] = None,
    is_last: bool = False,
) -> ReportingPeriodResult:
    """
    Calculate earned/unearned for a single reporting period.
    Both reportingperiod_start and reportingperiod_end are inclusive.

    Logic (mirrors GMS pseudocode):
    - Earned = daily_rate × days_in_period, but ONLY for coverage days where
      the installment covering that time has been collected by reportingperiod_end.
    - If a period was skipped (nothing collected) and payment arrives later,
      catch-up earns from the first un-earned day through reportingperiod_end.
    - Last period of coverage: sweep = total_premium - accumulated_earned.

    accumulated_earned: cumulative earned from all prior periods.
    last_earned_end: the last date through which premium was earned (None = nothing earned yet).
    """
    layers = _build_layers(policy)
    grand_total = sum((l["premium"] for l in layers), ZERO)

    paid_through = sum(
        (i.amount for i in policy.installments
         if _is_collected_by(i, reportingperiod_end) and i.bill_from <= reportingperiod_end),
        ZERO,
    )

    remaining_collectible = (paid_through - accumulated_earned).quantize(TWO_PLACES)

    if paid_through <= ZERO or remaining_collectible <= ZERO:
        return ReportingPeriodResult(
            reportingperiod_start=reportingperiod_start,
            reportingperiod_end=reportingperiod_end,
            earned_prior=accumulated_earned.quantize(TWO_PLACES),
            earned_current=ZERO,
            unearned=(grand_total - accumulated_earned).quantize(TWO_PLACES),
            total_paid=paid_through,
            policy_periods=[
                PolicyPeriod(label=l["label"], daily_rate=l["daily"], days=0, earned=ZERO)
                for l in layers
            ],
        )

    if last_earned_end is not None:
        earn_window_start = last_earned_end + timedelta(days=1)
    else:
        earn_window_start = None

    period_earned = ZERO
    policy_periods = []

    for layer in layers:
        layer_start = layer["start"]
        layer_end_excl = layer["end_exclusive"]
        layer_end_incl = layer_end_excl - timedelta(days=1)

        eff_start = max(earn_window_start, layer_start) if earn_window_start else layer_start
        eff_end_incl = min(reportingperiod_end, layer_end_incl)

        if eff_start > eff_end_incl:
            policy_periods.append(PolicyPeriod(
                label=layer["label"], daily_rate=layer["daily"], days=0, earned=ZERO))
            continue

        days_in_window = (eff_end_incl - eff_start).days + 1
        coverage_ends_this_period = (layer_end_incl <= reportingperiod_end)

        sweep = False
        if is_last or coverage_ends_this_period:
            layer_accumulated = _layer_accumulated(layer, accumulated_earned, grand_total, layers)
            layer_earned = (layer["premium"] - layer_accumulated).quantize(TWO_PLACES)
            layer_earned = max(layer_earned, ZERO)
            sweep = True
        else:
            layer_earned = (layer["daily"] * days_in_window).quantize(TWO_PLACES)
            layer_earned = min(layer_earned, layer["premium"])

        if sweep:
            formula = f"{layer['premium']:.2f} - {layer_accumulated:.2f}"
        else:
            formula = None

        period_earned += layer_earned
        policy_periods.append(PolicyPeriod(
            label=layer["label"],
            daily_rate=layer["daily"],
            days=days_in_window,
            earned=layer_earned,
            formula=formula,
        ))

    period_earned = period_earned.quantize(TWO_PLACES)
    period_earned = max(period_earned, ZERO)

    if period_earned > remaining_collectible:
        if is_last:
            period_earned = max(remaining_collectible, ZERO)
            policy_periods = [
                PolicyPeriod(
                    label=pp.label, daily_rate=pp.daily_rate, days=pp.days,
                    earned=period_earned,
                    formula=f"{paid_through:.2f} - {accumulated_earned:.2f}",
                )
                for pp in policy_periods
            ]
        else:
            period_earned = ZERO
            policy_periods = [
                PolicyPeriod(label=pp.label, daily_rate=pp.daily_rate, days=0, earned=ZERO)
                for pp in policy_periods
            ]

    unearned = (grand_total - accumulated_earned - period_earned).quantize(TWO_PLACES)

    return ReportingPeriodResult(
        reportingperiod_start=reportingperiod_start,
        reportingperiod_end=reportingperiod_end,
        earned_prior=accumulated_earned.quantize(TWO_PLACES),
        earned_current=period_earned,
        unearned=unearned,
        total_paid=paid_through,
        policy_periods=policy_periods,
    )


def _layer_accumulated(layer: dict, total_accumulated: Decimal, grand_total: Decimal,
                       layers: list) -> Decimal:
    """Proportional split of accumulated earned to a specific layer. Used for sweep."""
    if grand_total <= ZERO:
        return ZERO
    return (total_accumulated * (layer["premium"] / grand_total)).quantize(TWO_PLACES)


def calculate_all_periods(policy: Policy) -> List[ReportingPeriodResult]:
    """
    Calculate earned/unearned for all monthly periods across the policy term.
    Auto-generates inclusive monthly periods and calls calculate_for_period() for each.
    """
    max_end_excl = max(
        l["end_exclusive"] for l in _build_layers(policy)
    )
    periods = generate_monthly_periods(policy.start_date, max_end_excl)

    accumulated_earned = ZERO
    last_earned_end: Optional[date] = None
    results = []

    for idx, (ps, pe) in enumerate(periods):
        is_last = (idx == len(periods) - 1)
        result = calculate_for_period(
            policy, ps, pe,
            accumulated_earned=accumulated_earned,
            last_earned_end=last_earned_end,
            is_last=is_last,
        )
        results.append(result)
        accumulated_earned += result.earned_current
        if result.earned_current > ZERO:
            last_earned_end = pe

    return results


def compute_policy_result(policy: Policy) -> PolicyResult:
    """Pre-compute all business results for a policy into a single object."""
    periods = calculate_all_periods(policy)
    layers = _build_layers(policy)

    summary_layers = []
    for i, layer in enumerate(layers):
        if i == 0:
            end_type = "inclusive" if policy.end_date_inclusive else "exclusive"
            end_dt = policy.end_date
        else:
            e = policy.endorsements[i - 1]
            end_type = "inclusive" if e.end_date_inclusive else "exclusive"
            end_dt = e.end_date
        summary_layers.append(SummaryLayerInfo(
            label=layer["label"],
            start=layer["start"],
            end=end_dt,
            end_type=end_type,
            premium=layer["premium"],
            days=(layer["end_exclusive"] - layer["start"]).days,
            daily=layer["daily"],
        ))

    installments = [
        InstallmentInfo(index=idx, bill_from=inst.bill_from, bill_to=inst.bill_to,
                        inclusive=inst.bill_to_inclusive, amount=inst.amount,
                        status=inst.status, collected_date=inst.collected_date)
        for idx, inst in enumerate(policy.installments, 1)
    ]

    policy_period_labels = []
    seen = set()
    for r in periods:
        for pp in r.policy_periods:
            if pp.label not in seen:
                policy_period_labels.append(pp.label)
                seen.add(pp.label)

    total_earned_current = sum((r.earned_current for r in periods), ZERO)
    policy_period_totals: dict = {}
    for r in periods:
        for pp in r.policy_periods:
            policy_period_totals[pp.label] = policy_period_totals.get(pp.label, ZERO) + pp.earned

    last = periods[-1] if periods else None

    return PolicyResult(
        policy_number=policy.policy_number,
        policy_id=policy.policy_id,
        summary_layers=summary_layers,
        has_endorsements=bool(policy.endorsements),
        grand_total_premium=policy.grand_total_premium,
        installments=installments,
        periods=periods,
        policy_period_labels=policy_period_labels,
        total_earned_current=total_earned_current,
        final_total_paid=last.total_paid if last else ZERO,
        final_unearned=last.unearned if last else ZERO,
        policy_period_totals=policy_period_totals,
    )


def generate_monthly_periods(start: date, end_exclusive: date) -> List[tuple]:
    """Generate monthly (start, end) pairs with both dates inclusive."""
    periods = []
    current = date(start.year, start.month, 1)
    while current < end_exclusive:
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(current.year, current.month + 1, 1)
        last_day = next_month - timedelta(days=1)
        periods.append((current, last_day))
        current = next_month
    return periods


def _fmt(val: Decimal) -> str:
    """Format a Decimal to 2dp string for display."""
    return f"{val:.2f}"


def print_results(result: PolicyResult):
    """Format and print a pre-computed PolicyResult. No business logic here."""

    print()
    print(f"  Policy Number : {result.policy_number}")
    print(f"  Policy ID     : {result.policy_id}")
    print()

    # --- Policy summary table ---
    w = 90
    print(f"  {'Policy Summary':^{w}}")
    print(f"  {'─' * w}")
    print(f"  {'Policy period':<16} {'Start':>12} {'End':>12} {'End Type':>10} {'Premium':>12} {'Days':>6} {'Daily':>9}")
    print(f"  {'─' * w}")
    for sl in result.summary_layers:
        print(f"  {sl.label:<16} {str(sl.start):>12} {str(sl.end):>12} {sl.end_type:>10} {sl.premium:>12.2f} {sl.days:>6} {sl.daily:>9.2f}")
    if result.has_endorsements:
        print(f"  {'─' * w}")
        print(f"  {'Grand Total':<16} {'':>12} {'':>12} {'':>10} {result.grand_total_premium:>12.2f} {'':>6} {'':>9}")
    print(f"  {'─' * w}")
    print()

    # --- Installments ---
    inst_w = 83
    print(f"  {'Installments':^{inst_w}}")
    print(f"  {'─' * inst_w}")
    print(f"  {'#':<4} {'Bill From':>12} {'Bill To':>12} {'Inclusive':>10} {'Amount':>12} {'Status':>11} {'Collected':>12}")
    print(f"  {'─' * inst_w}")
    for inst in result.installments:
        incl = "Yes" if inst.inclusive else "No"
        coll = str(inst.collected_date) if inst.collected_date else "—"
        print(f"  {inst.index:<4} {str(inst.bill_from):>12} {str(inst.bill_to):>12} {incl:>10} {inst.amount:>12.2f} {inst.status.value:>11} {coll:>12}")
    print(f"  {'─' * inst_w}")
    print()

    # --- Earned / Unearned table ---
    policy_period_labels = result.policy_period_labels
    formula_w = 13
    earned_w = 10
    sep = " = "
    pp_col_width = formula_w + len(sep) + earned_w
    base_width = 71
    total_width = base_width + (pp_col_width + 2)

    header = (
        f"  {'ReportingPeriod':<25} {'Paid':>10} {'EarnedPrior':>12} {'EarnedCurr':>12} {'Unearned':>12}"
    )
    header += f"  {'Calculation':^{pp_col_width}}"
    print(header)
    print(f"  {'─' * total_width}")

    for r in result.periods:
        line = (
            f"  {str(r.reportingperiod_start)+' - '+str(r.reportingperiod_end):<25} "
            f"{r.total_paid:>10.2f} {r.earned_prior:>12.2f} "
            f"{r.earned_current:>12.2f} {r.unearned:>12.2f}"
        )
        pp = r.policy_periods[0] if r.policy_periods else None
        if pp and pp.earned != ZERO:
            if pp.formula:
                calc = pp.formula
            else:
                calc = f"{pp.daily_rate:.2f} x {pp.days}d"
            line += f"  {calc:>{formula_w}}{sep}{pp.earned:>{earned_w}.2f}"
        else:
            line += f"  {'—':^{pp_col_width}}"
        print(line)

    # --- Total row ---
    total_line = (
        f"  {'Total':<25} "
        f"{result.final_total_paid:>10.2f} {'':>12} "
        f"{result.total_earned_current:>12.2f} {result.final_unearned:>12.2f}"
    )
    total_calc = sum(result.policy_period_totals.values(), ZERO).quantize(TWO_PLACES)
    total_line += f"  {'':>{formula_w}}{' ':>{len(sep)}}{_fmt(total_calc):>{earned_w}}"
    print(f"  {'─' * total_width}")
    print(total_line)
    print()


def run_scenario(key: str, scenario: dict):
    """Run all policies in a scenario and print results."""
    print("=" * 75)
    print(f"  {key}: {scenario['description']}")
    print("=" * 75)
    for i, policy in enumerate(scenario["policies"]):
        if len(scenario["policies"]) > 1:
            print(f"\n--- Policy {i + 1} ---")
        result = compute_policy_result(policy)
        print_results(result)


if __name__ == "__main__":
    import sys
    from test_data import SCENARIOS

    print(f"{'*' * 50}")
    print(f"{'*' * 50}")
    print()
    print(f"  {'EXECUTING CALCULATOR....'}")
    print()
    print(f"{'*' * 50}")
    print(f"{'*' * 50}")

    keys = list(SCENARIOS.keys())

    if len(sys.argv) > 1:
        chosen = sys.argv[1]
    else:
        print("Available scenarios:")
        for idx, k in enumerate(keys, 1):
            print(f"  {idx}. {k} — {SCENARIOS[k]['description']}")
        print(f"  *. all — run every scenario")
        choice = input("\nSelect scenario (number, name, or 'all'): ").strip()
        if choice.lower() == "all" or choice == "*":
            chosen = "all"
        elif choice.isdigit() and 1 <= int(choice) <= len(keys):
            chosen = keys[int(choice) - 1]
        else:
            chosen = choice

    if chosen == "all":
        for k in keys:
            run_scenario(k, SCENARIOS[k])
    elif chosen in SCENARIOS:
        run_scenario(chosen, SCENARIOS[chosen])
    else:
        print(f"Unknown scenario '{chosen}'. Available: {', '.join(keys)}")
        sys.exit(1)
