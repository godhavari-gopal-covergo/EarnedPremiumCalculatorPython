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
        "daily": round(policy.total_premium / days, 2),
    })
    for idx, e in enumerate(policy.endorsements):
        e_end_excl = e.end_date + timedelta(days=1) if e.end_date_inclusive else e.end_date
        e_days = max((e_end_excl - e.effective_date).days, 1)
        layers.append({
            "label": f"Endorsement {idx+1}",
            "start": e.effective_date,
            "end_exclusive": e_end_excl,
            "premium": e.additional_premium,
            "daily": round(e.additional_premium / e_days, 2),
        })
    return layers


def calculate_for_period(
    policy: Policy,
    reportingperiod_start: date,
    reportingperiod_end: date,
    cumulative_reported: float = 0.0,
    prev_policy_period_cumulative: Optional[Dict[str, float]] = None,
    prev_policy_period_days: Optional[Dict[str, int]] = None,
    is_last: bool = False,
) -> ReportingPeriodResult:
    """
    Calculate earned/unearned for a single reporting period.
    Both reportingperiod_start and reportingperiod_end are inclusive.

    Chaining: pass the returned cumulative state into the next call
    via cumulative_reported, prev_policy_period_cumulative, prev_policy_period_days.
    """
    if prev_policy_period_cumulative is None:
        prev_policy_period_cumulative = {}
    if prev_policy_period_days is None:
        prev_policy_period_days = {}

    layers = _build_layers(policy)
    grand_total = sum(l["premium"] for l in layers)
    pe_excl = reportingperiod_end + timedelta(days=1)

    paid_through = sum(
        i.amount for i in policy.installments
        if i.status == InstallmentStatus.COLLECTED and i.bill_from <= reportingperiod_end
    )

    total_cumulative_earned = 0.0
    layer_cumulative_list = []

    for layer in layers:
        if pe_excl <= layer["start"]:
            days_through = 0
        else:
            days_through = max(0, (min(pe_excl, layer["end_exclusive"]) - layer["start"]).days)

        layer_earned = round(layer["daily"] * days_through, 2)
        if layer["premium"] >= 0:
            layer_earned = min(layer_earned, layer["premium"])
        else:
            layer_earned = max(layer_earned, layer["premium"])
        total_cumulative_earned += layer_earned
        layer_cumulative_list.append((layer, days_through, layer_earned))

    uncapped_cumulative = round(total_cumulative_earned, 2)
    total_cumulative_earned = min(uncapped_cumulative, paid_through)

    # Scale per-layer cumulative earned proportionally when capped by paid
    if uncapped_cumulative > 0 and total_cumulative_earned < uncapped_cumulative:
        scale = total_cumulative_earned / uncapped_cumulative
        layer_cumulative_list = [
            (layer, days, round(cum_e * scale, 2))
            for layer, days, cum_e in layer_cumulative_list
        ]

    if is_last:
        period_earned = round(grand_total - cumulative_reported, 2)
        period_earned = min(period_earned, round(paid_through - cumulative_reported, 2))
    else:
        period_earned = round(total_cumulative_earned - cumulative_reported, 2)

    period_earned = max(period_earned, 0.0)
    unearned = round(grand_total - cumulative_reported - period_earned, 2)

    policy_periods = []
    for layer, days_through, cum_earned in layer_cumulative_list:
        prev_cum = prev_policy_period_cumulative.get(layer["label"], 0.0)
        prev_days = prev_policy_period_days.get(layer["label"], 0)
        period_earned_component = round(cum_earned - prev_cum, 2)
        if layer["daily"] > 0 and period_earned_component > 0:
            effective_days = round(period_earned_component / layer["daily"])
        else:
            effective_days = days_through - prev_days
        policy_periods.append(PolicyPeriod(
            label=layer["label"],
            daily_rate=layer["daily"],
            days=effective_days,
            earned=period_earned_component,
        ))
        prev_policy_period_cumulative[layer["label"]] = cum_earned
        prev_policy_period_days[layer["label"]] = days_through

    return ReportingPeriodResult(
        reportingperiod_start=reportingperiod_start,
        reportingperiod_end=reportingperiod_end,
        earned_prior=round(cumulative_reported, 2),
        earned_current=period_earned,
        unearned=unearned,
        total_paid=paid_through,
        policy_periods=policy_periods,
    )


def calculate_all_periods(policy: Policy) -> List[ReportingPeriodResult]:
    """
    Calculate earned/unearned for all monthly periods across the policy term.
    Auto-generates inclusive monthly periods and calls calculate_for_period() for each.
    """
    max_end_excl = max(
        l["end_exclusive"] for l in _build_layers(policy)
    )
    periods = generate_monthly_periods(policy.start_date, max_end_excl)

    cumulative_reported = 0.0
    prev_pp_cumulative: dict = {}
    prev_pp_days: dict = {}
    results = []

    for idx, (ps, pe) in enumerate(periods):
        is_last = (idx == len(periods) - 1)
        result = calculate_for_period(
            policy, ps, pe,
            cumulative_reported=cumulative_reported,
            prev_policy_period_cumulative=prev_pp_cumulative,
            prev_policy_period_days=prev_pp_days,
            is_last=is_last,
        )
        results.append(result)
        cumulative_reported += result.earned_current

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
                        status=inst.status)
        for idx, inst in enumerate(policy.installments, 1)
    ]

    policy_period_labels = []
    seen = set()
    for r in periods:
        for pp in r.policy_periods:
            if pp.label not in seen:
                policy_period_labels.append(pp.label)
                seen.add(pp.label)

    total_earned_current = sum(r.earned_current for r in periods)
    policy_period_totals: dict = {}
    for r in periods:
        for pp in r.policy_periods:
            policy_period_totals[pp.label] = policy_period_totals.get(pp.label, 0.0) + pp.earned

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
        final_total_paid=last.total_paid if last else 0.0,
        final_unearned=last.unearned if last else 0.0,
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
    print(f"  {'Installments':^65}")
    print(f"  {'─' * 70}")
    print(f"  {'#':<4} {'Bill From':>12} {'Bill To':>12} {'Inclusive':>10} {'Amount':>12} {'Status':>11}")
    print(f"  {'─' * 70}")
    for inst in result.installments:
        incl = "Yes" if inst.inclusive else "No"
        print(f"  {inst.index:<4} {str(inst.bill_from):>12} {str(inst.bill_to):>12} {incl:>10} {inst.amount:>12.2f} {inst.status.value:>11}")
    print(f"  {'─' * 70}")
    print()

    # --- Earned / Unearned table ---
    policy_period_labels = result.policy_period_labels
    formula_w = 13
    earned_w = 10
    sep = " = "
    pp_col_width = formula_w + len(sep) + earned_w
    base_width = 71
    total_width = base_width + len(policy_period_labels) * (pp_col_width + 2)

    header = (
        f"  {'ReportingPeriod':<25} {'Paid':>10} {'EarnedPrior':>12} {'EarnedCurr':>12} {'Unearned':>12}"
    )
    for lbl in policy_period_labels:
        header += f"  {lbl:^{pp_col_width}}"
    print(header)
    print(f"  {'─' * total_width}")

    for r in result.periods:
        line = (
            f"  {str(r.reportingperiod_start)+' - '+str(r.reportingperiod_end):<25} "
            f"{r.total_paid:>10.2f} {r.earned_prior:>12.2f} "
            f"{r.earned_current:>12.2f} {r.unearned:>12.2f}"
        )
        pp_map = {pp.label: pp for pp in r.policy_periods}
        for lbl in policy_period_labels:
            pp = pp_map.get(lbl)
            if pp and pp.earned != 0:
                formula = f"{pp.daily_rate:.2f} x {pp.days}d"
                line += f"  {formula:>{formula_w}}{sep}{pp.earned:>{earned_w}.2f}"
            else:
                line += f"  {'—':^{pp_col_width}}"
        print(line)

    # --- Total row ---
    total_line = (
        f"  {'Total':<25} "
        f"{result.final_total_paid:>10.2f} {'':>12} "
        f"{result.total_earned_current:>12.2f} {result.final_unearned:>12.2f}"
    )
    for lbl in policy_period_labels:
        earned = f"{round(result.policy_period_totals.get(lbl, 0.0), 2):.2f}"
        total_line += f"  {'':>{formula_w}}{' ':>{len(sep)}}{earned:>{earned_w}}"
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
        for i, k in enumerate(keys, 1):
            print(f"  {i}. {k} — {SCENARIOS[k]['description']}")
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
