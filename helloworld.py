import streamlit as st
import numpy as np
import pandas as pd
import numpy_financial as npf

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
    interest_rate=0.05
):
    revenue_growth = [(1 + revenue_cagr) ** i for i in range(years + 1)]
    ebitda_growth = [(1 + ebitda_cagr) ** i for i in range(years + 1)]
    
    revenue_projection = np.array(revenue_growth) * entry_revenue
    ebitda_projection = np.array(ebitda_growth) * entry_ebitda
    
    exit_ebitda = ebitda_projection[-1]
    exit_tev = exit_ebitda * exit_multiple
    
    debt_balance = entry_debt
    cash_balance = 0.0
    cash_flows = [- (entry_tev - entry_debt)]
    
    financials = {
        "Metric": ["EBITDA", "Interest Expense", "Taxes", "Cash Flow"],
    }
    
    debt_schedule = {
        "Metric": ["Starting Debt", "Debt Paydown", "Ending Debt"],
    }
    
    cash_schedule = {
        "Metric": ["Starting Cash", "Cash Generated", "Ending Cash"],
    }
    
    for year in range(1, years + 1):
        interest_payment = debt_balance * interest_rate
        ebitda = ebitda_projection[year]
        taxes = (ebitda - interest_payment) * tax_rate
        free_cash_flow = ebitda - interest_payment - taxes
        
        # Assume 100% of available cash is used to pay down debt until fully repaid
        debt_repayment = min(free_cash_flow, debt_balance)
        debt_balance -= debt_repayment
        remaining_cash = free_cash_flow - debt_repayment
        
        if debt_balance == 0:
            cash_balance += remaining_cash
        
        cash_flows.append(remaining_cash)
        
        financials[year] = [ebitda, interest_payment, taxes, free_cash_flow]
        debt_schedule[year] = [debt_balance + debt_repayment, debt_repayment, debt_balance]
        cash_schedule[year] = [cash_balance - remaining_cash, remaining_cash, cash_balance]
    
    equity_value_at_exit = exit_tev - debt_balance
    cash_flows[-1] += equity_value_at_exit  # Add equity exit value in year 5
    
    entry_equity = entry_tev - entry_debt
    exit_equity = exit_tev - debt_balance
    equity_build = pd.DataFrame({
        "Metric": ["EBITDA", "Multiple", "TEV", "Debt", "Equity"],
        "Entry": [entry_ebitda, entry_tev / entry_ebitda, entry_tev, entry_debt, entry_equity],
        "Exit": [exit_ebitda, exit_multiple, exit_tev, debt_balance, exit_equity]
    })
    
    if all(c <= 0 for c in cash_flows):
        irr = None  # Avoid calculation error
    else:
        irr = npf.irr(cash_flows)
    
    return equity_value_at_exit, irr, pd.DataFrame(financials).set_index("Metric"), pd.DataFrame(debt_schedule).set_index("Metric"), pd.DataFrame(cash_schedule).set_index("Metric"), equity_build, cash_flows

st.title("LBO Model Calculator")

entry_revenue = float(st.number_input("Entry Revenue ($M)", value=100.0))
entry_ebitda = float(st.number_input("Entry EBITDA ($M)", value=20.0))
revenue_cagr = float(st.number_input("Revenue CAGR (%)", value=5.0)) / 100
ebitda_cagr = float(st.number_input("EBITDA CAGR (%)", value=6.0)) / 100
entry_tev = float(st.number_input("Entry TEV ($M)", value=150.0))
exit_multiple = float(st.number_input("Exit Multiple", value=8.0))
entry_debt = float(st.number_input("Entry Debt ($M)", value=90.0))
tax_rate = float(st.number_input("Tax Rate (%)", value=25.0)) / 100

if st.button("Calculate IRR"):
    equity_value_at_exit, irr, financials, debt_schedule, cash_schedule, equity_build, cash_flows = calculate_lbo_irr(
        entry_revenue, entry_ebitda, revenue_cagr, ebitda_cagr, entry_tev,
        exit_multiple, entry_debt, tax_rate
    )
    
    st.write(f"**Equity Value at Exit:** ${equity_value_at_exit:.2f}M")
    if irr is not None:
        st.write(f"**IRR:** {irr:.2%}")
    else:
        st.write("**IRR Calculation Error: Check inputs**")
    
    st.write("### Financial Metrics")
    st.dataframe(financials)
    
    st.write("### Debt Schedule")
    st.dataframe(debt_schedule)
    
    st.write("### Cash Schedule")
    st.dataframe(cash_schedule)
    
    st.write("### Entry & Exit Equity Build")
    st.dataframe(equity_build)
    
    st.write("**Debugging:**")
    st.write("Cash Flows Debug:", cash_flows)
