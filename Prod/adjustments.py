"""Delta engine for immutable closed periods."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Dict, Tuple

from models import LedgerPosting, MonthlyRevenue, ZERO, q2


def latest_posting_by_month(prior_postings: list[LedgerPosting]) -> Dict[date, LedgerPosting]:
    """
    Build the latest visible posting per month from immutable history.

    We keep all prior postings immutable and derive month-state by latest created_at.
    """
    best: Dict[date, LedgerPosting] = {}
    for posting in prior_postings:
        current = best.get(posting.reportingperiod_start)
        if current is None or posting.created_at > current.created_at:
            best[posting.reportingperiod_start] = posting
    return best


def aggregate_closed_deltas(
    recomputed: Dict[date, MonthlyRevenue],
    prior_postings: list[LedgerPosting],
    report_month: date,
) -> Tuple[
    Decimal,
    Decimal,
    Decimal,
    Dict[date, Tuple[Decimal, Decimal, Decimal]],
]:
    """
    Compare recomputed truth to closed posted months and return net deltas.

    Deltas are posted only in report_month, never by rewriting older periods.
    """
    current_by_month = latest_posting_by_month(prior_postings)

    earned_delta_total = ZERO
    unearned_paid_delta_total = ZERO
    unearned_written_delta_total = ZERO
    month_deltas: Dict[date, Tuple[Decimal, Decimal, Decimal]] = {}

    for month, posted in current_by_month.items():
        if month >= report_month:
            continue
        truth = recomputed.get(month)
        if truth is None:
            continue

        earned_delta = q2(truth.earned - posted.earned)
        unearned_paid_delta = q2(truth.unearned_paid_basis - posted.unearned_paid_basis)
        unearned_written_delta = q2(truth.unearned_written_basis - posted.unearned_written_basis)
        if earned_delta == ZERO and unearned_paid_delta == ZERO and unearned_written_delta == ZERO:
            continue

        month_deltas[month] = (earned_delta, unearned_paid_delta, unearned_written_delta)
        earned_delta_total = q2(earned_delta_total + earned_delta)
        unearned_paid_delta_total = q2(unearned_paid_delta_total + unearned_paid_delta)
        unearned_written_delta_total = q2(unearned_written_delta_total + unearned_written_delta)

    return earned_delta_total, unearned_paid_delta_total, unearned_written_delta_total, month_deltas

