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
from typing import List

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


def calculate_all_periods(policy: Policy) -> List[ReportingPeriodResult]:
    """
    Calculate earned/unearned for all monthly periods across the policy term.
    Handles endorsements via waterfall paid allocation and retro catch-up.
    Applies last-month rule on overall total.
    """
    layers = _build_layers(policy)
    grand_total = sum(l["premium"] for l in layers)

    # Determine the latest end date across all layers for period generation
    max_end_excl = max(l["end_exclusive"] for l in layers)
    periods = generate_monthly_periods(policy.start_date, max_end_excl)

    cumulative_reported = 0.0
    prev_policy_period_cumulative = {}
    prev_policy_period_days = {}
    results = []

    for idx, (ps, pe) in enumerate(periods):
        is_last = (idx == len(periods) - 1)

        # Total paid as of this period (collected installments with bill_from <= reportingperiod_start)
        paid_through = sum(
            i.amount for i in policy.installments
            if i.status == InstallmentStatus.COLLECTED and i.bill_from <= ps
        )

        # Waterfall: each layer reserves its full premium from paid pool.
        # Only the excess beyond prior layers' premiums funds later layers.
        remaining_paid = paid_through
        total_cumulative_earned = 0.0
        layer_cumulative_list = []

        for layer in layers:
            # How much of the paid pool is available to this layer
            layer_available = min(remaining_paid, layer["premium"])
            remaining_paid = round(remaining_paid - layer_available, 2)

            # Days from layer start through end of this period
            if pe <= layer["start"]:
                days_through = 0
            else:
                days_through = max(0, (min(pe, layer["end_exclusive"]) - layer["start"]).days)

            layer_earned = round(layer["daily"] * days_through, 2)
            layer_earned = min(layer_earned, layer["premium"])    # cap at layer total
            layer_earned = min(layer_earned, layer_available)     # cap at funded amount
            total_cumulative_earned += layer_earned
            layer_cumulative_list.append((layer, days_through, layer_earned))

        total_cumulative_earned = round(total_cumulative_earned, 2)

        if is_last:
            # Last month rule: earned = whatever remains to reach grand total (or paid limit)
            period_earned = round(min(grand_total, paid_through) - cumulative_reported, 2)
        else:
            period_earned = round(total_cumulative_earned - cumulative_reported, 2)

        period_earned = max(period_earned, 0.0)
        unearned = round(paid_through - cumulative_reported - period_earned, 2)

        # Build per premium-component breakdown for this reporting row
        policy_periods = []
        for layer, days_through, cum_earned in layer_cumulative_list:
            prev_cum = prev_policy_period_cumulative.get(layer["label"], 0.0)
            prev_days = prev_policy_period_days.get(layer["label"], 0)
            period_earned_component = round(cum_earned - prev_cum, 2)
            # Effective days = days that produced this period's earned amount.
            # When a component was unfunded in prior periods, catch-up means
            # the earned amount covers more days than just the current period.
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

        results.append(ReportingPeriodResult(
            reportingperiod_start=ps,
            reportingperiod_end=pe,
            earned_prior=round(cumulative_reported, 2),
            earned_current=period_earned,
            unearned=unearned,
            total_paid=paid_through,
            policy_periods=policy_periods,
        ))

        cumulative_reported += period_earned

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


def generate_monthly_periods(start: date, end: date) -> List[tuple]:
    """Generate monthly [reportingperiod_start, reportingperiod_end) pairs covering the policy."""
    periods = []
    current = date(start.year, start.month, 1)
    while current < end:
        y, m = current.year, current.month
        if m == 12:
            next_month = date(y + 1, 1, 1)
        else:
            next_month = date(y, m + 1, 1)
        periods.append((current, next_month))
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
        f"  {'Period':<25} {'Paid':>10} {'EarnedPrior':>12} {'EarnedCurr':>12} {'Unearned':>12}"
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
