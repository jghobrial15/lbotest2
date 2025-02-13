import streamlit as st
import numpy as np
import pandas as pd
import numpy_financial as npf

[previous code remains the same until the calculate_irr method]

    def calculate_irr(self, entry_equity, exit_equity, cash_flows):
        """Calculate IRR based on equity flows."""
        flows = [-entry_equity] + cash_flows[1:-1].tolist() + [exit_equity]
        
        # Debug prints
        print("IRR Calculation Components:")
        print(f"Entry Equity: {entry_equity}")
        print(f"Intermediate Cash Flows: {cash_flows[1:-1].tolist()}")
        print(f"Exit Equity: {exit_equity}")
        print(f"Complete Flow Series: {flows}")
        
        # Check for valid IRR calculation conditions
        if not any(f < 0 for f in flows):
            print("Warning: No negative cash flows found - IRR calculation may fail")
        if not any(f > 0 for f in flows):
            print("Warning: No positive cash flows found - IRR calculation may fail")
        
        try:
            irr = npf.irr(flows)
            if np.isnan(irr):
                print("IRR calculation returned NaN - falling back to 0.0")
                return 0.0
            return irr
        except Exception as e:
            print(f"IRR calculation failed: {str(e)}")
            return 0.0

[previous code remains the same until the main calculation section]

    if st.button("Calculate IRR"):
        # [previous calculations remain the same until IRR section]
        
        # Calculate equity values and IRRs
        entry_equity = entry_tev - entry_debt
        exit_equity = exit_tev - debt_schedule['Year 5']['Ending Debt']
        
        # Debug information about cash flows
        st.subheader("Debug Information")
        st.write("Key Values:")
        st.write(f"Entry TEV: ${entry_tev:,.1f}M")
        st.write(f"Entry Debt: ${entry_debt:,.1f}M")
        st.write(f"Entry Equity: ${entry_equity:,.1f}M")
        st.write(f"Exit TEV: ${exit_tev:,.1f}M")
        st.write(f"Exit Debt: ${debt_schedule['Year 5']['Ending Debt']:,.1f}M")
        st.write(f"Exit Equity: ${exit_equity:,.1f}M")
        
        # Show intermediate cash flows
        st.write("\nIntermediate Cash Flows:")
        yearly_flows = pd.DataFrame({
            'Year': range(calculator.years + 1),
            'Free Cash Flow ($M)': financial_schedule['Free Cash Flow'].values,
            'Debt Balance ($M)': debt_schedule.loc['Ending Debt'].values
        })
        st.dataframe(yearly_flows.round(1))
        
        # Calculate IRRs with the cash flows from financial schedule
        cash_flows = financial_schedule['Free Cash Flow'].values
        levered_irr = calculator.calculate_irr(entry_equity, exit_equity, cash_flows)
        
        # Calculate unlevered IRR with the unlevered cash flows
        unlevered_cash_flows = calculator.calculate_cash_flows(
            ebitda_schedule,
            initial_debt_df,
            tax_rate,
            capex_pct
        )
        unlevered_irr = calculator.calculate_irr(
            unlevered_entry_equity, 
            unlevered_exit_equity, 
            unlevered_cash_flows
        )
        
        # Display IRR Results with complete cash flow series
        st.subheader("IRR Results")
        
        # Show complete levered cash flow series
        levered_flows = [-entry_equity] + cash_flows[1:-1].tolist() + [exit_equity]
        st.write("Levered Cash Flow Series ($M):")
        levered_series_df = pd.DataFrame({
            'Time': ['Entry'] + [f'Year {i}' for i in range(1, calculator.years)] + ['Exit'],
            'Cash Flow': levered_flows
        })
        st.dataframe(levered_series_df.round(1))
        st.write(f"Levered IRR: {levered_irr:.1%}")
        
        # Show complete unlevered cash flow series
        unlevered_flows = [-unlevered_entry_equity] + unlevered_cash_flows[1:-1] + [unlevered_exit_equity]
        st.write("\nUnlevered Cash Flow Series ($M):")
        unlevered_series_df = pd.DataFrame({
            'Time': ['Entry'] + [f'Year {i}' for i in range(1, calculator.years)] + ['Exit'],
            'Cash Flow': unlevered_flows
        })
        st.dataframe(unlevered_series_df.round(1))
        st.write(f"Unlevered IRR: {unlevered_irr:.1%}")

[rest of the code remains the same]
