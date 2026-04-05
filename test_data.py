"""
Test data sets for earned/unearned premium calculation.
Add new scenarios here. Each entry is a dict with a list of Policy objects.
Run with:  python earned_unearned_premium.py <scenario_key>
"""

from datetime import date
from models import Endorsement, Installment, InstallmentStatus, Policy


SCENARIOS = {

    # -------------------------------------------------------------------------
    "annual_feb1_pol0002_billed": {
        "description": "POL-0002: 1-Feb-2026 to 1-Feb-2027 inclusive; single BILLED inst. to 2-Feb-2027 exclusive",
        "policies": [
            Policy(
                policy_number="POL-0002",
                policy_id="a1b2c3d4-0002-0002-0002-000000000021",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=2529.36,
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 2, 1),
                        date(2027, 2, 2),
                        2529.36,
                        InstallmentStatus.BILLED,
                        bill_to_inclusive=False,
                    ),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    "annual_feb1_pol0002_collected": {
        "description": "POL-0002: 1-Feb-2026 to 1-Feb-2027 inclusive; single COLLECTED inst. to 2-Feb-2027 exclusive",
        "policies": [
            Policy(
                policy_number="POL-0002",
                policy_id="a1b2c3d4-0002-0002-0002-000000000020",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=2529.36,
                end_date_inclusive=True,
                installments=[
                    Installment(
                        date(2026, 2, 1),
                        date(2027, 2, 2),
                        2529.36,
                        InstallmentStatus.COLLECTED,
                        bill_to_inclusive=False,
                    ),
                ],
            ),
        ],
    },

}
