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
    capex_percent,
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
    
    for year in range(1, years + 1):
        interest_payment = round(debt_balance * interest_rate, 1)
        ebitda = round(ebitda_projection[year], 1)
        capex = round(ebitda * capex_percent, 1)
        depreciation = capex
        taxable_income = ebitda - depreciation - interest_payment
        taxes = round(taxable_income * tax_rate, 1)
        free_cash_flow = round(ebitda - capex - interest_payment - taxes, 1)
        
        debt_repayment = round(min(free_cash_flow, debt_balance), 1)
        debt_balance = round(debt_balance - debt_repayment, 1)
        remaining_cash = round(free_cash_flow - debt_repayment, 1)
        cash_balance = round(cash_balance + remaining_cash, 1)
        
        cash_flows.append(free_cash_flow)
    
    cash_flows.append(exit_tev - debt_balance + cash_balance)
    return npf.irr(cash_flows) if any(cash_flows) else None, cash_flows, ebitda_projection, exit_tev, debt_balance, cash_balance, entry_equity

st.title("LBO Model Calculator")

entry_ebitda = float(st.number_input("Entry EBITDA ($M)", value=100.0))
ebitda_cagr = float(st.number_input("EBITDA CAGR (%)", value=11.0)) / 100
entry_tev = float(st.number_input("Entry TEV ($M)", value=2000.0))
exit_multiple = float(st.number_input("Exit Multiple", value=19.0))
entry_debt = float(st.number_input("Entry Debt ($M)", value=800.0))
tax_rate = float(st.number_input("Tax Rate (%)", value=25.0)) / 100
interest_rate = float(st.number_input("Interest Rate (%)", value=8.0)) / 100
capex_percent = float(st.number_input("Capex as % of EBITDA", value=5.0)) / 100

if st.button("Calculate IRR"): 
    irr, cash_flows, ebitda_projection, exit_tev, debt_balance, cash_balance, entry_equity = calculate_lbo_irr(
        entry_ebitda, ebitda_cagr, entry_tev,
        exit_multiple, entry_debt, tax_rate, interest_rate, capex_percent
    )
    
    unlevered_irr, _, _, _, _, _, _ = calculate_lbo_irr(
        entry_ebitda, ebitda_cagr, entry_tev,
        exit_multiple, 0, tax_rate, interest_rate, capex_percent
    )
    
    years = 5
    annualized_exit_multiple_change = ((exit_multiple / (entry_tev / entry_ebitda)) ** (1 / years)) - 1
    tev_growth = ((exit_tev / entry_tev) ** (1 / years)) - 1
    yield_rate = 1 / (entry_tev / entry_ebitda)
    covariance = unlevered_irr - (tev_growth + yield_rate)
    leverage_impact = irr - unlevered_irr
    
    irr_decomposition = pd.DataFrame({
        "Metric": ["EBITDA Growth", "Exit Multiple Change", "TEV Growth", "Yield", "Covariance", "Unlevered IRR", "Leverage Impact", "Levered IRR"],
        "Value (%)": [f"{ebitda_cagr:.1%}", f"{annualized_exit_multiple_change:.1%}", f"{tev_growth:.1%}", f"{yield_rate:.1%}", f"{covariance:.1%}", f"{unlevered_irr:.1%}", f"{leverage_impact:.1%}", f"{irr:.1%}"]
    })
    
    st.write("### IRR Decomposition")
    st.dataframe(irr_decomposition)
    
    st.write("### Financial Metrics")
    financial_metrics = pd.DataFrame({
        "Metric": ["Entry EBITDA", "Exit EBITDA", "Entry TEV", "Exit TEV"],
        "Value ($M)": [entry_ebitda, ebitda_projection[-1], entry_tev, exit_tev]
    })
    st.dataframe(financial_metrics)
    
    st.write("### Debt Schedule")
    debt_schedule = pd.DataFrame({
        "Metric": ["Entry Debt", "Exit Debt"],
        "Value ($M)": [entry_debt, debt_balance]
    })
    st.dataframe(debt_schedule)
    
    st.write("### Cash Schedule")
    cash_schedule = pd.DataFrame({
        "Metric": ["Entry Cash", "Exit Cash"],
        "Value ($M)": [0, cash_balance]
    })
    st.dataframe(cash_schedule)
    
    st.write("### Entry & Exit Equity Build")
    equity_build = pd.DataFrame({
        "Metric": ["Entry Equity", "Exit Equity"],
        "Value ($M)": [entry_equity, exit_tev - debt_balance + cash_balance]
    })
    st.dataframe(equity_build)
    
    st.write("**Debugging:**")
    st.write("Cash Flows Debug:", cash_flows)
