"""Stateless earning and collected-amount computation engine."""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable

from models import InstallmentStatus, MonthlyRevenue, PolicyInput, PremiumSlice, ZERO, q2


def month_start(dt: date) -> date:
    return date(dt.year, dt.month, 1)


def month_end(dt: date) -> date:
    last = calendar.monthrange(dt.year, dt.month)[1]
    return date(dt.year, dt.month, last)


def next_month(dt: date) -> date:
    if dt.month == 12:
        return date(dt.year + 1, 1, 1)
    return date(dt.year, dt.month + 1, 1)


def month_range(start: date, end_exclusive: date) -> Iterable[date]:
    cur = month_start(start)
    while cur < end_exclusive:
        yield cur
        cur = next_month(cur)


def _collected_amount_by_month(policy: PolicyInput) -> Dict[date, Decimal]:
    collected_by_month: Dict[date, Decimal] = {}
    for inst in policy.installments:
        if inst.status != InstallmentStatus.COLLECTED:
            continue
        if inst.collected_date is None:
            continue
        m = month_start(inst.collected_date)
        collected_by_month[m] = q2(collected_by_month.get(m, ZERO) + inst.amount)
    return collected_by_month


def _collected_paid_through_by_month(policy: PolicyInput, months: list[date]) -> Dict[date, Decimal]:
    """Collected amount available up to each month-end."""
    collected = [
        inst
        for inst in policy.installments
        if inst.status == InstallmentStatus.COLLECTED and inst.collected_date is not None
    ]
    paid_through: Dict[date, Decimal] = {}
    for m in months:
        me = month_end(m)
        paid = q2(
            sum(
                (
                    inst.amount
                    for inst in collected
                    if inst.collected_date <= me and inst.bill_from <= me
                ),
                ZERO,
            )
        )
        paid_through[m] = paid
    return paid_through


def compute_monthly_truth(policy: PolicyInput, slices: list[PremiumSlice]) -> Dict[date, MonthlyRevenue]:
    """Compute monthly earned/unearned/collected from slices (true view as-of run)."""
    months = list(month_range(policy.start_date, policy.policy_end_exclusive))
    collected_by_month = _collected_amount_by_month(policy)
    paid_through_by_month = _collected_paid_through_by_month(policy, months)

    theoretical_earned_by_month: Dict[date, Decimal] = {}

    for m in months:
        ms = m
        month_earned = ZERO

        for sl in slices:
            overlap_start = max(ms, sl.start_date)
            overlap_end_exclusive = min(next_month(m), sl.end_exclusive)
            overlap_days = (overlap_end_exclusive - overlap_start).days
            if overlap_days <= 0:
                continue
            month_earned = q2(month_earned + (sl.daily_rate * Decimal(overlap_days)))

        theoretical_earned_by_month[m] = q2(month_earned)

    if months:
        last_month = months[-1]
        total_premium = q2(sum((sl.premium for sl in slices), ZERO))
        prior = q2(sum((theoretical_earned_by_month[m] for m in months[:-1]), ZERO))
        theoretical_earned_by_month[last_month] = q2(total_premium - prior)

    recognized_earned_by_month: Dict[date, Decimal] = {}
    recognized_running = ZERO
    theoretical_running = ZERO
    for m in months:
        theoretical_running = q2(theoretical_running + theoretical_earned_by_month[m])
        paid_through = paid_through_by_month[m]
        capped_cumulative = min(theoretical_running, paid_through)
        month_earned = q2(capped_cumulative - recognized_running)
        if month_earned < ZERO:
            month_earned = ZERO
        recognized_earned_by_month[m] = month_earned
        recognized_running = q2(recognized_running + month_earned)

    results: Dict[date, MonthlyRevenue] = {}
    running = ZERO
    for m in months:
        earned = recognized_earned_by_month[m]
        running = q2(running + earned)
        written_to_month = q2(
            sum((sl.premium for sl in slices if sl.start_date <= month_end(m)), ZERO)
        )
        paid_through = paid_through_by_month[m]
        unearned_paid_basis = q2(paid_through - running)
        unearned_written_basis = q2(written_to_month - running)
        collected_amount = collected_by_month.get(m, ZERO)
        results[m] = MonthlyRevenue(
            month=m,
            earned=earned,
            unearned_paid_basis=unearned_paid_basis,
            unearned_written_basis=unearned_written_basis,
            collected_amount=collected_amount,
        )

    return results

