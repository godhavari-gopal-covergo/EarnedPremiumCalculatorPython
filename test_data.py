"""
Test data sets for earned/unearned premium calculation.
Add new scenarios here. Each entry is a dict with a list of Policy objects.
Run with:  python earned_unearned_premium.py <scenario_key>
"""

from datetime import date
from earned_unearned_premium import Policy, Product, Installment, Endorsement


SCENARIOS = {

    # -------------------------------------------------------------------------
    "excel_monthly": {
        "description": "Excel example: 3 monthly installments, 2 products",
        "policies": [
            Policy(
                policy_number="POL-0001",
                policy_id="a1b2c3d4-0001-0001-0001-000000000001",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 4, 10),
                total_premium=1250,
                products=[Product("Product A", 850), Product("Product B", 400)],
                end_date_inclusive=False,
                installments=[
                    Installment(date(2026, 1, 1), date(2026, 2, 1), 550, "collected", bill_to_inclusive=False),
                    Installment(date(2026, 2, 1), date(2026, 3, 1), 350, "collected", bill_to_inclusive=True),
                    Installment(date(2026, 3, 1), date(2026, 4, 1), 350, "collected", bill_to_inclusive=True),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    "excel_annual": {
        "description": "Excel example: single installment paid in full",
        "policies": [
            Policy(
                policy_number="POL-0002",
                policy_id="a1b2c3d4-0002-0002-0002-000000000002",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 4, 10),
                total_premium=1250,
                products=[Product("Product A", 850), Product("Product B", 400)],
                end_date_inclusive=False,
                installments=[
                    Installment(date(2026, 1, 1), date(2026, 4, 10), 1250, "collected", bill_to_inclusive=False),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    "annual_no_endorsement": {
        "description": "Annual policy, no endorsement (inclusive end date)",
        "policies": [
            Policy(
                policy_number="POL-0003",
                policy_id="a1b2c3d4-0003-0003-0003-000000000003",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=2529.36,
                products=[Product("Health", 2529.36)],
                end_date_inclusive=True,
                installments=[
                    Installment(date(2026, 2, 1), date(2027, 2, 2), 2529.36, "collected", bill_to_inclusive=False),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    "annual_with_mta": {
        "description": "Annual policy + MTA on 25-Feb adding 1095.24 (from screenshot)",
        "policies": [
            Policy(
                policy_number="P01669",
                policy_id="4b30ecdb-a2d1-47c8-a21b-75b0db4123ef",
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 1),
                total_premium=2529.36,
                products=[Product("Health", 2529.36)],
                end_date_inclusive=True,
                endorsements=[
                    Endorsement(
                        effective_date=date(2026, 2, 20),
                        end_date=date(2027, 2, 1),     # defaults to policy end_date
                        additional_premium=1095.24,
                        end_date_inclusive=True,         # inclusive, same as policy
                    ),
                ],
                installments=[
                    # Original annual payment
                    Installment(date(2026, 2, 1), date(2027, 2, 2), 2529.36, "collected", bill_to_inclusive=False),
                    # Adhoc installment for MTA (bill_from = endorsement effective date)
                    Installment(date(2026, 2, 20), date(2027, 2, 1), 1095.24, "collected", bill_to_inclusive=True),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    # ADD NEW SCENARIOS BELOW
    # -------------------------------------------------------------------------

}
