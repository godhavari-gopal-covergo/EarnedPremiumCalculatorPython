"""Timeline builder from policy events to premium slices."""

from __future__ import annotations

import calendar
from datetime import date
from typing import List

from models import PolicyInput, PremiumSlice


def build_premium_slices(policy: PolicyInput, as_of_month: date) -> List[PremiumSlice]:
    """
    Build premium slices from policy events visible by reporting month.

    Only events with transaction_date <= as_of_month are considered available.
    """
    month_last_day = calendar.monthrange(as_of_month.year, as_of_month.month)[1]
    as_of_cutoff = date(as_of_month.year, as_of_month.month, month_last_day)

    visible_events = [
        event
        for event in policy.events
        if event.transaction_date <= as_of_cutoff
    ]

    slices: List[PremiumSlice] = []
    for event in sorted(visible_events, key=lambda e: (e.effective_date, e.transaction_date, e.event_id)):
        start = max(event.effective_date, policy.start_date)
        end_exclusive = min(event.end_exclusive, policy.policy_end_exclusive)
        if start >= end_exclusive:
            continue
        slices.append(
            PremiumSlice(
                event_id=event.event_id,
                event_type=event.event_type,
                start_date=start,
                end_exclusive=end_exclusive,
                premium=event.premium_delta,
            )
        )
    return slices

