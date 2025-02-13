import streamlit as st
import numpy as np
import pandas as pd
import numpy_financial as npf

class LBOCalculator:
    def __init__(self):
        self.years = 5  # Fixed 5-year projection period
        
    def calculate_ebitda_schedule(self, entry_ebitda, ebitda_cagr):
        """Calculate EBITDA progression over the projection period."""
        ebitda_schedule = []
        for year in range(self.years + 1):
            ebitda = entry_ebitda * (1 + ebitda_cagr) ** year
            ebitda_schedule.append(ebitda)
        return ebitda_schedule
    
    def calculate_debt_schedule(self, entry_debt, interest_rate, available_cash_flow):
        """Calculate debt schedule including beginning debt, paydown, and ending debt."""
        debt_schedule = []
        current_debt = entry_debt
        
        for year in range(self.years + 1):
            if year == 0:
                debt_schedule.append({
                    'beginning_debt': entry_debt,
                    'interest_payment': 0,
                    'debt_paydown': 0,
                    'ending_debt': entry_debt
                })
                continue
                
            interest_payment = current_debt * interest_rate
            debt_paydown = min(available_cash_flow[year], current_debt)
            ending_debt = current_debt - debt_paydown
            
            debt_schedule.append({
                'beginning_debt': current_debt,
                'interest_payment': interest_payment,
                'debt_paydown': debt_paydown,
                'ending_debt': ending_debt
            })
            
            current_debt = ending_debt
            
        return pd.DataFrame(debt_schedule)
    
    def calculate_cash_flows(self, ebitda_schedule, debt_schedule, tax_rate, capex_pct):
        """Calculate available cash flows after interest, taxes, and capex."""
        cash_flows = []
        
        for year in range(self.years + 1):
            ebitda = ebitda_schedule[year]
            capex = ebitda * capex_pct
            
            if year == 0:
                cash_flows.append(0)
                continue
                
            interest = debt_schedule.iloc[year]['interest_payment']
            ebit = ebitda - capex
            taxes = max(0, (ebit - interest) * tax_rate)
            available_cash_flow = ebit - taxes - interest
            
            cash_flows.append(available_cash_flow)
            
        return cash_flows
    
    def calculate_irr(self, entry_equity, exit_equity, cash_flows):
        """Calculate IRR based on equity flows."""
        flows = [-entry_equity] + cash_flows[1:-1] + [exit_equity]
        return npf.irr(flows)
    
    def calculate_irr_decomposition(self, entry_ebitda, exit_ebitda, entry_multiple, 
                                  exit_multiple, levered_irr, unlevered_irr):
        """Calculate IRR decomposition components."""
        ebitda_growth = (exit_ebitda / entry_ebitda) ** (1/self.years) - 1
        multiple_change = (exit_multiple / entry_multiple) ** (1/self.years) - 1
        tev_growth = (1 + ebitda_growth) * (1 + multiple_change) - 1
        yield_component = 1 / entry_multiple
        covariance = unlevered_irr - (tev_growth + yield_component)
        leverage_impact = levered_irr - unlevered_irr
        
        return {
            'EBITDA Growth': ebitda_growth,
            'Multiple Change': multiple_change,
            'TEV Growth': tev_growth,
            'Yield': yield_component,
            'Covariance': covariance,
            'Unlevered IRR': unlevered_irr,
            'Leverage Impact': leverage_impact,
            'Levered IRR': levered_irr
        }

def main():
    st.title("LBO Model Calculator")
    
    # Input Section
    st.header("Input Assumptions")
    col1, col2 = st.columns(2)
    
    with col1:
        entry_ebitda = st.number_input("Entry EBITDA ($M)", value=100.0)
        ebitda_cagr = st.number_input("EBITDA CAGR (%)", value=10.0) / 100
        entry_tev = st.number_input("Entry TEV ($M)", value=1000.0)
        exit_multiple = st.number_input("Exit Multiple", value=10.0)
    
    with col2:
        entry_debt = st.number_input("Entry Debt ($M)", value=600.0)
        tax_rate = st.number_input("Tax Rate (%)", value=25.0) / 100
        interest_rate = st.number_input("Interest Rate (%)", value=5.0) / 100
        capex_pct = st.number_input("Capex as % of EBITDA (%)", value=10.0) / 100
    
    calculator = LBOCalculator()
    
    if st.button("Calculate IRR"):
        # Core calculations
        entry_multiple = entry_tev / entry_ebitda
        ebitda_schedule = calculator.calculate_ebitda_schedule(entry_ebitda, ebitda_cagr)
        
        # Calculate exit values
        exit_ebitda = ebitda_schedule[-1]
        exit_tev = exit_ebitda * exit_multiple
        
        # Calculate equity values
        entry_equity = entry_tev - entry_debt
        
        # Calculate cash flows and debt schedule
        initial_cash_flows = calculator.calculate_cash_flows(
            ebitda_schedule, 
            pd.DataFrame([{'interest_payment': 0}]), 
            tax_rate, 
            capex_pct
        )
        
        debt_schedule = calculator.calculate_debt_schedule(
            entry_debt, 
            interest_rate, 
            initial_cash_flows
        )
        
        cash_flows = calculator.calculate_cash_flows(
            ebitda_schedule,
            debt_schedule,
            tax_rate,
            capex_pct
        )
        
        # Exit equity calculation
        exit_equity = exit_tev - debt_schedule.iloc[-1]['ending_debt']
        
        # Calculate IRRs
        levered_irr = calculator.calculate_irr(entry_equity, exit_equity, cash_flows)
        
        # Calculate unlevered IRR (setting entry debt to 0)
        unlevered_entry_equity = entry_tev
        unlevered_exit_equity = exit_tev
        unlevered_cash_flows = calculator.calculate_cash_flows(
            ebitda_schedule,
            pd.DataFrame([{'interest_payment': 0}] * (calculator.years + 1)),
            tax_rate,
            capex_pct
        )
        unlevered_irr = calculator.calculate_irr(
            unlevered_entry_equity, 
            unlevered_exit_equity, 
            unlevered_cash_flows
        )
        
        # Display Results
        st.header("Results")
        
        # Financial Metrics
        st.subheader("Financial Metrics")
        metrics_df = pd.DataFrame({
            'Metric': ['Entry EBITDA', 'Exit EBITDA', 'Entry TEV', 'Exit TEV'],
            'Value ($M)': [entry_ebitda, exit_ebitda, entry_tev, exit_tev]
        })
        st.table(metrics_df)
        
        # Debt Schedule
        st.subheader("Debt Schedule")
        st.dataframe(debt_schedule)
        
        # IRR Results
        st.subheader("IRR Results")
        st.write(f"Levered IRR: {levered_irr:.1%}")
        st.write(f"Unlevered IRR: {unlevered_irr:.1%}")
        
        # IRR Decomposition
        st.subheader("IRR Decomposition")
        decomposition = calculator.calculate_irr_decomposition(
            entry_ebitda,
            exit_ebitda,
            entry_multiple,
            exit_multiple,
            levered_irr,
            unlevered_irr
        )
        
        decomposition_df = pd.DataFrame(
            list(decomposition.items()),
            columns=['Component', 'Value']
        )
        decomposition_df['Value'] = decomposition_df['Value'].apply(lambda x: f"{x:.1%}")
        st.table(decomposition_df)

if __name__ == "__main__":
    main()
