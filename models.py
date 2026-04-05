"""Data models for earned / unearned premium calculation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional

ZERO = Decimal("0.00")
TWO_PLACES = Decimal("0.01")


class InstallmentStatus(str, Enum):
    BILLED = "BILLED"
    DUE = "DUE"
    OVERDUE = "OVERDUE"
    COLLECTED = "COLLECTED"


@dataclass
class Installment:
    bill_from: date       # inclusive
    bill_to: date
    amount: Decimal
    status: InstallmentStatus
    bill_to_inclusive: bool = True  # if True, bill_to is inclusive; if False, exclusive
    collected_date: Optional[date] = None  # date payment was actually collected


@dataclass
class Endorsement:
    effective_date: date      # when coverage change starts
    end_date: date            # end of coverage for this layer
    additional_premium: Decimal  # premium added by this endorsement
    end_date_inclusive: bool = True  # if True, end_date is inclusive; if False, exclusive


@dataclass
class Policy:
    policy_number: str
    policy_id: str
    start_date: date
    end_date: date
    total_premium: Decimal
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
    def daily_premium(self) -> Decimal:
        return (self.total_premium / self.days_in_policy).quantize(TWO_PLACES)

    @property
    def grand_total_premium(self) -> Decimal:
        return self.total_premium + sum(
            (e.additional_premium for e in self.endorsements), ZERO
        )


@dataclass
class PolicyPeriod:
    """Earned premium slice for one premium component (e.g. Original, Endorsement 1) within a reporting row."""
    label: str        # e.g. "Original", "Endorsement 1"
    daily_rate: Decimal
    days: int
    earned: Decimal     # daily_rate * days (or remainder for last month)
    formula: Optional[str] = None  # override display formula (e.g. for sweep / cap)


@dataclass
class ReportingPeriodResult:
    reportingperiod_start: date
    reportingperiod_end: date
    earned_prior: Decimal
    earned_current: Decimal
    unearned: Decimal
    total_paid: Decimal
    policy_periods: List[PolicyPeriod] = field(default_factory=list)


@dataclass
class SummaryLayerInfo:
    label: str
    start: date
    end: date
    end_type: str       # "inclusive" or "exclusive"
    premium: Decimal
    days: int
    daily: Decimal


@dataclass
class InstallmentInfo:
    index: int
    bill_from: date
    bill_to: date
    inclusive: bool
    amount: Decimal
    status: InstallmentStatus
    collected_date: Optional[date] = None


@dataclass
class PolicyResult:
    policy_number: str
    policy_id: str
    summary_layers: List[SummaryLayerInfo]
    has_endorsements: bool
    grand_total_premium: Decimal
    installments: List[InstallmentInfo]
    periods: List[ReportingPeriodResult]
    policy_period_labels: List[str]
    total_earned_current: Decimal
    final_total_paid: Decimal
    final_unearned: Decimal
    policy_period_totals: dict = field(default_factory=dict)
