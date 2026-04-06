"""Production-like scenario inputs including immutable prior postings."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from models import (
    EventType,
    Installment,
    InstallmentStatus,
    LedgerPosting,
    PolicyEvent,
    PolicyInput,
    PolicyRunInput,
    ZERO,
)

D = Decimal


def seeded_posting(
    policy_id: str,
    period_start: date,
    period_end: date,
    earned: str,
    unearned_written_basis: str,
    unearned_paid_basis: str | None = None,
    source: str = "SEED",
) -> LedgerPosting:
    paid_basis = unearned_paid_basis if unearned_paid_basis is not None else unearned_written_basis
    return LedgerPosting(
        posting_id=f"seed-{policy_id}-{period_start.isoformat()}",
        policy_id=policy_id,
        reportingperiod_start=period_start,
        reportingperiod_end=period_end,
        earned=D(earned),
        unearned_paid_basis=D(paid_basis),
        unearned_written_basis=D(unearned_written_basis),
        collected_amount=ZERO,
        adjustment_earned=ZERO,
        adjustment_unearned_paid_basis=ZERO,
        adjustment_unearned_written_basis=ZERO,
        source=source,
        created_at=datetime(2026, 4, 1, 0, 0, 0),
        run_id="seed-history",
        details={},
    )


SCENARIOS = {
    "shortterm_monthly_phil_scenario": {
        "description": (
            "Phil short-term monthly-pay scenario: policy 1-Jan-2026 to 10-Apr-2026, premium 1250.00 with payments 550/350/350 in Jan/Feb/Mar."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="MOCK-SHORTTERM-MONTHLY-PHIL-001",
                    policy_number="POL-PHIL-MONTHLY-001",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 4, 10),
                    end_date_inclusive=False,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-PHIL-MONTHLY-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 1, 1),
                            end_date=date(2026, 4, 10),
                            premium_delta=D("1250.00"),
                            transaction_date=date(2026, 1, 1),
                            end_date_inclusive=False,
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 1, 1),
                            bill_to_exclusive=date(2026, 2, 1),
                            amount=D("550.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 1, 1),
                        ),
                        Installment(
                            bill_from=date(2026, 2, 1),
                            bill_to_exclusive=date(2026, 3, 1),
                            amount=D("350.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 2, 1),
                        ),
                        Installment(
                            bill_from=date(2026, 3, 1),
                            bill_to_exclusive=date(2026, 4, 1),
                            amount=D("350.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 3, 1),
                        ),
                    ],
                ),
                report_month=date(2026, 3, 1),
                prior_postings=[],
                include_persisted_history=False,
            ),
        ],
    },
    "shortterm_fullpay_phil_scenario": {
        "description": (
            "Phil short-term full-pay scenario: policy 1-Jan-2026 to 10-Apr-2026, premium 1250.00 fully paid."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="MOCK-SHORTTERM-FULLPAY-PHIL-001",
                    policy_number="POL-PHIL-FULLPAY-001",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 4, 10),
                    end_date_inclusive=False,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-PHIL-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 1, 1),
                            end_date=date(2026, 4, 10),
                            premium_delta=D("1250.00"),
                            transaction_date=date(2026, 1, 1),
                            end_date_inclusive=False,
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 1, 1),
                            bill_to_exclusive=date(2026, 4, 10),
                            amount=D("1250.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 1, 1),
                        ),
                    ],
                ),
                report_month=date(2026, 1, 1),
                prior_postings=[],
                include_persisted_history=False,
            ),
        ],
    },
    "annual_feb1_pol0002_billed": {
        "description": (
            "POL-0002: 1-Feb-2026 to 1-Feb-2027 inclusive; single BILLED installment (not collected)."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="MOCK-ANNUAL-BILLED-001",
                    policy_number="POL-0002",
                    start_date=date(2026, 2, 1),
                    end_date=date(2027, 2, 1),
                    end_date_inclusive=True,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-ANNUAL-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 2, 1),
                            end_date=date(2027, 2, 1),
                            premium_delta=D("2529.36"),
                            transaction_date=date(2026, 2, 1),
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 2, 1),
                            bill_to_exclusive=date(2027, 2, 2),
                            amount=D("2529.36"),
                            status=InstallmentStatus.BILLED,
                            collected_date=None,
                        ),
                    ],
                ),
                report_month=date(2026, 2, 1),
                prior_postings=[],
                include_persisted_history=False,
            ),
        ],
    },
    "annual_feb1_pol0002_collected_feb": {
        "description": (
            "POL-0002: 1-Feb-2026 to 1-Feb-2027 inclusive; single COLLECTED installment in Feb."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="MOCK-ANNUAL-COL-FEB-001",
                    policy_number="POL-0002",
                    start_date=date(2026, 2, 1),
                    end_date=date(2027, 2, 1),
                    end_date_inclusive=True,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-ANNUAL-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 2, 1),
                            end_date=date(2027, 2, 1),
                            premium_delta=D("2529.36"),
                            transaction_date=date(2026, 2, 1),
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 2, 1),
                            bill_to_exclusive=date(2027, 2, 2),
                            amount=D("2529.36"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 2, 5),
                        ),
                    ],
                ),
                report_month=date(2026, 2, 1),
                prior_postings=[],
                include_persisted_history=False,
            ),
        ],
    },
    "annual_feb1_pol0002_collected_mar": {
        "description": (
            "POL-0002: 1-Feb-2026 to 1-Feb-2027 inclusive; single COLLECTED installment in Mar."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="MOCK-ANNUAL-COL-MAR-001",
                    policy_number="POL-0002",
                    start_date=date(2026, 2, 1),
                    end_date=date(2027, 2, 1),
                    end_date_inclusive=True,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-ANNUAL-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 2, 1),
                            end_date=date(2027, 2, 1),
                            premium_delta=D("2529.36"),
                            transaction_date=date(2026, 2, 1),
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 2, 1),
                            bill_to_exclusive=date(2027, 2, 2),
                            amount=D("2529.36"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 2, 5),
                        ),
                    ],
                ),
                report_month=date(2026, 3, 1),
                prior_postings=[
                    seeded_posting("MOCK-ANNUAL-COL-MAR-001", date(2026, 2, 1), date(2026, 2, 28), "193.48", "2335.88"),
                ],
                include_persisted_history=False,
            ),
        ],
    },
    "annual_feb1_pol0002_mtaFeb25_collected_mar": {
        "description": (
            "POL-0002: 1-Feb-2026 to 1-Feb-2027 inclusive; MTA effective 25-Feb (txn 5-Mar) with +1095.24 premium, collected in Mar."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="MOCK-ANNUAL-FEB1-MTAFEB25-COL-MAR-001",
                    policy_number="POL-0002",
                    start_date=date(2026, 2, 1),
                    end_date=date(2027, 2, 1),
                    end_date_inclusive=True,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-ANNUAL-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 2, 1),
                            end_date=date(2027, 2, 1),
                            premium_delta=D("2529.36"),
                            transaction_date=date(2026, 2, 1),
                        ),
                        PolicyEvent(
                            event_id="E-MTA-FEB25-1",
                            event_type=EventType.MTA,
                            effective_date=date(2026, 2, 25),
                            end_date=date(2027, 2, 1),
                            premium_delta=D("1095.24"),
                            transaction_date=date(2026, 3, 5),
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 2, 1),
                            bill_to_exclusive=date(2027, 2, 2),
                            amount=D("2529.36"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 2, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 2, 25),
                            bill_to_exclusive=date(2027, 2, 2),
                            amount=D("1095.24"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 3, 5),
                        ),
                    ],
                ),
                report_month=date(2026, 3, 1),
                prior_postings=[
                    seeded_posting(
                        "MOCK-ANNUAL-FEB1-MTAFEB25-COL-MAR-001",
                        date(2026, 2, 1),
                        date(2026, 2, 28),
                        "193.48",
                        "2335.88",
                    ),
                ],
                include_persisted_history=False,
            ),
        ],
    },
    "monthly_feb1_regular": {
        "description": (
            "Regular monthly policy: ISSUE Jan-Dec 2026 with premium 1200.00 and all monthly installments collected in respective months."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="MOCK-MONTHLY-FEB1-REG-001",
                    policy_number="POL-MONTHLY-REG-001",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    end_date_inclusive=True,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-REG-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 1, 1),
                            end_date=date(2026, 12, 31),
                            premium_delta=D("1200.00"),
                            transaction_date=date(2026, 1, 1),
                        ),
                    ],
                    installments=[
                        Installment(date(2026, 1, 1), date(2026, 2, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 1, 5)),
                        Installment(date(2026, 2, 1), date(2026, 3, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 2, 5)),
                        Installment(date(2026, 3, 1), date(2026, 4, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 3, 5)),
                        Installment(date(2026, 4, 1), date(2026, 5, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 4, 5)),
                        Installment(date(2026, 5, 1), date(2026, 6, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 5, 5)),
                        Installment(date(2026, 6, 1), date(2026, 7, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 6, 5)),
                        Installment(date(2026, 7, 1), date(2026, 8, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 7, 5)),
                        Installment(date(2026, 8, 1), date(2026, 9, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 8, 5)),
                        Installment(date(2026, 9, 1), date(2026, 10, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 9, 5)),
                        Installment(date(2026, 10, 1), date(2026, 11, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 10, 5)),
                        Installment(date(2026, 11, 1), date(2026, 12, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 11, 5)),
                        Installment(date(2026, 12, 1), date(2027, 1, 1), D("100.00"), InstallmentStatus.COLLECTED, date(2026, 12, 5)),
                    ],
                ),
                report_month=date(2026, 4, 1),
                prior_postings=[],
                include_persisted_history=False,
            ),
        ],
    },
    "backdated_mta_increase": {
        "description": (
            "Backdated premium increase posted in April. Jan-Feb-Mar were already posted and immutable."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="P-BACK-INC-001",
                    policy_number="POL-BACK-INC-001",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    end_date_inclusive=True,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 1, 1),
                            end_date=date(2026, 12, 31),
                            premium_delta=D("1200.00"),
                            transaction_date=date(2026, 1, 1),
                        ),
                        PolicyEvent(
                            event_id="E-MTA-BACK-1",
                            event_type=EventType.MTA,
                            effective_date=date(2026, 2, 1),
                            end_date=date(2026, 12, 31),
                            premium_delta=D("600.00"),
                            transaction_date=date(2026, 4, 10),  # backdated event recorded in April
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 1, 1),
                            bill_to_exclusive=date(2026, 2, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 1, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 2, 1),
                            bill_to_exclusive=date(2026, 3, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 2, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 3, 1),
                            bill_to_exclusive=date(2026, 4, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 3, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 4, 1),
                            bill_to_exclusive=date(2026, 5, 1),
                            amount=D("300.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 4, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 5, 1),
                            bill_to_exclusive=date(2026, 6, 1),
                            amount=D("150.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 5, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 6, 1),
                            bill_to_exclusive=date(2026, 7, 1),
                            amount=D("150.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 6, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 7, 1),
                            bill_to_exclusive=date(2026, 8, 1),
                            amount=D("150.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 7, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 8, 1),
                            bill_to_exclusive=date(2026, 9, 1),
                            amount=D("150.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 8, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 9, 1),
                            bill_to_exclusive=date(2026, 10, 1),
                            amount=D("150.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 9, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 10, 1),
                            bill_to_exclusive=date(2026, 11, 1),
                            amount=D("150.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 10, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 11, 1),
                            bill_to_exclusive=date(2026, 12, 1),
                            amount=D("150.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 11, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 12, 1),
                            bill_to_exclusive=date(2027, 1, 1),
                            amount=D("150.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 12, 5),
                        ),
                    ],
                ),
                report_month=date(2026, 4, 1),
                prior_postings=[
                    seeded_posting("P-BACK-INC-001", date(2026, 1, 1), date(2026, 1, 31), "100.00", "1100.00", "0.00"),
                    seeded_posting("P-BACK-INC-001", date(2026, 2, 1), date(2026, 2, 28), "94.11", "1005.89", "5.89"),
                    seeded_posting("P-BACK-INC-001", date(2026, 3, 1), date(2026, 3, 31), "101.99", "903.90", "3.90"),
                ],
                include_persisted_history=False,
            ),
        ],
    },
    "backdated_cancellation_refund": {
        "description": (
            "Cancellation effective Feb-15 recorded in April. Closed months remain immutable; delta posts in April."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="P-BACK-CAN-001",
                    policy_number="POL-BACK-CAN-001",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    end_date_inclusive=True,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 1, 1),
                            end_date=date(2026, 12, 31),
                            premium_delta=D("1200.00"),
                            transaction_date=date(2026, 1, 1),
                        ),
                        PolicyEvent(
                            event_id="E-CANCEL-1",
                            event_type=EventType.CANCEL,
                            effective_date=date(2026, 2, 15),
                            end_date=date(2026, 12, 31),
                            premium_delta=D("-700.00"),
                            transaction_date=date(2026, 4, 2),
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 1, 1),
                            bill_to_exclusive=date(2026, 2, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 1, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 2, 1),
                            bill_to_exclusive=date(2026, 3, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 2, 5),
                        ),
                    ],
                ),
                report_month=date(2026, 4, 1),
                prior_postings=[
                    seeded_posting("P-BACK-CAN-001", date(2026, 1, 1), date(2026, 1, 31), "100.00", "1100.00", "0.00"),
                    seeded_posting("P-BACK-CAN-001", date(2026, 2, 1), date(2026, 2, 28), "94.11", "1005.89", "5.89"),
                    seeded_posting("P-BACK-CAN-001", date(2026, 3, 1), date(2026, 3, 31), "101.99", "903.90", "3.90"),
                ],
                include_persisted_history=False,
            ),
        ],
    },
    "backdated_flat_cancellation_refund": {
        "description": (
            "Flat cancellation from policy start recorded in April with refund processed immediately. Closed months remain immutable; delta posts in April."
        ),
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="P-BACK-FLAT-CAN-001",
                    policy_number="POL-BACK-FLAT-CAN-001",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    end_date_inclusive=True,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 1, 1),
                            end_date=date(2026, 12, 31),
                            premium_delta=D("1200.00"),
                            transaction_date=date(2026, 1, 1),
                        ),
                        PolicyEvent(
                            event_id="E-CANCEL-FLAT-1",
                            event_type=EventType.CANCEL,
                            effective_date=date(2026, 1, 1),
                            end_date=date(2026, 12, 31),
                            premium_delta=D("-1200.00"),
                            transaction_date=date(2026, 4, 2),
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 1, 1),
                            bill_to_exclusive=date(2026, 2, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 1, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 2, 1),
                            bill_to_exclusive=date(2026, 3, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 2, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 3, 1),
                            bill_to_exclusive=date(2026, 4, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 3, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 4, 1),
                            bill_to_exclusive=date(2026, 5, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 4, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 4, 1),
                            bill_to_exclusive=date(2026, 5, 1),
                            amount=D("-400.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 4, 6),
                        ),
                    ],
                ),
                report_month=date(2026, 4, 1),
                prior_postings=[
                    seeded_posting("P-BACK-FLAT-CAN-001", date(2026, 1, 1), date(2026, 1, 31), "100.00", "1100.00", "0.00"),
                    seeded_posting("P-BACK-FLAT-CAN-001", date(2026, 2, 1), date(2026, 2, 28), "94.11", "1005.89", "5.89"),
                    seeded_posting("P-BACK-FLAT-CAN-001", date(2026, 3, 1), date(2026, 3, 31), "101.99", "903.90", "3.90"),
                ],
                include_persisted_history=False,
            ),
        ],
    },
    "future_mta_increase_no_adjustment": {
        "description": "Future-dated MTA from July should not trigger closed month adjustments in April run.",
        "inputs": [
            PolicyRunInput(
                policy=PolicyInput(
                    policy_id="P-FUT-MTA-001",
                    policy_number="POL-FUT-MTA-001",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    end_date_inclusive=True,
                    events=[
                        PolicyEvent(
                            event_id="E-ISSUE-1",
                            event_type=EventType.ISSUE,
                            effective_date=date(2026, 1, 1),
                            end_date=date(2026, 12, 31),
                            premium_delta=D("1200.00"),
                            transaction_date=date(2026, 1, 1),
                        ),
                        PolicyEvent(
                            event_id="E-MTA-FWD-1",
                            event_type=EventType.MTA,
                            effective_date=date(2026, 7, 1),
                            end_date=date(2026, 12, 31),
                            premium_delta=D("600.00"),
                            transaction_date=date(2026, 4, 10),
                        ),
                    ],
                    installments=[
                        Installment(
                            bill_from=date(2026, 1, 1),
                            bill_to_exclusive=date(2026, 2, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 1, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 2, 1),
                            bill_to_exclusive=date(2026, 3, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 2, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 3, 1),
                            bill_to_exclusive=date(2026, 4, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 3, 5),
                        ),
                        Installment(
                            bill_from=date(2026, 4, 1),
                            bill_to_exclusive=date(2026, 5, 1),
                            amount=D("100.00"),
                            status=InstallmentStatus.COLLECTED,
                            collected_date=date(2026, 4, 5),
                        ),
                    ],
                ),
                report_month=date(2026, 4, 1),
                prior_postings=[
                    seeded_posting("P-FUT-MTA-001", date(2026, 1, 1), date(2026, 1, 31), "100.00", "1100.00", "0.00"),
                    seeded_posting("P-FUT-MTA-001", date(2026, 2, 1), date(2026, 2, 28), "94.11", "1005.89", "5.89"),
                    seeded_posting("P-FUT-MTA-001", date(2026, 3, 1), date(2026, 3, 31), "101.99", "903.90", "3.90"),
                ],
                include_persisted_history=False,
            ),
        ],
    },
}

