"""Production-style revenue runner with immutable posting history."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from adjustments import aggregate_closed_deltas
from earning import compute_monthly_truth
from models import LedgerPosting, PolicyRunInput, ZERO, q2
from posting_repository import append_postings, load_postings
from test_data import SCENARIOS
from timeline import build_premium_slices


STORE_PATH = Path(__file__).resolve().parent / "postings_store.json"


def _month_label(month: date) -> str:
    return month.strftime("%Y-%m")


def _fmt_money(value) -> str:
    return f"{q2(value):.2f}"


def _reporting_period_label(month_start: date) -> str:
    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    month_end = date(month_start.year, month_start.month, last_day)
    return f"{month_start.strftime('%d-%b-%Y')} to {month_end.strftime('%d-%b-%Y')}"


def _reporting_period_end(month_start: date) -> date:
    last_day = calendar.monthrange(month_start.year, month_start.month)[1]
    return date(month_start.year, month_start.month, last_day)


def _merge_prior_postings(run_input: PolicyRunInput) -> list[LedgerPosting]:
    """
    Merge seed prior postings (from test input) + persisted postings.

    All postings stay immutable; we only append new postings.
    """
    persisted: list[LedgerPosting] = []
    if run_input.include_persisted_history:
        persisted = [
            p
            for p in load_postings(STORE_PATH)
            if p.policy_id == run_input.policy.policy_id
        ]
    return run_input.prior_postings + persisted


def process_policy(
    run_input: PolicyRunInput,
    scenario_name: str = "",
    scenario_description: str = "",
) -> LedgerPosting:
    policy = run_input.policy
    report_month = run_input.report_month
    now = datetime.utcnow()
    run_id = f"run-{uuid4().hex[:10]}"

    slices = build_premium_slices(policy, report_month)
    truth = compute_monthly_truth(policy, slices)
    current = truth.get(report_month)
    if current is None:
        raise ValueError(
            f"Report month {_month_label(report_month)} is outside policy range for {policy.policy_id}"
        )

    prior_postings = _merge_prior_postings(run_input)
    (
        adj_earned,
        adj_unearned_paid_basis,
        adj_unearned_written_basis,
        month_deltas,
    ) = aggregate_closed_deltas(
        recomputed=truth,
        prior_postings=prior_postings,
        report_month=report_month,
    )

    posting = LedgerPosting(
        posting_id=f"pst-{uuid4().hex[:12]}",
        policy_id=policy.policy_id,
        reportingperiod_start=report_month,
        reportingperiod_end=_reporting_period_end(report_month),
        earned=q2(current.earned + adj_earned),
        unearned_paid_basis=q2(current.unearned_paid_basis + adj_unearned_paid_basis),
        unearned_written_basis=q2(current.unearned_written_basis + adj_unearned_written_basis),
        collected_amount=current.collected_amount,
        adjustment_earned=adj_earned,
        adjustment_unearned_paid_basis=adj_unearned_paid_basis,
        adjustment_unearned_written_basis=adj_unearned_written_basis,
        source=(
            "BASE+ADJUSTMENT"
            if (
                adj_earned != ZERO
                or adj_unearned_paid_basis != ZERO
                or adj_unearned_written_basis != ZERO
            )
            else "BASE"
        ),
        created_at=now,
        run_id=run_id,
        details={
            f"{_month_label(month)}_earned_delta": e
            for month, (e, _up, _uw) in month_deltas.items()
        }
        | {
            f"{_month_label(month)}_unearned_paid_delta": up
            for month, (_e, up, _uw) in month_deltas.items()
        }
        | {
            f"{_month_label(month)}_unearned_written_delta": uw
            for month, (_e, _up, uw) in month_deltas.items()
        },
    )

    append_postings(STORE_PATH, [posting])
    report_lines = build_policy_report_lines(
        run_input=run_input,
        posting=posting,
        slices=slices,
        month_deltas=month_deltas,
        truth=truth,
        scenario_name=scenario_name,
        scenario_description=scenario_description,
    )
    print_policy_report(report_lines)
    return posting


def build_policy_report_lines(
    run_input: PolicyRunInput,
    posting: LedgerPosting,
    slices,
    month_deltas,
    truth,
    scenario_name: str = "",
    scenario_description: str = "",
) -> list[str]:
    policy = run_input.policy
    report_month = run_input.report_month
    lines: list[str] = []

    lines.append("*" * 95)
    lines.append("Scenario Context")
    lines.append("-" * 95)
    lines.append(f"Scenario Name : {scenario_name}")
    lines.append(f"Description   : {scenario_description}")
    lines.append("*" * 95)
    lines.append("Policy Context")
    lines.append("-" * 95)
    lines.append(f"Policy Number : {policy.policy_number}")
    lines.append(f"Policy ID     : {policy.policy_id or ''}")
    lines.append(f"Coverage      : {policy.start_date} -> {policy.end_date}")
    lines.append(f"Report Month  : {_month_label(report_month)}")
    lines.append("*" * 95)

    lines.append("")
    lines.append("Policy events (source timeline):")
    lines.append(
        f"  {'#':<2} {'Type':<9} {'Effective':<12} {'End(excl)':<12} {'Txn Date':<12} {'Premium Delta':>13}"
    )
    for idx, event in enumerate(
        sorted(policy.events, key=lambda e: (e.effective_date, e.transaction_date, e.event_id)), 1
    ):
        lines.append(
            f"  {idx:<2} {event.event_type.value:<9} {str(event.effective_date):<12} "
            f"{str(event.end_date):<12} {str(event.transaction_date):<12} {_fmt_money(event.premium_delta):>13}"
        )

    lines.append("")
    lines.append("Derived premium slices (as-of report month):")
    lines.append(
        f"  {'#':<2} {'Event ID':<14} {'Type':<9} {'Start':<12} {'End(excl)':<12} "
        f"{'Premium':>10} {'Days':>9} {'DailyRate':>10}"
    )
    for idx, sl in enumerate(sorted(slices, key=lambda s: (s.start_date, s.event_id)), 1):
        lines.append(
            f"  {idx:<2} {sl.event_id:<14} {sl.event_type.value:<9} {str(sl.start_date):<12} "
            f"{str(sl.end_exclusive):<12} {_fmt_money(sl.premium):>10} {sl.total_days:>9} {_fmt_money(sl.daily_rate):>10}"
        )
    total_slice_premium = sum((sl.premium for sl in slices), ZERO)
    lines.append(f"  {'':<49} {'Total':<9} {_fmt_money(total_slice_premium):>10}")

    lines.append("")
    lines.append("Installments (collection schedule):")
    lines.append(
        f"  {'#':<2} {'Bill From':<12} {'Bill To(excl)':<12} {'Amount':>10} {'Status':<12} {'Collected Date':<12}"
    )
    if policy.installments:
        for idx, inst in enumerate(sorted(policy.installments, key=lambda i: i.bill_from), 1):
            collected = str(inst.collected_date) if inst.collected_date else "—"
            lines.append(
                f"  {idx:<2} {str(inst.bill_from):<12} {str(inst.bill_to_exclusive):<12} "
                f"{_fmt_money(inst.amount):>10} "
                f"{inst.status.value:<12} {collected:<12}"
            )
    else:
        lines.append("  (none)")

    if run_input.prior_postings:
        lines.append("")
        lines.append("Seed prior postings provided by test input:")
        lines.append(
            f"  {'ReportingPeriod':<27} {'Earned':>10} {'Unearned(Paid)':>14} {'Unearned(Written)':>18} {'Source':<10} {'Run ID':<14}"
        )
        for p in sorted(run_input.prior_postings, key=lambda x: (x.reportingperiod_start, x.created_at)):
            lines.append(
            f"  {_reporting_period_label(p.reportingperiod_start):<27} {_fmt_money(p.earned):>10} {_fmt_money(p.unearned_paid_basis):>14} {_fmt_money(p.unearned_written_basis):>18} "
                f"{p.source:<10} {p.run_id:<14}"
            )
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Month truth (as-of report run):")
    lines.append(
        f"  {'ReportingPeriod':<27} {'Earned':>10} {'Unearned(Paid)':>14} {'Unearned(Written)':>18} {'Collected':>10}"
    )
    for month in sorted(truth.keys()):
        row = truth[month]
        lines.append(
            f"  {_reporting_period_label(month):<27} {_fmt_money(row.earned):>10} {_fmt_money(row.unearned_paid_basis):>14} {_fmt_money(row.unearned_written_basis):>18} {_fmt_money(row.collected_amount):>10}"
        )

    lines.append("")
    lines.append("Closed month deltas posted forward:")
    if month_deltas:
        lines.append(
            f"  {'ReportingPeriod':<27} {'Earned Delta':>14} {'Unearned Paid Delta':>20} {'Unearned Written Delta':>24}"
        )
        for month in sorted(month_deltas.keys()):
            e, up, uw = month_deltas[month]
            lines.append(
                f"  {_reporting_period_label(month):<27} {_fmt_money(e):>14} {_fmt_money(up):>20} {_fmt_money(uw):>24}"
            )
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("Posted row for report month:")
    lines.append(
        f"  {'ReportingPeriod':<27} {'Earned':>10} {'Unearned(Paid)':>14} {'Unearned(Written)':>18} {'Collected':>10} "
        f"{'Adj(Earned)':>13} {'Adj(UnearnedPaid)':>18} {'Adj(UnearnedWritten)':>22} {'Source':>17}"
    )
    lines.append(
        f"  {_reporting_period_label(posting.reportingperiod_start):<27} {_fmt_money(posting.earned):>10} {_fmt_money(posting.unearned_paid_basis):>14} {_fmt_money(posting.unearned_written_basis):>18}"
        f" {_fmt_money(posting.collected_amount):>10} {_fmt_money(posting.adjustment_earned):>13}"
        f" {_fmt_money(posting.adjustment_unearned_paid_basis):>18} {_fmt_money(posting.adjustment_unearned_written_basis):>22} {posting.source:>17}"
    )
    lines.append("")
    return lines


def print_policy_report(lines: list[str]) -> None:
    """Pure output function: only prints already-prepared report lines."""
    for line in lines:
        print(line)


def run_scenario(name: str) -> None:
    scenario = SCENARIOS[name]
    for run_input in scenario["inputs"]:
        process_policy(
            run_input=run_input,
            scenario_name=name,
            scenario_description=scenario["description"],
        )


def main() -> None:
    import sys

    keys = list(SCENARIOS.keys())
    if len(sys.argv) > 1:
        selected = sys.argv[1]
    else:
        print("Available scenarios:")
        for i, key in enumerate(keys, 1):
            print(f"  {i}. {key}")
        print("  *. all")
        choice = input("Select scenario (number/name/all): ").strip()
        if choice == "*" or choice.lower() == "all":
            selected = "all"
        elif choice.isdigit() and 1 <= int(choice) <= len(keys):
            selected = keys[int(choice) - 1]
        else:
            selected = choice

    if selected == "all":
        for key in keys:
            run_scenario(key)
    elif selected in SCENARIOS:
        run_scenario(selected)
    else:
        raise SystemExit(f"Unknown scenario '{selected}'. Options: {', '.join(keys)}")


if __name__ == "__main__":
    main()

