"""
Earned / Unearned Premium Calculator
Replicates the logic from "Earned and Unearned Sample - Phil.xlsx"

Supports two billing modes:
  1. Monthly billing  – multiple installments, only collected ones count
  2. Annual billing   – single installment covering the full term

Core idea: daily pro-rata earning, constrained by what has actually been paid.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional


@dataclass
class Installment:
    bill_from: date       # inclusive
    bill_to: date         # exclusive
    amount: float
    status: str           # "billed" or "collected"


@dataclass
class Product:
    name: str
    premium: float


@dataclass
class Policy:
    start_date: date
    end_date: date
    total_premium: float
    products: List[Product]
    installments: List[Installment]

    @property
    def days_in_policy(self) -> int:
        return (self.end_date - self.start_date).days

    @property
    def daily_premium(self) -> float:
        return round(self.total_premium / self.days_in_policy, 2)


@dataclass
class PeriodResult:
    period_start: date
    period_end: date
    earned_prior: float
    earned_current: float
    unearned: float
    total_paid: float
    product_breakdown: dict = field(default_factory=dict)


def calculate_earned_unearned(
    policy: Policy,
    period_start: date,
    period_end: date,
) -> PeriodResult:
    """
    For a reporting period [period_start, period_end), calculate:
      - Earned in prior periods
      - Earned premium in this period
      - Unearned premium
    Only collected installments are considered.
    """
    daily = policy.daily_premium

    # Step 1: paid amounts (only collected installments)
    paid_prior = sum(
        i.amount for i in policy.installments
        if i.status == "collected" and i.bill_from < period_start
    )
    paid_through = sum(
        i.amount for i in policy.installments
        if i.status == "collected" and i.bill_from <= period_start
    )

    # Step 2: earned in prior periods
    days_prior = max((period_start - policy.start_date).days, 0)
    earned_prior = round(min(paid_prior, daily * days_prior), 2)

    # Step 3: earned premium this period
    is_last_period = period_end >= policy.end_date
    if is_last_period:
        # Last month rule: absorb rounding remainder
        earned_current = round(min(policy.total_premium - earned_prior, paid_through - earned_prior), 2)
    else:
        eff_start = max(period_start, policy.start_date)
        eff_end = min(period_end, policy.end_date)
        days_in_period = max((eff_end - eff_start).days, 0)
        earned_current = round(min(daily * days_in_period, paid_through - earned_prior), 2)
    earned_current = max(earned_current, 0)

    # Step 4: unearned premium
    unearned = round(paid_through - earned_prior - earned_current, 2)

    # Step 5: product split
    product_breakdown = {}
    for p in policy.products:
        ratio = p.premium / policy.total_premium
        product_breakdown[p.name] = {
            "earned_prior": earned_prior * ratio,
            "earned_current": earned_current * ratio,
            "unearned": unearned * ratio,
        }

    return PeriodResult(
        period_start=period_start,
        period_end=period_end,
        earned_prior=earned_prior,
        earned_current=earned_current,
        unearned=unearned,
        total_paid=paid_through,
        product_breakdown=product_breakdown,
    )


def generate_monthly_periods(start: date, end: date) -> List[tuple]:
    """Generate monthly [period_start, period_end) pairs covering the policy."""
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


def print_results(policy: Policy, results: List[PeriodResult]):
    """Print results in a tabular format for verification."""
    print(f"Policy: {policy.start_date} to {policy.end_date}")
    print(f"Total Premium: {policy.total_premium:.2f}")
    print(f"Days in Policy: {policy.days_in_policy}")
    print(f"Daily Premium: {policy.daily_premium:.6f}")
    print(f"Products: {', '.join(f'{p.name}={p.premium}' for p in policy.products)}")
    print(f"Installments: {len(policy.installments)}")
    for inst in policy.installments:
        print(f"  {inst.bill_from} -> {inst.bill_to}  amount={inst.amount:.2f}  status={inst.status}")
    print()

    header = f"{'Period':<25} {'Paid':>10} {'EarnedPrior':>12} {'EarnedCurr':>12} {'Unearned':>12}"
    print(header)
    print("-" * len(header))

    for r in results:
        print(
            f"{str(r.period_start)+' - '+str(r.period_end):<25} "
            f"{r.total_paid:>10.2f} {r.earned_prior:>12.2f} "
            f"{r.earned_current:>12.2f} {r.unearned:>12.2f}"
        )
        # for pname, pvals in r.product_breakdown.items():
        #     print(
        #         f"  {pname:<23} {'':>10} {pvals['earned_prior']:>12.2f} "
        #         f"{pvals['earned_current']:>12.2f} {pvals['unearned']:>12.2f}"
        #     )
    print()


def run_scenario(key: str, scenario: dict):
    """Run all policies in a scenario and print results."""
    print("=" * 75)
    print(f"  {key}: {scenario['description']}")
    print("=" * 75)
    for i, policy in enumerate(scenario["policies"]):
        if len(scenario["policies"]) > 1:
            print(f"\n--- Policy {i + 1} ---")
        periods = generate_monthly_periods(policy.start_date, policy.end_date)
        results = [calculate_earned_unearned(policy, ps, pe) for ps, pe in periods]
        print_results(policy, results)


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
