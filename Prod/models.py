"""Domain and ledger models for production revenue accounting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional

ZERO = Decimal("0.00")
TWO_PLACES = Decimal("0.01")


def q2(value: Decimal) -> Decimal:
    """Normalize to 2 decimal places using financial rounding."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class EventType(str, Enum):
    ISSUE = "ISSUE"
    MTA = "MTA"
    CANCEL = "CANCEL"


class InstallmentStatus(str, Enum):
    BILLED = "BILLED"
    DUE = "DUE"
    OVERDUE = "OVERDUE"
    COLLECTED = "COLLECTED"


@dataclass(frozen=True)
class PolicyEvent:
    """Coverage event that creates a premium layer."""

    event_id: str
    event_type: EventType
    effective_date: date
    end_date: date
    premium_delta: Decimal
    transaction_date: date
    end_date_inclusive: bool = True

    @property
    def end_exclusive(self) -> date:
        return self.end_date + timedelta(days=1) if self.end_date_inclusive else self.end_date


@dataclass(frozen=True)
class Installment:
    bill_from: date
    bill_to_exclusive: date
    amount: Decimal
    status: InstallmentStatus
    collected_date: Optional[date] = None


@dataclass(frozen=True)
class PolicyInput:
    policy_id: str
    policy_number: str
    start_date: date
    end_date: date
    events: List[PolicyEvent]
    installments: List[Installment] = field(default_factory=list)
    end_date_inclusive: bool = True

    @property
    def policy_end_exclusive(self) -> date:
        return self.end_date + timedelta(days=1) if self.end_date_inclusive else self.end_date


@dataclass(frozen=True)
class PremiumSlice:
    event_id: str
    event_type: EventType
    start_date: date
    end_exclusive: date
    premium: Decimal

    @property
    def total_days(self) -> int:
        return max((self.end_exclusive - self.start_date).days, 1)

    @property
    def daily_rate(self) -> Decimal:
        return q2(self.premium / Decimal(self.total_days))


@dataclass(frozen=True)
class MonthlyRevenue:
    month: date
    earned: Decimal
    unearned_paid_basis: Decimal
    unearned_written_basis: Decimal
    collected_amount: Decimal

    @property
    def unearned(self) -> Decimal:
        """Backward-compatible alias to written-basis unearned."""
        return self.unearned_written_basis


@dataclass(frozen=True)
class LedgerPosting:
    """
    Immutable posting for a policy-month.

    Store this append-only and derive the latest month view from full history.
    """

    posting_id: str
    policy_id: str
    reportingperiod_start: date
    reportingperiod_end: date
    earned: Decimal
    unearned_paid_basis: Decimal
    unearned_written_basis: Decimal
    collected_amount: Decimal
    adjustment_earned: Decimal
    adjustment_unearned_paid_basis: Decimal
    adjustment_unearned_written_basis: Decimal
    source: str  # BASE or ADJUSTMENT
    created_at: datetime
    run_id: str
    details: Dict[str, Decimal] = field(default_factory=dict)

    @property
    def unearned(self) -> Decimal:
        """Backward-compatible alias to written-basis unearned."""
        return self.unearned_written_basis

    @property
    def adjustment_unearned(self) -> Decimal:
        """Backward-compatible alias to written-basis unearned adjustment."""
        return self.adjustment_unearned_written_basis


@dataclass(frozen=True)
class PolicyRunInput:
    policy: PolicyInput
    report_month: date
    prior_postings: List[LedgerPosting] = field(default_factory=list)
    include_persisted_history: bool = True

