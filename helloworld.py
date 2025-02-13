import streamlit as st
import numpy as np
import pandas as pd
import numpy_financial as npf

def calculate_lbo_irr(
    entry_ebitda,
    ebitda_cagr,
    entry_tev,
    exit_multiple,
    entry_debt,
    tax_rate,
    interest_rate,
    years=5
):
    ebitda_growth = [(1 + ebitda_cagr) ** i for i in range(years + 1)]
    ebitda_projection = np.array(ebitda_growth) * entry_ebitda
    
    exit_ebitda = ebitda_projection[-1]
    exit_tev = exit_ebitda * exit_multiple
    
    debt_balance = entry_debt
    cash_balance = 0.0
    entry_equity = round(entry_tev - entry_debt, 1)
    cash_flows = [-entry_equity]
    
    financials = {"Metric": ["EBITDA", "Interest Expense", "Taxes", "Cash Flow"]}
    debt_schedule = {"Metric": ["Starting Debt", "Debt Paydown", "Ending Debt"]}
    cash_schedule = {"Metric": ["Starting Cash", "Cash Generated", "Ending Cash"]}
    
    for year in range(1, years + 1):
        interest_payment = round(debt_balance * interest_rate, 1)
        ebitda = round(ebitda_projection[year], 1)
        taxes = round((ebitda - interest_payment) * tax_rate, 1)
        free_cash_flow = round(ebitda - interest_payment - taxes, 1)
        
        # Use 100% of free cash flow to pay down debt until fully repaid
        debt_repayment = round(min(free_cash_flow, debt_balance), 1)
        debt_balance = round(debt_balance - debt_repayment, 1)
        remaining_cash = round(free_cash_flow - debt_repayment, 1)
        
        # Retain remaining cash instead of distributing it to equity holders
        cash_balance = round(cash_balance + remaining_cash, 1)
        
        financials[year] = [ebitda, interest_payment, taxes, free_cash_flow]
        debt_schedule[year] = [debt_balance + debt_repayment, debt_repayment, debt_balance]
        cash_schedule[year] = [cash_balance - remaining_cash, remaining_cash, cash_balance]
    
    equity_value_at_exit = round(exit_tev - debt_balance + cash_balance, 1)
    cash_flows.extend([0] * (years - 1))
    cash_flows.append(equity_value_at_exit)
    
    exit_equity = round(exit_tev - debt_balance + cash_balance, 1)
    
    equity_build = pd.DataFrame({
        "Metric": ["EBITDA", "Multiple", "TEV", "Debt", "Cash", "Equity"],
        "Entry": [
            round(entry_ebitda, 1), 
            round(entry_tev / entry_ebitda, 1), 
            round(entry_tev, 1), 
            round(entry_debt, 1),
            round(0.0, 1),
            entry_equity
        ],
        "Exit": [
            round(exit_ebitda, 1), 
            round(exit_multiple, 1), 
            round(exit_tev, 1), 
            round(debt_balance, 1),
            round(cash_balance, 1),
            exit_equity
        ]
    })
    
    if all(c <= 0 for c in cash_flows):
        irr = None  # Avoid calculation error
    else:
        irr = npf.irr(cash_flows)
    
    return equity_value_at_exit, irr, pd.DataFrame(financials).set_index("Metric"), pd.DataFrame(debt_schedule).set_index("Metric"), pd.DataFrame(cash_schedule).set_index("Metric"), equity_build, cash_flows

st.title("LBO Model Calculator")

entry_ebitda = float(st.number_input("Entry EBITDA ($M)", value=100))
ebitda_cagr = float(st.number_input("EBITDA CAGR (%)", value=11)) / 100
entry_tev = float(st.number_input("Entry TEV ($M)", value=2000))
exit_multiple = float(st.number_input("Exit Multiple", value=19))
entry_debt = float(st.number_input("Entry Debt ($M)", value=800))
tax_rate = float(st.number_input("Tax Rate (%)", value=25.0)) / 100
interest_rate = float(st.number_input("Interest Rate (%)", value=8)) / 100

if st.button("Calculate IRR"):
    equity_value_at_exit, irr, financials, debt_schedule, cash_schedule, equity_build, cash_flows = calculate_lbo_irr(
        entry_ebitda, ebitda_cagr, entry_tev,
        exit_multiple, entry_debt, tax_rate, interest_rate
    )
    
    st.write(f"**Equity Value at Exit:** ${equity_value_at_exit:.1f}M")
    if irr is not None:
        st.write(f"**IRR:** {irr:.1%}")
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
