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

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List


@dataclass
class Installment:
    bill_from: date       # inclusive
    bill_to: date
    amount: float
    status: str           # "billed" or "collected"
    bill_to_inclusive: bool = True  # if True, bill_to is inclusive; if False, exclusive


@dataclass
class Product:
    name: str
    premium: float


@dataclass
class Endorsement:
    effective_date: date      # when coverage change starts
    end_date: date            # end of coverage for this layer
    additional_premium: float # premium added by this endorsement
    end_date_inclusive: bool = True  # if True, end_date is inclusive; if False, exclusive


@dataclass
class Policy:
    policy_number: str
    policy_id: str
    start_date: date
    end_date: date
    total_premium: float
    products: List[Product]
    installments: List[Installment]
    end_date_inclusive: bool = True
    endorsements: List[Endorsement] = field(default_factory=list)

    def _days(self, start: date, end: date) -> int:
        d = (end - start).days
        return d + 1 if self.end_date_inclusive else d

    def _end_exclusive(self, end: date) -> date:
        return end + timedelta(days=1) if self.end_date_inclusive else end

    @property
    def days_in_policy(self) -> int:
        return self._days(self.start_date, self.end_date)

    @property
    def daily_premium(self) -> float:
        return round(self.total_premium / self.days_in_policy, 2)

    @property
    def grand_total_premium(self) -> float:
        return self.total_premium + sum(e.additional_premium for e in self.endorsements)


@dataclass
class LayerDetail:
    label: str        # e.g. "Original", "Endorsement 1"
    daily_rate: float
    days: int
    earned: float     # daily_rate * days (or remainder for last month)

@dataclass
class PeriodResult:
    period_start: date
    period_end: date
    earned_prior: float
    earned_current: float
    unearned: float
    total_paid: float
    layer_details: List[LayerDetail] = field(default_factory=list)
    product_breakdown: dict = field(default_factory=dict)


@dataclass
class SummaryLayerInfo:
    label: str
    start: date
    end: date
    end_type: str       # "inclusive" or "exclusive"
    premium: float
    days: int
    daily: float


@dataclass
class ProductInfo:
    name: str
    premium: float
    ratio: float


@dataclass
class InstallmentInfo:
    index: int
    bill_from: date
    bill_to: date
    inclusive: bool
    amount: float
    status: str


@dataclass
class PolicyResult:
    policy_number: str
    policy_id: str
    summary_layers: List[SummaryLayerInfo]
    has_endorsements: bool
    grand_total_premium: float
    products: List[ProductInfo]
    installments: List[InstallmentInfo]
    periods: List[PeriodResult]
    layer_labels: List[str]
    total_earned_current: float
    final_total_paid: float
    final_unearned: float
    layer_totals: dict = field(default_factory=dict)


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


def calculate_all_periods(policy: Policy) -> List[PeriodResult]:
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
    prev_layer_cumulative = {}
    prev_layer_days = {}
    results = []

    for idx, (ps, pe) in enumerate(periods):
        is_last = (idx == len(periods) - 1)

        # Total paid as of this period (collected installments with bill_from <= period_start)
        paid_through = sum(
            i.amount for i in policy.installments
            if i.status == "collected" and i.bill_from <= ps
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

        # Build per-layer detail for this period (current period contribution)
        layer_details = []
        for layer, days_through, cum_earned in layer_cumulative_list:
            prev_cum = prev_layer_cumulative.get(layer["label"], 0.0)
            prev_days = prev_layer_days.get(layer["label"], 0)
            layer_period_earned = round(cum_earned - prev_cum, 2)
            # Effective days = days that produced this period's earned amount.
            # When a layer was unfunded in prior periods, catch-up means
            # the earned amount covers more days than just the current period.
            if layer["daily"] > 0 and layer_period_earned > 0:
                effective_days = round(layer_period_earned / layer["daily"])
            else:
                effective_days = days_through - prev_days
            layer_details.append(LayerDetail(
                label=layer["label"],
                daily_rate=layer["daily"],
                days=effective_days,
                earned=layer_period_earned,
            ))
            prev_layer_cumulative[layer["label"]] = cum_earned
            prev_layer_days[layer["label"]] = days_through

        # Product split (proportional to product premium / grand total)
        product_breakdown = {}
        for p in policy.products:
            ratio = p.premium / policy.total_premium  # ratio within original products
            product_breakdown[p.name] = {
                "earned_prior": round(cumulative_reported * ratio, 2),
                "earned_current": round(period_earned * ratio, 2),
                "unearned": round(unearned * ratio, 2),
            }

        results.append(PeriodResult(
            period_start=ps,
            period_end=pe,
            earned_prior=round(cumulative_reported, 2),
            earned_current=period_earned,
            unearned=unearned,
            total_paid=paid_through,
            layer_details=layer_details,
            product_breakdown=product_breakdown,
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

    products = [
        ProductInfo(name=p.name, premium=p.premium,
                    ratio=p.premium / policy.total_premium)
        for p in policy.products
    ]

    installments = [
        InstallmentInfo(index=idx, bill_from=inst.bill_from, bill_to=inst.bill_to,
                        inclusive=inst.bill_to_inclusive, amount=inst.amount,
                        status=inst.status)
        for idx, inst in enumerate(policy.installments, 1)
    ]

    layer_labels = []
    seen = set()
    for r in periods:
        for ld in r.layer_details:
            if ld.label not in seen:
                layer_labels.append(ld.label)
                seen.add(ld.label)

    total_earned_current = sum(r.earned_current for r in periods)
    layer_totals: dict = {}
    for r in periods:
        for ld in r.layer_details:
            layer_totals[ld.label] = layer_totals.get(ld.label, 0.0) + ld.earned

    last = periods[-1] if periods else None

    return PolicyResult(
        policy_number=policy.policy_number,
        policy_id=policy.policy_id,
        summary_layers=summary_layers,
        has_endorsements=bool(policy.endorsements),
        grand_total_premium=policy.grand_total_premium,
        products=products,
        installments=installments,
        periods=periods,
        layer_labels=layer_labels,
        total_earned_current=total_earned_current,
        final_total_paid=last.total_paid if last else 0.0,
        final_unearned=last.unearned if last else 0.0,
        layer_totals=layer_totals,
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
    print(f"  {'Layer':<16} {'Start':>12} {'End':>12} {'End Type':>10} {'Premium':>12} {'Days':>6} {'Daily':>9}")
    print(f"  {'─' * w}")
    for sl in result.summary_layers:
        print(f"  {sl.label:<16} {str(sl.start):>12} {str(sl.end):>12} {sl.end_type:>10} {sl.premium:>12.2f} {sl.days:>6} {sl.daily:>9.2f}")
    if result.has_endorsements:
        print(f"  {'─' * w}")
        print(f"  {'Grand Total':<16} {'':>12} {'':>12} {'':>10} {result.grand_total_premium:>12.2f} {'':>6} {'':>9}")
    print(f"  {'─' * w}")
    print()

    # --- Products ---
    print(f"  {'Products':^45}")
    print(f"  {'─' * 45}")
    print(f"  {'Name':<25} {'Premium':>12} {'Ratio':>6}")
    print(f"  {'─' * 45}")
    for p in result.products:
        print(f"  {p.name:<25} {p.premium:>12.2f} {p.ratio:>6.1%}")
    print(f"  {'─' * 45}")
    print()

    # --- Installments ---
    print(f"  {'Installments':^65}")
    print(f"  {'─' * 70}")
    print(f"  {'#':<4} {'Bill From':>12} {'Bill To':>12} {'Inclusive':>10} {'Amount':>12} {'Status':>11}")
    print(f"  {'─' * 70}")
    for inst in result.installments:
        incl = "Yes" if inst.inclusive else "No"
        print(f"  {inst.index:<4} {str(inst.bill_from):>12} {str(inst.bill_to):>12} {incl:>10} {inst.amount:>12.2f} {inst.status:>11}")
    print(f"  {'─' * 70}")
    print()

    # --- Earned / Unearned table ---
    layer_labels = result.layer_labels
    formula_w = 13
    earned_w = 10
    sep = " = "
    layer_col_width = formula_w + len(sep) + earned_w
    base_width = 71
    total_width = base_width + len(layer_labels) * (layer_col_width + 2)

    header = (
        f"  {'Period':<25} {'Paid':>10} {'EarnedPrior':>12} {'EarnedCurr':>12} {'Unearned':>12}"
    )
    for lbl in layer_labels:
        header += f"  {lbl:^{layer_col_width}}"
    print(header)
    print(f"  {'─' * total_width}")

    for r in result.periods:
        line = (
            f"  {str(r.period_start)+' - '+str(r.period_end):<25} "
            f"{r.total_paid:>10.2f} {r.earned_prior:>12.2f} "
            f"{r.earned_current:>12.2f} {r.unearned:>12.2f}"
        )
        ld_map = {ld.label: ld for ld in r.layer_details}
        for lbl in layer_labels:
            ld = ld_map.get(lbl)
            if ld and ld.earned != 0:
                formula = f"{ld.daily_rate:.2f} x {ld.days}d"
                line += f"  {formula:>{formula_w}}{sep}{ld.earned:>{earned_w}.2f}"
            else:
                line += f"  {'—':^{layer_col_width}}"
        print(line)

    # --- Total row ---
    total_line = (
        f"  {'Total':<25} "
        f"{result.final_total_paid:>10.2f} {'':>12} "
        f"{result.total_earned_current:>12.2f} {result.final_unearned:>12.2f}"
    )
    for lbl in layer_labels:
        earned = f"{round(result.layer_totals.get(lbl, 0.0), 2):.2f}"
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
