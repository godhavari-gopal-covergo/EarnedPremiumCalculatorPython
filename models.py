"""Data models for earned / unearned premium calculation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import List


class InstallmentStatus(str, Enum):
    BILLED = "BILLED"
    DUE = "DUE"
    OVERDUE = "OVERDUE"
    COLLECTED = "COLLECTED"


@dataclass
class Installment:
    bill_from: date       # inclusive
    bill_to: date
    amount: float
    status: InstallmentStatus
    bill_to_inclusive: bool = True  # if True, bill_to is inclusive; if False, exclusive


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
class PolicyPeriod:
    """Earned premium slice for one premium component (e.g. Original, Endorsement 1) within a reporting row."""
    label: str        # e.g. "Original", "Endorsement 1"
    daily_rate: float
    days: int
    earned: float     # daily_rate * days (or remainder for last month)


@dataclass
class ReportingPeriodResult:
    reportingperiod_start: date
    reportingperiod_end: date
    earned_prior: float
    earned_current: float
    unearned: float
    total_paid: float
    policy_periods: List[PolicyPeriod] = field(default_factory=list)


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
class InstallmentInfo:
    index: int
    bill_from: date
    bill_to: date
    inclusive: bool
    amount: float
    status: InstallmentStatus


@dataclass
class PolicyResult:
    policy_number: str
    policy_id: str
    summary_layers: List[SummaryLayerInfo]
    has_endorsements: bool
    grand_total_premium: float
    installments: List[InstallmentInfo]
    periods: List[ReportingPeriodResult]
    policy_period_labels: List[str]
    total_earned_current: float
    final_total_paid: float
    final_unearned: float
    policy_period_totals: dict = field(default_factory=dict)
