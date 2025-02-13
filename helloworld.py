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
    interest_rate=0.05,
    debt_paydown=0.1
):
    revenue_growth = [(1 + revenue_cagr) ** i for i in range(years + 1)]
    ebitda_growth = [(1 + ebitda_cagr) ** i for i in range(years + 1)]
    
    revenue_projection = np.array(revenue_growth) * entry_revenue
    ebitda_projection = np.array(ebitda_growth) * entry_ebitda
    
    exit_ebitda = ebitda_projection[-1]
    exit_tev = exit_ebitda * exit_multiple
    
    debt_balance = entry_debt
    debt_schedule = []
    cash_flows = [- (entry_tev - entry_debt)]
    
    for year in range(1, years + 1):
        interest_payment = debt_balance * interest_rate
        debt_repayment = debt_balance * debt_paydown
        debt_balance -= debt_repayment
        ebitda = ebitda_projection[year]
        taxes = (ebitda - interest_payment) * tax_rate
        free_cash_flow = ebitda - interest_payment - taxes
        cash_available_to_equity = free_cash_flow - debt_repayment
        
        debt_schedule.append((year, debt_balance, interest_payment, debt_repayment, free_cash_flow, cash_available_to_equity))
        cash_flows.append(cash_available_to_equity)
    
    debt_repaid = entry_debt - debt_balance
    equity_value_at_exit = exit_tev - debt_balance
    cash_flows.append(equity_value_at_exit)
    
    if all(c <= 0 for c in cash_flows):
        irr = None  # Avoid calculation error
    else:
        irr = npf.irr(cash_flows)
    
    return equity_value_at_exit, irr, pd.DataFrame(debt_schedule, columns=["Year", "Debt Balance", "Interest Payment", "Debt Repayment", "Free Cash Flow", "Cash Available to Equity"]), cash_flows

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
    equity_value_at_exit, irr, debt_schedule, cash_flows = calculate_lbo_irr(
        entry_revenue, entry_ebitda, revenue_cagr, ebitda_cagr, entry_tev,
        exit_multiple, entry_debt, tax_rate
    )
    
    st.write(f"**Equity Value at Exit:** ${equity_value_at_exit:.2f}M")
    if irr is not None:
        st.write(f"**IRR:** {irr:.2%}")
    else:
        st.write("**IRR Calculation Error: Check inputs**")
    
    st.write("### Debt Schedule")
    st.dataframe(debt_schedule)
    
    st.write("**Debugging:**")
    st.write("Cash Flows Debug:", cash_flows)
