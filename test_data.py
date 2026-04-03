"""
Test data sets for earned/unearned premium calculation.
Add new scenarios here. Each entry is a dict with a list of Policy objects.
Run with:  python earned_unearned_premium.py <scenario_key>
"""

from datetime import date
from earned_unearned_premium import Policy, Product, Installment


SCENARIOS = {

    # -------------------------------------------------------------------------
    "excel_monthly": {
        "description": "Excel example: 3 monthly installments, 2 products",
        "policies": [
            Policy(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 4, 10),
                total_premium=1250,
                products=[Product("Product A", 850), Product("Product B", 400)],
                installments=[
                    Installment(date(2026, 1, 1), date(2026, 2, 1), 550, "collected"),
                    Installment(date(2026, 2, 1), date(2026, 3, 1), 350, "collected"),
                    Installment(date(2026, 3, 1), date(2026, 4, 1), 350, "collected"),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    "excel_annual": {
        "description": "Excel example: single installment paid in full",
        "policies": [
            Policy(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 4, 10),
                total_premium=1250,
                products=[Product("Product A", 850), Product("Product B", 400)],
                installments=[
                    Installment(date(2026, 1, 1), date(2026, 4, 10), 1250, "collected"),
                ],
            ),
        ],
    },

    # -------------------------------------------------------------------------
    # ADD NEW SCENARIOS BELOW — copy the template and adjust values
    # -------------------------------------------------------------------------

    "my_new_test": {
        "description": "Describe the scenario",
        "policies": [
            Policy(
                start_date=date(2026, 1, 1),
                end_date=date(2027, 1, 1),
                total_premium=2112.24,
                products=[Product("Health", 2112.24)],
                installments=[
                    Installment(date(2026, 1, 1), date(2027, 1, 1), 2112.24, "collected")
                    
                    # ... remaining months
                ],
            ),
        ],
    },
     "my_new_test": {
        "description": "Describe the scenario",
        "policies": [
            Policy(
                start_date=date(2026, 2, 1),
                end_date=date(2027, 2, 2),
                total_premium=2529.36,
                products=[Product("Health", 2529.36)],
                installments=[
                    Installment(date(2026, 2, 1), date(2027, 2, 2), 2529.36, "collected")
                    
                    # ... remaining months
                ],
            ),
        ],
    },

}
