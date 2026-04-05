"""
Test data sets for earned/unearned premium calculation.
Add new scenarios here. Each entry is a dict with a list of Policy objects.
Run with:  python earned_unearned_premium.py <scenario_key>
"""

from datetime import date
from decimal import Decimal
from models import Endorsement, Installment, InstallmentStatus, Policy

D = Decimal

SCENARIOS = {

    # -------------------------------------------------------------------------
    "annual_feb1_pol0002_billed": {
        "description": "POL-0002: 1-Feb-2026 to 1-Feb-2027 inclusive; single BILLED inst. (no collected_date)",
        "policies": [
            Policy(
                policy_number="POL-0002",
                policy_id="a1b2c3d4-0002-0002-0002-000000000021",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=D("2529.36"),
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 2, 1),
                        date(2027, 2, 2),
                        D("2529.36"),
                        InstallmentStatus.BILLED,
                        bill_to_inclusive=False,
                        collected_date=None,
                    ),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    "annual_feb1_pol0002_collected": {
        "description": "POL-0002: 1-Feb-2026 to 1-Feb-2027 inclusive; COLLECTED on 5-Feb-2026",
        "policies": [
            Policy(
                policy_number="POL-0002",
                policy_id="a1b2c3d4-0002-0002-0002-000000000020",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=D("2529.36"),
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 2, 1),
                        date(2027, 2, 2),
                        D("2529.36"),
                        InstallmentStatus.COLLECTED,
                        bill_to_inclusive=False,
                        collected_date=date(2026, 2, 5),
                    ),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    "annual_feb1_pol0002_collected_apr": {
        "description": "POL-0002: COLLECTED but collected_date is 1-Apr-2026; report_as_of=28-Feb shows unearned",
        "policies": [
            Policy(
                policy_number="POL-0002",
                policy_id="a1b2c3d4-0002-0002-0002-000000000022",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=D("2529.36"),
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 2, 1),
                        date(2027, 2, 2),
                        D("2529.36"),
                        InstallmentStatus.COLLECTED,
                        bill_to_inclusive=False,
                        collected_date=date(2026, 4, 1),
                    ),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    # Monthly billing: 12 installments, ~210.78 each
    # Case 1: Only Feb collected (in Feb); Mar–Jan remain BILLED
    # -------------------------------------------------------------------------
    "monthly_feb1_pol0002_feb_collected": {
        "description": "POL-0002 monthly: Feb COLLECTED (collected Feb), Mar-Jan BILLED",
        "policies": [
            Policy(
                policy_number="POL-0002",
                policy_id="a1b2c3d4-0002-0002-0002-000000000030",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=D("2529.36"),
                end_date_inclusive=True,
                installments=[
                    Installment(date(2026, 2, 1), date(2026, 3, 1), D("210.78"), InstallmentStatus.COLLECTED, bill_to_inclusive=False, collected_date=date(2026, 2, 5)),
                    Installment(date(2026, 3, 1), date(2026, 4, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 4, 1), date(2026, 5, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 5, 1), date(2026, 6, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 6, 1), date(2026, 7, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 7, 1), date(2026, 8, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 8, 1), date(2026, 9, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 9, 1), date(2026, 10, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 10, 1), date(2026, 11, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 11, 1), date(2026, 12, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 12, 1), date(2027, 1, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2027, 1, 1), date(2027, 2, 2), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    # Case 2: Feb collected (in Mar) + Mar collected (in Mar); Apr–Jan BILLED
    # -------------------------------------------------------------------------
    "monthly_feb1_pol0002_feb_mar_collected": {
        "description": "POL-0002 monthly: Feb COLLECTED (collected Mar), Mar COLLECTED (collected Mar), Apr-Jan BILLED",
        "policies": [
            Policy(
                policy_number="POL-0002",
                policy_id="a1b2c3d4-0002-0002-0002-000000000031",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=D("2529.36"),
                end_date_inclusive=True,
                installments=[
                    Installment(date(2026, 2, 1), date(2026, 3, 1), D("210.78"), InstallmentStatus.COLLECTED, bill_to_inclusive=False, collected_date=date(2026, 3, 10)),
                    Installment(date(2026, 3, 1), date(2026, 4, 1), D("210.78"), InstallmentStatus.COLLECTED, bill_to_inclusive=False, collected_date=date(2026, 3, 15)),
                    Installment(date(2026, 4, 1), date(2026, 5, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 5, 1), date(2026, 6, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 6, 1), date(2026, 7, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 7, 1), date(2026, 8, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 8, 1), date(2026, 9, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 9, 1), date(2026, 10, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 10, 1), date(2026, 11, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 11, 1), date(2026, 12, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2026, 12, 1), date(2027, 1, 1), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                    Installment(date(2027, 1, 1), date(2027, 2, 2), D("210.78"), InstallmentStatus.BILLED, bill_to_inclusive=False, collected_date=None),
                ],
            ),
        ],
    },

    # =========================================================================
    # SCENARIO TESTS — "Current month" = March 2026
    # Based on requirement doc section 8 (payment received assumption)
    # =========================================================================

    # -------------------------------------------------------------------------
    # Scenario 1: Coverage starts AND ends within the current month.
    # Recognize entire premium for that month.
    # Policy: Mar 1 – Mar 31, 2026 (inclusive). Single installment, COLLECTED.
    # -------------------------------------------------------------------------
    "Scenario1_coverage_within_month": {
        "description": "Scenario 1: Coverage starts and ends within current month (Mar 2026) — recognize entire premium",
        "policies": [
            Policy(
                policy_number="SC1-001",
                policy_id="sc1-0001-0001-0001-000000000001",
                start_date=date(2026, 3, 1),
                end_date=date(2026, 3, 31),
                total_premium=D("500.00"),
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 3, 1),
                        date(2026, 4, 1),
                        D("500.00"),
                        InstallmentStatus.COLLECTED,
                        bill_to_inclusive=False,
                        collected_date=date(2026, 3, 5),
                    ),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    # Scenario 2: Coverage starts AFTER the current month.
    # No premium recognized as income in current month; total premium = liability.
    # Policy: Apr 1, 2026 – Apr 1, 2027 (inclusive). Single installment, COLLECTED in March.
    # -------------------------------------------------------------------------
    "Scenario2_coverage_starts_after_month": {
        "description": "Scenario 2: Coverage starts after current month (Apr 2026) — no income in Mar, all liability",
        "policies": [
            Policy(
                policy_number="SC2-001",
                policy_id="sc2-0001-0001-0001-000000000002",
                start_date=date(2026, 4, 1),
                end_date=date(2027, 4, 1),
                total_premium=D("2400.00"),
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 4, 1),
                        date(2027, 4, 2),
                        D("2400.00"),
                        InstallmentStatus.COLLECTED,
                        bill_to_inclusive=False,
                        collected_date=date(2026, 3, 20),
                    ),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    # Scenario 3: Coverage started BEFORE and ENDS within the current month.
    # Part of premium already recognized; calculate remaining days in current month.
    # Last month covered.
    # Policy: Feb 1 – Mar 15, 2026 (inclusive). Single installment, COLLECTED.
    # -------------------------------------------------------------------------
    "Scenario3_started_before_ends_within": {
        "description": "Scenario 3: Coverage started before (Feb) and ends within current month (Mar 15) — last month, partial earn",
        "policies": [
            Policy(
                policy_number="SC3-001",
                policy_id="sc3-0001-0001-0001-000000000003",
                start_date=date(2026, 2, 1),
                end_date=date(2026, 3, 15),
                total_premium=D("600.00"),
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 2, 1),
                        date(2026, 3, 16),
                        D("600.00"),
                        InstallmentStatus.COLLECTED,
                        bill_to_inclusive=False,
                        collected_date=date(2026, 2, 5),
                    ),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    # Scenario 4: Coverage started BEFORE and ENDED BEFORE the current month.
    # 100% premium already recognized. Start a new policy / new accrual cycle.
    # Policy: Jan 1 – Feb 15, 2026 (inclusive). Single installment, COLLECTED.
    # -------------------------------------------------------------------------
    "Scenario4_started_and_ended_before": {
        "description": "Scenario 4: Coverage started and ended before current month (Jan-Feb) — 100% already earned",
        "policies": [
            Policy(
                policy_number="SC4-001",
                policy_id="sc4-0001-0001-0001-000000000004",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 2, 15),
                total_premium=D("700.00"),
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 1, 1),
                        date(2026, 2, 16),
                        D("700.00"),
                        InstallmentStatus.COLLECTED,
                        bill_to_inclusive=False,
                        collected_date=date(2026, 1, 5),
                    ),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    # Scenario 5: Coverage started BEFORE and continues to FUTURE months.
    # Part of premium already recognized. Middle months.
    # Earn the current month's portion; remaining balance stays as liability.
    # Policy: Feb 1, 2026 – Feb 1, 2027 (inclusive). Single installment, COLLECTED.
    # -------------------------------------------------------------------------
    "Scenario5_started_before_continues_future": {
        "description": "Scenario 5: Coverage started before (Feb) and continues to future — middle month, partial earn + liability",
        "policies": [
            Policy(
                policy_number="SC5-001",
                policy_id="sc5-0001-0001-0001-000000000005",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=D("2529.36"),
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 2, 1),
                        date(2027, 2, 2),
                        D("2529.36"),
                        InstallmentStatus.COLLECTED,
                        bill_to_inclusive=False,
                        collected_date=date(2026, 2, 5),
                    ),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    # Scenario 6: Coverage starts WITHIN the current month and continues to future.
    # First month. Calculate coverage period for current month; recognize that portion.
    # Remaining balance stays as liability.
    # Policy: Mar 15, 2026 – Mar 15, 2027 (inclusive). Single installment, COLLECTED.
    # -------------------------------------------------------------------------
    "Scenario6_starts_within_continues_future": {
        "description": "Scenario 6: Coverage starts within current month (Mar 15) and continues to future — first month, partial earn",
        "policies": [
            Policy(
                policy_number="SC6-001",
                policy_id="sc6-0001-0001-0001-000000000006",
                start_date=date(2026, 3, 15),
                end_date=date(2027, 3, 15),
                total_premium=D("2400.00"),
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 3, 15),
                        date(2027, 3, 16),
                        D("2400.00"),
                        InstallmentStatus.COLLECTED,
                        bill_to_inclusive=False,
                        collected_date=date(2026, 3, 15),
                    ),
                ],
            ),
        ],
    },

}
