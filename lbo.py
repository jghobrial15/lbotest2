import numpy as np
import pandas as pd

def calculate_lbo_irr(
    entry_revenue,
    entry_ebitda,
    revenue_cagr,
    ebitda_cagr,
    entry_tev,
    exit_multiple,
    entry_debt,
    tax_rate,
    years=5,
    interest_rate=0.05,
    debt_paydown=0.1
):
    
    revenue_growth = [(1 + revenue_cagr) ** i for i in range(years + 1)]
    ebitda_growth = [(1 + ebitda_cagr) ** i for i in range(years + 1)]
    
    revenue_projection = np.array(revenue_growth) * entry_revenue
    ebitda_projection = np.array(ebitda_growth) * entry_ebitda
    
    exit_ebitda = ebitda_projection[-1]
    exit_tev = exit_ebitda * exit_multiple
    
    # Debt Schedule
    debt_balance = entry_debt
    debt_schedule = []
    
    for year in range(1, years + 1):
        interest_payment = debt_balance * interest_rate
        debt_repayment = debt_balance * debt_paydown
        debt_balance -= debt_repayment
        debt_schedule.append((year, debt_balance, interest_payment, debt_repayment))
    
    debt_repaid = entry_debt - debt_balance
    equity_value_at_exit = exit_tev - debt_balance
    
    # IRR Calculation
    cash_flows = [- (entry_tev - entry_debt)]
    for year in range(1, years + 1):
        tax_shield = debt_schedule[year - 1][2] * tax_rate
        cash_flows.append(tax_shield)
    
    cash_flows.append(equity_value_at_exit)
    irr = np.irr(cash_flows)
    
    return {
        "Revenue Projection": revenue_projection.tolist(),
        "EBITDA Projection": ebitda_projection.tolist(),
        "Debt Schedule": pd.DataFrame(debt_schedule, columns=["Year", "Debt Balance", "Interest Payment", "Debt Repayment"]),
        "Equity Value at Exit": equity_value_at_exit,
        "IRR": irr
    }

# Example usage
lbo_results = calculate_lbo_irr(
    entry_revenue=100,
    entry_ebitda=20,
    revenue_cagr=0.05,
    ebitda_cagr=0.06,
    entry_tev=150,
    exit_multiple=8,
    entry_debt=90,
    tax_rate=0.25
)

import ace_tools as tools
tools.display_dataframe_to_user("Debt Schedule", lbo_results["Debt Schedule"])
